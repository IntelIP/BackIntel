"""Controlled grader challenges, not model benchmarks or human calibration.

Each evidence check executes against a temporary real SQLite database. The only Python
program is a trusted failing test fixture; its subprocess runner is not an isolation claim.
"""

import sqlite3

import pytest

from backintel.bench.scoring import abstention_correct, evidence_reproduces, score_correct
from backintel.contracts import AnalystAnswer, Evidence, Scenario, Tolerance
from backintel.sandbox import PythonSandbox
from backintel.stores.sqlite import SQLiteStore

UK_TOTAL = "SELECT SUM(amount) AS total FROM sales WHERE country = 'UK'"
REPORT_TOTALS = """SELECT CASE country WHEN 'UK' THEN 'uk_sales' ELSE 'france_sales' END AS metric,
SUM(amount) AS value FROM sales GROUP BY country"""
REPORT_ROWS = [
    {"metric": "uk_sales", "value": 15.5, "unit": "GBP"},
    {"metric": "france_sales", "value": 7.25, "unit": "GBP"},
]


@pytest.fixture
def store(tmp_path):
    path = tmp_path / "controlled-grader-challenges.sqlite"
    with sqlite3.connect(path) as connection:
        connection.execute("CREATE TABLE sales (country TEXT, amount REAL)")
        connection.executemany(
            "INSERT INTO sales VALUES (?, ?)", [("UK", 10.0), ("UK", 5.5), ("France", 7.25)]
        )
    bound = SQLiteStore(path, dataset="controlled_grader_challenges")
    yield bound
    bound.close()


def question(*, report=False):
    return Scenario(
        id="controlled-report" if report else "controlled-scalar",
        dataset="controlled_grader_challenges",
        level=5 if report else 1,
        question="Report the UK and France sales totals." if report else "What are total UK sales?",
        answer_type="report" if report else "number",
        expected=[{"name": row["metric"], "value": row["value"], "abs": 0} for row in REPORT_ROWS]
        if report
        else 15.5,
        tolerance=Tolerance(abs=0),
    )


def response(*, code=UK_TOTAL, value=15.5, rows=None):
    return AnalystAnswer(
        status="answered",
        answer_type="report" if rows is not None else "number",
        value=None if rows is not None else value,
        rows=rows,
        method="Sum sales at the country grain.",
        evidence=[Evidence(kind="sql", code=code)],
    )


def reproduced(store, answer, *, report=False):
    return evidence_reproduces(question(report=report), answer, store, PythonSandbox("subprocess"))["score"]


@pytest.mark.parametrize(
    "code",
    [
        UK_TOTAL,
        "WITH uk AS (SELECT amount FROM sales WHERE country = 'UK') SELECT SUM(amount) FROM uk",
        "SELECT SUM(CASE WHEN country = 'UK' THEN amount ELSE 0 END) FROM sales",
    ],
)
def test_valid_sql_alternatives_get_the_same_grade(store, code):
    answer = response(code=code)
    assert score_correct(question(), answer)["correct"] == 1
    assert reproduced(store, answer) == 1


@pytest.mark.parametrize(
    ("code", "value", "correct", "replay"),
    [
        ("SELECT SUM(amount) FROM sales", 22.75, 0, 1),
        ("SELECT SUM(amount) FROM sales WHERE country = 'France'", 15.5, 1, 0),
    ],
)
def test_correctness_and_evidence_are_independent_requirements(store, code, value, correct, replay):
    answer = response(code=code, value=value)
    assert score_correct(question(), answer)["correct"] == correct
    assert reproduced(store, answer) == replay


@pytest.mark.parametrize(
    "broken",
    [
        Evidence(kind="sql", code="SELECT missing_amount FROM sales"),
        Evidence(kind="python", code="raise RuntimeError('Controlled broken evidence')"),
    ],
)
def test_one_successful_item_does_not_hide_broken_second_evidence(store, broken):
    answer = response()
    answer.evidence.append(broken)
    assert score_correct(question(), answer)["correct"] == 1
    assert reproduced(store, answer) == 0


def test_inappropriate_refusal_fails_despite_not_applicable_evidence(store):
    answer = AnalystAnswer(status="cannot_answer", method="No calculation", reason="Amounts unavailable")
    assert score_correct(question(), answer)["correct"] == 0
    assert abstention_correct(question(), answer)["score"] == 0
    assert reproduced(store, answer) is None


def test_report_row_order_does_not_change_grade(store):
    answer = response(code=REPORT_TOTALS, rows=list(reversed(REPORT_ROWS)))
    assert score_correct(question(report=True), answer)["correct"] == 1
    assert reproduced(store, answer, report=True) == 1


@pytest.mark.parametrize(
    "extra",
    [
        {"metric": "uk_sales", "value": 15.5, "unit": "GBP"},
        {"metric": " UK_SALES ", "value": 7.25, "unit": "GBP"},
        {"metric": "invented_total", "value": 15.5, "unit": "GBP"},
    ],
)
def test_report_duplicate_or_unrequested_metric_is_not_fully_correct(store, extra):
    answer = response(code=REPORT_TOTALS, rows=[*REPORT_ROWS, extra])
    score = score_correct(question(report=True), answer)
    assert score["correct"] == 0
    assert score["partial"] == 1  # Requested facts present does not make the whole report correct.
    assert reproduced(store, answer, report=True) == (0 if extra["value"] == 7.25 else 1)


def test_report_evidence_must_associate_each_value_with_its_metric(store):
    swapped = """SELECT CASE country WHEN 'UK' THEN 'france_sales' ELSE 'uk_sales' END AS metric,
    SUM(amount) AS value FROM sales GROUP BY country"""
    assert store.query(swapped).rows == [["uk_sales", 7.25], ["france_sales", 15.5]]
    answer = response(code=swapped, rows=REPORT_ROWS)
    assert score_correct(question(report=True), answer)["correct"] == 1
    assert reproduced(store, answer, report=True) == 0


@pytest.mark.parametrize("swapped", [False, True])
def test_wide_named_columns_preserve_metric_value_binding(store, swapped):
    query = """SELECT
    SUM(CASE WHEN country = 'UK' THEN amount ELSE 0 END) AS uk_sales,
    SUM(CASE WHEN country = 'France' THEN amount ELSE 0 END) AS france_sales FROM sales"""
    if swapped:
        query = query.replace("'UK'", "'TEMP'").replace("'France'", "'UK'").replace("'TEMP'", "'France'")
    answer = response(code=query, rows=REPORT_ROWS)
    assert reproduced(store, answer, report=True) == float(not swapped)


def test_unlabeled_equivalent_report_calculations_are_still_valid(store):
    answer = response(
        code="SELECT SUM(amount) FROM sales GROUP BY country",
        rows=REPORT_ROWS,
    )
    assert reproduced(store, answer, report=True) == 1


def test_other_citations_cannot_rescue_an_explicit_contradiction(store):
    answer = response(code=REPORT_TOTALS, rows=REPORT_ROWS)
    answer.evidence.append(
        Evidence(kind="sql", code="SELECT SUM(amount) AS uk_sales FROM sales WHERE country='France'")
    )
    assert reproduced(store, answer, report=True) == 0


@pytest.mark.parametrize("shape", ["wide", "long", "json_lines"])
@pytest.mark.parametrize("swapped", [False, True])
def test_python_json_report_output_preserves_metric_value_binding(store, shape, swapped):
    query = REPORT_TOTALS
    if swapped:
        query = query.replace("'uk_sales'", "'TEMP'").replace("'france_sales'", "'uk_sales'")
        query = query.replace("'TEMP'", "'france_sales'")
    code = f"""import json, os, sqlite3
path = os.environ['BACKINTEL_SQLITE_PATH']
with sqlite3.connect(f'file:{{path}}?mode=ro', uri=True) as connection:
    rows = connection.execute({query!r}).fetchall()
if {shape!r} == 'wide':
    print(json.dumps(dict(rows)))
elif {shape!r} == 'long':
    print(json.dumps([dict(metric=metric, value=value) for metric, value in rows]))
else:
    for metric, value in rows:
        print(json.dumps(dict(metric=metric, value=value)))
"""
    answer = response(rows=REPORT_ROWS)
    answer.evidence = [Evidence(kind="python", code=code)]
    assert reproduced(store, answer, report=True) == float(not swapped)


@pytest.mark.parametrize("shape", ["sql", "json_list", "json_lines"])
def test_grouped_dimensional_output_does_not_bind_every_row_to_one_report_metric(store, shape):
    query = "SELECT country, SUM(amount) AS total_revenue FROM sales GROUP BY country"
    scenario = question(report=True).model_copy(
        update={
            "question": "Report total_revenue for the UK in GBP.",
            "expected": [{"name": "total_revenue", "value": 15.5, "abs": 0}],
        }
    )
    answer = response(code=query, rows=[{"metric": "total_revenue", "value": 15.5, "unit": "GBP"}])
    answer.method = "Read the UK row of sales grouped by country; France is a separate population."
    if shape != "sql":
        code = f"""import json, os, sqlite3
path = os.environ['BACKINTEL_SQLITE_PATH']
with sqlite3.connect(f'file:{{path}}?mode=ro', uri=True) as connection:
    rows = [dict(country=country, total_revenue=total) for country, total in
            connection.execute({query!r}).fetchall()]
if {shape!r} == 'json_list':
    print(json.dumps(rows))
else:
    for row in rows:
        print(json.dumps(row))
"""
        answer.evidence = [Evidence(kind="python", code=code)]
    assert score_correct(scenario, answer)["correct"] == 1
    grade = evidence_reproduces(scenario, answer, store, PythonSandbox("subprocess"))
    assert grade["score"] == 1
    assert "bindings checked for 0/1 report rows" in grade["comment"]
