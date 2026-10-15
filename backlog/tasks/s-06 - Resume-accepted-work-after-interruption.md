---
id: S-06
title: Resume accepted work after interruption
status: To Do
assignee: []
created_date: '2026-10-14 22:58'
updated_date: '2026-10-15 00:21'
labels:
  - needs-refinement
  - toolkit
  - platform
  - shared-core
milestone: m-0
dependencies:
  - S-04
  - S-05
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
- [ ] #1 Interrupt a bounded job, restart it, and retrieve the accepted result. Replaying accepted work creates no second result or charge. An uncertain paid operation is reconciled or visibly blocked before repetition; cancellation has a clear terminal state.
<!-- AC:END -->
