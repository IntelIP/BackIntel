---
id: S-34
title: Connect findings across business systems
status: To Do
assignee: []
created_date: '2026-10-14 22:59'
updated_date: '2026-10-15 00:21'
labels:
  - needs-refinement
  - platform
milestone: m-5
dependencies:
  - S-24
  - S-26
  - S-33
documentation:
  - docs/ROADMAP.md
  - docs/roadmap/README.md
  - docs/roadmap/agile-backlog.md#shared-delivery-contract
priority: medium
type: task
ordinal: 22
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Original roadmap story: S34. Original priority: P1. Work type: implementation.

## Business outcome

As a business owner, I need permitted systems to contribute to and receive useful findings, so I can answer a question across business boundaries without manually moving data between tools.

## Scope

Select at least two sources and one permitted result destination for a concrete workflow. Discover relevant information, reconcile identities, units and update timing, prepare checked cross-source relationships, and deliver agreed results or events. Scope any write-back action separately from read access; retain source and delivery history.

## Owned surface

Selected additional connectors, shared business definitions, cross-source preparation, and permitted result delivery. Further connectors remain individually selected tasks; no universal connector coverage is claimed.

## Prerequisites

S-24, S-26, S-33 and selected source/destination permissions.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Complete the selected cross-system question with reconciled joins and evidence from each source. Deliver to the authorized destination and verify receipt without duplicate effects on replay. A conflicting identity, unavailable source, or forbidden destination is handled explicitly. Source permissions do not implicitly authorize business-record changes.
<!-- AC:END -->
