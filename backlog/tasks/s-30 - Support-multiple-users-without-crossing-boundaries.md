---
id: S-30
title: Support multiple users without crossing boundaries
status: To Do
assignee: []
created_date: '2026-10-14 22:59'
updated_date: '2026-10-16 02:03'
labels:
  - needs-refinement
  - platform
  - post-reference
milestone: m-5
dependencies:
  - S-19
  - S-04
  - S-05
references:
  - docs/retail-reference-workflow.md
  - docs/roadmap/agile-backlog.md
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

## Next staged delivery

Let several permitted users run the selected workflows while keeping their information, results, progress, and spending separate. User separation is required before claiming sustained operation for a shared deployment.

## Decisions before selection

Agree representative roles, source scopes, simultaneous-user and workload targets, shared resource limits, and how queued work is shown. Do not invent a concurrency target from the current machine or worker count.

These refinements record future work. Hudson selects one implementation story at a time; no implementation, model spending, live scheduling, commit, publication, or deployment is authorized by this planning update.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Concurrent permitted users complete the selected workflows without cross-user disclosure or overspending. An attempted cross-user access is denied. Report observed capacity rather than inferring it from the current worker configuration.
- [ ] #2 The agreed concurrent run records results, failures, waiting time, and known usage by user and for the shared service. Shared capacity contention is visible, and one user cannot inspect, change, cancel, or spend against another user's work without explicit permission.
<!-- AC:END -->
