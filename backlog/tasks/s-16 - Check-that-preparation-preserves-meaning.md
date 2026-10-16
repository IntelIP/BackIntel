---
id: S-16
title: Check that preparation preserves meaning
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
  - S-15
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
ordinal: 10
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Original roadmap story: S16. Original priority: P0. Work type: implementation.

## Business outcome

As an analyst, I need checked records, totals, units, and joins, so that a transformation that executes successfully cannot quietly change the answer.

## Scope

Reconcile retained and excluded records; check identities, units, missingness, and business totals; detect a join that duplicates quantities or money.

## Owned surface

Preparation correctness checks and exclusion records. High risk: materially wrong business results.

## Prerequisites

S-15.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Prepared data matches an independent expected result. A double-counting join, mixed unit, or unexplained exclusion fails the check and prevents a misleading accepted answer. Retain the reason and affected records.
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Independently compare every prepared row with its retained original under current source permissions. Check exact decimal equivalence, date meaning and offsets, identifier identity, missing values, unchanged categories, declared units, source links and complete coverage. Do not reuse the preparation worker to calculate expected values. 2. Refuse duplicate/fan-out rows, unexplained omissions, changed units, unsupported joins or unresolved conversion errors. Retain clear failure reasons and affected source references; a failed check must not publish an accepted answer. 3. Expose a durable validation operation and concise platform result. Test deliberate duplication, omission, unit changes and value changes; ensure denied access hides the result. 4. Run the independent checker across all 541,909 prepared real rows, then compare prepared values against the unchanged original CSV using a separate validation program. Record measured time and coverage, without provider calls. S-29 owns interruption/whole-workload acceptance and S-17 owns business findings.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Selected under S-38 after S-15 completion. Only S-16 is active. Use the saved S15Preparation database; do not recollect or reinterpret the source. No provider calls are planned.

Independent runtime meaning checks passed, followed by a separate comparison against the unchanged original CSV: all 541,909 rows and 4,335,272 original field values matched. Exact invoice-value/cancellation totals and every one of 4,070 product groups and 38 country groups reconciled. The full demonstration took 49.813 seconds, used zero provider calls, and retained unknown local compute cost. Evidence, complete expected aggregates, and database dump: /Users/hudson/Library/Application Support/BackIntel/Validation/S16MeaningCheck-20261014/. Synthetic tests rejected duplicate/join fan-out identities, mixed or changed units, unexplained omissions, altered values and invented timezone offsets. A real runtime failure retained affected source references and did not publish an accepted answer; revoked access hid its evidence. Platform interaction tests, web build, dead-code, diff check and refreshed graph passed. No business finding or reusable workflow has been delivered yet.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Prepared rows now undergo independent source-value, identity, unit, missingness and coverage checks. Failures retain source references and prevent accepted results. All real rows and independently calculated business totals passed; the platform shows the check outcome.
<!-- SECTION:FINAL_SUMMARY:END -->
