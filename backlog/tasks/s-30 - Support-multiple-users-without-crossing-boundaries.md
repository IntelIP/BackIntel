---
id: S-30
title: Support multiple users without crossing boundaries
status: To Do
assignee: []
created_date: '2026-10-14 22:59'
updated_date: '2026-10-15 00:21'
labels:
  - needs-refinement
  - platform
milestone: m-5
dependencies:
  - S-19
  - S-04
  - S-05
documentation:
  - docs/ROADMAP.md
  - docs/roadmap/README.md
  - docs/roadmap/agile-backlog.md#shared-delivery-contract
priority: medium
type: task
ordinal: 23
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Original roadmap story: S30. Original priority: P1. Work type: implementation.

## Business outcome

As an application owner, I need multiple users to work safely, so that their data, permissions, jobs, and budgets remain separate.

## Scope

Agree the representative concurrency target; exercise distinct roles and source scopes; resolve demonstrated contention while preserving admission and recovery guarantees.

## Owned surface

Selected multi-user execution, isolation, and capacity constraints. High risk: access and concurrent financial admission.

## Prerequisites

S-19, S-04, S-05 and an agreed concurrent-user target.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Concurrent permitted users complete the selected workflows without cross-user disclosure or overspending. An attempted cross-user access is denied. Report observed capacity rather than inferring it from the current worker configuration.
<!-- AC:END -->
