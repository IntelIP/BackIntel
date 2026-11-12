"""Offline, bounded report bundles from one explicit set of analytical tables.

Validation establishes structural consistency, not the truth of a supplied calculation.
Run source/evidence checks separately. This module also runs inside the analysis image;
its top-level imports deliberately use only the Python standard library.
"""

from __future__ import annotations

import csv
import hashlib
import html
import io
import json
import math
import os
import re
import shutil
import tempfile
import textwrap
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

SCHEMA_VERSION = 1
MAX_SPEC_BYTES = 8 * 1024 * 1024
DEFAULT_MAX_BYTES = 64 * 1024 * 1024
_ID = re.compile(r"[a-z][a-z0-9_-]{0,39}\Z")
_MEDIA = {
    ".html": "text/html",
    ".json": "application/json",
    ".csv": "text/csv",
    ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    ".png": "image/png",
    ".svg": "image/svg+xml",
}
_CSP = (
    "default-src 'none'; script-src 'unsafe-inline'; style-src 'unsafe-inline'; "
    "img-src 'self' data:; font-src 'none'; connect-src 'none'; object-src 'none'; "
    "base-uri 'none'; form-action 'none'; frame-src 'none'"
)
_CSS = """
:root{color-scheme:light;font-family:Arial,Helvetica,sans-serif;color:#182d3e;background:#f7f8fa}
*{box-sizing:border-box}body{margin:0}main{max-width:1080px;margin:auto;padding:48px 32px 64px}
header{border-bottom:2px solid #1f6185;padding-bottom:24px;margin-bottom:32px}
.eyebrow{font-size:12px;letter-spacing:.12em;text-transform:uppercase;color:#46637a}
h1{font-size:38px;line-height:1.15;max-width:850px;margin:14px 0 18px}h2{font-size:23px;margin:32px 0 14px}
h3{font-size:18px;margin:0 0 12px}p,li{font-size:16px;line-height:1.6}p{max-width:85ch}
a{color:#145e89;text-underline-offset:3px}.meta,.note{font-size:13px;line-height:1.6;color:#4c6171}
.metrics{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:24px;margin:28px 0}
.metric{border-top:1px solid #b8cbd8;padding-top:12px}
.metric strong{font-size:29px;display:block;margin:8px 0}
.metric span{display:block;font-size:14px}.unit{font-size:14px!important;font-weight:400}
figure{margin:28px 0;background:white;padding:22px 20px}figure img{max-width:100%;height:auto;display:block}
figcaption{font-size:13px;line-height:1.5;color:#4c6171;margin-top:12px}.table-wrap{overflow-x:auto}
table{width:100%;border-collapse:collapse;font-size:14px}
th,td{padding:10px 12px;text-align:left;border-bottom:1px solid #dce3e9}
th{background:#eaf0f4;font-weight:600}.number{text-align:right;font-variant-numeric:tabular-nums}
details{margin:16px 0}summary{cursor:pointer}
pre{white-space:pre-wrap;overflow-wrap:anywhere;font-size:12px;line-height:1.5;background:#edf1f4;padding:16px}
.downloads{display:flex;gap:18px;flex-wrap:wrap}.interactive{min-height:400px;width:100%}
footer{border-top:1px solid #b8cbd8;margin-top:36px;padding-top:14px}
@media(max-width:600px){main{padding:24px 16px}h1{font-size:29px}figure{padding:12px 4px}th,td{padding:8px}}
@media print{body{background:white}main{padding:0}figure,.metric{break-inside:avoid}.downloads{display:none}}
"""


def _json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, allow_nan=False, sort_keys=True, indent=2)


def _text(value: Any, name: str, limit: int = 2000) -> str:
    if not isinstance(value, str) or not value.strip() or len(value) > limit:
        raise ValueError(f"{name} must be nonempty text of at most {limit} characters")
    if any(ord(c) < 32 and c not in "\n\t\r" for c in value):
        raise ValueError(f"{name} contains unsupported control characters")
    return value


def _records(value: Any, name: str, maximum: int, *, empty: bool = False) -> list[dict]:
    if not isinstance(value, list) or len(value) > maximum or (not value and not empty):
        raise ValueError(f"{name} must contain {'0' if empty else '1'} to {maximum} objects")
    seen = set()
    for record in value:
        if not isinstance(record, dict) or not _ID.fullmatch(str(record.get("id", ""))):
            raise ValueError(f"{name} ids must match {_ID.pattern}")
        if record["id"] in seen:
            raise ValueError(f"duplicate {name} id: {record['id']}")
        seen.add(record["id"])
    return value


def _finite_number(value: Any) -> bool:
    return type(value) in (int, float) and abs(value) < 1e100 and math.isfinite(value)


def _line_x(values: list) -> list:
    if all(_finite_number(v) for v in values):
        return values
    if not all(isinstance(v, str) for v in values):
        raise ValueError("line x must contain only numbers or ISO dates/times")
    try:
        dates = [datetime.fromisoformat(v) for v in values]
        return [d.replace(tzinfo=UTC) if d.tzinfo is None else d.astimezone(UTC) for d in dates]
    except ValueError as exc:
        raise ValueError("line x strings must be ISO dates/times, not category labels") from exc


def validate_report(spec: dict) -> dict:
    """Return an isolated normalized spec; reject broken bindings and unsafe shapes.

    Metrics reference a table cell instead of repeating its value. Chart columns also
    reference that table. Evidence is recorded, never executed by this renderer.
    """
    try:
        encoded = _json(spec)
    except (ValueError, TypeError) as exc:
        raise ValueError("report must contain JSON values with finite numbers") from exc
    if len(encoded.encode()) > MAX_SPEC_BYTES or not isinstance(spec, dict):
        raise ValueError("report exceeds the specification limit or is not an object")
    report = json.loads(encoded)
    if report.get("schema_version", SCHEMA_VERSION) != SCHEMA_VERSION:
        raise ValueError("unsupported report schema_version")
    report["schema_version"] = SCHEMA_VERSION
    if not _ID.fullmatch(str(report.get("run_id", ""))):
        raise ValueError("run_id must be a safe lowercase identifier")
    _text(report.get("title"), "title", 200)
    _text(report.get("summary"), "summary", 6000)
    for field in ("findings", "caveats"):
        values = report.setdefault(field, [])
        if not isinstance(values, list) or len(values) > 30:
            raise ValueError(f"{field} must be a list of at most 30 strings")
        for value in values:
            _text(value, field)
    sources = _records(report.get("sources"), "sources", 20)
    for source in sources:
        _text(source.get("snapshot"), "source snapshot", 300)
        _text(source.get("description"), "source description", 2000)
    source_ids = {s["id"] for s in sources}
    evidence = _records(report.get("evidence"), "evidence", 100)
    for item in evidence:
        if item.get("kind") not in {"sql", "python", "query"}:
            raise ValueError("evidence kind must be sql, python or query")
        _text(item.get("code"), "evidence code", 20000)
        refs = item.get("source_ids")
        if not isinstance(refs, list) or not refs or not all(s in source_ids for s in refs):
            raise ValueError("evidence must reference existing sources")
    evidence_ids = {e["id"] for e in evidence}
    tables = _records(report.get("tables"), "tables", 20)
    cell_count = 0
    for table in tables:
        _text(table.get("title"), "table title", 200)
        columns, rows, units = table.get("columns"), table.get("rows"), table.get("units", {})
        if not isinstance(columns, list) or not 1 <= len(columns) <= 30:
            raise ValueError("table requires 1 to 30 column names")
        for column in columns:
            _text(column, "column", 100)
        if len(set(columns)) != len(columns):
            raise ValueError("table column names must be unique")
        if not isinstance(units, dict) or any(c not in columns for c in units):
            raise ValueError("units must map existing columns to their units")
        for unit in units.values():
            _text(unit, "unit", 100)
        table["units"] = units
        if not isinstance(rows, list) or len(rows) > 10000:
            raise ValueError("table requires at most 10000 rows; aggregate large inputs first")
        refs = table.get("evidence_ids")
        if not isinstance(refs, list) or not refs or not all(e in evidence_ids for e in refs):
            raise ValueError("table must reference existing evidence")
        for row in rows:
            if not isinstance(row, list) or len(row) != len(columns):
                raise ValueError("table row width must equal its columns")
            for cell in row:
                if cell is None or isinstance(cell, bool):
                    continue
                if isinstance(cell, str):
                    if cell:
                        _text(cell, "cell", 2000)
                elif not _finite_number(cell):
                    raise ValueError("cells must be finite JSON scalars")
            cell_count += len(row)
    if cell_count > 100000:
        raise ValueError("report exceeds 100000 cells; aggregate data before rendering")
    by_table = {t["id"]: t for t in tables}
    for metric in _records(report.setdefault("metrics", []), "metrics", 20, empty=True):
        _text(metric.get("label"), "metric label", 150)
        _text(metric.get("definition"), "metric definition", 2000)
        table = by_table.get(metric.get("table"))
        row = metric.get("row")
        if table is None or type(row) is not int or not 0 <= row < len(table["rows"]):
            raise ValueError("metric must reference an existing table row")
        if metric.get("column") not in table["columns"]:
            raise ValueError("metric must reference an existing column")
        value = table["rows"][row][table["columns"].index(metric["column"])]
        if not _finite_number(value) or metric["column"] not in table["units"]:
            raise ValueError("metric cell must be numeric and have an explicit unit")
        if "value" in metric and metric["value"] != value:
            raise ValueError("metric value disagrees with its bound table cell")
        metric["value"] = value
        metric["unit"] = table["units"][metric["column"]]
    for chart in _records(report.setdefault("charts", []), "charts", 12, empty=True):
        _text(chart.get("title"), "chart title", 200)
        table = by_table.get(chart.get("table"))
        kind = chart.get("kind")
        if table is None or kind not in {"bar", "line", "scatter", "histogram", "heatmap"}:
            raise ValueError("chart requires an existing table and supported kind")
        limit = 40 if kind == "bar" else 10000 if kind == "histogram" else 2000
        if not 1 <= len(table["rows"]) <= limit:
            raise ValueError("chart has no rows or too many marks; aggregate or select a declared subset")
        if chart.get("x") not in table["columns"]:
            raise ValueError("chart axes must reference existing columns")
        xs = [r[table["columns"].index(chart["x"])] for r in table["rows"]]
        if kind == "histogram":
            if not all(_finite_number(x) for x in xs) or chart["x"] not in table["units"]:
                raise ValueError("histogram x must be numeric, non-null and have a unit")
            bins = chart.setdefault("bins", 10)
            if type(bins) is not int or not 1 <= bins <= 100:
                raise ValueError("histogram bins must be an integer from 1 to 100")
            continue
        if chart.get("y") not in table["columns"]:
            raise ValueError("chart axes must reference existing columns")
        ys = [r[table["columns"].index(chart["y"])] for r in table["rows"]]
        if kind == "heatmap":
            if chart.get("z") not in table["columns"] or chart["z"] not in table["units"]:
                raise ValueError("heatmap requires a numeric z column with a unit")
            zs = [r[table["columns"].index(chart["z"])] for r in table["rows"]]
            if not all(_finite_number(z) for z in zs) or any(x is None for x in [*xs, *ys]):
                raise ValueError("heatmap requires non-null axes and numeric z values")
            if len(set(zip(xs, ys, strict=True))) != len(xs):
                raise ValueError("heatmap cells must be unique at the x/y grain")
            if len(set(xs)) > 30 or len(set(ys)) > 30 or len(set(xs)) * len(set(ys)) != len(zs):
                raise ValueError("heatmap requires a complete grid of at most 30 by 30 cells")
            continue
        if not all(_finite_number(y) for y in ys) or chart["y"] not in table["units"]:
            raise ValueError("chart y must be numeric, non-null and have an explicit unit")
        if kind == "scatter" and not all(_finite_number(x) for x in xs):
            raise ValueError("scatter x must be numeric and non-null")
        if kind == "scatter" and chart["x"] not in table["units"]:
            raise ValueError("scatter x must have an explicit unit")
        if any(x is None or isinstance(x, bool) for x in xs):
            raise ValueError("chart x cannot contain null or boolean values")
        if kind != "scatter" and len(set(xs)) != len(xs):
            raise ValueError("bar/line x values must be unique; aggregate the intended grain first")
        if kind == "line":
            ordered = _line_x(xs)
            if ordered != sorted(ordered):
                raise ValueError("line x values must be sorted chronologically or numerically")
    return report


def _escape(value: Any) -> str:
    return html.escape("—" if value is None else str(value), quote=True)


def _display(value: Any) -> str:
    if _finite_number(value):
        return f"{value:,.12g}" if isinstance(value, float) else f"{value:,}"
    return _escape(value)


def _csv_cell(value: Any) -> Any:
    # Excel/LibreOffice may execute formula-like text even when CSV quotes it.
    if isinstance(value, str) and value.lstrip().startswith(("=", "+", "-", "@")):
        return "'" + value
    return value


def _page(title: str, body: str, script: str = "") -> str:
    return (
        f'<!doctype html><html lang="en"><head><meta charset="utf-8">'
        f'<meta http-equiv="Content-Security-Policy" content="{_escape(_CSP)}">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        f"<title>{_escape(title)}</title><style>{_CSS}</style></head>"
        f"<body><main>{body}</main>{script}</body></html>"
    )


def _table_html(table: dict) -> str:
    headings = "".join(f'<th scope="col">{_escape(c)}</th>' for c in table["columns"])
    rows = []
    for row in table["rows"][:100]:
        cells = "".join(
            f'<td class="{"number" if _finite_number(v) else "text"}">{_display(v)}</td>' for v in row
        )
        rows.append(f"<tr>{cells}</tr>")
    return (
        f'<div class="table-wrap"><table><thead><tr>{headings}</tr></thead>'
        f"<tbody>{''.join(rows)}</tbody></table></div>"
    )


def _column(table: dict, name: str) -> list:
    return [row[table["columns"].index(name)] for row in table["rows"]]


def _histogram(chart: dict, table: dict) -> tuple[list, list, float]:
    values = _column(table, chart["x"])
    low, high = min(values), max(values)
    if low == high:
        low, high = low - 0.5, high + 0.5
    width = (high - low) / chart["bins"]
    counts = [0] * chart["bins"]
    for value in values:
        counts[min(int((value - low) / width), len(counts) - 1)] += 1
    centers = [low + (i + 0.5) * width for i in range(len(counts))]
    return centers, counts, width


def _heatmap(chart: dict, table: dict) -> tuple[list, list, list]:
    xs, ys = _column(table, chart["x"]), _column(table, chart["y"])
    zs = _column(table, chart["z"])
    x_labels, y_labels = list(dict.fromkeys(xs)), list(dict.fromkeys(ys))
    values = dict(zip(zip(xs, ys, strict=True), zs, strict=True))
    return x_labels, y_labels, [[values[x, y] for x in x_labels] for y in y_labels]


def _static_chart(chart: dict, table: dict, directory: Path) -> None:
    import matplotlib

    matplotlib.use("Agg")
    from matplotlib import pyplot as plt
    from matplotlib.ticker import StrMethodFormatter

    xs = _column(table, chart["x"])
    ys = _column(table, chart["y"]) if "y" in chart else []
    with plt.rc_context(
        {
            "font.family": "DejaVu Sans",
            "font.size": 11,
            "text.usetex": False,
            "text.parse_math": False,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "axes.labelcolor": "#334e62",
            "xtick.color": "#334e62",
            "ytick.color": "#334e62",
        }
    ):
        height = max(4.4, len(xs) * 0.32 + 1.4) if chart["kind"] == "bar" else 4.8
        fig, ax = plt.subplots(figsize=(10, height), layout="constrained")
        measure = (
            chart["z"]
            if chart["kind"] == "heatmap"
            else chart["x"]
            if chart["kind"] == "histogram"
            else chart["y"]
        )
        unit = table["units"][measure]
        if chart["kind"] == "bar":
            labels = ["\n".join(textwrap.wrap(str(x), 34)) for x in xs]
            ax.barh(labels, ys, color="#246a91", height=0.65)
            ax.invert_yaxis()
            ax.set_xlabel(f"{chart['y']} ({unit})")
            ax.xaxis.set_major_formatter(StrMethodFormatter("{x:,.6g}"))
            ax.axvline(0, linewidth=0.8, color="#334e62")
            ax.grid(axis="x", color="#dce4e9", linewidth=0.6)
        elif chart["kind"] == "histogram":
            centers, counts, width = _histogram(chart, table)
            ax.bar(centers, counts, width=width * 0.98, color="#246a91")
            ax.set_xlabel(f"{chart['x']} ({unit})")
            ax.set_ylabel("Observations")
            ax.grid(axis="y", color="#dce4e9", linewidth=0.6)
        elif chart["kind"] == "heatmap":
            x_labels, y_labels, values = _heatmap(chart, table)
            fig.set_size_inches(max(8, len(x_labels) * 0.6 + 3), max(4.8, len(y_labels) * 0.35 + 2))
            im = ax.imshow(values, cmap="Blues", aspect="auto")
            ax.set_xticks(range(len(x_labels)), [str(x) for x in x_labels], rotation=30, ha="right")
            ax.set_yticks(range(len(y_labels)), [str(y) for y in y_labels])
            ax.set_xlabel(chart["x"])
            ax.set_ylabel(chart["y"])
            fig.colorbar(im, ax=ax, label=f"{chart['z']} ({unit})", shrink=0.85)
            if len(x_labels) * len(y_labels) <= 100:
                midpoint = (min(map(min, values)) + max(map(max, values))) / 2
                for row, row_values in enumerate(values):
                    for column, value in enumerate(row_values):
                        ax.text(
                            column,
                            row,
                            f"{value:,.3g}",
                            ha="center",
                            va="center",
                            color="white" if value > midpoint else "#182d3e",
                            fontsize=10,
                        )
        else:
            if chart["kind"] == "scatter":
                ax.scatter(xs, ys, color="#246a91", s=28, alpha=0.8)
            else:
                ax.plot(_line_x(xs), ys, color="#246a91", linewidth=2, marker="o", markersize=4)
                if isinstance(xs[0], str):
                    import matplotlib.dates as mdates

                    locator = mdates.AutoDateLocator(minticks=3, maxticks=8)
                    ax.xaxis.set_major_locator(locator)
                    ax.xaxis.set_major_formatter(mdates.ConciseDateFormatter(locator))
            x_unit = table["units"].get(chart["x"])
            ax.set_xlabel(chart["x"] + (f" ({x_unit})" if x_unit else ""))
            ax.set_ylabel(f"{chart['y']} ({unit})")
            ax.yaxis.set_major_formatter(StrMethodFormatter("{x:,.6g}"))
            ax.grid(axis="y", color="#dce4e9", linewidth=0.6)
        ax.set_axisbelow(True)
        ax.set_title(textwrap.fill(chart["title"], 75), loc="left", pad=18, fontweight="bold", fontsize=14)
        try:
            for extension in ("png", "svg"):
                fig.savefig(directory / f"{chart['id']}.{extension}", dpi=160, bbox_inches="tight")
        finally:
            plt.close(fig)


def _interactive(chart: dict, table: dict) -> str:
    import plotly.graph_objects as go
    from plotly.offline import get_plotlyjs

    xs = _column(table, chart["x"])
    ys = _column(table, chart["y"]) if "y" in chart else []
    xs = [_escape(x) if isinstance(x, str) else x for x in xs]
    measure = (
        chart["z"]
        if chart["kind"] == "heatmap"
        else chart["x"]
        if chart["kind"] == "histogram"
        else chart["y"]
    )
    unit = _escape(table["units"][measure])
    if chart["kind"] == "bar":
        trace = go.Bar(
            y=xs,
            x=ys,
            orientation="h",
            marker_color="#246a91",
            hovertemplate="%{y}: %{x:,.6g} " + unit + "<extra></extra>",
        )
    elif chart["kind"] == "histogram":
        centers, counts, width = _histogram(chart, table)
        trace = go.Bar(
            x=centers,
            y=counts,
            width=width * 0.98,
            marker_color="#246a91",
            customdata=[[x - width / 2, x + width / 2] for x in centers],
            hovertemplate="%{customdata[0]:,.6g} – %{customdata[1]:,.6g} "
            + unit
            + "<br>%{y} observations<extra></extra>",
        )
    elif chart["kind"] == "heatmap":
        x_labels, y_labels, values = _heatmap(chart, table)
        trace = go.Heatmap(
            x=[_escape(x) for x in x_labels],
            y=[_escape(y) for y in y_labels],
            z=values,
            colorscale="Blues",
            colorbar={"title": unit},
            hovertemplate="%{x} · %{y}<br>%{z:,.6g} " + unit + "<extra></extra>",
        )
    else:
        trace = go.Scatter(
            x=xs,
            y=ys,
            mode="markers" if chart["kind"] == "scatter" else "lines+markers",
            marker_color="#246a91",
            line_color="#246a91",
            hovertemplate="%{x}: %{y:,.6g} " + unit + "<extra></extra>",
        )
    fig = go.Figure(trace)
    fig.update_layout(
        template="plotly_white",
        font={"family": "Arial", "size": 14, "color": "#334e62"},
        margin={"l": 80, "r": 24, "t": 24, "b": 60},
        showlegend=False,
        height=max(420, len(xs) * 29 + 100) if chart["kind"] == "bar" else 480,
    )
    if chart["kind"] == "bar":
        fig.update_yaxes(autorange="reversed", automargin=True)
        fig.update_xaxes(title_text=f"{_escape(chart['y'])} ({unit})", rangemode="tozero")
    elif chart["kind"] == "histogram":
        fig.update_xaxes(title_text=f"{_escape(chart['x'])} ({unit})")
        fig.update_yaxes(title_text="Observations", rangemode="tozero")
    elif chart["kind"] == "heatmap":
        fig.update_xaxes(title_text=_escape(chart["x"]), automargin=True)
        fig.update_yaxes(title_text=_escape(chart["y"]), autorange="reversed", automargin=True)
    else:
        x_unit = table["units"].get(chart["x"])
        fig.update_xaxes(title_text=_escape(chart["x"] + (f" ({x_unit})" if x_unit else "")), automargin=True)
        fig.update_yaxes(title_text=f"{_escape(chart['y'])} ({unit})", automargin=True)
    # Inline data cannot close a script tag; only the installed Plotly library is executable code.
    payload = fig.to_json().replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026")
    config = json.dumps(
        {
            "responsive": True,
            "displaylogo": False,
            "showLink": False,
            "modeBarButtonsToRemove": ["sendDataToCloud", "toImage"],
        }
    )
    script = (
        f"<script>{get_plotlyjs()}</script><script>const figure={payload};"
        f"Plotly.newPlot('chart',figure.data,figure.layout,{config});</script>"
    )
    body = (
        f'<p class="eyebrow">BackIntel · interactive analysis</p><h1>{_escape(chart["title"])}</h1>'
        '<div id="chart" class="interactive" role="img" '
        'aria-label="Interactive chart; exact values below"></div>'
        f'<h2>Exact values</h2>{_table_html(table)}<p class="note">Units: {unit}. '
        f'Source table: {_escape(table["id"])}. <a href="../report.html">Return to report</a>.</p>'
    )
    return _page(chart["title"], body, script)


def _workbook(report: dict, path: Path) -> None:
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Font, PatternFill
    from openpyxl.utils import get_column_letter

    workbook = Workbook()
    workbook.remove(workbook.active)
    sheets = [
        (
            "Metrics",
            ["Metric", "Value", "Unit", "Definition", "Table", "Row", "Column"],
            [
                [m["label"], m["value"], m["unit"], m["definition"], m["table"], m["row"], m["column"]]
                for m in report["metrics"]
            ],
        )
    ]
    sheets += [(f"T{i + 1}-{t['id']}"[:31], t["columns"], t["rows"]) for i, t in enumerate(report["tables"])]
    sheets += [
        (
            "Sources",
            ["ID", "Snapshot", "Description"],
            [[s["id"], s["snapshot"], s["description"]] for s in report["sources"]],
        ),
        (
            "Evidence",
            ["ID", "Kind", "Code", "Sources"],
            [[e["id"], e["kind"], e["code"], ", ".join(e["source_ids"])] for e in report["evidence"]],
        ),
        ("Caveats", ["Limitation"], [[c] for c in report["caveats"]]),
    ]
    for name, columns, rows in sheets:
        sheet = workbook.create_sheet(name)
        for row_index, row in enumerate([columns, *rows], 1):
            for column_index, value in enumerate(row, 1):
                cell = sheet.cell(row_index, column_index, value)
                if isinstance(value, str):
                    cell.data_type = "s"  # Never allow generated/source text to become a formula.
                cell.alignment = Alignment(vertical="top", wrap_text=True)
                if row_index == 1:
                    cell.font = Font(name="Calibri", bold=True, color="FFFFFF")
                    cell.fill = PatternFill("solid", fgColor="245B7B")
                elif _finite_number(value):
                    cell.number_format = "#,##0.######"
            sheet.row_dimensions[row_index].height = 28 if row_index == 1 else None
        for index, column in enumerate(columns, 1):
            sheet.column_dimensions[get_column_letter(index)].width = min(60, max(18, len(column) + 5))
        sheet.freeze_panes = "A2"
        sheet.auto_filter.ref = sheet.dimensions
    workbook.save(path)


def _report_html(report: dict) -> str:
    body = [
        f'<header><p class="eyebrow">BackIntel · analytical report</p><h1>{_escape(report["title"])}</h1>',
        f'<p>{_escape(report["summary"])}</p><p class="meta">Run {_escape(report["run_id"])}</p></header>',
        '<nav class="downloads" aria-label="Downloads"><a href="supporting.xlsx">Supporting workbook</a>'
        '<a href="report.json">Structured analysis</a><a href="manifest.json">Artifact manifest</a></nav>',
    ]
    if report["metrics"]:
        body.append('<section class="metrics" aria-label="Key metrics">')
        for m in report["metrics"]:
            body.append(
                f'<div class="metric"><span>{_escape(m["label"])}</span><strong>{_display(m["value"])} '
                f'<span class="unit">{_escape(m["unit"])}</span></strong><p class="note">'
                f"{_escape(m['definition'])}</p></div>"
            )
        body.append("</section>")
    if report["findings"]:
        body.append(
            "<h2>Findings</h2><ul>" + "".join(f"<li>{_escape(f)}</li>" for f in report["findings"]) + "</ul>"
        )
    for chart in report["charts"]:
        body.append(
            f'<figure><img src="charts/{chart["id"]}.png" alt="{_escape(chart["title"])}">'
            f"<figcaption>Table {_escape(chart['table'])} · "
            f'<a href="charts/{chart["id"]}.html">Explore interactive chart</a> · '
            f'<a href="charts/{chart["id"]}.svg">Download SVG</a></figcaption></figure>'
        )
    if report["caveats"]:
        body.append(
            "<h2>Limits of this analysis</h2><ul>"
            + "".join(f"<li>{_escape(c)}</li>" for c in report["caveats"])
            + "</ul>"
        )
    body.append("<h2>Supporting tables</h2>")
    for table in report["tables"]:
        units = "; ".join(f"{c}: {u}" for c, u in table["units"].items())
        body.append(
            f"<details><summary>{_escape(table['title'])} · {len(table['rows']):,} rows</summary>"
            f'<p class="note">{_escape(units)}. Evidence: {_escape(", ".join(table["evidence_ids"]))}. '
            f'<a href="tables/{table["id"]}.csv">Download CSV</a>. First 100 rows shown.</p>'
            f"{_table_html(table)}</details>"
        )
    body.append("<h2>Sources and reproducibility</h2>")
    for source in report["sources"]:
        body.append(
            f'<p class="note"><strong>{_escape(source["id"])}</strong>: {_escape(source["description"])}'
            f"<br>Snapshot: {_escape(source['snapshot'])}</p>"
        )
    for evidence in report["evidence"]:
        body.append(
            f"<details><summary>{_escape(evidence['id'])} · {_escape(evidence['kind'])}</summary>"
            f"<pre>{_escape(evidence['code'])}</pre></details>"
        )
    body.append(
        '<footer><p class="note">Figures, metrics and workbook share the supplied analytical tables. '
        "Bundle checks establish consistency and file integrity, not independent correctness "
        "of the source analysis. Formula-like text is escaped in CSV; original text is retained "
        "in JSON and as text cells in Excel.</p></footer>"
    )
    return _page(report["title"], "".join(body))


def render_report(spec: dict, output_dir: str | Path, *, max_bytes: int = DEFAULT_MAX_BYTES) -> dict:
    """Atomically create a new bundle directory. Existing outputs are never overwritten."""
    report = validate_report(spec)
    if type(max_bytes) is not int or not 1 <= max_bytes <= 1024 * 1024 * 1024:
        raise ValueError("max_bytes must be 1 to 1073741824")
    output = Path(output_dir).absolute()
    if output.exists() or output.is_symlink():
        raise ValueError("output_dir must be a new directory")
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = Path(tempfile.mkdtemp(prefix=".report-", dir=output.parent))
    try:
        (temporary / "charts").mkdir()
        (temporary / "tables").mkdir()
        (temporary / "report.json").write_text(_json(report) + "\n", encoding="utf-8")
        by_table = {t["id"]: t for t in report["tables"]}
        for table in report["tables"]:
            with (temporary / "tables" / f"{table['id']}.csv").open(
                "w", newline="", encoding="utf-8"
            ) as handle:
                writer = csv.writer(handle)
                writer.writerow([_csv_cell(c) for c in table["columns"]])
                writer.writerows([[_csv_cell(v) for v in row] for row in table["rows"]])
        _workbook(report, temporary / "supporting.xlsx")
        for chart in report["charts"]:
            _static_chart(chart, by_table[chart["table"]], temporary / "charts")
            (temporary / "charts" / f"{chart['id']}.html").write_text(
                _interactive(chart, by_table[chart["table"]]), encoding="utf-8"
            )
            if sum(p.stat().st_size for p in temporary.rglob("*") if p.is_file()) > max_bytes:
                raise ValueError("artifact bundle exceeds max_bytes")
        (temporary / "report.html").write_text(_report_html(report), encoding="utf-8")
        artifacts = []
        for path in sorted(temporary.rglob("*")):
            if path.is_file():
                artifacts.append(
                    {
                        "path": path.relative_to(temporary).as_posix(),
                        "media_type": _MEDIA[path.suffix],
                        "bytes": path.stat().st_size,
                        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                    }
                )
        manifest = {
            "schema_version": SCHEMA_VERSION,
            "run_id": report["run_id"],
            "created_at": datetime.now(UTC).isoformat(),
            "report": "report.html",
            "sources": report["sources"],
            "metrics": report["metrics"],
            "evidence_ids": [e["id"] for e in report["evidence"]],
            "validation": "structural consistency; not independent numerical correctness",
            "artifacts": artifacts,
        }
        (temporary / "manifest.json").write_text(_json(manifest) + "\n", encoding="utf-8")
        if sum(a["bytes"] for a in artifacts) + (temporary / "manifest.json").stat().st_size > max_bytes:
            raise ValueError("artifact bundle exceeds max_bytes")
        os.rename(temporary, output)
        return manifest
    except BaseException:
        shutil.rmtree(temporary, ignore_errors=True)
        raise


def verify_bundle(output_dir: str | Path, *, max_bytes: int = DEFAULT_MAX_BYTES) -> dict:
    """Check exported paths, file inventory, checksums and canonical report consistency.

    This is not a signature, a sandbox escape check or an independent correctness oracle.
    """
    root = Path(output_dir)
    if root.is_symlink() or not root.is_dir():
        raise ValueError("bundle must be a real directory")
    root = root.resolve()
    paths = list(root.rglob("*"))
    if len(paths) > 150 or any(p.is_symlink() or not (p.is_file() or p.is_dir()) for p in paths):
        raise ValueError("bundle contains unsupported entries or too many files")
    if sum(p.stat().st_size for p in paths if p.is_file()) > max_bytes:
        raise ValueError("bundle exceeds max_bytes")
    manifest = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
    report = validate_report(json.loads((root / "report.json").read_text(encoding="utf-8")))
    if manifest.get("schema_version") != SCHEMA_VERSION or manifest.get("run_id") != report["run_id"]:
        raise ValueError("manifest identity differs from report")
    if manifest.get("metrics") != report["metrics"] or manifest.get("sources") != report["sources"]:
        raise ValueError("manifest analytical bindings differ from report")
    expected = set()
    for artifact in manifest.get("artifacts", []):
        name = artifact.get("path", "")
        relative = Path(name)
        if (
            relative.is_absolute()
            or ".." in relative.parts
            or "\\" in name
            or relative.as_posix() != name
            or name in expected
            or name == "manifest.json"
        ):
            raise ValueError("invalid or duplicate artifact path")
        path = root / relative
        if (
            not path.is_file()
            or path.suffix not in _MEDIA
            or artifact.get("media_type") != _MEDIA[path.suffix]
        ):
            raise ValueError("missing or unsupported artifact")
        if (
            artifact.get("bytes") != path.stat().st_size
            or artifact.get("sha256") != hashlib.sha256(path.read_bytes()).hexdigest()
        ):
            raise ValueError(f"artifact integrity mismatch: {name}")
        expected.add(name)
    actual = {p.relative_to(root).as_posix() for p in paths if p.is_file()} - {"manifest.json"}
    required = {"report.html", "report.json", "supporting.xlsx"}
    required.update(f"tables/{table['id']}.csv" for table in report["tables"])
    required.update(
        f"charts/{chart['id']}.{ext}" for chart in report["charts"] for ext in ("png", "svg", "html")
    )
    if expected != actual or expected != required:
        raise ValueError("bundle inventory differs from manifest")
    if (root / "report.html").read_text(encoding="utf-8") != _report_html(report):
        raise ValueError("report presentation differs from its analytical specification")
    for table in report["tables"]:
        name = f"tables/{table['id']}.csv"
        if name not in expected:
            raise ValueError("missing supporting CSV")
        expected_csv = io.StringIO(newline="")
        writer = csv.writer(expected_csv)
        writer.writerow([_csv_cell(c) for c in table["columns"]])
        writer.writerows([[_csv_cell(v) for v in row] for row in table["rows"]])
        if (root / name).read_bytes() != expected_csv.getvalue().encode():
            raise ValueError("supporting CSV differs from analytical table")
    return manifest
