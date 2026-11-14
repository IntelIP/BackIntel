"""An authored Streamlit story over the taxi demonstration's retained aggregate tables."""

import json
import os
from pathlib import Path

import streamlit as st

from backintel.presentation.taxi_story import (
    GLOSSARY,
    LABELS,
    MONTHS,
    airport_chart,
    business_workbook,
    fare_chart,
    frame,
    monthly_chart,
    rhythm_chart,
    summary,
    validate_story,
    zone_chart,
)

st.set_page_config(
    page_title="Taxi operations · BackIntel",
    page_icon="🚕",
    layout="wide",
    menu_items={"Get help": None, "Report a bug": None, "About": None},
)


@st.cache_data(show_spinner=False)
def load_data(path: str, modified: int) -> dict:
    del modified
    return json.loads(Path(path).read_text())


def chart(figure, label, key):
    st.plotly_chart(
        figure,
        width="stretch",
        theme=None,
        key=key,
        config={"displayModeBar": False, "responsive": True},
        on_select="ignore",
    )
    st.markdown(f":small[{label}]")


path = Path(os.environ.get("BACKINTEL_STORY_DATA", "data/output/taxi-story/story.json"))
if not path.is_file():
    st.title("Taxi operations")
    st.info(
        "The analysis is not available yet. Prepare the taxi analysis tables before opening this dashboard."
    )
    st.stop()
try:
    story = load_data(str(path), path.stat().st_mtime_ns)
    validate_story(story)
    totals = summary(story)
except (ValueError, KeyError, TypeError, OSError):
    st.error("The analysis tables could not be opened. Please prepare a fresh copy of the taxi analysis.")
    st.stop()

st.markdown(":small[BackIntel · New York City · January–March 2025]")
heading, download = st.columns([4, 1], vertical_alignment="bottom")
with heading:
    st.title("Plan the next shift with evidence")
    st.markdown(
        "Daily activity, busy hours and the airport tradeoff. "
        "Use the patterns to plan a focused operational trial."
    )
with download:
    st.download_button(
        "Download analysis",
        data=business_workbook(story),
        file_name="nyc-taxi-analysis.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        on_click="ignore",
        width="stretch",
    )

trip, fare, growth = st.columns(3)
trip.metric(
    "Recorded trips",
    f"{totals['trips'] / 1e6:.2f}m",
    help="Reported trips that meet the stated analysis rules.",
)
fare.metric(
    "Gross metered fares",
    f"${totals['fare'] / 1e6:.1f}m",
    help="Recorded metered fares; excludes separate charges and costs.",
)
growth.metric(
    "Daily activity, January → March",
    f"{totals['daily_growth']:+.1f}%",
    help="Change in trips per calendar day, using comparable monthly populations.",
)
st.divider()
story_tab, explore_tab, notes_tab = st.tabs(["The story", "Explore", "Definitions & limits"])
monthly = frame(story, "monthly").set_index("Month")

with story_tab:
    text, visual = st.columns([1, 1.7], gap="large", vertical_alignment="center")
    with text:
        direction = "rose" if totals["daily_growth"] > 0 else "fell"
        st.header(
            "A stronger pace by March"
            if totals["daily_growth"] > 0
            else "A slower pace by March"
            if totals["daily_growth"] < 0
            else "A steady pace from January to March"
        )
        st.write(
            (
                f"Average daily trip activity {direction} from "
                f"**{monthly.loc['2025-01-01'].Trips_per_day:,.0f} "
                f"in January** to **{monthly.loc['2025-03-01'].Trips_per_day:,.0f} in March**. "
                if totals["daily_growth"] != 0
                else "Average daily trip activity was unchanged at "
                f"**{monthly.loc['2025-01-01'].Trips_per_day:,.0f} "
                "in January and March**. "
            )
            + "Comparing daily rates accounts for February’s shorter month."
        )
        st.write(
            "Use this as a historical baseline when planning shifts. It does not establish "
            "the effect of congestion pricing or forecast what happens next."
        )
    with visual:
        chart(
            monthly_chart(story), "Average recorded trips per calendar day · All eligible pickups", "monthly"
        )
    st.divider()
    st.header("Find the busiest hours before changing a shift")
    peak = frame(story, "weekly_hours").sort_values("Trips_per_occurrence").iloc[-1]
    weekday = {
        "Mon": "Monday",
        "Tue": "Tuesday",
        "Wed": "Wednesday",
        "Thu": "Thursday",
        "Fri": "Friday",
        "Sat": "Saturday",
        "Sun": "Sunday",
    }[peak.Weekday]
    hour = int(peak.Hour)
    clock = f"{hour % 12 or 12} {'am' if hour < 12 else 'pm'}"
    st.write(
        f"The hour beginning **{clock} on {weekday}** averaged **{peak.Trips_per_occurrence:,.0f} pickups**, "
        "the highest weekday-hour average in the quarter. Darker cells show more recorded pickups."
    )
    chart(
        rhythm_chart(story),
        "Average pickups per occurrence of each weekday and hour · New York local time",
        "rhythm",
    )
    st.divider()
    text, visual = st.columns([1, 1.7], gap="large", vertical_alignment="center")
    with text:
        st.header("Airport fares punch above their trip share")
        st.write(
            f"JFK and LaGuardia together account for **{totals['airport_trip_share']:.1f}% of trips** "
            f"and **{totals['airport_fare_share']:.1f}% of metered fares**."
        )
        st.write(
            "Larger fares do not prove a more productive shift. Airport queues, return journeys "
            "and idle time could change the decision."
        )
    with visual:
        chart(
            airport_chart(story),
            "Share of all eligible quarterly trips and metered fares · Airport pickups only",
            "airport",
        )
    st.subheader("Put the patterns to work")
    evening, airport = st.columns(2, gap="large")
    with evening.container(border=True):
        st.markdown("### Trial an evening overlap")
        st.write(
            "Compare a modest shift overlap around busy evenings with similar unchanged shifts. "
            "Track pickup waits, vehicle availability and net receipts per vehicle-hour."
        )
    with airport.container(border=True):
        st.markdown("### Compare airport and city positioning")
        st.write(
            "Alternate matched shifts between airport staging and a core-city route. "
            "Include queue, repositioning and operating costs before expanding the trial."
        )

with explore_tab:
    st.header("Where recorded fares concentrate")
    st.write(
        "JFK and LaGuardia lead this ranking by fare value. City pickup areas still contribute "
        "substantial trip volume, so a useful trial needs a city comparator."
    )
    chart(
        zone_chart(story), "Ten pickup zones with the highest quarterly metered fares · US dollars", "zones"
    )
    st.header("Keep everyday fares in view")
    band = frame(story, "fare_bands").iloc[1]
    st.write(
        f"**{band.Trip_share_pct:.1f}% of eligible trips had metered fares from $10 to below $20.** "
        "A strategy based only on the largest ticket could overlook the everyday core."
    )
    chart(
        fare_chart(story),
        "Share of eligible quarterly trips by metered fare · Upper bounds are exclusive, except $1,000",
        "fares",
    )
    st.divider()
    st.header("Airport mix changes by month")
    selected = st.selectbox("Month", list(MONTHS.values()), index=2, key="month")
    date = next(key for key, value in MONTHS.items() if value == selected)
    month = frame(story, "monthly").set_index("Month").loc[date]
    first, second = st.columns(2)
    first.metric(f"{selected} trips per day", f"{month.Trips_per_day:,.0f}")
    second.metric(f"{selected} average metered fare", f"${month.Mean_fare_USD:.2f}")
    chart(
        airport_chart(story, date[:7]),
        f"{selected} airport share of all eligible monthly trips and metered fares",
        "month-mix",
    )

with notes_tab:
    st.header("A useful view, with clear limits")
    st.write(
        "This is an analysis of reported yellow-taxi activity, not a count of unique vehicles "
        "or a measure of unmet demand. It uses the January–March 2025 NYC TLC files."
    )
    for term, explanation in GLOSSARY[:-1]:
        with st.expander(term):
            st.write(explanation)
    st.subheader("How the analysis population was selected")
    coverage = frame(story, "quality")
    st.write(
        f"The source contains {coverage.iloc[0].Records:,.0f} records. The common eligibility rules retain "
        f"{totals['trips']:,.0f} records. The final $1,000 fare guardrail excludes "
        f"{coverage.iloc[6].Records:,.0f} otherwise eligible "
        "records; it is a pragmatic choice, not proof that those records are wrong."
    )
    quality = frame(story, "quality").rename(columns=LABELS)
    st.dataframe(quality, hide_index=True, width="stretch")
    st.markdown(
        ":small[Rows after ‘Eligible records’ describe subsets or the tail screen; do not add them together.]"
    )
    st.markdown(
        "Source: [NYC Taxi & Limousine Commission]"
        "(https://www.nyc.gov/site/tlc/about/tlc-trip-record-data.page). "
        "Reporting errors and unobserved activity remain possible."
    )
