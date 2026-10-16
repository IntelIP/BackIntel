---
id: S-23
title: Collect complete and traceable information
status: Done
assignee:
  - '@codex'
created_date: '2026-10-14 22:59'
updated_date: '2026-10-15 02:38'
labels:
  - toolkit
  - platform
  - shared-core
  - goal-reference-workflow
milestone: m-2
dependencies:
  - S-22
  - S-13
references:
  - >-
    backlog/tasks/s-38 -
    Deliver-one-checked-Databricks-answer-through-the-toolkit-and-platform.md
documentation:
  - docs/ROADMAP.md
  - docs/roadmap/README.md
  - docs/roadmap/agile-backlog.md#shared-delivery-contract
priority: high
type: task
ordinal: 7
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Original roadmap story: S23. Original priority: P0. Work type: implementation.

## Business outcome

As an analyst, I need complete permitted records with source links, so that findings are not based on a silently partial or duplicated collection.

## Scope

Fetch the required pages; check completeness and duplicate identities; retain original responses and collection boundaries.

## Owned surface

Selected extraction workflow, collection checks, raw snapshots, and lineage.

## Prerequisites

S-22, S-13.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 The collected snapshot reconciles with an independent expected set. A missing page, interrupted collection, or enforced limit is visible; partial results are not labeled complete. Duplicate records do not inflate the answer.
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Extend the native PostgreSQL connector to discover all permitted tables and stable primary keys, then stream the whole bounded source through a consistent read-only database snapshot. No user-written queries or manual batches. 2. Retain each original response through S-13, checkpoint page identities, and reconcile distinct source identities with independent database counts. On restart, reread and verify retained pages before reusing them; changed data, missing/duplicate pages and limits remain partial. 3. Wire collection into the durable runtime, source-authorized API and platform controls without paid calls. Record complete/processed/pending counts and retain originals separately from any analysis. 4. Verify interruption, denial, duplicate/missing pages and limits in focused PostgreSQL checks. Run real-source collection over all 541,909 retail rows and compare every retained value and source identity against the independent unchanged CSV. Stop at S-23 acceptance; preparation and analytical interpretation remain subsequent stories.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Selected after S-22 and S-13 completion. Only S-23 is active. Reference scope: local PostgreSQL, single-column string/integer primary keys, scalar source fields, agreed 100 MiB and 900-second operating ceilings. Unsupported source shapes receive a clear disposition. No additional paid calls.

Passed real-source collection: all 541,909 rows retained and every field plus stable row identity independently compared with the unchanged original Kaggle CSV. Full result and database dumps: /Users/hudson/Library/Application Support/BackIntel/Validation/S23Collection-20261014/. No provider calls; local compute cost remains unmeasured. The isolated database was stopped after retaining artifacts. Synthetic PostgreSQL checks passed for interruption/reuse, missing or repeated pages, changed retained contents, byte limits and unauthorized result access; partial/cancelled runs remain visibly incomplete. A shared authorization lock conflict found by collection was fixed and the source-permission checks passed. Platform interaction tests, build and repository dead-code check passed; Graphify callers refreshed.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
BackIntel discovers stable source identities and collects the whole permitted PostgreSQL workload without manual batches. It preserves original responses, reuses verified progress and rejects incomplete or inconsistent collections. All 541,909 real retail records matched the independent original CSV; analysis is still a later stage.
<!-- SECTION:FINAL_SUMMARY:END -->
