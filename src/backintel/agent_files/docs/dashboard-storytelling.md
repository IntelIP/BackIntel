# Dashboard storytelling reference pack

Use this through the read-only instruction filesystem. No internet retrieval is needed
during analysis. This small curated pack uses progressive disclosure through the
`dashboard-storytelling` skill; it is not a vector database or a trained model.

## What a report should look like

Assume the reader has never seen the analytical brief. Establish who would use this,
what decision it supports, the ordinary source, dates and population, and whether the
business scenario is illustrative. Do not silently treat public market data as the
reader's own company data. Explain unfamiliar charts in a short reading guide: what a
mark represents, what color means, and the relevant denominator. Follow the finding
with its business implication and one material limit; avoid repeating the same claim
across the title, takeaway and caption. Put detailed totals and methods behind disclosure.

1. **A useful headline.** Name the decision or the strongest supported finding. State the
   source and time period in ordinary language.
2. **A short readout.** Two or three measures with definitions, units and an appropriate
   comparison. Avoid a wall of metric cards.
3. **The story.** A few findings, each with one chart and a plain-language explanation.
   Separate what happened from a proposed action. Put a material caveat beside the claim.
4. **Exploration.** Relevant comparisons or filters for readers who want detail. Controls
   should answer a real question, not add decorative interactivity.
5. **Meaning and limits.** Definitions, coverage, exclusions, source names and limitations.
6. **Supporting analysis.** A readable workbook with the same measures and human headers.

Keep execution metadata and code outside this business surface. Do not hide material
uncertainty or the identity of the ordinary data source.

## Choose the encoding, then the styling

| Analytical question | Starting point | Important check |
| --- | --- | --- |
| Compare a few months | Columns with direct values | Calendar-day normalization when month lengths differ; zero baseline |
| Continuous trend over many dates | Line | Actual dates, gaps and incomplete periods |
| Rank named places or products | Sorted horizontal bars | Full names, comparable population, units |
| Compare two shares for each group | Grouped bars or dots | Same denominator/time; common scale; text identifies both measures |
| Compare patterns across day and hour | Sequential heatmap | Normalize unequal weekday counts; label scale and timezone |
| Describe a distribution | Histogram or ordered bins | Disclose bin bounds, exclusions and denominator |

Use one neutral text color, one primary series color and a purposeful accent. Color must
not be the only way to identify a series. Avoid gradients on ordinary bars, unnecessary
3D, truncated bar scales, repeated legends, raw field names and unreadable tiny labels.
Chart titles should explain a supported comparison, not say “Chart 1” or repeat a table ID.

Name the quantity precisely. “Recorded trips” is not “Demand”. “Metered fares” is not
profit. “Average daily trips” is not a monthly total. A fare range is not a trip-distance
range. Preserve unrounded values in supporting data and round display values consistently.

## Framework boundaries

Streamlit's native layout, tabs, controls and Plotly support suit the current local Python
presentation. Prefer native themes and bundled fonts to CSS selectors or remote fonts.
Cache immutable aggregate data, not credentials. The host owns serving and dependency
installation. Streamlit is not currently installed in the qualified analysis image and
the host now generates a Streamlit dashboard after verified report export.

Reflex is a viable future Python UI option where a separately built frontend and backend
are justified. Do not change the chosen framework or hosting inside a bounded analysis.

## Curated references

Reviewed 2026-11-14. These links document the guidance; offline analysis uses this text.

- [Streamlit design practices](https://docs.streamlit.io/develop/concepts/design/best-practices):
  native layout, useful organization and contextual help.
- [Streamlit themes](https://docs.streamlit.io/develop/concepts/configuration/theming) and
  [bundled fonts](https://docs.streamlit.io/develop/concepts/configuration/theming-customize-fonts):
  a consistent local presentation without fetching public font assets.
- [Plotly in Streamlit](https://docs.streamlit.io/develop/api-reference/charts/st.plotly_chart):
  explicit widths, chart behavior and interaction settings.
- [Datawrapper chart guide](https://www.datawrapper.de/blog/chart-types-guide): choose a
  chart from the question and data shape; a few discrete dates work well as columns.
- [Streamlit gallery](https://streamlit.io/gallery): examples of focused analytical apps.

References are design guidance, not copied dashboard code, benchmark answers or evidence
that an agent-generated presentation has passed review.
