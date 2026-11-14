"""A curated taxi story: public language and figures, separate from execution metadata."""

from __future__ import annotations

import io
import json
import math
from decimal import Decimal
from pathlib import Path

MONTHS = {"2025-01-01": "January", "2025-02-01": "February", "2025-03-01": "March"}
DAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
AIRPORTS = ("JFK", "LaGuardia")
FARE_BANDS = ["<$10", "$10–<20", "$20–<40", "$40–<80", "$80–1,000"]
INK, BLUE, AMBER, MUTED = "#203646", "#176581", "#B66A13", "#65747B"

# These labels are the presentation contract. Source field names never become axis copy.
LABELS = {
    "Month": "Month",
    "Trips": "Recorded trips",
    "Calendar_days": "Calendar days",
    "Trips_per_day": "Trips per day",
    "Gross_fare_USD": "Metered fares ($)",
    "Fare_per_day_USD": "Metered fares per day ($)",
    "Mean_fare_USD": "Average fare ($)",
    "Median_fare_USD": "Median fare ($)",
    "Passenger_charges_USD": "Passenger charges ($)",
    "Weekday": "Day of week",
    "Hour": "Hour",
    "Trips_per_occurrence": "Average hourly pickups",
    "Fare_per_occurrence_USD": "Average hourly fares ($)",
    "Pickup_zone": "Pickup zone",
    "Trip_share_pct": "Share of trips (%)",
    "Fare_share_pct": "Share of metered fares (%)",
    "Fare_band": "Metered fare",
    "Pickup_segment": "Pickup area",
    "Population": "Coverage step",
    "Records": "Records",
    "Recorded_fare_USD": "Recorded metered fares ($)",
}
TITLES = {
    "monthly": "Monthly overview",
    "weekly_hours": "Hourly patterns",
    "zones": "Pickup zones",
    "fare_bands": "Fare distribution",
    "segments": "Airport mix",
    "quality": "Data coverage",
}
QUALITY_LABELS = {
    "01 Source rows": "Source records",
    "02 Q1 pickup": "Pickups within the quarter",
    "03 Paid codes": "Eligible payment types",
    "04 Positive charges": "Positive recorded fares and charges",
    "05 Valid duration": "Valid trip durations",
    "06 Eligible": "Eligible records",
    "07 Tail sensitivity": "Records above the fare guardrail",
    "08 Missing passengers": "Missing passenger counts, retained",
    "09 Invalid distance": "Invalid distances, retained",
    "10 Unmatched pickups": "Unmatched pickup zones",
}
TEXT_COLUMNS = {"Month", "Weekday", "Pickup_zone", "Fare_band", "Pickup_segment", "Population"}
GLOSSARY = [
    ["Recorded trips", "Eligible reported trip records; not vehicles, passengers or unmet demand."],
    [
        "Metered fares",
        "Recorded time-and-distance fares in US dollars, before separate tips, taxes and surcharges. "
        "These are not profit or audited cash receipts.",
    ],
    [
        "Eligible records",
        "Pickup in January–March 2025; Flex Fare, card or cash payment; positive finite fare and "
        "passenger charge; duration above zero and no longer than 24 hours; metered fare at most $1,000.",
    ],
    [
        "Daily comparisons",
        "Monthly totals divided by every calendar day in that month, including quiet days.",
    ],
    ["Hourly patterns", "Pickups for each day/hour divided by occurrences of that weekday in the quarter."],
    [
        "Airport mix",
        "JFK and LaGuardia pickup zones. Shares use all eligible trips or metered fares "
        "for the selected period.",
    ],
    [
        "Time and missing data",
        "Local New York civil time is assumed. Daylight saving is not corrected. Missing passenger "
        "counts and invalid distances are retained; no occupancy or mileage claims are made.",
    ],
    [
        "Interpretation",
        "Historical patterns support small operational trials. Costs, idle time, queues, fleet availability "
        "and unmet demand are absent; causal congestion-pricing effects are not established.",
    ],
    [
        "Source",
        "NYC Taxi & Limousine Commission, yellow taxi records and zone lookup, January–March 2025. https://www.nyc.gov/site/tlc/about/tlc-trip-record-data.page",
    ],
]


def validate_story(story: dict) -> None:
    """Reject incomplete aggregate projections before displaying part of a story."""
    required = {
        "monthly": {"Month", "Trips", "Gross_fare_USD", "Trips_per_day", "Mean_fare_USD"},
        "weekly_hours": {"Weekday", "Hour", "Trips_per_occurrence"},
        "zones": {"Pickup_zone", "Trips", "Gross_fare_USD", "Trip_share_pct", "Fare_share_pct"},
        "fare_bands": {"Fare_band", "Trip_share_pct"},
        "segments": {
            "Month",
            "Pickup_segment",
            "Trips",
            "Gross_fare_USD",
            "Trip_share_pct",
            "Fare_share_pct",
        },
        "quality": {"Population", "Records"},
    }
    for name, columns in required.items():
        table = story["tables"][name]
        if not columns <= set(table["columns"]) or not table["rows"]:
            raise ValueError(f"Incomplete {name} table.")
        for row in table["rows"]:
            if len(row) != len(table["columns"]):
                raise ValueError(f"Invalid {name} row.")
            for column, value in zip(table["columns"], row, strict=True):
                if column in TEXT_COLUMNS:
                    if not isinstance(value, str) or not value.strip():
                        raise ValueError(f"Invalid label in {name}.{column}.")
                else:
                    if type(value) not in (int, float):
                        raise ValueError(f"Nonnumeric value in {name}.{column}.")
                    if not math.isfinite(value):
                        raise ValueError(f"Non-finite value in {name}.{column}.")
                    if value < 0:
                        raise ValueError(f"Negative value in {name}.{column}.")
                    if column in {"Trips", "Records", "Calendar_days", "Hour"} and value % 1:
                        raise ValueError(f"Fractional count in {name}.{column}.")
                    if column.endswith("_pct") and value > 100:
                        raise ValueError(f"Percentage outside 0–100 in {name}.{column}.")
                    if column == "Calendar_days" and not 1 <= value <= 31:
                        raise ValueError("Calendar days must be between 1 and 31.")
    monthly = frame(story, "monthly")
    if list(monthly.Month) != list(MONTHS) or (monthly.Trips_per_day <= 0).any():
        raise ValueError("This story requires the complete January–March 2025 monthly view.")
    if monthly.Trips.sum() <= 0 or monthly.Gross_fare_USD.sum() <= 0:
        raise ValueError("Quarterly trip and fare totals must be positive.")
    hours = frame(story, "weekly_hours")
    if set(zip(hours.Weekday, hours.Hour, strict=True)) != {
        (day, hour) for day in DAYS for hour in range(24)
    }:
        raise ValueError("Incomplete weekday/hour coverage.")
    if hours.duplicated(["Weekday", "Hour"]).any():
        raise ValueError("Repeated weekday/hour values.")
    if list(frame(story, "fare_bands").Fare_band) != FARE_BANDS or list(
        frame(story, "quality").Population
    ) != list(QUALITY_LABELS.values()):
        raise ValueError("Incomplete fare or coverage table.")
    if len(frame(story, "zones")) != 10:
        raise ValueError("The pickup-zone ranking must contain exactly ten rows.")
    for name, key, expected in [
        ("zones", "Pickup_zone", {"JFK Airport", "LaGuardia Airport"}),
        ("segments", "Pickup_segment", set(AIRPORTS)),
    ]:
        data = frame(story, name)
        if not expected <= set(data[key]):
            raise ValueError("Missing airport comparison.")
        if data.duplicated((["Month"] if name == "segments" else []) + [key]).any():
            raise ValueError("Repeated pickup areas.")
    segments = frame(story, "segments")
    if set(segments.Month) != {date[:7] for date in MONTHS}:
        raise ValueError("Airport mix must cover only January–March 2025.")
    for month in (date[:7] for date in MONTHS):
        if not set(AIRPORTS) <= set(segments[segments.Month == month].Pickup_segment):
            raise ValueError("Incomplete monthly airport coverage.")
    zones = frame(story, "zones")
    airports = zones[zones.Pickup_zone.isin(["JFK Airport", "LaGuardia Airport"])]
    for column in ("Trips", "Gross_fare_USD"):
        if sum(Decimal(str(x)) for x in airports[column]) > sum(Decimal(str(x)) for x in monthly[column]):
            raise ValueError("Airport totals cannot exceed the quarterly trip or fare totals.")
    comparisons = [(zones, monthly)] + [
        (segments[segments.Month == date[:7]], monthly[monthly.Month == date]) for date in MONTHS
    ]
    for rows, population in comparisons:
        for column, share in (("Trips", "Trip_share_pct"), ("Gross_fare_USD", "Fare_share_pct")):
            denominator = sum(Decimal(str(x)) for x in population[column])
            if denominator <= 0 or sum(Decimal(str(x)) for x in rows[column]) > denominator:
                raise ValueError("Pickup-area totals exceed or lack their stated population.")
            # Source percentages are rounded to two decimal places.
            if any(
                abs(Decimal(str(pct)) - 100 * Decimal(str(value)) / denominator) > Decimal("0.01")
                for value, pct in zip(rows[column], rows[share], strict=True)
            ):
                raise ValueError("Pickup-area shares disagree with their stated population.")
            airport_rows = rows[rows.Pickup_segment.isin(AIRPORTS)] if "Month" in rows else airports
            if airport_rows[share].sum() > 100.01:
                raise ValueError("Combined airport shares exceed 100%.")
    quality = frame(story, "quality").set_index("Population").Records
    funnel = [quality[label] for label in list(QUALITY_LABELS.values())[:6]]
    if any(later > earlier for earlier, later in zip(funnel, funnel[1:], strict=False)):
        raise ValueError("Coverage funnel counts must not increase.")
    # The retained SQL defines Eligible after the fare guardrail, not before it.
    if (
        funnel[-2] - quality["Records above the fare guardrail"] != funnel[-1]
        or funnel[-1] != monthly.Trips.sum()
    ):
        raise ValueError("Coverage eligibility and fare exclusions disagree with retained trips.")
    if any(quality[label] > funnel[-1] for label in list(QUALITY_LABELS.values())[7:]):
        raise ValueError("Retained coverage subsets exceed eligible records.")


def prepare_story(report: dict) -> dict:
    """Project only the six relevant tables; never publish run, source-snapshot or evidence objects."""
    source = {table["id"]: table for table in report["tables"]}
    tables = {}
    for name in TITLES:
        table = source[name]
        columns = [c for c in table["columns"] if c in LABELS]
        positions = [table["columns"].index(c) for c in columns]
        rows = [[row[i] for i in positions] for row in table["rows"]]
        if name == "weekly_hours":
            hour = columns.index("Hour")
            for row in rows:
                if isinstance(row[hour], str) and row[hour].isdecimal():
                    row[hour] = int(row[hour])
        if name == "quality":
            population = columns.index("Population")
            names = [row[population] for row in rows]
            if len(names) != len(QUALITY_LABELS) or set(names) != set(QUALITY_LABELS):
                raise ValueError("Unexpected or repeated coverage population labels.")
            by_name = dict(zip(names, rows, strict=True))
            rows = [by_name[name] for name in QUALITY_LABELS]
            for row, label in zip(rows, QUALITY_LABELS.values(), strict=True):
                row[population] = label
        tables[name] = {"columns": columns, "rows": rows}
    story = {
        "title": "Plan the next shift with evidence",
        "period": "January–March 2025",
        "source": "NYC TLC yellow taxis",
        "tables": tables,
    }
    validate_story(story)
    return story


def frame(story: dict, name: str):
    import pandas as pd

    table = story["tables"][name]
    return pd.DataFrame(table["rows"], columns=table["columns"])


def summary(story: dict) -> dict:
    monthly, zones = frame(story, "monthly"), frame(story, "zones")
    trips = int(monthly.Trips.sum())
    fare = sum(Decimal(str(x)) for x in monthly.Gross_fare_USD)
    airport = zones[zones.Pickup_zone.isin(["JFK Airport", "LaGuardia Airport"])]
    return {
        "trips": trips,
        "fare": float(fare),
        "daily_growth": (monthly.iloc[-1].Trips_per_day / monthly.iloc[0].Trips_per_day - 1) * 100,
        "airport_trip_share": 100 * int(airport.Trips.sum()) / trips,
        "airport_fare_share": float(100 * sum(Decimal(str(x)) for x in airport.Gross_fare_USD) / fare),
    }


def business_workbook(story: dict) -> bytes:
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Font, PatternFill
    from openpyxl.utils import get_column_letter

    workbook = Workbook()
    workbook.remove(workbook.active)
    for name in TITLES:
        table = story["tables"][name]
        sheet = workbook.create_sheet(TITLES[name])
        sheet.append([LABELS[c] for c in table["columns"]])
        for row in table["rows"]:
            sheet.append(row)
    sheet = workbook.create_sheet("Definitions")
    sheet.append(["Measure", "Meaning"])
    for row in GLOSSARY:
        sheet.append(row)
    for sheet in workbook:
        sheet.freeze_panes = "A2"
        sheet.auto_filter.ref = sheet.dimensions
        for row in sheet:
            for cell in row:
                if isinstance(cell.value, str):
                    cell.data_type = "s"
                cell.alignment = Alignment(vertical="top", wrap_text=True)
                if cell.row == 1:
                    cell.fill = PatternFill("solid", fgColor="203646")
                    cell.font = Font(name="Calibri", bold=True, color="FFFFFF")
                elif isinstance(cell.value, (int, float)):
                    cell.number_format = "#,##0.##"
        for i in range(1, sheet.max_column + 1):
            sheet.column_dimensions[get_column_letter(i)].width = 26 if i > 1 else 34
        if sheet.title == "Definitions":
            sheet.column_dimensions["B"].width = 95
    output = io.BytesIO()
    workbook.save(output)
    return output.getvalue()


def figure(*, height=330):
    import plotly.graph_objects as go

    f = go.Figure()
    f.update_layout(
        height=height,
        margin=dict(l=8, r=20, t=25, b=12),
        font=dict(family="Arial, sans-serif", size=14, color=INK),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        showlegend=False,
        hoverlabel=dict(bgcolor="white", font_color=INK),
    )
    f.update_xaxes(showgrid=False, zeroline=False, automargin=True)
    f.update_yaxes(gridcolor="#E4E2DB", zeroline=False, automargin=True)
    return f


def monthly_chart(story: dict):
    import plotly.graph_objects as go

    data = frame(story, "monthly")
    f = figure(height=310)
    f.add_trace(
        go.Bar(
            x=[MONTHS[x] for x in data.Month],
            y=data.Trips_per_day,
            marker_color=["#BACBD0", "#7297A5", BLUE],
            width=0.52,
            text=[f"{n / 1000:.1f}k" for n in data.Trips_per_day],
            textposition="outside",
            cliponaxis=False,
            hovertemplate="%{x}<br>%{y:,.0f} trips per day<extra></extra>",
        )
    )
    f.update_yaxes(range=[0, max(1, max(data.Trips_per_day) * 1.15)], tickformat="~s")
    f.update_xaxes(type="category", tickfont_size=15)
    return f


def rhythm_chart(story: dict):
    import plotly.graph_objects as go

    data = frame(story, "weekly_hours")
    values = data.pivot(index="Weekday", columns="Hour", values="Trips_per_occurrence").reindex(DAYS)
    f = figure(height=340)
    f.add_trace(
        go.Heatmap(
            z=values.values,
            x=list(range(24)),
            y=DAYS,
            zmin=0,
            colorscale=[[0, "#F0F3F3"], [0.4, "#A6C9D1"], [1, BLUE]],
            xgap=2,
            ygap=3,
            showscale=False,
            hovertemplate="%{y}, %{x}:00<br>%{z:,.0f} average pickups<extra></extra>",
        )
    )
    f.update_xaxes(tickvals=[0, 6, 12, 18, 23], ticktext=["Midnight", "6 am", "Noon", "6 pm", "11 pm"])
    f.update_yaxes(autorange="reversed", showgrid=False)
    return f


def airport_chart(story: dict, month: str | None = None):
    import plotly.graph_objects as go

    if month:
        data = frame(story, "segments")
        data = data[(data.Month == month) & data.Pickup_segment.isin(AIRPORTS)].set_index("Pickup_segment")
    else:
        data = frame(story, "zones")
        data = data[data.Pickup_zone.isin(["JFK Airport", "LaGuardia Airport"])].copy()
        data.index = data.Pickup_zone.map({"JFK Airport": "JFK", "LaGuardia Airport": "LaGuardia"})
    f = figure(height=280)
    for field, label, color in [
        ("Trip_share_pct", "Share of trips", BLUE),
        ("Fare_share_pct", "Share of fares", AMBER),
    ]:
        v = [float(data.loc[name, field]) for name in AIRPORTS]
        f.add_trace(
            go.Bar(
                y=list(AIRPORTS),
                x=v,
                name=label,
                orientation="h",
                marker_color=color,
                text=[f"{x:.1f}%" for x in v],
                textposition="outside",
                cliponaxis=False,
                hovertemplate=f"%{{y}}<br>{label}: %{{x:.2f}}%<extra></extra>",
            )
        )
    f.update_layout(barmode="group", bargap=0.4, showlegend=True, legend=dict(orientation="h", y=1.25, x=0))
    f.update_xaxes(
        range=[0, max(1, max(value for trace in f.data for value in trace.x) * 1.15)],
        ticksuffix="%",
        showgrid=True,
        gridcolor="#E4E2DB",
    )
    f.update_yaxes(autorange="reversed", showgrid=False)
    return f


def zone_chart(story: dict):
    import plotly.graph_objects as go

    data = frame(story, "zones").sort_values("Gross_fare_USD")
    f = figure(height=480)
    f.update_layout(margin=dict(l=8, r=65, t=25, b=12))
    f.add_trace(
        go.Bar(
            y=data.Pickup_zone,
            x=data.Gross_fare_USD / 1e6,
            orientation="h",
            marker_color=[
                AMBER if x in ("JFK Airport", "LaGuardia Airport") else BLUE for x in data.Pickup_zone
            ],
            text=[f"${x / 1e6:.1f}m" for x in data.Gross_fare_USD],
            textposition="outside",
            cliponaxis=False,
            hovertemplate="%{y}<br>$%{x:.2f}m in metered fares<extra></extra>",
        )
    )
    f.update_xaxes(
        range=[0, max(0.001, max(data.Gross_fare_USD) / 1e6 * 1.15)],
        tickprefix="$",
        ticksuffix="m",
        showgrid=True,
        gridcolor="#E4E2DB",
    )
    f.update_yaxes(showgrid=False, tickfont_size=12)
    return f


def fare_chart(story: dict):
    import plotly.graph_objects as go

    data = frame(story, "fare_bands")
    f = figure(height=320)
    labels = ["Below $10", "$10–20", "$20–40", "$40–80", "$80–1,000"]
    f.add_trace(
        go.Bar(
            y=labels,
            x=data.Trip_share_pct,
            orientation="h",
            marker_color=[BLUE, AMBER, BLUE, BLUE, BLUE],
            text=[f"{x:.1f}%" for x in data.Trip_share_pct],
            textposition="outside",
            cliponaxis=False,
            hovertemplate="%{y}<br>%{x:.2f}% of trips<extra></extra>",
        )
    )
    f.update_xaxes(
        range=[0, max(1, max(data.Trip_share_pct) * 1.15)], ticksuffix="%", showgrid=True, gridcolor="#E4E2DB"
    )
    f.update_yaxes(autorange="reversed", showgrid=False)
    return f


def write_story(source: Path, destination: Path) -> Path:
    destination.mkdir(parents=True, exist_ok=True)
    story = prepare_story(json.loads(source.read_text()))
    target = destination / "story.json"
    target.write_text(json.dumps(story, ensure_ascii=False, indent=2) + "\n")
    (destination / "taxi-analysis.xlsx").write_bytes(business_workbook(story))
    return target
