---
id: S-13
title: Admit permitted inputs and retain originals
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
  - S-12
  - S-04
documentation:
  - docs/ROADMAP.md
  - docs/roadmap/README.md
  - docs/roadmap/agile-backlog.md#shared-delivery-contract
priority: high
type: task
ordinal: 6
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Original roadmap story: S13. Original priority: P0. Work type: implementation.

## Business outcome

As a data owner, I need original source files and responses preserved, so that cleaning cannot destroy evidence or prevent another approach.

## Scope

Admit permitted unfamiliar files or connector responses; retain their unchanged contents and identities; record collection context, permissions, and required handling limits.

## Owned surface

Raw-input admission, retained snapshots, and access context. High risk: loss or unauthorized data movement.

## Prerequisites

S-12, S-04.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Retrieve the unchanged original after processing and link derived rows to it. A denied, malformed, or unsupported input receives a clear disposition without replacing an accepted source.
<!-- AC:END -->
