from __future__ import annotations

import copy
import csv
import hashlib
import json
from pathlib import Path

import pytest

from backintel.artifacts import render_report, validate_report, verify_bundle


@pytest.fixture
def report_spec():
    spec = json.loads((Path(__file__).parents[1] / "examples" / "analysis-report.json").read_text())
    spec["tables"].append(
        {
            "id": "segments",
            "title": "Revenue by segment",
            "columns": ["Segment", "Revenue", "Orders"],
            "rows": [["Small business", 80, 4], ["Enterprise", 120, 5]],
            "units": {"Revenue": "USD", "Orders": "orders"},
            "evidence_ids": ["monthly-calc"],
        }
    )
    spec["tables"].append(
        {
            "id": "cohorts",
            "title": "Cohort counts",
            "columns": ["Cohort", "Period", "Customers"],
            "rows": [
                ["July", "First", 20],
                ["July", "Second", 12],
                ["August", "First", 25],
                ["August", "Second", 18],
            ],
            "units": {"Customers": "customers"},
            "evidence_ids": ["monthly-calc"],
        }
    )
    spec["charts"] += [
        {
            "id": "segments",
            "title": "Revenue by segment",
            "kind": "bar",
            "table": "segments",
            "x": "Segment",
            "y": "Revenue",
        },
        {
            "id": "relationship",
            "title": "Orders and revenue",
            "kind": "scatter",
            "table": "segments",
            "x": "Orders",
            "y": "Revenue",
        },
        {
            "id": "distribution",
            "title": "Revenue distribution",
            "kind": "histogram",
            "table": "segments",
            "x": "Revenue",
            "bins": 2,
        },
        {
            "id": "cohort-grid",
            "title": "Customers by cohort and period",
            "kind": "heatmap",
            "table": "cohorts",
            "x": "Period",
            "y": "Cohort",
            "z": "Customers",
        },
    ]
    return spec


@pytest.fixture
def renderer_dependencies():
    pytest.importorskip("matplotlib", reason="renderer packages are installed in the analysis image")
    pytest.importorskip("plotly", reason="renderer packages are installed in the analysis image")
    pytest.importorskip("openpyxl")


def test_normalizes_metrics_from_one_table_without_mutating_input(report_spec):
    original = copy.deepcopy(report_spec)
    result = validate_report(report_spec)
    assert result["metrics"][0]["value"] == 14850
    assert result["metrics"][0]["unit"] == "USD"
    assert report_spec == original
    result["metrics"][0]["value"] = 999
    with pytest.raises(ValueError, match="disagrees"):
        validate_report(result)


@pytest.mark.parametrize(
    "change",
    [
        lambda s: s["tables"][0].update(id="../escape"),
        lambda s: s["tables"][0]["rows"][0].__setitem__(1, float("nan")),
        lambda s: s["metrics"].append(dict(s["metrics"][0])),
        lambda s: s["charts"][0].update(x="absent"),
        lambda s: s["tables"][1]["rows"][1].__setitem__(0, "Small business"),
        lambda s: s["tables"][2]["rows"].pop(),
        lambda s: s["tables"][0]["rows"][0].__setitem__(0, "July"),
        lambda s: s["charts"][3].update(bins=0),
    ],
)
def test_rejects_invalid_grain_bindings_and_values(report_spec, change):
    change(report_spec)
    with pytest.raises(ValueError):
        validate_report(report_spec)


def test_complete_bundle_agrees_across_formats(tmp_path, report_spec, renderer_dependencies):
    from openpyxl import load_workbook

    output = tmp_path / "report"
    manifest = render_report(report_spec, output)
    assert verify_bundle(output) == manifest
    assert len(manifest["artifacts"]) == 21  # Three tables, five charts and three primary files.
    workbook = load_workbook(output / "supporting.xlsx", data_only=False)
    assert workbook["Metrics"]["B2"].value == 14850
    assert workbook["T1-monthly"]["B5"].value == 14850
    for table in report_spec["tables"]:
        with (output / "tables" / f"{table['id']}.csv").open(newline="") as handle:
            rows = list(csv.reader(handle))
        assert rows[0] == table["columns"]
        assert len(rows) == len(table["rows"]) + 1
    for chart in report_spec["charts"]:
        html = (output / "charts" / f"{chart['id']}.html").read_text()
        assert "<script src=" not in html
        assert "connect-src &#x27;none&#x27;" in html
        assert (output / "charts" / f"{chart['id']}.png").read_bytes().startswith(b"\x89PNG\r\n\x1a\n")
        payload = html.split("const figure=", 1)[1].split(";Plotly.newPlot", 1)[0]
        figure = json.loads(payload)
        if chart["kind"] == "histogram":
            assert sum(figure["data"][0]["y"]) == 2
        if chart["kind"] == "heatmap":
            assert figure["data"][0]["z"] == [[20, 12], [25, 18]]


def test_plain_text_does_not_become_formulas_or_html(tmp_path, report_spec, renderer_dependencies):
    from openpyxl import load_workbook

    report_spec["title"] = "Report <script>alert('x')</script>"
    report_spec["tables"][1]["rows"][0][0] = '=HYPERLINK("https://example.invalid","x")'
    report_spec["tables"][1]["rows"][1][0] = '</script><script>alert("x")</script>'
    output = tmp_path / "report"
    render_report(report_spec, output)
    html = (output / "report.html").read_text()
    assert "<script>alert('x')</script>" not in html
    assert "&lt;script&gt;" in html
    chart = (output / "charts" / "segments.html").read_text()
    assert '</script><script>alert("x")</script>' not in chart
    workbook = load_workbook(output / "supporting.xlsx", data_only=False)
    cell = workbook["T2-segments"]["A2"]
    assert cell.value.startswith("=HYPERLINK") and cell.data_type == "s"
    with (output / "tables" / "segments.csv").open(newline="") as handle:
        assert list(csv.reader(handle))[1][0].startswith("'=HYPERLINK")


def test_output_is_atomic_and_bounded(tmp_path, report_spec, renderer_dependencies):
    output = tmp_path / "report"
    with pytest.raises(ValueError, match="max_bytes"):
        render_report(report_spec, output, max_bytes=10)
    assert not output.exists()
    assert not list(tmp_path.glob(".report-*"))
    output.mkdir()
    (output / "keep").write_text("existing user data")
    with pytest.raises(ValueError, match="new directory"):
        render_report(report_spec, output)
    assert (output / "keep").read_text() == "existing user data"


def test_verification_rejects_rehashed_csv_and_extra_files(tmp_path, report_spec, renderer_dependencies):
    report_spec["charts"] = []
    output = tmp_path / "report"
    manifest = render_report(report_spec, output)
    csv_path = output / "tables" / "monthly.csv"
    csv_path.write_text(csv_path.read_text().replace("14850", "99999"))
    item = next(a for a in manifest["artifacts"] if a["path"] == "tables/monthly.csv")
    item.update(bytes=csv_path.stat().st_size, sha256=hashlib.sha256(csv_path.read_bytes()).hexdigest())
    (output / "manifest.json").write_text(json.dumps(manifest))
    with pytest.raises(ValueError, match="differs from analytical table"):
        verify_bundle(output)
    (output / "unexpected.html").write_text("<script>alert(1)</script>")
    with pytest.raises(ValueError, match="inventory"):
        verify_bundle(output)


def test_verification_rejects_symlinks(tmp_path, report_spec, renderer_dependencies):
    report_spec["charts"] = []
    output = tmp_path / "report"
    render_report(report_spec, output)
    (output / "escape.csv").symlink_to(tmp_path / "outside")
    with pytest.raises(ValueError, match="unsupported entries"):
        verify_bundle(output)


def test_percentage_heatmap_keeps_absolute_scale_and_exact_timestamps():
    from backintel.artifacts import _heatmap_limits, _heatmap_ticks

    assert _heatmap_limits("%", [[0, 25], [50, 61.6666666667]]) == {"vmin": 0, "vmax": 100}
    assert _heatmap_limits("customers", [[0, 25]]) == {}
    assert _heatmap_limits("%", [[-5, 125]]) == {}
    labels = ["2026-03-15T00:00:00Z", "2026-03-15T01:00:00Z"]
    assert _heatmap_ticks(labels) == (["00:00", "01:00"], " · 15 Mar 2026 UTC")
    different_dates = ["2026-03-15T00:00:00Z", "2026-03-16T00:00:00Z"]
    assert _heatmap_ticks(different_dates) == (different_dates, "")


def test_headline_rounding_keeps_exact_metric_in_definition(report_spec):
    from backintel.artifacts import _report_html

    report = validate_report(report_spec)
    report["metrics"][0]["value"] = 59.43396226415094
    report["metrics"][0]["unit"] = "%"
    page = _report_html(report)
    assert "59.43 " in page
    assert "Exact value: 59.43396226415094" in page
    assert 'href="#table-' in page
    assert 'aria-label="Report sections"' in page
