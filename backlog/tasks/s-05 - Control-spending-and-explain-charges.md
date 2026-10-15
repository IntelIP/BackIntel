---
id: S-05
title: Control spending and explain charges
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
- [ ] #1 A permitted request reserves within the cap and settles recorded usage. Exhausted limits or unresolved charges prevent new paid admissions; overlapping requests cannot overspend. Fixtures test these paths before any separately authorized live calls. Unmeasured local compute remains unknown rather than zero.
<!-- AC:END -->
