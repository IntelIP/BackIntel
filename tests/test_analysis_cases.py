"""Task correctness controls, independent of model calls or Docker availability."""

import copy
import json

import pytest

from backintel.artifacts import validate_report
from scripts.analysis_cases import (
    CASE_IDS,
    build_cases,
    reference_queries,
    scripted_spec,
    verify_case_completion,
    verify_case_report,
)


@pytest.fixture
def cases(tmp_path):
    return {case.case_id: case for case in build_cases(tmp_path / "cases")}


def test_frozen_cases_are_reproducible_and_keep_references_out_of_runtime(tmp_path):
    first, second = (build_cases(tmp_path / name) for name in ("first", "second"))
    assert tuple(case.case_id for case in first) == CASE_IDS
    assert len({case.source_sha256 for case in first}) == 3
    assert json.loads((tmp_path / "first" / "manifest.json").read_text()) == json.loads(
        (tmp_path / "second" / "manifest.json").read_text()
    )
    for case, repeat in zip(first, second, strict=True):
        assert case.source_sha256 == repeat.source_sha256
        assert case.reference_sha256 == repeat.reference_sha256
        assert case.reference.parent.name == "private-references"
        assert case.reference.stat().st_mode & 0o777 == 0o600
        assert "private-references" not in case.brief.model_dump_json()
        assert "SELECT " not in case.brief.model_dump_json()
        store = case.open_store()
        try:
            assert store.python_mounts() == {str(case.source): str(case.source)}
            assert str(case.reference) not in store.python_environment().values()
        finally:
            store.close()


@pytest.mark.parametrize("case_id", [case for case in CASE_IDS if case != "missing-cost"])
def test_executable_reference_solutions_match_raw_source_oracles(cases, case_id):
    case = cases[case_id]
    spec = scripted_spec(case)
    verify_case_report(case, validate_report(spec))
    verify_case_completion(case, {"status": "completed"}, spec)
    assert {table["id"] for table in spec["tables"]} == set(reference_queries(case_id))
    # The declaration describes the integration honestly; it is not a model success record.
    assert "does not measure model reasoning" in spec["summary"]


def test_equivalent_ordering_and_numeric_roundoff_are_accepted(cases):
    case = cases["irregular-energy"]
    spec = scripted_spec(case)
    for table in spec["tables"]:
        table["columns"].reverse()
        table["rows"] = [list(reversed(row)) for row in reversed(table["rows"])]
    spec["tables"].reverse()
    total = next(table for table in spec["tables"] if table["id"] == "energy_total")
    energy_index = total["columns"].index("Energy")
    total["rows"][0][energy_index] += 1e-10
    verify_case_report(case, validate_report(spec))


def test_alternate_minute_grid_calculation_is_accepted(cases):
    """Fixture endpoints are whole minutes, so an explicit minute grid is also exact.

    The shipped solution integrates LEAD intervals. This independently written query
    samples the active observation at each minute and groups those valid minutes.
    """
    case = cases["irregular-energy"]
    query = """
    WITH RECURSIVE minute(n) AS (SELECT 0 UNION ALL SELECT n+1 FROM minute WHERE n<59),
    grid AS (
      SELECT meter_id, window_start_utc,
             CAST(strftime('%s',window_start_utc) AS INTEGER)+60*n AS instant
      FROM meters CROSS JOIN windows CROSS JOIN minute
    ), samples AS (
      SELECT g.*, r.power, r.unit, r.quality,
             CAST(strftime('%s',r.observed_at) AS INTEGER) AS observed
      FROM grid g LEFT JOIN readings r ON r.meter_id=g.meter_id
      AND CAST(strftime('%s',r.observed_at) AS INTEGER)=(
        SELECT MAX(CAST(strftime('%s',prior.observed_at) AS INTEGER))
        FROM readings prior WHERE prior.meter_id=g.meter_id
          AND CAST(strftime('%s',prior.observed_at) AS INTEGER)<=g.instant
      )
    ), valid AS (
      SELECT *, quality='good' AND power IS NOT NULL AND instant-observed<900 AS usable
      FROM samples
    )
    SELECT meter_id AS Meter,window_start_utc AS WindowStart,
           SUM(CASE WHEN usable THEN power*CASE unit WHEN 'kW' THEN 1000 ELSE 1 END/60000 END)
             AS Energy,
           SUM(CASE WHEN usable THEN 1 ELSE 0 END) AS CoveredMinutes,
           SUM(CASE WHEN usable THEN 1 ELSE 0 END)*100.0/60 AS CoveragePercent
    FROM valid GROUP BY meter_id,window_start_utc ORDER BY window_start_utc DESC,meter_id DESC
    """
    store = case.open_store()
    try:
        result = store.query(query)
    finally:
        store.close()
    spec = scripted_spec(case)
    hourly, total = spec["tables"]
    hourly.update(columns=result.columns, rows=result.rows)
    energy = sum(row[2] for row in result.rows if row[2] is not None)
    minutes = sum(row[3] for row in result.rows)
    total["rows"] = [[energy, minutes, 540, 100 * minutes / 540]]
    assert energy == pytest.approx(2.1791666666666667)
    assert minutes == 127
    verify_case_report(case, validate_report(spec))


def test_plausible_wrong_business_calculations_fail_despite_valid_artifact_shape(cases):
    # Joining raw refund and duplicate-line rows inflates delivered net revenue.
    case = cases["sales-refunds"]
    store = case.open_store()
    try:
        naive = store.query("""
            SELECT SUM((l.quantity-COALESCE(r.quantity,0))*l.unit_cents)/100.0 AS Revenue
            FROM lines l JOIN orders o ON o.order_id=l.order_id
            LEFT JOIN refunds r ON r.line_id=l.line_id WHERE o.status='delivered'
        """)
    finally:
        store.close()
    spec = scripted_spec(case)
    next(t for t in spec["tables"] if t["id"] == "total")["rows"] = naive.rows
    assert naive.rows == [[190.0]]
    with pytest.raises(ValueError, match="independent raw-source reference"):
        verify_case_report(case, validate_report(spec))

    # Missing coverage cannot be silently rendered as measured zero consumption.
    case = cases["irregular-energy"]
    spec = scripted_spec(case)
    for row in spec["tables"][0]["rows"]:
        if row[2] is None:
            row[2] = 0.0
    with pytest.raises(ValueError, match="independent raw-source reference"):
        verify_case_report(case, validate_report(spec))

    # Mean service percentages ignores unequal eligible exposure and customer weights.
    case = cases["service-availability"]
    spec = scripted_spec(case)
    services, fleet = spec["tables"]
    percentages = [row[3] for row in services["rows"] if row[3] is not None]
    fleet["rows"][0][2] = sum(percentages) / len(percentages)
    with pytest.raises(ValueError, match="independent raw-source reference"):
        verify_case_report(case, validate_report(spec))


def test_units_population_and_chart_binding_are_required(cases):
    case = cases["service-availability"]
    correct = scripted_spec(case)
    mutations = []
    wrong_units = copy.deepcopy(correct)
    wrong_units["tables"][0]["units"]["DowntimeMinutes"] = "hours"
    mutations.append(wrong_units)
    missing_empty_service = copy.deepcopy(correct)
    missing_empty_service["tables"][0]["rows"] = [
        row for row in missing_empty_service["tables"][0]["rows"] if row[0] != "chat"
    ]
    mutations.append(missing_empty_service)
    wrong_chart = copy.deepcopy(correct)
    wrong_chart["charts"][0]["y"] = "EligibleMinutes"
    mutations.append(wrong_chart)
    for report in mutations:
        with pytest.raises(ValueError):
            verify_case_report(case, report)


def test_missing_cost_requires_explanatory_refusal_without_substitute_report(cases):
    case = cases["missing-cost"]
    completion = {
        "status": "cannot_answer",
        "reason": "Product costs are missing; they are required for profit.",
    }
    verify_case_completion(case, completion)
    assert reference_queries(case.case_id) == {}
    for invalid in (
        {"status": "completed", "reason": "Profit is revenue."},
        {"status": "cannot_answer", "reason": "I cannot answer."},
        {"status": "cannot_answer", "reason": "Costs are present."},
        {"status": "cannot_answer", "reason": "Costs are not missing."},
        {"status": "cannot_answer", "reason": "There is no cost issue."},
        {"status": "cannot_answer", "reason": "There is no issue with costs."},
        {"status": "cannot_answer", "reason": "Costs are missing. Costs are present."},
        {"status": "cannot_answer", "reason": "Costs aren't unavailable."},
        {"status": "cannot_answer", "reason": "It is not true that costs are missing."},
        {"status": "cannot_answer", "reason": "Costs are required to calculate profit."},
    ):
        with pytest.raises(ValueError):
            verify_case_completion(case, invalid)
    with pytest.raises(ValueError, match="substitute"):
        verify_case_completion(case, completion, scripted_spec(cases["sales-refunds"]))


@pytest.mark.parametrize(
    "reason",
    [
        "Product costs and operating expenses are unavailable.",
        "The source lacks product costs and expense data.",
        "No cost data is supplied.",
        "Missing product cost inputs prevent calculating profit.",
        "Costs are not provided in this source.",
        "Required profit inputs are absent: cost of goods sold and applicable expenses.",
    ],
)
def test_explicit_missing_cost_statements_are_accepted(cases, reason):
    verify_case_completion(cases["missing-cost"], {"status": "cannot_answer", "reason": reason})


@pytest.mark.parametrize("metric_id", ["arbitrary", "revenue", None])
def test_correct_cell_with_wrong_metric_identity_is_rejected(cases, metric_id):
    case = cases["irregular-energy"]
    report = scripted_spec(case)
    report["metrics"][0]["id"] = metric_id
    with pytest.raises(ValueError, match="summary metric"):
        verify_case_report(case, report)


@pytest.mark.parametrize("target", ["source", "reference"])
def test_changed_inputs_invalidate_refusal_and_success(cases, target):
    case = cases["sales-refunds"]
    report = scripted_spec(case)
    path = getattr(case, target)
    path.chmod(0o600)
    path.write_bytes(path.read_bytes() + b" ")
    with pytest.raises(ValueError, match="changed after case preparation"):
        verify_case_report(case, report)
    if target == "source":
        with pytest.raises(ValueError, match="changed after case preparation"):
            verify_case_completion(
                cases["missing-cost"], {"status": "cannot_answer", "reason": "Costs are absent."}
            )
