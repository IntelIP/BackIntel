---
id: S-04
title: Use only permitted information and actions
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
  - S-01
documentation:
  - docs/ROADMAP.md
  - docs/roadmap/README.md
  - docs/roadmap/agile-backlog.md#shared-delivery-contract
priority: high
type: task
ordinal: 1
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Original roadmap story: S04. Original priority: P0. Work type: implementation.

## Business outcome

As a data owner, I need source and role permissions enforced, so that an agent uses only the information and actions I allowed.

## Scope

Reuse existing permission controls in the selected runtime, generated-code, and connector entry points; check allowed, denied, and expired access; ensure source text cannot grant additional authority.

## Owned surface

Selected runtime source admission and tool authorization using existing access controls. High risk: data exposure.

## Prerequisites

S-01; requires an identified candidate and agreed access policy.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 An allowed user accesses the intended source. An unauthorized or expired request cannot inspect data or publish a result. Instructions embedded in source content cannot alter access policy.
<!-- AC:END -->
