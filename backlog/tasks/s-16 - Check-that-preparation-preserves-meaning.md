---
id: S-16
title: Check that preparation preserves meaning
status: To Do
assignee: []
created_date: '2026-10-14 22:59'
updated_date: '2026-10-15 00:21'
labels:
  - needs-refinement
  - toolkit
  - platform
  - shared-core
milestone: m-2
dependencies:
  - S-15
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
- [ ] #1 Prepared data matches an independent expected result. A double-counting join, mixed unit, or unexplained exclusion fails the check and prevents a misleading accepted answer. Retain the reason and affected records.
<!-- AC:END -->
