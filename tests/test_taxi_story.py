"""Presentation regressions use invented aggregates, not benchmark reference answers."""

import copy
import io
import json
from pathlib import Path

import pytest
from openpyxl import load_workbook

pytest.importorskip("streamlit")
pytest.importorskip("plotly")

from backintel.presentation.taxi_story import (  # noqa: E402
    DAYS,
    FARE_BANDS,
    MONTHS,
    QUALITY_LABELS,
    airport_chart,
    business_workbook,
    fare_chart,
    monthly_chart,
    prepare_story,
    summary,
    validate_story,
    zone_chart,
)


@pytest.fixture
def report():
    tables = {
        "monthly": (
            ["Month", "Trips", "Gross_fare_USD", "Trips_per_day", "Mean_fare_USD"],
            [[date, 100, 1000, rate, 10] for date, rate in zip(MONTHS, [100, 110, 120], strict=True)],
        ),
        "weekly_hours": (
            ["Weekday", "Hour", "Trips_per_occurrence"],
            [[day, f"{hour:02d}", hour + 1] for day in DAYS for hour in range(24)],
        ),
        # Deliberately reverse airport order and use misleading rounded shares: the
        # headline must calculate from counts and the full quarterly denominator.
        "zones": (
            ["Pickup_zone", "Trips", "Gross_fare_USD", "Trip_share_pct", "Fare_share_pct"],
            [
                ["LaGuardia Airport", 6, 300, 2, 10],
                ["JFK Airport", 9, 600, 3, 20],
                ["=Untrusted label", 10, 10, 90, 90],
                *[[f"Zone {i}", 1, 10, 0.1, 0.1] for i in range(7)],
            ],
        ),
        "fare_bands": (["Fare_band", "Trip_share_pct"], [[band, 20] for band in FARE_BANDS]),
        "segments": (
            ["Month", "Pickup_segment", "Trip_share_pct", "Fare_share_pct"],
            [
                [date[:7], area, index + 1, index + 4]
                for index, date in enumerate(MONTHS)
                for area in ["JFK", "LaGuardia"]
            ],
        ),
        "quality": (["Population", "Records"], [[name, 1000 - i] for i, name in enumerate(QUALITY_LABELS)]),
    }
    return {
        "run_id": "private-run-marker",
        "sources": [{"sha256": "private-hash-marker"}],
        "tables": [
            {"id": name, "columns": columns, "rows": rows, "evidence": "private-query-marker"}
            for name, (columns, rows) in tables.items()
        ],
    }


def test_projection_and_business_workbook_keep_values_without_execution_metadata(report):
    story = prepare_story(report)
    serialized = json.dumps(story)
    assert "private-" not in serialized
    assert summary(story)["airport_trip_share"] == 5
    assert summary(story)["airport_fare_share"] == 30
    assert list(airport_chart(story).data[0].x) == [3, 2]
    book = load_workbook(io.BytesIO(business_workbook(story)))
    assert book.sheetnames == [
        "Monthly overview",
        "Hourly patterns",
        "Pickup zones",
        "Fare distribution",
        "Airport mix",
        "Data coverage",
        "Definitions",
    ]
    assert book["Monthly overview"]["C1"].value == "Metered fares ($)"
    assert book["Monthly overview"]["C2"].value == 1000
    assert book["Pickup zones"]["A4"].value == "=Untrusted label"
    assert book["Pickup zones"]["A4"].data_type == "s"
    assert not any("private-" in str(cell.value) for sheet in book for row in sheet for cell in row)


def test_incomplete_comparisons_are_rejected_before_presentation(report):
    story = prepare_story(report)
    story["tables"]["weekly_hours"]["rows"].pop()
    with pytest.raises(ValueError, match="coverage"):
        validate_story(story)
    story = prepare_story(report)
    story["tables"]["segments"]["rows"].pop()
    with pytest.raises(ValueError, match="coverage"):
        validate_story(story)
    story = prepare_story(report)
    story["tables"]["monthly"]["rows"][0][3] = float("nan")
    with pytest.raises(ValueError, match="Non-finite"):
        validate_story(story)
    wrong_period = copy.deepcopy(report)
    wrong_period["tables"][0]["rows"][0][0] = "2024-01-01"
    with pytest.raises(ValueError, match="January"):
        prepare_story(wrong_period)


def test_streamlit_month_control_updates_the_scoped_view(report, tmp_path, monkeypatch):
    from streamlit.testing.v1 import AppTest

    data = tmp_path / "story.json"
    data.write_text(json.dumps(prepare_story(report)))
    monkeypatch.setenv("BACKINTEL_STORY_DATA", str(data))
    app = AppTest.from_file(str(Path(__file__).parents[1] / "dashboards/taxi/streamlit_app.py")).run()
    assert not app.exception
    assert app.metric[3].label == "March trips per day"
    assert app.metric[3].value == "120"
    before = json.loads(app.get("plotly_chart")[-1].proto.spec)
    app.selectbox(key="month").select("January").run()
    assert not app.exception
    assert app.metric[3].label == "January trips per day"
    assert app.metric[3].value == "100"
    after = json.loads(app.get("plotly_chart")[-1].proto.spec)
    assert before["data"][0]["x"] != after["data"][0]["x"]
    assert app.metric[0].value == "0.00m"  # Quarterly summary does not change with the local filter.


@pytest.mark.parametrize("contents", [None, "{broken", '{"tables": {}}'])
def test_streamlit_missing_or_invalid_data_has_a_readable_state(contents, tmp_path, monkeypatch):
    from streamlit.testing.v1 import AppTest

    data = tmp_path / "story.json"
    if contents is not None:
        data.write_text(contents)
    monkeypatch.setenv("BACKINTEL_STORY_DATA", str(data))
    app = AppTest.from_file(str(Path(__file__).parents[1] / "dashboards/taxi/streamlit_app.py")).run()
    assert not app.exception
    assert app.info if contents is None else app.error
    assert not app.get("plotly_chart")


@pytest.mark.parametrize("month", [None, next(iter(MONTHS))[:7]])
def test_airport_axis_contains_both_series_with_label_space(report, month):
    story = prepare_story(report)
    chart = airport_chart(story, month)
    assert chart.layout.xaxis.range[0] == 0
    assert chart.layout.xaxis.range[1] > max(v for trace in chart.data for v in trace.x)
    assert chart.layout.xaxis.ticksuffix == "%"
    if month is None:
        assert list(chart.data[1].x) == [20, 10]


@pytest.mark.parametrize("count", [3, 9, 11])
def test_zone_ranking_requires_exactly_ten_unique_areas(report, count):
    table = next(t for t in report["tables"] if t["id"] == "zones")
    table["rows"] = table["rows"][:count] + ([["Extra zone", 1, 1, 1, 1]] if count == 11 else [])
    with pytest.raises(ValueError, match="exactly ten"):
        prepare_story(report)


@pytest.mark.parametrize(
    "table,column,bad",
    [
        ("monthly", "Gross_fare_USD", "not a number"),
        ("monthly", "Trips", True),
        ("monthly", "Mean_fare_USD", None),
        ("weekly_hours", "Trips_per_occurrence", "12"),
        ("zones", "Gross_fare_USD", "12"),
        ("fare_bands", "Trip_share_pct", "12"),
        ("segments", "Fare_share_pct", "12"),
        ("quality", "Records", "12"),
    ],
)
def test_numeric_columns_reject_untyped_values_before_publication(report, table, column, bad):
    source = next(t for t in report["tables"] if t["id"] == table)
    source["rows"][0][source["columns"].index(column)] = bad
    with pytest.raises(ValueError, match="Nonnumeric"):
        prepare_story(report)


def test_invalid_numeric_story_shows_readable_error(report, tmp_path, monkeypatch):
    from streamlit.testing.v1 import AppTest

    story = prepare_story(report)
    story["tables"]["monthly"]["rows"][0][2] = "not a number"
    path = tmp_path / "story.json"
    path.write_text(json.dumps(story))
    monkeypatch.setenv("BACKINTEL_STORY_DATA", str(path))
    app = AppTest.from_file(str(Path(__file__).parents[1] / "dashboards/taxi/streamlit_app.py")).run()
    assert not app.exception and app.error
    assert not app.get("plotly_chart")


@pytest.mark.parametrize("column", ["Trips", "Gross_fare_USD"])
def test_zero_quarter_totals_are_rejected_before_percentage_division(report, column):
    table = next(t for t in report["tables"] if t["id"] == "monthly")
    for row in table["rows"]:
        row[table["columns"].index(column)] = 0
    with pytest.raises(ValueError, match="totals must be positive"):
        prepare_story(report)


def test_quality_labels_preserve_source_counts_across_row_and_column_order(report):
    table = next(t for t in report["tables"] if t["id"] == "quality")
    table["columns"] = ["Records", "Population"]
    table["rows"] = [[row[1], row[0]] for row in reversed(table["rows"])]
    quality = prepare_story(report)["tables"]["quality"]
    assert quality["rows"] == [[1000 - i, name] for i, name in enumerate(QUALITY_LABELS.values())]


@pytest.mark.parametrize("bad", ["unknown", "duplicate"])
def test_unknown_or_duplicate_quality_labels_are_rejected(report, bad):
    table = next(t for t in report["tables"] if t["id"] == "quality")
    table["rows"][0][0] = "Unrecognized population" if bad == "unknown" else table["rows"][1][0]
    with pytest.raises(ValueError, match="coverage population"):
        prepare_story(report)


def test_taxi_axes_fit_retained_values_above_old_ceilings(report):
    story = prepare_story(report)
    story["tables"]["zones"]["rows"][0][2] = 45_000_000
    story["tables"]["monthly"]["rows"][0][3] = 200_000
    story["tables"]["fare_bands"]["rows"][0][1] = 70
    for chart, axis, values in [
        (zone_chart(story), "xaxis", "x"),
        (monthly_chart(story), "yaxis", "y"),
        (fare_chart(story), "xaxis", "x"),
    ]:
        assert chart.layout[axis].range[0] == 0
        assert chart.layout[axis].range[1] > max(chart.data[0][values])


@pytest.mark.parametrize(
    "table,column,value",
    [
        ("monthly", "Trips", 1.5),
        ("quality", "Records", -1),
        ("zones", "Trip_share_pct", 101),
        ("segments", "Fare_share_pct", -0.5),
        ("fare_bands", "Trip_share_pct", 100.1),
        ("weekly_hours", "Trips_per_occurrence", -0.1),
        ("monthly", "Gross_fare_USD", -1),
        ("monthly", "Calendar_days", 0),
        ("monthly", "Calendar_days", 32),
    ],
)
def test_numeric_domains_reject_impossible_counts_rates_and_shares(report, table, column, value):
    source = next(t for t in report["tables"] if t["id"] == table)
    if column not in source["columns"]:
        source["columns"].append(column)
        for row in source["rows"]:
            row.append(31)
    source["rows"][0][source["columns"].index(column)] = value
    with pytest.raises(ValueError, match="Negative|Fractional|Percentage|Calendar days"):
        prepare_story(report)


@pytest.mark.parametrize("column", ["Trips", "Gross_fare_USD"])
def test_combined_airport_totals_cannot_exceed_the_quarter(report, column):
    monthly = next(t for t in report["tables"] if t["id"] == "monthly")
    zones = next(t for t in report["tables"] if t["id"] == "zones")
    total = sum(row[monthly["columns"].index(column)] for row in monthly["rows"])
    position = zones["columns"].index(column)
    for row in zones["rows"][:2]:
        row[position] = total // 2
    assert prepare_story(report)  # Exactly 100% remains valid.
    zones["rows"][0][position] += 1
    with pytest.raises(ValueError, match="Airport totals"):
        prepare_story(report)


def test_airport_mix_rejects_extra_months(report):
    segments = next(t for t in report["tables"] if t["id"] == "segments")
    segments["rows"].append(["2025-04", "JFK", 1, 4])
    with pytest.raises(ValueError, match="only January"):
        prepare_story(report)


@pytest.mark.parametrize(
    "rate,value,heading,phrase",
    [
        (90, "-10.0%", "A slower pace by March", "activity fell"),
        (100, "+0.0%", "A steady pace from January to March", "activity was unchanged"),
        (120, "+20.0%", "A stronger pace by March", "activity rose"),
    ],
)
def test_growth_story_follows_measured_direction(report, tmp_path, monkeypatch, rate, value, heading, phrase):
    from streamlit.testing.v1 import AppTest

    monthly = next(t for t in report["tables"] if t["id"] == "monthly")
    monthly["rows"][-1][monthly["columns"].index("Trips_per_day")] = rate
    path = tmp_path / "story.json"
    path.write_text(json.dumps(prepare_story(report)))
    monkeypatch.setenv("BACKINTEL_STORY_DATA", str(path))
    app = AppTest.from_file(str(Path(__file__).parents[1] / "dashboards/taxi/streamlit_app.py")).run()
    assert not app.exception
    assert app.metric[2].value == value
    assert app.header[0].value == heading
    assert any(phrase in element.value for element in app.markdown)
