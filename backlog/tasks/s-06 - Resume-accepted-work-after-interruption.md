---
id: S-06
title: Resume accepted work after interruption
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
  - S-05
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
ordinal: 3
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Original roadmap story: S06. Original priority: P0. Work type: implementation.

## Business outcome

As a workflow owner, I need interrupted work to resume safely, so that I keep accepted results without unnecessary repeated calls or charges.

## Scope

Reuse durable jobs and retained evidence; resume partial work; exercise duplicate submission, cancellation, and uncertain provider outcomes.

## Owned surface

Selected runtime job continuation and existing recovery paths. High risk: lost work or duplicate charges.

## Prerequisites

S-04, S-05; requires a runnable job path.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Interrupt a bounded job, restart it, and retrieve the accepted result. Replaying accepted work creates no second result or charge. An uncertain paid operation is reconciled or visibly blocked before repetition; cancellation has a clear terminal state.
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Reuse the durable job and cached provider paths proven by S-12/S-05. 2. Interrupt an actual local planning worker process after a retained proposal/provider receipt, restart it against the same database, and verify the accepted plan plus one completed result/charge identity. Use explicitly simulated provider replies, never paid calls. 3. Verify cancellation and unresolved-charge recovery through focused existing PostgreSQL checks. 4. Record scope and evidence; the integrated connected-data workflow still repeats recovery acceptance in S-39.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Selected after S-04 and S-05 completion. Owned surface: durable job continuation and a focused real-process interruption check of the selected planning path. Stop when interruption/resume preserves the accepted result and accounting identity, uncertain charges prevent repetition, and cancellation is terminal. No new provider spending.

Added a real subprocess interruption check for the selected planning job. It uses a simulated provider response with actual PostgreSQL reservation/settlement and saved proposal evidence, terminates the worker process before job acceptance, advances only the disposable lease clock, and restarts against the same database without a provider credential. It requires one accepted plan, one completion event, and one retained simulated charge after repeated dispatch. Focused existing checks also cover cancellation and uncertain-charge resumption. Execution result is being inspected; acceptance remains unchecked until it passes. No real provider request was made.

Verified durable recovery on the current planning path. A real subprocess exited during a planning job after retained proposal/provider evidence; restarting against the same PostgreSQL database, with the disposable lease advanced past expiry and no provider credential, recovered one accepted plan. Repeated dispatch retained one completion event and one simulated charge identity. Three focused existing checks also passed for terminal cancellation, uncertain-charge blocking before resumption, and duplicate/orphan recovery. Four checks passed in total. Provider replies and the recorded test charge were explicitly simulated; no real provider call occurred. The connected full-workload recovery demonstration remains S-39 acceptance.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Verified durable recovery on the current planning path. A real subprocess exited during a planning job after retained proposal/provider evidence; restarting against the same PostgreSQL database, with the disposable lease advanced past expiry and no provider credential, recovered one accepted plan. Repeated dispatch retained one completion event and one simulated charge identity. Three focused existing checks also passed for terminal cancellation, uncertain-charge blocking before resumption, and duplicate/orphan recovery. Four checks passed in total. Provider replies and the recorded test charge were explicitly simulated; no real provider call occurred. The connected full-workload recovery demonstration remains S-39 acceptance.
<!-- SECTION:FINAL_SUMMARY:END -->
