"""Generate data-driven Streamlit apps from validated reports; never interpolate executable code."""

from __future__ import annotations

import calendar
import html
import io
import json
import re
import shutil
import tempfile
import textwrap
from datetime import date
from pathlib import Path

from backintel.artifacts import _heatmap, _histogram, validate_report

LAUNCHER = """from pathlib import Path
from backintel.presentation.dashboard import show_dashboard

show_dashboard(Path(__file__).with_name("dashboard.json"))
"""


def label(name: str, unit: str = "") -> str:
    words = name.replace("_", " ").strip()
    words = words[0].upper() + words[1:]
    return f"{words} ({unit})" if unit and unit.lower() not in words.lower().split() else words


def project_report(spec: dict) -> dict:
    report = validate_report(spec)
    # Explicit allowlists prevent arbitrary report extensions and execution metadata
    # from entering the browser. Narrative text remains the analyst's responsibility.
    result = {key: report[key] for key in ("title", "summary", "findings", "caveats")}
    result["sources"] = [{"description": s["description"]} for s in report["sources"]]
    result["tables"] = [
        {key: t[key] for key in ("id", "title", "columns", "rows", "units")} for t in report["tables"]
    ]
    result["metrics"] = [
        {key: m[key] for key in ("label", "definition", "value", "unit")} for m in report["metrics"]
    ]
    result["charts"] = [
        {key: c[key] for key in ("title", "kind", "table", "x", "y", "z", "bins") if key in c}
        for c in report["charts"]
    ]
    return result


def workbook_bytes(data: dict, plan=None) -> bytes:
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Font, PatternFill

    book = Workbook()
    overview = book.active
    overview.title = "Read me"
    overview.append(["Analysis", plan.title if plan else data["title"]])
    overview.append(["Summary", plan.introduction if plan else data["summary"]])
    for source in data.get("sources", []):
        overview.append(["Data source", source["description"]])
    if plan and plan.context:
        for key, value in plan.context.model_dump().items():
            overview.append([key.capitalize(), value])
    findings = [s.takeaway for s in plan.sections] if plan else data["findings"]
    for finding in findings:
        overview.append(["Finding", finding])
    for caveat in data["caveats"]:
        overview.append(["Limit", caveat])
    for metric in data["metrics"]:
        overview.append([metric["label"], metric["definition"]])
    for index, table in enumerate(data["tables"], 1):
        title = re.sub(r"[\\/*?:\[\]]", " ", table["title"]).strip(" '") or "Analysis"
        sheet = book.create_sheet(f"{index} {title}"[:31])
        sheet.append([label(c, table["units"].get(c, "")) for c in table["columns"]])
        for row in table["rows"]:
            sheet.append(row)
        sheet.freeze_panes = "A2"
        sheet.auto_filter.ref = sheet.dimensions
    for sheet in book:
        for row in sheet:
            for cell in row:
                if isinstance(cell.value, str):
                    cell.data_type = "s"
                cell.alignment = Alignment(wrap_text=True, vertical="top")
                if cell.row == 1:
                    cell.fill = PatternFill("solid", fgColor="203646")
                    cell.font = Font(bold=True, color="FFFFFF")
                sheet.column_dimensions[cell.column_letter].width = 28
    overview.column_dimensions["B"].width = 90
    output = io.BytesIO()
    book.save(output)
    return output.getvalue()


def generate_dashboard(spec: dict, destination: Path, *, presentation: dict | None = None) -> dict:
    """Publish a new dashboard atomically; optional UI packages are only needed to serve it."""
    data = project_report(spec)
    from backintel.presentation.design import validate_plan

    plan = validate_plan(presentation, data) if presentation is not None else None
    destination = Path(destination)
    if destination.exists():
        raise ValueError("Use a new dashboard directory; existing deliveries are preserved.")
    destination.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=".dashboard-", dir=destination.parent))
    try:
        (staging / "dashboard.json").write_text(json.dumps(data, ensure_ascii=False, allow_nan=False))
        (staging / "app.py").write_text(LAUNCHER)
        if plan:
            (staging / "presentation.json").write_text(plan.model_dump_json(indent=2))
        (staging / "analysis.xlsx").write_bytes(workbook_bytes(data, plan))
        (staging / "README.md").write_text(
            "# Open this analysis\n\nFrom a BackIntel checkout with the dashboard extra installed:\n\n"
            "`uv run --extra dashboard backintel dashboard serve /path/to/this/directory`\n\n"
            "Serving is local. The app contains aggregate tables, findings and supporting sheets.\n"
        )
        staging.rename(destination)
    finally:
        if staging.exists():
            shutil.rmtree(staging)
    return {"path": str(destination), "entrypoint": "app.py", "status": "generated"}


def category_labels(field: str, values: list) -> list[str]:
    """Format declared month/hour categories without changing coordinates or values.

    First-of-month dates only mean months on a month-named field. Daily dates and
    invalid/ambiguous categories remain literal; no aggregation is inferred.
    """
    name = re.sub(r"[^a-z]", "", field.lower())
    labels = []
    for value in values:
        text = str(value)
        if name in {"month", "yearmonth", "monthstart"} and re.fullmatch(r"\d{4}-\d{2}(?:-01)?", text):
            try:
                month = date.fromisoformat(text[:7] + "-01")
                text = f"{calendar.month_abbr[month.month]} {month.year}"
            except ValueError:
                pass
        elif name in {"hour", "pickuphour"} and re.fullmatch(r"\d{1,2}", text) and 0 <= int(text) < 24:
            hour = int(text)
            text = f"{hour % 12 or 12} {'am' if hour < 12 else 'pm'}"
        labels.append(html.escape(text))
    return labels


def chart_figure(chart: dict, table: dict, design=None):
    import plotly.graph_objects as go

    from backintel.presentation.taxi_story import figure

    def column(name):
        return [row[table["columns"].index(name)] for row in table["rows"]]

    def safe(values):
        return [html.escape(x) if isinstance(x, str) else x for x in values]

    x = column(chart["x"])
    kind = "column" if design and design.encoding == "column" else chart["kind"]
    transposed = False
    f = figure(height=max(340, len(x) * 28 + 80) if kind == "bar" else 360)
    xlabel = html.escape(label(chart["x"], table["units"].get(chart["x"], "")))
    if kind == "histogram":
        centers, counts, width = _histogram(chart, table)
        f.add_trace(go.Bar(x=centers, y=counts, width=width, marker_color="#176581"))
        f.update_xaxes(title=xlabel)
        f.update_yaxes(title="Observations", rangemode="tozero")
    elif kind == "heatmap":
        xs, ys, values = _heatmap(chart, table)
        xfield, yfield = chart["x"], chart["y"]
        # Keep a weekday/hour grid readable on phones without detecting a device,
        # dropping hours, averaging cells, or requiring sideways page scrolling.
        transposed = len(xs) > 12 and len(ys) < len(xs)
        if transposed:
            xs, ys = ys, xs
            values = [list(row) for row in zip(*values, strict=True)]
            xfield, yfield = yfield, xfield
        xlabels, ylabels = category_labels(xfield, xs), category_labels(yfield, ys)
        unit = html.escape(table["units"][chart["z"]])
        cells = [value for row in values for value in row]
        endpoints = sorted({min(cells), max(cells)})
        f.add_trace(
            go.Heatmap(
                x=safe(xs),
                y=safe(ys),
                z=values,
                zmin=endpoints[0],
                zmax=endpoints[-1],
                colorscale=[[0, "#F0F3F3"], [0.4, "#A6C9D1"], [1, "#176581"]],
                xgap=2,
                ygap=2,
                texttemplate="%{z:.1f}" if len(xs) * len(ys) <= 24 else None,
                customdata=[[f"{yname} · {xname}" for xname in xlabels] for yname in ylabels],
                hovertemplate="%{customdata}<br>%{z:,.2f} " + unit + "<extra></extra>",
                colorbar=dict(
                    orientation="h",
                    x=0.1,
                    xanchor="left",
                    y=1.04,
                    yanchor="bottom",
                    len=0.8,
                    thickness=12,
                    outlinewidth=0,
                    tickmode="array",
                    tickvals=endpoints,
                    ticktext=[f"{v:,}".removesuffix(".0") + ("%" if unit == "%" else "") for v in endpoints],
                    title=dict(text="<br>".join(textwrap.wrap(unit, 28)), side="top"),
                ),
            )
        )
        f.update_layout(height=max(390, len(ys) * 25 + 160), margin=dict(l=8, r=8, t=100, b=40))
        f.update_xaxes(
            title=html.escape(label(xfield)),
            type="category",
            tickmode="array",
            tickvals=safe(xs),
            ticktext=xlabels,
            tickangle=0,
        )
        f.update_yaxes(
            title=html.escape(label(yfield)),
            type="category",
            autorange="reversed",
            tickmode="array",
            tickvals=safe(ys),
            ticktext=ylabels,
            showgrid=False,
        )
    else:
        y = column(chart["y"])
        ylabel = html.escape(label(chart["y"], table["units"][chart["y"]]))
        if kind == "column":
            f.add_trace(
                go.Bar(
                    x=safe(x),
                    y=y,
                    marker_color="#176581",
                    text=y,
                    texttemplate="%{y:,.3s}",
                    textposition="outside",
                    cliponaxis=False,
                )
            )
            f.update_xaxes(title=xlabel, type="category")
            f.update_yaxes(title=ylabel, rangemode="tozero")
        elif kind == "bar":
            f.add_trace(
                go.Bar(
                    x=y,
                    y=safe(x),
                    orientation="h",
                    marker_color="#176581",
                    text=[f"{v:,.4g}" for v in y],
                    textposition="outside",
                    cliponaxis=False,
                )
            )
            f.update_layout(margin=dict(l=8, r=75, t=25, b=12))
            f.update_xaxes(title=ylabel, rangemode="tozero")
            f.update_yaxes(title=xlabel, type="category", autorange="reversed", showgrid=False)
        else:
            f.add_trace(
                go.Scatter(
                    x=safe(x),
                    y=y,
                    mode="lines+markers" if kind == "line" else "markers",
                    marker_color="#176581",
                )
            )
            f.update_xaxes(title=xlabel)
            f.update_yaxes(title=ylabel)
    if design:
        # Units remain mandatory even when the writer improves the display name.
        if kind == "bar":
            f.update_xaxes(title=html.escape(label(design.y_label, table["units"].get(chart["y"], ""))))
            f.update_yaxes(title=html.escape(design.x_label))
        elif transposed:
            f.update_xaxes(title=html.escape(design.y_label))
            f.update_yaxes(title=html.escape(design.x_label))
        else:
            f.update_xaxes(title=html.escape(label(design.x_label, table["units"].get(chart["x"], ""))))
            f.update_yaxes(title=html.escape(label(design.y_label, table["units"].get(chart.get("y"), ""))))
    if kind in {"column", "line", "scatter", "bar"}:
        ticks = list(dict.fromkeys(x))
        formatted = category_labels(chart["x"], ticks)
        if formatted != safe(ticks):
            axis = f.update_yaxes if kind == "bar" else f.update_xaxes
            axis(tickmode="array", tickvals=safe(ticks), ticktext=formatted, tickangle=0)
            f.update_traces(customdata=category_labels(chart["x"], x))
            value = "%{x}" if kind == "bar" else "%{y}"
            f.update_traces(
                hovertemplate="%{customdata}<br>"
                + value
                + " "
                + html.escape(table["units"].get(chart["y"], ""))
                + "<extra></extra>"
            )
    f.update_xaxes(automargin=True)
    f.update_yaxes(automargin=True)
    if f.layout.yaxis.title.text:
        f.update_yaxes(
            title="<br>".join(textwrap.wrap(f.layout.yaxis.title.text, 30, break_long_words=False))
        )
    if kind == "heatmap":
        f.update_yaxes(title_standoff=20)
    return f


def plain(text: str) -> str:
    """Escape analyst text for Streamlit labels that only support Markdown."""
    return re.sub(r"([\\`*_{}\[\]()<>#+.!|$~])", r"\\\1", text)


def display_number(value: float) -> str:
    for magnitude, suffix in [(1e9, "bn"), (1e6, "m")]:
        if abs(value) >= magnitude:
            return f"{value / magnitude:,.2f}{suffix}"
    return f"{value:,.2f}".rstrip("0").rstrip(".") if value % 1 else f"{value:,.0f}"


def show_dashboard(path: Path) -> None:
    import pandas as pd
    import streamlit as st

    st.set_page_config(page_title="Analysis · BackIntel", layout="wide")
    try:
        data = json.loads(path.read_text())
    except (OSError, ValueError):
        st.error("This analysis is unavailable. Generate a fresh dashboard from the completed report.")
        return
    if (path.parent / "presentation.json").exists():
        from backintel.presentation.design import validate_plan

        try:
            plan = validate_plan(json.loads((path.parent / "presentation.json").read_text()), data)
        except (ValueError, OSError):
            st.error("The dashboard presentation is invalid. Generate a fresh reviewed version.")
            return
        show_designed_dashboard(data, plan)
        return
    st.text("BackIntel · Analysis")
    st.title(plain(data["title"]))
    st.text(data["summary"], width="stretch")
    st.download_button(
        "Download analysis",
        workbook_bytes(data),
        file_name="analysis.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        on_click="ignore",
    )
    for offset in range(0, len(data["metrics"]), 3):
        for col, metric in zip(st.columns(3), data["metrics"][offset : offset + 3], strict=False):
            col.metric(plain(metric["label"]), display_number(metric["value"]))
            col.text(metric["unit"])
    story, explore, limits = st.tabs(["The story", "Explore", "Definitions & limits"])
    tables = {t["id"]: t for t in data["tables"]}
    with story:
        if data["findings"]:
            with st.expander("Read the key findings", expanded=False):
                for finding in data["findings"]:
                    st.text(finding, width="stretch")
        for index, chart in enumerate(data["charts"]):
            st.header(plain(chart["title"]))
            st.plotly_chart(
                chart_figure(chart, tables[chart["table"]]),
                width="stretch",
                theme=None,
                config={"displayModeBar": False},
                key=f"chart-{index}",
            )
        if not data["charts"]:
            st.info("This analysis contains tables without chart comparisons. Open Explore to read them.")
    with explore:
        selected = st.selectbox(
            "Analysis table", range(len(data["tables"])), format_func=lambda i: data["tables"][i]["title"]
        )
        table = data["tables"][selected]
        df = pd.DataFrame(table["rows"], columns=table["columns"])
        search = st.text_input(
            "Find rows in this table", help="Matches text in any cell; charts keep their full scope."
        )
        if search:
            df = df[
                df.astype(str)
                .apply(lambda col: col.str.contains(search, case=False, regex=False))
                .any(axis=1)
            ]
        if df.empty:
            st.info("No rows match this view.")
        st.dataframe(
            df,
            hide_index=True,
            width="stretch",
            column_config={c: label(c, table["units"].get(c, "")) for c in table["columns"]},
        )
        st.text("Table search affects this view only. Charts and the workbook retain the full analysis.")
    with limits:
        for source in data.get("sources", []):
            st.text(source["description"], width="stretch")
        for metric in data["metrics"]:
            st.header(plain(metric["label"]))
            st.text(metric["definition"], width="stretch")
        for caveat in data["caveats"]:
            st.text(caveat, width="stretch")
        if not data["caveats"]:
            st.info("No limitations were supplied in the report. This does not establish that none exist.")


def show_designed_dashboard(data, plan):
    """Native page navigation over a validated plan; model output is never executable."""
    import pandas as pd
    import streamlit as st

    tables = {t["id"]: t for t in data["tables"]}

    def story(index):
        section = plan.sections[index]
        st.text("BackIntel · Analysis")
        if index == 0:
            st.title(plain(plan.title))
            if plan.context:
                st.text(plan.context.audience + " " + plan.context.decision)
                with st.expander("What data am I looking at?", expanded=True):
                    st.text(plan.context.coverage)
                    st.text(plan.context.limitation)
            st.text(plan.introduction)
            totals = st.expander("Coverage and totals") if plan.context else st.container()
            with totals:
                for offset in range(0, len(data["metrics"]), 3):
                    for col, metric in zip(st.columns(3), data["metrics"][offset : offset + 3], strict=False):
                        col.metric(plain(metric["label"]), display_number(metric["value"]))
                        col.text(metric["unit"])
        st.header(plain(section.title))
        st.text(section.takeaway)
        for offset in range(0, len(section.charts), section.columns):
            columns = st.columns(section.columns)
            for col, design in zip(columns, section.charts[offset : offset + section.columns], strict=False):
                with col:
                    chart = data["charts"][design.chart]
                    st.subheader(plain(design.title))
                    if design.reading_guide:
                        st.text(design.reading_guide)
                    st.plotly_chart(
                        chart_figure(chart, tables[chart["table"]], design),
                        width="stretch",
                        theme=None,
                        config={"displayModeBar": False},
                        key=f"story-{design.chart}",
                        alt=design.title + ". " + design.caption,
                    )
                    if design.caption:
                        st.text(design.caption)
        with st.container(horizontal=True):
            if index:
                st.page_link(pages[index - 1], label=plain("Previous: " + plan.sections[index - 1].title))
            if index + 1 < len(plan.sections):
                st.page_link(pages[index + 1], label=plain("Next: " + plan.sections[index + 1].title))

    def explore():
        st.title("Explore")
        selected = st.selectbox(
            "Analysis table", range(len(data["tables"])), format_func=lambda i: data["tables"][i]["title"]
        )
        table = data["tables"][selected]
        frame = pd.DataFrame(table["rows"], columns=table["columns"])
        search = st.text_input("Find rows in this table")
        if search:
            frame = frame[
                frame.astype(str).apply(lambda c: c.str.contains(search, case=False, regex=False)).any(axis=1)
            ]
        st.dataframe(
            frame,
            hide_index=True,
            width="stretch",
            column_config={c: label(c, table["units"].get(c, "")) for c in table["columns"]},
        )
        if frame.empty:
            st.info("No rows match this view.")
        st.text("Search affects this table only. Charts and the workbook retain the full analysis.")

    def about():
        st.title("About the data")
        for source in data.get("sources", []):
            st.text(source["description"])
        for metric in data["metrics"]:
            st.subheader(plain(metric["label"]))
            st.text(metric["definition"])
        for caveat in data["caveats"]:
            st.text(caveat)
        st.download_button(
            "Download analysis", workbook_bytes(data, plan), file_name="analysis.xlsx", on_click="ignore"
        )

    pages = [
        st.Page(lambda i=i: story(i), title=plain(s.title), url_path=f"section-{i + 1}", default=i == 0)
        for i, s in enumerate(plan.sections)
    ]
    pages.extend(
        [
            st.Page(explore, title="Explore", url_path="explore"),
            st.Page(about, title="About the data", url_path="about"),
        ]
    )
    st.navigation(pages, position="top").run()
