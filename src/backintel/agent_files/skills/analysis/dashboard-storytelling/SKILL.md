---
name: dashboard-storytelling
description: "Use when presenting analysis as a dashboard or report: business titles, clear charts, useful interactions and clean supporting sheets."
---

# Present a business story

Read `/docs/dashboard-storytelling.md` with the instruction `read_file` tool. This is an
offline reference pack, not a VM shell path or permission to install a framework.

Start with the audience's decision and a supported finding. Give each view one question,
a descriptive title, a population/time/unit caption, and a short explanation of what the
reader can do with it. Put detailed definitions and quality limits in a clearly named
secondary view. Keep limits near a finding when they could change the decision.

Orient a first-time reader: who is making what decision, what source and period the
data covers, and whether this is an illustrative scenario. Do not assume public data
belongs to the reader's business. Explain unfamiliar encodings in ordinary language.
The host's DesignPlan supports a business context and a per-chart reading guide.

Use business names instead of database identifiers. Turn `Gross_fare_USD` into “Metered
fares ($)”, not “Revenue” or “Profit”. Do not imply distance from a fare band. Choose a
column chart for a few discrete periods, horizontal bars for long category names, and a
heatmap for day/hour patterns. Use comparable denominators and zero baselines for bars.
Prefer direct labels, restrained colors and whitespace over decorative chart density.

Run IDs, hashes, tool traces, snapshot identities, file manifests and evidence code belong
in engineering records. Do not put them in business titles, chart labels, KPI cards or
downloadable business sheets. Ordinary source names, periods, definitions, limitations
and calculation meaning remain useful to the reader. Preserve the host's required
engineering records separately; do not delete or falsify them.

Successful analysis completion now generates a Streamlit dashboard automatically from the
validated report's findings, metrics, tables and chart bindings. Use `render_report` and
`AnalysisCompletion` as usual; the host creates the dashboard after clean export succeeds.
Provide useful chart titles, business column names, explicit units, definitions and caveats.
Do not write or launch a Streamlit server in the VM. The host uses a fixed trusted app;
model output remains data. Serving is an explicit local operator command, not deployment.

When the operator enables design review, the host captures the rendered dashboard at two
widths, independently grades it and can request at most two presentation-only revisions.
The host owns the rubric in `/docs/dashboard-review.md`. A completed numerical analysis
does not establish design acceptance. Do not claim the dashboard was reviewed unless the
host review record says so; the reviewer cannot repair new analytical calculations.

Inspect the actual rendered view at desktop and narrow widths when tools permit. Check
labels, units, clipping, color meaning and the control's effect. A filter must name its
scope, change the relevant view, and preserve a meaningful empty state. Fix demonstrated
defects, then stop once the requested presentation works.
