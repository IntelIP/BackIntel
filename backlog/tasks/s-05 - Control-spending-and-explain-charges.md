---
id: S-05
title: Control spending and explain charges
status: Done
assignee:
  - '@codex'
created_date: '2026-10-14 22:58'
updated_date: '2026-10-15 06:21'
labels:
  - toolkit
  - platform
  - shared-core
  - goal-reference-workflow
milestone: m-0
dependencies:
  - S-04
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
ordinal: 2
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Original roadmap story: S05. Original priority: P0. Work type: implementation.

## Business outcome

As a budget owner, I need bounded and explainable analysis spending, so that work cannot silently exceed the agreed limit.

## Scope

Reconcile relevant existing campaign charges and authority; expose reservations and measured usage; check exhausted limits, unknown charges, and overlapping admissions.

## Owned surface

Existing budget and usage controls exposed through the selected runtime and connector calls. High risk: financial correctness. This story grants no new spending allowance.

## Prerequisites

S-04; requires operating limits for the selected workload.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 A permitted request reserves within the cap and settles recorded usage. Exhausted limits or unresolved charges prevent new paid admissions; overlapping requests cannot overspend. Fixtures test these paths before any separately authorized live calls. Unmeasured local compute remains unknown rather than zero.
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Verify the existing reservation and settlement paths reused by S-12 and the selected connected workflow. 2. Exercise permitted reservation, cap exhaustion, unresolved/over-reservation charges, concurrent admissions, and explicit unknown local compute using isolated PostgreSQL and fixture provider replies. 3. Reconcile the two already-authorized planning calls against their saved receipts without repeating them. Make only a demonstrated necessary fix; no new spending is authorized.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Selected after S-04 completion. Owned surface: existing runtime reservation/usage and provider charge settlement, with focused database checks. Existing live S-12 charges are complete and total USD 0.03186612. Stop when all stated spending outcomes have current evidence; do not repeat live requests or infer any additional spending authority.

Ten focused PostgreSQL campaign checks passed: charge settlement/replay, over-reservation and unresolved-charge blocking, concurrent and near-suite-cap admission, per-goal/run and attempt limits, zero-budget rejection, invalidated authority, ambiguous provider timeout, and cached replay without credentials/transport. Added one direct check of request/domain/suite caps; its run is pending. Existing live planning receipts contain two complete charges totaling USD 0.03186612. Local compute remains None/unknown. No additional paid calls were made.

Verified and reused existing reservation/settlement controls. Eleven focused checks against isolated PostgreSQL passed: request/domain/suite/goal limits, zero budget, concurrent admission near the suite cap, call/attempt limits, charge settlement and cached replay, unresolved and over-reservation charge blocking, changed authority, and ambiguous timeout without retry. Added explicit zero-budget/unknown-local-cost and individual-cap checks. The two authorized live planning charges are complete and total USD 0.03186612; no further provider calls were made. Local compute remains explicitly unmeasured.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Verified and reused existing reservation/settlement controls. Eleven focused checks against isolated PostgreSQL passed: request/domain/suite/goal limits, zero budget, concurrent admission near the suite cap, call/attempt limits, charge settlement and cached replay, unresolved and over-reservation charge blocking, changed authority, and ambiguous timeout without retry. Added explicit zero-budget/unknown-local-cost and individual-cap checks. The two authorized live planning charges are complete and total USD 0.03186612; no further provider calls were made. Local compute remains explicitly unmeasured.
<!-- SECTION:FINAL_SUMMARY:END -->
