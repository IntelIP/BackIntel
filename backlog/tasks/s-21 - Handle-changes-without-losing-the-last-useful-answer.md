---
id: S-21
title: Handle changes without losing the last useful answer
status: To Do
assignee: []
created_date: '2026-10-14 22:59'
updated_date: '2026-10-15 00:21'
labels:
  - needs-refinement
  - platform
milestone: m-4
dependencies:
  - S-19
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
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
Include data-quality changes and deterioration of an accepted analytical method in the selected change cases. Routine repairs can proceed within the acceptance policy; unresolved business meaning or a change beyond that policy requires escalation.

- [ ] #1 Process a selected source change and show which results were reused or replaced. A materially incompatible schema blocks or repairs the affected step visibly. Failed refresh or interruption preserves the last accepted answer and source history.
- [ ] #2 Include data-quality changes and deterioration of an accepted analytical method in the selected change cases. Routine repairs can proceed within the acceptance policy; unresolved business meaning or a change beyond that policy requires escalation.
<!-- AC:END -->
