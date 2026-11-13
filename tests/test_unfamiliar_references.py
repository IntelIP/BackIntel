"""Small deterministic counterexamples for evaluator references; no models/raw download."""

from __future__ import annotations

import csv
import sys
from copy import deepcopy
from datetime import datetime, timedelta
from pathlib import Path

import polars as pl
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from build_unfamiliar_references import differences, save_comparison  # noqa: E402
from qualify_unfamiliar_data import domain_csv_files  # noqa: E402
from unfamiliar_fact_checks import check_bound_fact  # noqa: E402
from unfamiliar_python_references import calculate as python_calculate  # noqa: E402
from unfamiliar_sql_references import calculate as sql_calculate  # noqa: E402


@pytest.fixture
def raw(tmp_path):
    pickups = [
        datetime.fromisoformat(t)
        for t in [
            "2022-12-31T23:59:59",
            "2023-01-01",
            "2023-01-02",
            "2023-01-09",
            "2023-01-16",
            "2023-01-31",
            "2023-02-01",
        ]
    ]
    pl.DataFrame(
        {
            "lpep_pickup_datetime": pickups,
            "lpep_dropoff_datetime": [
                t + timedelta(seconds=s)
                for t, s in zip(pickups, [60, 60, 120, 10800, -1, 10801, 60], strict=True)
            ],
            "payment_type": [1.0, 1.0, None, 1.0, 1.0, 2.0, 1.0],
            "total_amount": [100.0, 10.0, -2.0, 20.0, 5.0, 0.0, 100.0],
            "PULocationID": [1, 1, 2, 1, 99, 3, 1],
        }
    ).write_parquet(tmp_path / "green_tripdata_2023-01.parquet")
    (tmp_path / "taxi_zone_lookup.csv").write_text(
        "LocationID,Borough,Zone,service_zone\n1,Manhattan,A,B\n2,Unknown,X,Y\n3,N/A,Q,R\n"
    )
    with (tmp_path / "household_power_consumption.txt").open("w", newline="") as handle:
        writer = csv.writer(handle, delimiter=";")
        writer.writerow(
            ["Date", "Time", "Global_active_power", "Sub_metering_1", "Sub_metering_2", "Sub_metering_3"]
        )
        # Include exact 95%, one minute below, missing readings, zero power and negative residuals.
        for day, numeric_count, power in [(1, 1368, 60), (2, 1367, 120), (3, 1439, 30), (8, 60, 0)]:
            for minute in range(1440):
                stamp = datetime(2007, 1, day) + timedelta(minutes=minute)
                numeric = minute < numeric_count
                writer.writerow(
                    [
                        stamp.strftime("%d/%m/%Y"),
                        stamp.strftime("%H:%M:%S"),
                        power if numeric else "?",
                        1 if numeric else "?",
                        2 if numeric else "?",
                        3 if numeric else "",
                    ]
                )
        writer.writerow(["01/02/2007", "00:00:00", 999, 1, 2, 3])
        writer.writerow(["31/12/2006", "23:59:00", 999, 1, 2, 3])
    return tmp_path


def test_independent_paths_cover_windows_signed_amounts_quantiles_units_and_unknowns(raw):
    first, second = python_calculate(raw), sql_calculate(raw)
    assert not differences(first, second)
    assert first["transport-01"] == {"eligible_rows": 5, "excluded_rows": 2}
    assert first["transport-02"]["total_usd"] == 33.0
    assert first["transport-02"]["by_payment"][-1] == {"payment_type": "unknown", "total_usd": -2.0}
    assert first["transport-03"]["joined_rows"] == 5
    assert first["transport-03"]["unmatched_rows"] == 1
    assert first["transport-03"]["unknown_borough_rows"] == 2
    assert first["transport-04"] == {
        "eligible_rows": 3,
        "excluded_rows": 2,
        "median_minutes": 2.0,
        "p95_minutes": pytest.approx(162.2),
    }
    assert first["transport-05"] == {
        "first_count": 1,
        "second_count": 1,
        "absolute_change": 0,
        "relative_change": 0,
    }
    assert first["energy-01"] == {
        "eligible_minute_slots": 44640,
        "rows_present": 5760,
        "observed_minutes": 4234,
        "missing_minutes": 40406,
    }
    assert first["energy-02"]["observed_kwh"] == 4821.5
    assert first["energy-03"]["global_wh"] == 4821500.0
    assert first["energy-03"]["residual_wh"] == 4821500.0 - 4234 * 6
    assert [day["date"] for day in first["energy-04"]["days"]] == ["2007-01-01", "2007-01-03"]
    assert first["energy-04"]["days"][0]["coverage_fraction"] == pytest.approx(0.95)
    assert first["energy-05"]["second_observed_minutes"] == 60
    assert first["energy-05"]["second_mean_kw"] == 0.0
    assert first["energy-05"]["absolute_change_kw"] < 0
    assert first["transport-06"]["status"] == first["energy-06"]["status"] == "cannot_answer"


@pytest.mark.parametrize("calculator", [python_calculate, sql_calculate])
def test_duplicate_lookup_cannot_multiply_reference_rows(raw, calculator):
    with (raw / "taxi_zone_lookup.csv").open("a") as handle:
        handle.write("1,Manhattan,Duplicate,B\n")
    with pytest.raises((ValueError, AssertionError)):
        calculator(raw)


def test_comparator_exact_counts_finite_numbers_and_discrepancy_retention(tmp_path):
    assert differences(2, 2.0)
    assert differences(1.0, True)
    assert differences(float("nan"), float("nan"))
    assert differences(100.0, 100.1)
    assert not differences(100.0, 100.0000001)
    first, second = {"case": {"count": 2}}, {"case": {"count": 3}}
    receipt = save_comparison(tmp_path / "failed", first, second, inputs={"fixture": True})
    assert receipt["difference_count"] == 1
    assert (tmp_path / "failed/python.json").exists()
    assert (tmp_path / "failed/sql.json").exists()
    assert (tmp_path / "failed/discrepancies.json").exists()


def test_unverified_matching_weather_csv_does_not_enter_profile(tmp_path):
    raw = tmp_path / "raw"
    raw.mkdir()
    (raw / "gsod_2023_verified.csv").write_text("verified source")
    (raw / "gsod_2023_decoy.csv").write_text("unverified; not an input")
    manifest = {
        "assets": [{"file": "gsod_2023_verified.csv"}],
        "domains": [{"id": "weather", "assets": ["gsod_2023_verified.csv"]}],
    }
    assert domain_csv_files(tmp_path, manifest, "weather") == [raw / "gsod_2023_verified.csv"]
    manifest["domains"][0]["assets"].append("gsod_2023_decoy.csv")
    with pytest.raises(ValueError, match="unverified"):
        domain_csv_files(tmp_path, manifest, "weather")


@pytest.fixture
def bound_fact():
    report = {
        "run_id": "fixture",
        "title": "Report",
        "summary": "Descriptive observed total.",
        "sources": [{"id": "source", "snapshot": "sha256:fixture", "description": "Test"}],
        "evidence": [{"id": "e", "kind": "sql", "code": "select 33 as total", "source_ids": ["source"]}],
        "tables": [
            {
                "id": "amount",
                "title": "Signed recorded total",
                "columns": ["total"],
                "rows": [[33.0]],
                "units": {"total": "USD"},
                "evidence_ids": ["e"],
            }
        ],
        "metrics": [
            {
                "id": "total",
                "label": "Recorded total",
                "definition": "January signed total",
                "table": "amount",
                "row": 0,
                "column": "total",
            }
        ],
    }
    scope = {
        "metric": "signed recorded total",
        "population": "all pickups in window",
        "window": "[2023-01-01,2023-02-01)",
        "grain": "trip",
    }
    args = {
        "table_id": "amount",
        "row": 0,
        "column": "total",
        "expected_value": 33.0,
        "expected_unit": "USD",
        "expected_scope": scope,
        "interpreted_scope": deepcopy(scope),
        "reproduction": {"tables_reproduced": ["amount"], "executed_evidence": ["e"]},
    }
    return report, args


def test_equivalent_presentation_can_bind_a_supported_fact(bound_fact):
    report, args = bound_fact
    report["title"] = "A different reasonable presentation"
    result = check_bound_fact(report, **args)
    assert result == {
        "bound_fact_supported": True,
        "narrative_assessed": False,
        "business_usefulness_assessed": False,
    }


@pytest.mark.parametrize("change", ["value", "unit", "population", "label", "window", "evidence", "binding"])
def test_wrong_fact_interpretation_or_broken_evidence_fails(bound_fact, change):
    report, args = bound_fact
    if change == "value":
        report["tables"][0]["rows"][0][0] = 44
    elif change == "unit":
        report["tables"][0]["units"]["total"] = "EUR"
    elif change == "population":
        args["interpreted_scope"]["population"] = "positive amounts only"
    elif change == "label":
        args["interpreted_scope"]["metric"] = "driver profit"
    elif change == "window":
        args["interpreted_scope"]["window"] = "all source dates"
    elif change == "evidence":
        args["reproduction"]["executed_evidence"] = []
    else:
        report["metrics"][0]["column"] = "absent"
    with pytest.raises(ValueError):
        check_bound_fact(report, **args)
