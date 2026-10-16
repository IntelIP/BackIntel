---
id: S-29
title: Complete the workload without manual batching
status: Done
assignee:
  - '@codex'
created_date: '2026-10-14 22:59'
updated_date: '2026-10-15 06:21'
labels:
  - toolkit
  - platform
  - shared-core
  - goal-reference-workflow
milestone: m-2
dependencies:
  - S-16
  - S-23
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
ordinal: 11
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Original roadmap story: S29. Original priority: P0. Work type: implementation.

## Business outcome

As an analyst, I need to submit the workload once and have all eligible records processed, so I do not manage repeated small batches or mistake a sample for completion.

## Scope

Manage pagination, partitions, internal batches, resumable progress, and resource limits. Account for collected, processed, excluded, failed, and pending records. Replace fixed-cohort behavior where the selected workload requires complete classification or scoring; distinguish output-display limits from processing coverage.

## Owned surface

Whole-workload execution and coverage in the selected collection/preparation/analysis path. Automatic internal batching is allowed; user-managed batching is not the completion contract.

## Prerequisites

S-16, S-23 and an agreed workload/resource boundary.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Complete the agreed workload with reconciled coverage and checked results. Resume an interrupted partition without loss or duplicate accepted work. Partial work and exhausted limits remain visibly incomplete or resumable. Any legitimate training/evaluation sampling is explicit and never substitutes for required operational coverage. Record time, resources, and known cost; larger sustained-capacity claims belong to S36.
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Keep the existing automatic source pages and complete-data preparation. Make retained preparation progress, reused pages, pending rows and limit failures visible through the shared operation result. Preserve a separate receipt for each executed pending partition so recovery remains traceable. 2. Inject an interruption immediately after an accepted prepared page, start a fresh execution, and verify that accepted rows are reused while only pending source pages execute. Repeat invocation must not duplicate accepted work or charges. 3. Exercise exhausted execution limits and report incomplete resumable coverage. Use small synthetic source data for fault cases, then demonstrate interruption and recovery across the entire 541,909-row historical workload using the retained S-16 database and independent expected answer. No user-created batches, training sample, provider call or new source collection is needed. Stop at checked whole-workload recovery; S-17 remains the business-answer story.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Selected under S-38 after S-16 and S-23 completion. Only S-29 is active. Full collection, preparation and independent correctness are proven; interruption recovery for this connected path is the remaining acceptance.

The real preparation worker terminated with exit 73 immediately after committing its first 2,000-row page. A fresh Python process reclaimed the durable job, reused exactly those 2,000 rows, and prepared the remaining 539,909 without duplicate pages. Resume preparation took 47.857 seconds; resumed preparation plus full independent meaning validation took 81.279 seconds. All 541,909 checked rows matched the prior independently CSV-checked page digests. Repeated invocation reused the accepted result and did not execute another sandbox or add charges. Provider calls remained zero. A separate synthetic real-container time-limit test remained visibly incomplete (all rows pending), then resumed successfully. UI showed partial coverage, and 16 interaction tests, build, dead-code, diff and graph checks passed. Evidence and restorable database: /Users/hudson/Library/Application Support/BackIntel/Validation/S29Recovery-20261014/. Local compute cost remains unmeasured; no sustained capacity or sampling claim is made.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Complete workload processing now exposes retained and pending preparation counts, reuses accepted pages after interruption, and keeps distinct execution receipts. Real worker termination/restart and a separate resource-limit failure both recovered without loss or duplicate accepted work. All 541,909 source rows remain checked.
<!-- SECTION:FINAL_SUMMARY:END -->
