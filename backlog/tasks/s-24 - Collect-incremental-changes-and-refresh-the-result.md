---
id: S-24
title: Collect incremental changes and refresh the result
status: To Do
assignee: []
created_date: '2026-10-14 22:59'
updated_date: '2026-10-15 00:21'
labels:
  - needs-refinement
  - toolkit
  - platform
  - shared-core
milestone: m-4
dependencies:
  - S-23
  - S-20
  - S-21
documentation:
  - docs/ROADMAP.md
  - docs/roadmap/README.md
  - docs/roadmap/agile-backlog.md#shared-delivery-contract
priority: medium
type: task
ordinal: 19
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Original roadmap story: S24. Original priority: P1. Work type: implementation.

## Business outcome

As an operations user, I need new and changed source records incorporated, so that a recurring answer stays current without unnecessary full recollection.

## Scope

Retain collection progress; apply the selected source's update and deletion semantics; invoke the saved workflow and recover an interrupted update.

## Owned surface

Incremental extraction, source-change admission, refresh, and recovery for the selected connector.

## Prerequisites

S-23, S-20, S-21.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Add and change known records, then show the correct refreshed answer and retained originals. Repeated or interrupted collection does not lose or duplicate accepted records. Failed collection preserves the last useful result and identifies staleness.
<!-- AC:END -->
