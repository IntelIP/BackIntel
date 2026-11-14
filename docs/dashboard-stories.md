# Dashboard stories

The owner selected a Python dashboard direction on 2026-11-14: readable analysis and
storytelling, without execution IDs, hashes or manifest vocabulary in the business view.
The first implementation is a trusted **Streamlit taxi story** over the retained
January–March 2025 aggregate tables. It does not rerun the agent or change its historical
benchmark scores.

## The reader's experience

The opening view explains the decision, shows three defined measures, then develops a
small number of findings. Each finding has a chart, a plain-language interpretation and
limits that matter to the decision. An Explore tab provides rankings, a fare distribution
and a month-specific airport comparison. Definitions & limits explains the population and
quality rules. Download analysis returns a business workbook with readable sheet/column
names and the same underlying aggregates.

The typography uses bundled Source Serif headings and Source Sans body text on a warm
background. Navy text, blue measures and an amber comparison keep the visual language
consistent. Native Streamlit components provide keyboard controls and narrow-screen
stacking. Plotly charts use direct labels, explicit units and meaningful ordering.

This replaces the taxi demonstration's business-facing HTML presentation. Engineering
records remain available separately for debugging and reproducibility; they are not
included in dashboard cards, chart labels or the downloaded business workbook.

## Run locally

Python 3.12 is the tested project environment. Install the optional presentation packages:

```bash
uv sync --frozen --extra dashboard
uv run --extra dashboard python scripts/prepare_taxi_dashboard.py \
  --report /path/to/taxi/report.json \
  --output data/output/taxi-story
uv run --extra dashboard streamlit run dashboards/taxi/streamlit_app.py --server.port 8503
```

Open <http://127.0.0.1:8503>. To use another prepared data location, set
`BACKINTEL_STORY_DATA` to its `story.json` before starting Streamlit. The input is the
retained taxi report specification, not raw Parquet or an arbitrary report. The adapter
requires this demonstration's six table shapes and complete quarterly comparisons.
Raw source records are never sent to the browser; this app reads only aggregate tables.
The preparation command also writes `taxi-analysis.xlsx` beside the projected data.

The server binds to loopback. No cloud resource, paid API or model account is required.
The configuration disables usage telemetry and uses local fonts and bundled chart assets.
It does not load scripts, fonts or data from a CDN. The ordinary source link opens only
when the reader follows it.

## Framework decision

Streamlit 1.67.0 and Plotly 7.1.0 are pinned in the optional `dashboard` extra. Streamlit
uses the existing Python workflow and serves native controls without maintaining a
separate frontend build. Reflex can produce richer application interactions, but its
self-hosting model involves a compiled frontend and Python backend with WebSockets.
That added serving machinery is unnecessary for this first local analysis story.

Streamlit is maintained by Snowflake, a US company; Snowflake's acquisition of Streamlit
is documented in its filings and official announcement. The selection adds no inference
provider or model. This is a framework provenance decision, not a certification of every
contributor or dependency. Plotly reuses the version already selected for the sandbox
charting stack. No code or dependency from the third-party React references was installed.

Primary references reviewed on 2026-11-14:

- [Streamlit design practices](https://docs.streamlit.io/develop/concepts/design/best-practices),
  [themes](https://docs.streamlit.io/develop/concepts/configuration/theming),
  [fonts](https://docs.streamlit.io/develop/concepts/configuration/theming-customize-fonts),
  [Plotly API](https://docs.streamlit.io/develop/api-reference/charts/st.plotly_chart) and
  [app testing](https://docs.streamlit.io/develop/concepts/app-testing).
- [Reflex self-hosting](https://reflex.dev/docs/hosting/self-hosting/): frontend/backend
  deployment requirements inform the framework comparison.
- [Datawrapper chart selection](https://www.datawrapper.de/blog/chart-types-guide):
  discrete monthly columns, ordered bars and appropriate comparison encodings.
- [Streamlit gallery](https://streamlit.io/gallery): focused app structure and exploration.
- [21st.dev Advanced Stats by UI Layouts](https://21st.dev/@uilayout.contact/components/advanced-stats)
  and Analytics Bento by Roman Vasnev: layout references. Retrieved Advanced Stats source
  illustrates chart/summary grouping; its animations, area chart and tiny uppercase KPI
  labels were not adopted. Native Streamlit primitives implement the original composition.
- [Snowflake Streamlit announcement](https://www.snowflake.com/en/news/press-releases/snowflake-disrupts-application-development-with-general-availability-of-snowpark-for-python-native-streamlit-support-and-more-2/)
  and [Snowflake filing](https://investors.snowflake.com/files/doc_financials/2023/q4/0d4be772-30ac-4017-a78b-a5eaa081840e.pdf).

## Agent guidance and boundaries

`dashboard-storytelling` is a new on-demand analysis skill. Its local reference pack covers
story structure, naming, chart choice, source meaning and the separation of business
presentation from engineering records. This is small, curated retrieval through existing
instruction tools, rather than a new vector database. No reference answers or taxi-specific
expected numbers are added to runtime guidance.

The taxi-specific app remains an authored showcase. Automatic generation now uses a
separate generic adapter for every supported report, independent of domain/table names.
After clean export and bundle verification, `run_analysis` creates `dashboard/` containing
`app.py`, a business-data projection, `analysis.xlsx` and launch instructions. Generation
uses the existing validated report and makes no model calls. Failure to generate fails
completion; refusals and export failures do not deliver a dashboard. Existing engineering
bundles and their integrity records remain separate. Automatic generation shares the original
`analyze --timeout` deadline even when design review is disabled. The existing generator
runs in an owned child process so workbook styling and serialization can be stopped on
expiry or cancellation. Only an in-budget result is published; staged files are removed
on failure, and the run cannot report analytical completion after generation times out.

To convert any retained report without another agent run:

```bash
uv run backintel dashboard generate --report /path/to/report.json --output data/output/dashboard
uv run --extra dashboard backintel dashboard serve data/output/dashboard --port 8504
```

The generic app supports the report contract's bar, line, scatter, histogram and heatmap
charts, bound KPI values, findings, definitions, caveats, selectable tables and literal
text search. Search only filters the selected table view; charts and downloads retain
full declared populations. Empty tables and reports without charts have readable states.
Human-readable names are derived from field names and explicit units. The analyst still
owns appropriate wording, chart selection and supported conclusions; generation cannot
repair an unsound interpretation. The previously authored taxi showcase can have richer
custom interactions than the generic app.

The launcher is fixed trusted code; report text is data and never interpolated into Python.
The serve command uses the installed entry point even if a generated directory contains
another Python file. Narrative is rendered as literal text, chart text is escaped and
workbook strings are text cells. The server binds to loopback with telemetry disabled.
There is no automatic server launch, public hosting, arbitrary app-code execution or new
live model quality result. Install the dashboard extra only to serve the app; generation
works with the base installation.

The trusted local app is separate from the offline analysis VM. No arbitrary agent-written
Python is executed by the host. Streamlit is not preinstalled in the existing qualified
sandbox image; no image was rebuilt for this presentation. The new skill/document files
are available through the instruction filesystem on the next run using this source.

## Direct checks

Run `uv run --extra dashboard pytest -q tests/test_taxi_story.py tests/test_dashboard_generation.py` for projection/workbook,
incomplete-data and native Streamlit interaction regressions. CI installs the optional
extra to exercise these checks. Tests use small invented aggregates and call no models.
Rendered checks cover desktop and narrow widths, all tabs, month changes and workbook
download. These demonstrate the presentation adapter, not new analytical acceptance.

## Design review and revision

The optional review stage runs after verified export. It also works on a retained
dashboard, without rerunning the analysis or changing the frozen benchmark. Install:

```bash
uv sync --frozen --extra dashboard --extra dashboard-review
uv run playwright install chromium
```

Then use a text or JSON file containing the audience and business question:

```bash
doppler run -p backintel -c dev -- uv run --extra dashboard --extra dashboard-review \
  backintel dashboard review data/output/retail-report/dashboard \
  --brief examples/retail-brief.json --output data/output/retail-design-review
```

For worktrees outside the saved Doppler configuration scope, add the existing scope with
`doppler run --scope /Users/hudson ...`; do not copy credentials. Add `--review-dashboard`
to an `analyze` invocation to run this stage automatically after successful export.
The original analysis status and design acceptance remain separate: unsuccessful design
review produces a nonzero CLI exit even when the numerical analysis completed.

The writer defaults to the configured Sol specialist, with medium reasoning. The reviewer
defaults to `anthropic/claude-haiku-5-5` using the existing `ANTHROPIC_API_KEY` in Doppler.
Native Anthropic is available only through the dashboard reviewer factory; the shared
analyst and benchmark model factory retains its existing providers. No OpenRouter route
or new model account is involved. The review uses up to three reviewer
calls and two writer calls, with provider retries disabled. Review calls are separate from
the analyst's call budget. The standalone command limits requests to 120 seconds and
native reviewer output to 8,192 tokens (including reasoning); the inherited analysis writer
timeout can be up to 300 seconds. Automatic review shares the remaining `analyze --timeout`
budget, including browser capture, critique and revision. Standalone review has a 900-second
whole-loop limit. Expiry cancels active model I/O and browser work, closes the preview server,
retains any previously assessed candidate as provisional, and records `timed_out`. Cleanup
allows five seconds for the preview server to exit before killing it. `--max-revisions 0`
reviews without revising. Provider token usage is recorded;
an unreported dollar charge is unknown, never assumed zero. Subscription writer usage
continues to count against the existing ChatGPT plan.

The host launches only the installed Streamlit entry point, stripped of provider/store
credentials, on a temporary loopback port. A fresh headless Chromium context blocks
off-origin resources. It visits every section at 1280px and 390px, checks chart counts,
navigation, table search/empty states and workbook downloads, and compares downloaded
table values with the retained data. It closes the process/browser even after failure.
Overlapping viewport screenshots covering the full page and those checks go to a fresh
reviewer context each round; the reviewer never sees earlier scores. Browser automation is trusted host code, not a
new browser/network permission for the analytical sandbox.
Capture is bounded to 200 viewport images and 24 MB per round; long pages are captured
in full within those limits so the writer can reorganize them after review.

The fixed rubric grades story, chart effectiveness, organization, craft and business
usefulness from 1–5 with explicit anchors and illustrative examples. Each must reach 4,
with no semantic blockers or failed browser checks. Screenshots do not prove data truth:
numbers are protected by immutable data/chart bindings, and the critic checks wording
against the retained aggregates. Scores are automated judgments, not human-calibrated
quality certification. The rubric and example judgments live in
`src/backintel/agent_files/docs/dashboard-review.md`.

A revision is a strict `DesignPlan`: named sections, one/two-column grouping, titles,
captions, display labels and optional columns in place of an existing bar/line chart.
Native Streamlit page navigation renders it. Values, units, chart bindings and caveats
remain fixed; every chart must appear exactly once. Source descriptions remain visible in
About the data (or Definitions & limits), the workbook and the review context; source IDs,
snapshots and execution metadata stay out of those reader-facing views. Arbitrary Python/HTML/CSS is rejected.
New calculations, new chart bindings and unsupported interactions are unresolved work,
not edits the loop can invent. Workbooks retain identical analytical tables while their
read-me uses the revised narrative. This is runtime revision, not model-weight training.
Every candidate workbook is generated in an owned worker process that is stopped on
cancellation or deadline expiry. Review-only mode (`--max-revisions 0`) needs reviewer
credentials only; it neither constructs nor authenticates a writer.

Each candidate gets its own directory; the input delivery is untouched. `review.json`
records scores, evidence, usage and the selected candidate. The host prefers fewer failed
browser checks, then fewer semantic blockers, then the weakest criterion, then total score;
ties retain the earlier candidate. It stops on acceptance or after two revisions. Schema,
provider or capture failures return `review_error`; exhausted quality attempts return
`needs_revision`. Both are explicitly provisional, even when a retained candidate exists.
Only `passed` sets `ready: true`. Serve the selected directory with the existing
`backintel dashboard serve` command.

With `LANGSMITH_TRACING=true`, screenshot attachments, model calls and criterion feedback
are recorded using the existing project. No tracing destination or credentials are
changed. Engineering evidence stays in the review directory/LangSmith and out of business
pages. The bounded loop works locally when tracing is disabled.
Failed feedback uploads are recorded under `observability_warnings` without discarding
the completed local assessment.

The browser dependency is Microsoft's Playwright Python package, from the official
[Microsoft repository](https://github.com/microsoft/playwright-python). The native Claude
adapter uses LangChain's official `langchain-anthropic` integration; the reviewer reuses
the already selected Anthropic Haiku family and native account. References reviewed:
[Anthropic design evaluation](https://www.anthropic.com/research/harness-design-long-running-apps),
[Claude model IDs and vision](https://platform.claude.com/docs/en/models/overview),
[Playwright screenshots](https://playwright.dev/python/docs/screenshots), and
[LangSmith multimodal evaluations](https://docs.langchain.com/langsmith/evaluate-with-attachments).

### Live verification: taxi presentation, 2026-11-14

The completed validation used the retained taxi aggregates and a business brief for an
operations manager. It resumed Sol's first presentation revision after fixing browser
navigation capture, allowing only one further revision. Two independent visual reviews
and one Sol revision completed in 94 seconds, with 29 screenshots per review. Both reviews
received story 4, charts 3, organization 4, craft 3 and usefulness 4 (out of 5).
All navigation, chart rendering, table search and workbook-value checks passed.

The loop correctly returned `needs_revision`, retained the earlier candidate on the tie,
and did not declare the dashboard ready. Remaining findings concern mobile heatmap width,
whole-month labels and the airport-share comparison. These identify renderer work beyond
the current presentation schema. They do not justify lowering the acceptance threshold.
The [final LangSmith review](https://smith.langchain.com/o/90b24546-f3e2-4f48-af72-b06e73b27b49/projects/p/d975ee3d-b39c-4ea1-83a5-5007cd2e3be6/r/01a1db9f-b633-72a3-b995-f1f6dc6c8dbe)
contains the screenshots and criterion feedback; local detailed evidence remains under
`data/output/taxi-design-review-final-20261114/review.json` and is not committed.

Local verification: 229 tests passed, 15 skipped; lint, format and unused-code checks
passed. Browser tests cover both widths and the navigation overflow menu. Scripted tests
demonstrate early acceptance, the two-revision limit, regression retention and failure
handling. The live result demonstrates the quality hold; it is not a passing design
benchmark or a human-calibrated quality claim. The frozen analytical benchmark was unchanged.

### Readable heatmaps, months and business context

The renderer now puts the shorter dimension across wide heatmaps and the longer one
down the page. For the taxi example, all seven weekdays are columns and all 24 hours
are labeled rows. A horizontal legend leaves room for the cells on a phone. This is a
display transpose, not a new aggregation: every cell retains its original value.
Small heatmaps retain printed values, and hover text includes the formatted categories
and measure unit. Very large grids remain outside this example's demonstrated scope.

Month-named fields (`Month`, `Year_month`, `Month_start`) format valid `YYYY-MM` or
first-of-month date keys as `Jan 2025`. The underlying keys, years, measured values and
workbook tables remain unchanged. Ordinary daily dates are not relabeled as months.

`DesignPlan.context` introduces the audience, decision, data coverage and material
limitation. Each chart can include `reading_guide` to explain its marks, axes, colors
and denominator. These are optional for compatibility with earlier plans; the reviewer
now explicitly treats missing context that prevents understanding as a quality defect.
First-page totals are collapsed when context is supplied, and Previous/Next links
provide a reading order. Context is also included in the workbook's Read me sheet.

The authored taxi presentation is saved in `dashboards/taxi/presentation.json`. It
describes an illustrative fleet-manager decision using historical, citywide NYC TLC
records, not one company's fleet. It proposes limited timing/location trials; it does
not claim to have measured an intervention or its profitability. Apply a saved plan to
its matching retained report without inference:

```bash
uv run backintel dashboard generate --report /path/to/report.json \
  --presentation dashboards/taxi/presentation.json --output data/output/taxi-story
uv run --extra dashboard backintel dashboard serve data/output/taxi-story --port 8505
```

The revised taxi demo is under `data/output/taxi-business-story-20261114`. Direct browser
checks passed for every section at desktop and phone widths, navigation, table search
and unchanged workbook values. Local tests at implementation: 232 passed, 15 skipped.
These changes were authored and rendered directly. The subsequent review-only run passed
with all five criteria at 4/5, no blockers and all 18 browser checks passing across 30
screenshots. Charts and craft rose from 3 to 4; the other three scores stayed at 4.
The rubric now explicitly addresses business context, with the same acceptance threshold;
this is one automated review, not a controlled or human-calibrated design benchmark.

The [updated LangSmith review](https://smith.langchain.com/o/90b24546-f3e2-4f48-af72-b06e73b27b49/projects/p/d975ee3d-b39c-4ea1-83a5-5007cd2e3be6/r/01a1dbaa-849e-7024-bf08-da44ec1fef16)
contains the verified screenshot attachments and criterion feedback. Local evidence is
under `data/output/taxi-business-design-review-20261114`. One native Haiku review call
completed with capture in 41.5 seconds; no writer calls or presentation revisions ran.
The two renderer polish findings were subsequently fixed: heatmaps label their observed
minimum and maximum (with percent suffixes for percentage measures), and axis titles
have an explicit 20-pixel standoff. Both heatmaps were inspected at 390px and 1280px;
all endpoints were visible and title-to-label gaps exceeded 20px. The monthly-mix scale
shows 5.68%–82.73%. Targeted dashboard tests: 16 passed; mobile quality detection found
no issues. This direct renderer verification did not rerun the model judge.
The earlier scores above describe the earlier presentation. No dollar charge was reported
by the provider; recorded token usage is not a verified bill.

Implementation references: [Plotly heatmap axes and colorbar](https://plotly.com/python/reference/heatmap/)
and [Streamlit native containers](https://docs.streamlit.io/develop/api-reference/layout/st.container).
The [21st.dev Analytics Bento preview](https://21st.dev/@romanvasnev/components/analytics-bento)
was inspected for composition; its dense card layout was not adopted and no component
code or new dependency was imported.
