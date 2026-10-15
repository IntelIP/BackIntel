---
id: S-14
title: Understand fields and table relationships
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
  - S-13
documentation:
  - docs/ROADMAP.md
  - docs/roadmap/README.md
  - docs/roadmap/agile-backlog.md#shared-delivery-contract
priority: high
type: task
ordinal: 8
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Original roadmap story: S14. Original priority: P0. Work type: implementation.

## Business outcome

As an analyst, I need BackIntel to interpret unfamiliar fields, units, identities, and relationships, so that preparation reflects the business meaning.

## Scope

Inspect types, missingness, units, dates, keys, and candidate relationships; propose meanings and mappings; retain unresolved ambiguity.

## Owned surface

Source profiling and semantic preparation definitions for the selected task.

## Prerequisites

S-13.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Correctly interpret a selected unfamiliar schema with independently known meanings. Ambiguous dates, units, identities, or joins remain explicit rather than being silently resolved. No dataset-specific importer is required from the user.
<!-- AC:END -->
