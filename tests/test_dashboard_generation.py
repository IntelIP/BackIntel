"""Generic delivery and interaction checks, independent of taxi-specific presentation."""

import asyncio
import io
import json
import time
from pathlib import Path
from types import SimpleNamespace

import pytest
from openpyxl import load_workbook

from backintel.presentation.dashboard import LAUNCHER, generate_dashboard, project_report, workbook_bytes
from tests import test_artifacts


def test_month_labels_preserve_source_dates_and_values():
    pytest.importorskip("plotly")
    from backintel.presentation.dashboard import category_labels, chart_figure

    source = ["2025-12-01", "2026-01-01"]
    table = {
        "columns": ["Month", "Count"],
        "rows": [[source[0], 42], [source[1], 50]],
        "units": {"Count": "records"},
    }
    figure = chart_figure({"kind": "line", "x": "Month", "y": "Count"}, table)
    assert list(figure.data[0].x) == source
    assert list(figure.data[0].y) == [42, 50]
    assert list(figure.layout.xaxis.ticktext) == ["Dec 2025", "Jan 2026"]
    assert list(figure.data[0].customdata) == ["Dec 2025", "Jan 2026"]
    assert category_labels("Month", ["2025-02", "2025-13", "2025-02-14"]) == [
        "Feb 2025",
        "2025-13",
        "2025-02-14",
    ]
    assert category_labels("Date", source) == source  # Never relabel daily observations as months.


def test_portrait_heatmap_keeps_every_hour_value_and_matching_axis_label():
    pytest.importorskip("plotly")
    from backintel.presentation.dashboard import chart_figure
    from backintel.presentation.design import ChartDesign

    days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    table = {
        "columns": ["Hour", "Day", "Count"],
        "rows": [[f"{h:02}", d, h * 7 + i] for h in range(24) for i, d in enumerate(days)],
        "units": {"Count": "records"},
    }
    design = ChartDesign(chart=0, title="Busy times", caption="", x_label="Local hour", y_label="Weekday")
    figure = chart_figure({"kind": "heatmap", "x": "Hour", "y": "Day", "z": "Count"}, table, design)
    trace = figure.data[0]
    assert list(trace.x) == days and list(trace.y) == [f"{h:02}" for h in range(24)]
    for hour, day, value in table["rows"]:
        assert trace.z[int(hour)][days.index(day)] == value
    assert trace.colorbar.orientation == "h"
    assert figure.layout.xaxis.title.text == "Weekday"
    assert figure.layout.yaxis.title.text == "Local hour"
    assert list(figure.layout.yaxis.ticktext)[18] == "6 pm"
    assert len(figure.layout.yaxis.tickvals) == 24


@pytest.fixture
def report_spec():
    return test_artifacts.report_spec.__wrapped__()


def test_generated_app_is_constant_and_workbook_excludes_execution_metadata(tmp_path, report_spec):
    report_spec["summary"] = "![remote](https://example.invalid/pixel)\n__import__('os').system('bad')"
    report_spec["tables"][1]["rows"][0][0] = "=1+2"
    target = tmp_path / "dashboard"
    generate_dashboard(report_spec, target)
    assert (target / "app.py").read_text() == LAUNCHER
    data = json.loads((target / "dashboard.json").read_text())
    assert not {"run_id", "evidence"} & data.keys()
    assert data["sources"] == [{"description": s["description"]} for s in report_spec["sources"]]
    assert "evidence_ids" not in data["tables"][0]
    book = load_workbook(io.BytesIO(workbook_bytes(data)))
    assert ("Data source", report_spec["sources"][0]["description"]) in list(book.worksheets[0].values)
    assert book.worksheets[1]["B5"].value == 14850
    assert book.worksheets[2]["A2"].value == "=1+2"
    assert book.worksheets[2]["A2"].data_type == "s"
    with pytest.raises(ValueError, match="new dashboard"):
        generate_dashboard(report_spec, target)
    report_spec["charts"][0]["table"] = "absent"
    with pytest.raises(ValueError):
        generate_dashboard(report_spec, tmp_path / "invalid")
    assert not (tmp_path / "invalid").exists()


def test_saved_presentation_generates_context_without_changing_tables(tmp_path, report_spec):
    from tests.test_dashboard_review import plan_for

    data = project_report(report_spec)
    plan = plan_for(data)
    plan["context"] = {
        "audience": "Operations manager",
        "decision": "Choose a trial",
        "coverage": "Historical observations",
        "limitation": "No cost data",
    }
    generate_dashboard(report_spec, tmp_path / "planned", presentation=plan)
    delivered = json.loads((tmp_path / "planned/dashboard.json").read_text())
    assert delivered == data
    saved = json.loads((tmp_path / "planned/presentation.json").read_text())
    assert saved["context"]["coverage"] == "Historical observations"
    book = load_workbook(tmp_path / "planned/analysis.xlsx")
    assert ("Coverage", "Historical observations") in list(book.worksheets[0].values)
    for sheet, table in zip(book.worksheets[1:], data["tables"], strict=True):
        assert list(sheet.values)[1:] == [tuple(row) for row in table["rows"]]
    plan["sections"] = []
    with pytest.raises(ValueError):
        generate_dashboard(report_spec, tmp_path / "bad-plan", presentation=plan)
    assert not (tmp_path / "bad-plan").exists()


def test_all_chart_types_and_table_exploration(tmp_path, report_spec, monkeypatch):
    pytest.importorskip("streamlit")
    pytest.importorskip("plotly")
    from streamlit.testing.v1 import AppTest

    from backintel.presentation import dashboard

    target = tmp_path / "dashboard"
    generate_dashboard(report_spec, target)
    monkeypatch.setenv("BACKINTEL_DASHBOARD_DATA", str(target / "dashboard.json"))
    app = AppTest.from_file(
        str(Path(dashboard.__file__).with_name("streamlit_app.py")), default_timeout=15
    ).run()
    assert not app.exception
    assert report_spec["sources"][0]["description"] in [item.value for item in app.text]
    assert len(app.get("plotly_chart")) == 5
    assert app.metric[0].value == "14,850"
    app.selectbox[0].select(1).run()
    app.text_input[0].set_value("enterprise").run()
    assert not app.exception
    assert app.dataframe[0].value.iloc[0]["Revenue"] == 120
    assert len(app.dataframe[0].value) == 1
    app.text_input[0].set_value("no such segment").run()
    assert app.dataframe[0].value.empty
    assert app.info
    # Charts and headline values retain their declared population while a table is searched.
    assert app.metric[0].value == "14,850"


def test_table_only_report_remains_useful(tmp_path, report_spec, monkeypatch):
    pytest.importorskip("streamlit")
    from streamlit.testing.v1 import AppTest

    from backintel.presentation import dashboard

    report_spec.update(charts=[], metrics=[])
    report_spec["tables"][0]["rows"] = []
    target = tmp_path / "dashboard"
    generate_dashboard(report_spec, target)
    monkeypatch.setenv("BACKINTEL_DASHBOARD_DATA", str(target / "dashboard.json"))
    app = AppTest.from_file(
        str(Path(dashboard.__file__).with_name("streamlit_app.py")), default_timeout=15
    ).run()
    assert not app.exception
    assert not app.get("plotly_chart")
    assert app.dataframe[0].value.empty
    assert len(app.info) == 2
    assert project_report(report_spec)["metrics"] == []


def test_serve_uses_trusted_entry_and_loopback(tmp_path, monkeypatch):
    pytest.importorskip("streamlit")
    import subprocess

    from backintel.cli import main

    (tmp_path / "dashboard.json").write_text("{}")
    (tmp_path / "app.py").write_text("raise RuntimeError('Untrusted program must never execute')")
    called = []

    def call(command, **kwargs):
        called.append((command, kwargs))
        return 0

    monkeypatch.setattr(subprocess, "call", call)
    with pytest.raises(SystemExit) as stopped:
        main(["dashboard", "serve", str(tmp_path), "--port", "8504"])
    assert stopped.value.code == 0
    command, options = called[0]
    assert str(tmp_path / "app.py") not in command
    assert command[command.index("--server.address") + 1] == "127.0.0.1"
    assert command[4].endswith("presentation/streamlit_app.py")
    assert options["env"]["BACKINTEL_DASHBOARD_DATA"] == str(tmp_path.resolve() / "dashboard.json")


@pytest.mark.parametrize("invalid", [False, True])
def test_bounded_generation_uses_real_cli_and_preserves_tables(tmp_path, report_spec, invalid):
    from backintel.presentation.dashboard import generate_dashboard_async

    target = tmp_path / "dashboard"
    if invalid:
        report_spec["charts"][0]["table"] = "absent"
        with pytest.raises(RuntimeError, match="Dashboard generation failed"):
            asyncio.run(generate_dashboard_async(report_spec, target, deadline=time.monotonic() + 20))
        assert not target.exists()
    else:
        result = asyncio.run(generate_dashboard_async(report_spec, target, deadline=time.monotonic() + 20))
        assert result["status"] == "generated" and result["path"] == str(target)
        data = json.loads((target / "dashboard.json").read_text())
        assert data == project_report(report_spec)
        book = load_workbook(target / "analysis.xlsx")
        for sheet, table in zip(book.worksheets[1:], data["tables"], strict=True):
            assert list(sheet.values)[1:] == [tuple(row) for row in table["rows"]]
        with pytest.raises(ValueError, match="existing deliveries"):
            asyncio.run(generate_dashboard_async(report_spec, target, deadline=time.monotonic() + 20))
    assert not list(tmp_path.glob(".dashboard-*"))


@pytest.mark.parametrize("stop", ["deadline", "cancel"])
def test_stalled_workbook_is_stopped_without_publishing(tmp_path, report_spec, monkeypatch, stop):
    from backintel.presentation import dashboard

    # Run the real generator, but stall precisely inside its workbook builder.
    script = """
import time
from pathlib import Path
from backintel.presentation import dashboard
from backintel.cli import main

def stall(*args):
    Path('workbook-started').touch()
    time.sleep(60)
    raise AssertionError('stalled workbook should have been stopped')

dashboard.workbook_bytes = stall
main()
"""
    original = dashboard.subprocess.Popen
    processes, directories = [], []
    clock = SimpleNamespace(now=time.monotonic())
    deadline = clock.now + 20
    monkeypatch.setattr(dashboard, "time", SimpleNamespace(monotonic=lambda: clock.now))
    monkeypatch.setenv("OPENAI_API_KEY", "test-secret-must-not-reach-generator")

    def spawn(command, **kwargs):
        assert command[1:5] == ["-m", "backintel.cli", "dashboard", "generate"]
        assert "OPENAI_API_KEY" not in kwargs["env"]
        process = original([command[0], "-c", script, *command[3:]], **kwargs)
        processes.append(process)
        directories.append(Path(kwargs["cwd"]))
        return process

    monkeypatch.setattr(dashboard.subprocess, "Popen", spawn)
    target = tmp_path / "dashboard"

    async def run():
        task = asyncio.create_task(dashboard.generate_dashboard_async(report_spec, target, deadline=deadline))
        try:
            async with asyncio.timeout(15):
                while not directories or not (directories[0] / "workbook-started").exists():
                    if task.done():
                        await task  # Surface child startup failures instead of hiding them behind a timeout.
                        raise AssertionError("Generator ended before the workbook was reached")
                    await asyncio.sleep(0.01)
            if stop == "deadline":
                clock.now = deadline + 1
                with pytest.raises(TimeoutError, match="dashboard generation"):
                    await asyncio.wait_for(task, 2)
            else:
                task.cancel()
                with pytest.raises(asyncio.CancelledError):
                    await task
        finally:
            if not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass

    asyncio.run(run())
    assert processes and all(p.poll() is not None for p in processes)
    assert not target.exists()
    assert not list(tmp_path.glob(".dashboard-*"))


def test_histogram_hover_shows_bin_bounds_and_counts():
    pytest.importorskip("plotly")
    from backintel.presentation.dashboard import chart_figure

    table = {"columns": ["Fare"], "rows": [[0], [10], [20], [30]], "units": {"Fare": "USD"}}
    figure = chart_figure({"kind": "histogram", "x": "Fare", "bins": 3}, table)
    trace = figure.data[0]
    assert list(map(list, trace.customdata)) == [[0, 10], [10, 20], [20, 30]]
    assert list(trace.y) == [1, 1, 2]
    assert "%{customdata[0]" in trace.hovertemplate and "%{customdata[1]" in trace.hovertemplate
    assert "USD" in trace.hovertemplate and "%{y} observations" in trace.hovertemplate
