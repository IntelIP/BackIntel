# Report presentation review — November 13, 2026

Three retained Sol outputs were rendered with revised presentation: sales refunds,
service availability, and irregular energy coverage. These are **controlled synthetic
fixtures**, not customer analyses or fresh model runs. Rendering used zero model calls.
This review establishes presentation and data-preservation behavior, not new analytical
acceptance or production readiness.

## Changes and rationale

The former report placed technical run identifiers and long metric definitions ahead of
findings; float headlines exposed many insignificant digits. The revised renderer uses
an editorial title (with an explicit title/scope separator displayed as a subtitle) and readable headline values, expandable definitions with exact
values, section navigation, and direct links from charts/metrics to the supporting
source table. Narrative findings, caveats, evidence, and exact source values are unchanged.
Workbook styling adds readable headers, alternating rows, frozen headers and print setup
without changing sheet names or cells.

Charts now share restrained teal/ink colors, direct bar values, lighter grid lines, and
readable axis names. A same-day heatmap shows compact clock labels with its date and
UTC context. Percentage heatmaps wholly within 0–100 use that absolute scale: previously,
61.7% coverage could appear as fully saturated because the scale stopped at 61.7%.
Non-percentage and out-of-range percentage series retain their data-driven scales.
Small line series show the observed timestamps rather than artificial half-day tick marks.

Desktop and mobile layouts were inspected in headless Chromium. The first mobile pass
exposed unreadably shrunken chart labels; charts now retain a readable width inside a
labelled, keyboard-focusable horizontal scroll region. The interactive chart remains a
separate offline page. Small metadata, one marginal text contrast, overlong desktop reading lines, and redundant
section labels were corrected. Reports use system fonts and inline styles/scripts, with the
existing CSP and no external resources. Print styling exposes supporting detail content.

The visual direction used the spacing/table hierarchy of the 21st.dev
[InlineAnalyticsTable](https://21st.dev/@ruixen.ui/components/inline-analytics-table)
and [Editorial Testimonial](https://21st.dev/@jatin-yadav05/components/editorial-testimonial)
previews as references. No component source, library, or external font was adopted.

## Retained evidence

Original specimens remain under:

`data/output/specialist-guidance-pair-20261113T044726Z/candidate/arm-0/<case>/artifacts/report/`

Revised bundles, one ZIP per bundle, screenshots and verification receipts are local,
ignored artifacts under:

`data/output/artifact-design-review-20261113/`

Each case folder contains `report/report.html`, `supporting.xlsx`, source tables,
standalone interactive charts, PNG/SVG exports, `report.json`, and `manifest.json`.
`render-receipt.json` records the renderer hash, image identity and original/revised
locations. Report JSON and CSVs are byte-identical to the originals; all XLSX sheets and
cell values are identical, with no formula cells. Each delivered bundle passed its
manifest verification. Browser checks cover document overflow, chart image loading,
table-link expansion, interactive chart rendering, heatmap bounds, and network isolation.
The screenshots show the actual browser renders; there is no invented aesthetic score.

Focused verification: 16 artifact tests passed with the analysis-image pinned
`matplotlib==3.11.2` and `plotly==7.1.0`; Ruff and diff checks passed. These tests protect
renderer contracts and truthful scales; they do not grade the analytical conclusions.

## Runtime boundary and remaining issue

Source baseline: `51846a4`, with the presentation changes in `src/backintel/artifacts.py`.
Renderer SHA-256:

`2d4453f0d1d34556d14b7962207dd0dfbe3f31381c2a7717d5d6c6f66a462b99`

The final rerenders loaded this trusted module into `/workspace` in a clean, offline
SmolVM, rendering and exporting each report separately before clearing its output directory,
using the already-qualified image and installed Python packages.
The module bundled in the current default image has not been replaced. **Rebuild and
prepare the analysis image after integration before normal live runs can use this style.**
No production deployment, commit, or push is implied by this review.

An initial attempt to export all three reports from one VM failed with
`tarfile.ReadError: unexpected end of data` in `export_artifacts`. Its partial export
was removed by the existing atomic cleanup. Rendering and in-VM verification had
succeeded. Exporting one report at a time succeeded for all three; the aggregate-stream
failure remains a delivery reliability finding, with root cause not established here.
It is not a model or analytical failure, and this presentation change does not fix it.
