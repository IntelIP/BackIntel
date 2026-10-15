---
id: S-28
title: Process information near its source
status: To Do
assignee: []
created_date: '2026-10-14 22:59'
updated_date: '2026-10-15 00:21'
labels:
  - needs-refinement
  - optional
  - toolkit
  - platform
  - shared-core
milestone: m-8
dependencies:
  - S-24
documentation:
  - docs/ROADMAP.md
  - docs/roadmap/README.md
  - docs/roadmap/agile-backlog.md#shared-delivery-contract
priority: low
type: task
ordinal: 35
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Original roadmap story: S28. Original priority: P2. Work type: implementation.

## Business outcome

As a data owner, I need work performed near sensitive information, so that only permitted data or results leave that environment.

## Scope

Define the permitted processing and transmission boundary; configure one on-site worker; retain recoverable jobs and allowed result delivery.

## Owned surface

Selected on-site execution and permitted data movement. High risk: privacy and remote access.

## Prerequisites

S-24 and an agreed on-site/data-movement policy.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Complete one authorized workflow within the agreed boundary. An attempted forbidden transmission is denied. Connection loss retains progress and a clear recovery state. Fully local model reasoning is a separate design decision.
<!-- AC:END -->
