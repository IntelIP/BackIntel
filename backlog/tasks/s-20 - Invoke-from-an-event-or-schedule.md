---
id: S-20
title: Invoke from an event or schedule
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
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 An actual short-lived schedule runs when due and not before; a permitted event starts the same workflow. Duplicate events reuse accepted work. Expired authority or exhausted limits prevent new admissions rather than silently bypassing controls.
<!-- AC:END -->
