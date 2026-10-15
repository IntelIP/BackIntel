---
id: S-22
title: Configure a scoped connection
status: To Do
assignee: []
created_date: '2026-10-14 22:59'
updated_date: '2026-10-15 00:21'
labels:
  - needs-refinement
  - toolkit
  - platform
  - shared-core
milestone: m-1
dependencies:
  - S-12
  - S-04
  - S-05
documentation:
  - docs/ROADMAP.md
  - docs/roadmap/README.md
  - docs/roadmap/agile-backlog.md#shared-delivery-contract
priority: high
type: task
ordinal: 5
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Original roadmap story: S22. Original priority: P0. Work type: implementation.

## Business outcome

As a data owner, I need BackIntel to configure a connection from documentation and scoped access, so that I do not write an extraction routine manually.

## Scope

Inspect the permitted source catalog, schemas, API documentation, and available tools; identify relevant data and a collection contract; reuse an existing connector or generate and test bounded extraction; keep credentials outside generated code and packages.

## Owned surface

Selected connector configuration, source registration, and connection references. High risk: external access and credentials.

## Prerequisites

S-12, S-04, S-05.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Configure and check one permitted source without requiring the user to write extraction code or choose every routine step. The agent discovers only within the granted scope. Incorrect or insufficient access produces a clear result. Collection and any transmission remain within source permissions and the agreed data policy.
<!-- AC:END -->
