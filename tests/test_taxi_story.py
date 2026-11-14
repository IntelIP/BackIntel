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
    airport_chart,
    business_workbook,
    prepare_story,
    summary,
    validate_story,
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
        "quality": (["Population", "Records"], [["engineering-label", 1000 - i] for i in range(10)]),
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
