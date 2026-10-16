---
id: S-20
title: Invoke from an event or schedule
status: Done
assignee:
  - '@codex'
created_date: '2026-10-14 22:59'
updated_date: '2026-10-16 05:20'
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
ordinal: 17
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Original roadmap story: S20. Original priority: P1. Work type: implementation.

## Business outcome

As an operations user, I need event and scheduled invocation, so that recurring work runs within its granted limits without manual repetition.

## Scope

Connect one selected event and one bounded schedule; enforce source, expiry, and spending policy at execution time; retain invocation history and clean up the test schedule.

## Owned surface

Existing event/scheduler entry points and workflow admission. External delivery requires its own authority.

## Prerequisites

S-19.

## Next staged delivery

Begin continuous operation with one existing saved workflow, one permitted event, and one bounded schedule. This is product behavior; Hudson continues to select and start development work manually. Method development need not finish before this story can run against an already accepted workflow.

## Decisions before selection

Select the workflow, event source, event identity, schedule and timezone, owner, expiration, and run/spending limits. Any demonstration schedule must be short-lived and removed after its check; no permanent schedule is authorized by writing this story.

These refinements record future work. Hudson selects one implementation story at a time; no implementation, model spending, live scheduling, commit, publication, or deployment is authorized by this planning update.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 An actual short-lived schedule runs when due and not before; a permitted event starts the same workflow. Duplicate events reuse accepted work. Expired authority or exhausted limits prevent new admissions rather than silently bypassing controls.
- [x] #2 The owner can see the configured trigger, due time and timezone, actual run history, and denied or skipped attempts. A trigger invokes the same saved workflow contract as a manual request and respects current source access and operating limits.
- [x] #3 Pausing or expiring the trigger prevents further admissions. The bounded demonstration includes an actual event and due schedule execution, then removes its test schedule and records the cleanup.
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
Outcome: Start the accepted PostgreSQL retail workflow from a permitted event and a bounded native schedule; expose history and enforce current authority without duplicate accepted work.
1. Add persisted owner-scoped trigger configuration and attempt receipts around the existing saved-workflow admission contract. Reuse its stable run identity, current source checks, recovery and deterministic execution.
2. Expose authenticated configuration, event, pause/remove and history operations. Use the existing Aegra scheduler as timer owner; no separate daemon.
3. Demonstrate a local retail.collection.completed event with a unique identity and a one-shot schedule in America/New_York. Use the existing connection-demo-manager, expire after 15 minutes, allow at most two accepted occurrences and zero model spending. Remove the native demonstration schedule after checking it.
4. Check before-due behavior, actual due execution, duplicate/conflicting events, revoked access, expired/paused limits, interruption-safe admission and owner-visible history. Preserve all earlier work.
Owned surface: new runtime/workflow_triggers.py and migration; existing analysis API and graph registration; focused trigger tests and saved-workflow guidance.
Stop condition: S-20 acceptance observed on a disposable local copy of the retained retail demonstration, with native schedule cleanup and no paid calls. S-21 and S-24 remain separate sequential stories under the active goal. No commit, push, deployment or permanent schedule.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
The user selected execution of the remaining steps. S-20 is the first common step while clarification of the overall goal scope is pending. Dependency S-19 is Done; no other local story is In Progress. Existing uncommitted work belongs to this same reference-workflow effort and is preserved. Local working-tree validation will be distinguished from committed-head or deployment validation.

Scope confirmed by Hudson: complete S-20, S-21 and S-24 sequentially. S-20 configuration, shared workflow admission, owned event API, native Aegra timer, pause/removal, denied-attempt history and browser controls are implemented. Twenty web checks, build, eight existing workflow/answer/method checks, dead-code check, and required Graphify update passed. The actual native run has reached accepted event/scheduled results; browser history verification exposed a display/readback mismatch still being diagnosed. No acceptance criteria are checked yet. Private disposable evidence: S20Live-20261015Attempt5; its native process and database were stopped and removed. A sixth bounded local check is running. No paid calls are authorized or used by these saved deterministic workflow starts.

Correction to the previous progress note: event execution is observed, but actual scheduled acceptance is not yet verified. The async browser predicate did not provide trustworthy scheduled-result evidence, and the following 30-second UI assertion ended before the native scheduler minute tick. Attempt6 retained visible text showing one accepted event and a pending due schedule. Its server and database are confirmed stopped/removed. The browser check now waits on rendered accepted count and successful run status for up to 180 seconds. The exact full validation is restarting as Attempt7; do not start another copy while its exec session is live. S-20 remains In Progress with no acceptance boxes checked; S-21 and S-24 remain unstarted under the same goal.

Accepted on 2026-10-16. The full local native-timer demonstration passed in S20Live-20261016Attempt9: actual due schedule, actual authenticated event, no early schedule, duplicate reuse, conflicting identity denial, run cap, pause, expiry, revoked access, owner isolation, interrupted admission rollback, toolkit parity, native schedule removal, and no provider requests. Both starts used one succeeded workflow over all 541909 retail rows; net invoice value GBP 9747747.934. Server and disposable database were stopped/removed. Final frontend build passed. Final browser check S20UI-20261016D reused that successful runtime archive and confirmed visible accepted history and trigger controls within the mobile viewport; its server and database were also removed. The new selector is constrained to the form width. A standalone forecast table now uses the existing scrolling container. Whole-page mobile overflow was observed around wider result tables; that broader layout issue is not claimed resolved by the scoped trigger-panel check. Prior 20 web checks, eight source-workflow checks, and dead-code check passed; Graphify was refreshed and trigger callers were inspected. All evidence is working-tree local, not committed-head or deployed acceptance. Private evidence base: /Users/hudson/Library/Application Support/BackIntel/Validation. No paid inference, publication, or deployment.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Permitted events and bounded native schedules now invoke the saved workflow with durable owner-visible history and current access, expiry, run, and zero-spending limits. Verified with a real local timer and retained historical retail data, successful browser history, admission/recovery checks, toolkit parity, and confirmed schedule/server/database cleanup. Source recollection remains S-24.
<!-- SECTION:FINAL_SUMMARY:END -->
