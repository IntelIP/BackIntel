---
id: S-23
title: Collect complete and traceable information
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
  - S-22
  - S-13
documentation:
  - docs/ROADMAP.md
  - docs/roadmap/README.md
  - docs/roadmap/agile-backlog.md#shared-delivery-contract
priority: high
type: task
ordinal: 7
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Original roadmap story: S23. Original priority: P0. Work type: implementation.

## Business outcome

As an analyst, I need complete permitted records with source links, so that findings are not based on a silently partial or duplicated collection.

## Scope

Fetch the required pages; check completeness and duplicate identities; retain original responses and collection boundaries.

## Owned surface

Selected extraction workflow, collection checks, raw snapshots, and lineage.

## Prerequisites

S-22, S-13.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 The collected snapshot reconciles with an independent expected set. A missing page, interrupted collection, or enforced limit is visible; partial results are not labeled complete. Duplicate records do not inflate the answer.
<!-- AC:END -->
