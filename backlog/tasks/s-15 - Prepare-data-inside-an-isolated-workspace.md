---
id: S-15
title: Prepare data inside an isolated workspace
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
  - S-14
  - S-05
  - S-06
documentation:
  - docs/ROADMAP.md
  - docs/roadmap/README.md
  - docs/roadmap/agile-backlog.md#shared-delivery-contract
priority: high
type: task
ordinal: 9
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Original roadmap story: S15. Original priority: P0. Work type: implementation.

## Business outcome

As a business user, I need BackIntel to create and repair preparation steps, so that I do not manually write cleaning code for each export.

## Scope

Plan bounded transformations; execute generated or configured preparation code in an isolated workspace; retain accepted steps and repair a demonstrated failure within the operating limits.

## Owned surface

Preparation workspace, execution boundary, and retained preparation code. High risk: generated execution and data access.

## Prerequisites

S-14, S-05, S-06.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
Classifications must retain source links and uncertain or unclassified records; the agent cannot silently invent labels needed for the answer.

- [ ] #1 Produce reusable tables from the unfamiliar input. Demonstrate a recoverable transformation error and a refused unauthorized file or network operation. The user does not supply a bespoke importer; source content cannot expand tool authority.
- [ ] #2 Classifications must retain source links and uncertain or unclassified records; the agent cannot silently invent labels needed for the answer.
<!-- AC:END -->
