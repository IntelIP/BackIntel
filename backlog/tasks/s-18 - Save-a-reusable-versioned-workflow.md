---
id: S-18
title: 'Save a reusable, versioned workflow'
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
  - S-17
documentation:
  - docs/ROADMAP.md
  - docs/roadmap/README.md
  - docs/roadmap/agile-backlog.md#shared-delivery-contract
priority: high
type: task
ordinal: 13
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Original roadmap story: S18. Original priority: P0. Work type: implementation.

## Business outcome

As an application owner, I need the accepted procedure saved, so that future runs do not depend on reconstructing a conversation.

## Scope

Package input requirements, connection references, transformations, table definitions, checks, dependencies, outputs, and limits; retain version history; exclude credentials from the package.

## Owned surface

Workflow package and versioned execution contract.

## Prerequisites

S-17.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Load the package in a new permitted execution context and inspect its input/output contract and original source links. A missing dependency receives a clear disposition. The package contains references to secrets, not secret values.
<!-- AC:END -->
