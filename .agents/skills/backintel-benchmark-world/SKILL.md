---
name: backintel-benchmark-world
description: Reuse BackIntel's local benchmark setup and independent grading conventions.
---

Status: unreviewed agent-authored knowledge, 2026-11-09.

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
