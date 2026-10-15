---
id: S-29
title: Complete the workload without manual batching
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
  - S-16
  - S-23
documentation:
  - docs/ROADMAP.md
  - docs/roadmap/README.md
  - docs/roadmap/agile-backlog.md#shared-delivery-contract
priority: high
type: task
ordinal: 11
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Original roadmap story: S29. Original priority: P0. Work type: implementation.

## Business outcome

As an analyst, I need to submit the workload once and have all eligible records processed, so I do not manage repeated small batches or mistake a sample for completion.

## Scope

Manage pagination, partitions, internal batches, resumable progress, and resource limits. Account for collected, processed, excluded, failed, and pending records. Replace fixed-cohort behavior where the selected workload requires complete classification or scoring; distinguish output-display limits from processing coverage.

## Owned surface

Whole-workload execution and coverage in the selected collection/preparation/analysis path. Automatic internal batching is allowed; user-managed batching is not the completion contract.

## Prerequisites

S-16, S-23 and an agreed workload/resource boundary.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Complete the agreed workload with reconciled coverage and checked results. Resume an interrupted partition without loss or duplicate accepted work. Partial work and exhausted limits remain visibly incomplete or resumable. Any legitimate training/evaluation sampling is explicit and never substitutes for required operational coverage. Record time, resources, and known cost; larger sustained-capacity claims belong to S36.
<!-- AC:END -->
