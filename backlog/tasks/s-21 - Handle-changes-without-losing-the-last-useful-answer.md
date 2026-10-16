---
id: S-21
title: Handle changes without losing the last useful answer
status: Done
assignee:
  - '@codex'
created_date: '2026-10-14 22:59'
updated_date: '2026-10-16 07:17'
labels:
  - platform
  - post-reference
milestone: m-4
dependencies:
  - S-19
references:
  - docs/retail-reference-workflow.md
  - docs/roadmap/agile-backlog.md
documentation:
  - docs/ROADMAP.md
  - docs/roadmap/README.md
  - docs/roadmap/agile-backlog.md#shared-delivery-contract
priority: medium
type: task
ordinal: 18
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Original roadmap story: S21. Original priority: P1. Work type: implementation.

## Business outcome

As a returning user, I need changed data and definitions handled safely, so that an update does not erase useful work or silently corrupt the next answer.

## Scope

Detect changed columns, meanings, records, and corrections; create a workflow version or seek material clarification when needed; retain earlier accepted results through failed refreshes.

## Owned surface

Change detection, workflow versions, refresh, correction, and stale-result handling.

## Prerequisites

S-19.

## Next staged delivery

Protect the last checked answer while a recurring workflow encounters changed records, columns, business meanings, data quality, or method performance. Changes within the agreed repair policy may be handled automatically; changes to business meaning remain explicit decisions.

## Decisions before selection

Select representative source, quality, and method-deterioration cases and the boundary between routine repair and required clarification. Define when an answer becomes stale and how the user sees that condition.

These refinements record future work. Hudson selects one implementation story at a time; no implementation, model spending, live scheduling, commit, publication, or deployment is authorized by this planning update.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
Include data-quality changes and deterioration of an accepted analytical method in the selected change cases. Routine repairs can proceed within the acceptance policy; unresolved business meaning or a change beyond that policy requires escalation.

- [x] #1 Process a selected source change and show which results were reused or replaced. A materially incompatible schema blocks or repairs the affected step visibly. Failed refresh or interruption preserves the last accepted answer and source history.
- [x] #2 Include data-quality changes and deterioration of an accepted analytical method in the selected change cases. Routine repairs can proceed within the acceptance policy; unresolved business meaning or a change beyond that policy requires escalation.
- [x] #3 For each selected change case, the user can distinguish the last accepted answer, its source time, the failed or repaired update, and any unresolved decision. An unsuccessful update never appears as a fresh accepted answer.
- [x] #4 An accepted repair retains a new checked workflow or method version and explains what was reused or replaced. A change beyond the agreed policy leaves the last useful answer available and identifies the specific decision needed.
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
Approved outcome: retain the last accepted answer through changed source data, incompatible fields, quality failures, interruptions, and measured method deterioration. Hudson approved automatic repairs only when values and business definitions are preserved. Missing required fields, failed reconciliation, and worse measured forecast error require review. Implement a persisted change report around the existing saved-workflow steps; check schema and source coverage before preparation, preserve independent meaning checks, compare the saved forecast method on newly observed complete weeks, and gate publication before replacing last_success. Save accepted repairs as a new checked workflow version with source time and reused/recomputed steps. Expose this same accepted answer and update status through the API and browser. Demonstrate safe normalization, missing field, invalid value/reconciliation, interruption/retry, and forecast deterioration on disposable retained retail data. No model calls, deployment, commit, or push. S-20 remains the only active story until its check completes.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
S-20 is accepted. S-21 is now the sole active story under the existing goal, which still includes S-24. Approved policy is recorded in the implementation plan. Implementation has not begun. Existing workflow execution already retains last_success on exceptions, but publication and cached-success admission can replace it before a new change policy is applied. Place schema/quality/performance gates before publication; retain a visible change report and accepted source time; save checked repairs as new immutable workflow versions. Reuse source_preparation, source_validation, source_methods, existing evidence, and API/browser workflow paths. The existing saved forecast final-test mean absolute weekly error supplies the accepted comparison measure; no new method search or paid calls are authorized. S-24 deletion policy is now approved and recorded in its task. Preserve all pre-existing uncommitted reference-workflow work.

Implementation now exists: workflow_updates checks source shape and coverage, retains review decisions and source times, checks the unchanged forecast method against accepted error, blocks older-source publication, and saves successful changed-input workflows as new immutable versions. Cached connected-source replays no longer overwrite last_success. Toolkit status and authenticated API share the same status function; the browser shows last accepted answer, source time, latest attempt, reused/recomputed work, and required decisions. Focused guards, eight existing source-workflow/answer/method checks, 21 web checks, production build, and dead-code check passed. Graphify refreshed; current source confirms the publication guard call. No acceptance boxes checked yet. The controlled-source full-retail demonstration is running as S21Live-20261016C. Earlier two attempts stopped during controlled-input setup; their servers and databases were removed. The runner now places controlled connector responses and interruptions inside the actual isolated job worker. No paid calls, commits, pushes, or deployment.

Accepted locally on 2026-10-16. Six cases passed across retained S21Live-20261016D, F, and final G evidence: value-preserving format repair and checked version; missing field review; lost-record reconciliation review; invalid-value review; interruption/recovery with reused preparation and validation; measured forecast deterioration review. Safe repair and recovery preserve exact 541,909-row net invoice value GBP 9,747,747.934. Desktop/mobile accepted and review views inspected. G update-cases.json consolidates completed cases and preserves accepted-answer identity; summary.json confirms no new provider requests, zero provider cost, server stopped, database removed. Source changes and interruption were controlled injections into real isolated execution; live upstream change collection remains S-24. Harness-only date parsing and continuation were corrected after the final fixture setup failed; completed cases were retained, not rerun. Prior 21 web checks, production build, focused update guards, 8 source checks, dead-code check and Graphify remain applicable. No deployment, commit, push or predictor promotion.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
The last accepted answer survives source-quality failures and interruption. Safe repairs retain checked versions; changed meanings or worse measured forecast error require review. Toolkit, API and browser share the accepted answer and latest update state. Validated locally over all historical retail records with controlled source changes; real source refresh follows in S-24.
<!-- SECTION:FINAL_SUMMARY:END -->
