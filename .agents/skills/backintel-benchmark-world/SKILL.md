---
name: backintel-benchmark-world
description: Reuse BackIntel's local benchmark setup and independent grading conventions.
---

Status: unreviewed agent-authored knowledge, updated 2026-11-12.

BackIntel uses LangSmith Evals over a single Deep Agents analyst. See docs/benchmark.md
for the task specification and README.md for commands. Add storage adapters behind the
Store protocol; keep native query paths and dialect skills distinct. Local services are
started one profile at a time through backintel stores to fit this Mac's memory.

Use canonical typed data for independent polars oracles, and store-visible copies for the
analyst. Keep reference files, loading credentials, grader code and planting declarations
outside all agent-visible mounts. Preserve source/reference hashes and LangSmith run IDs.
Reports need explicit metric identifiers so correct numbers cannot pass under swapped
labels. Replay cutoffs hide future observations, while predictions known at the cutoff
remain visible. Declared planting and naturally occurring changes are different evidence.

Fix a harness defect before treating its score as agent capability. Keep the original run
and label the rerun. Read a complete relevant trace, not only aggregate percentages. A
numerical score does not establish narrative quality; use the independently versioned
method judge and its written reasons. Cost reports must say whether judge cost is included.

The opt-in analysis graph uses persistent SmolVM execution and a bounded report specification.
After the analyst stops, a clean renderer VM produces the delivered files from the
host-retained specification. The artifact manifest establishes file integrity; table citations
establish reproducibility. Neither establishes analytical truth. New artifact tasks need an
independent reference and reconciliation across report tables, charts, CSV and workbook cells.
See `docs/analysis-sandbox.md` and `evals/analysis/Task.md` for the implemented pattern.
Scripted graph runs exercise real tools and export but cannot establish model judgment or
unseen-domain competence. Keep their results separate from live LangSmith experiments.

Cross-format reconciliation must use declared numerical tolerances: XLSX serialization
can change a floating-point value's last digit. Preserve null versus zero and text types;
do not weaken population, unit or metric-binding checks. The controlled energy/availability
cases in `scripts/analysis_cases.py` provide independent-oracle patterns for irregular
observations and overlapping intervals. Their exact requests and truth stay in the task
specification and evaluator-owned references. A comparison with unclassified failures or
unknown charges cannot qualify an arm by excluding those cases from its denominator.

A successful render inside an analyst VM is not a delivered bundle. A completed analysis
requires structured completion and the host's clean export. Classify a text-only terminal
response separately from infrastructure failure; retain the provisional score and trace
when adding reviewed failure feedback. A correct refusal must not imply that temporary
artifacts were delivered. See the live SmolVM rerun in `docs/results-analysis-sandbox.md`.

The specialist now explicitly requires its completion tool and permits one recovery prompt
for a text-only stop. Keep recovery inside the original graph's call/time limits and count
the failed completion attempt before jumping back to the model. Test both recovered export
and exhaustion; a live success with zero recovery prompts does not exercise the fallback.
Selected-case reruns retain full frozen dataset validation and have their own experiment;
never combine their passes with an earlier baseline to claim a complete candidate suite.
