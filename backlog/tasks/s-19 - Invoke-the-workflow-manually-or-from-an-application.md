---
id: S-19
title: Invoke the workflow manually or from an application
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
  - S-18
  - S-06
documentation:
  - docs/ROADMAP.md
  - docs/roadmap/README.md
  - docs/roadmap/agile-backlog.md#shared-delivery-contract
priority: high
type: task
ordinal: 14
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Original roadmap story: S19. Original priority: P0. Work type: implementation.

## Business outcome

As a user or application developer, I need a callable workflow, so that I can repeat accepted work with new authorized inputs.

## Scope

Expose stable manual and application entry points; validate input and workflow versions; reuse unchanged accepted results where valid.

## Owned surface

Workflow invocation interfaces and durable execution. Exact interfaces are selected at refinement.

## Prerequisites

S-18, S-06.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Invoke the same saved workflow manually and through the application interface. Both return equivalent checked results with run identity. A duplicate invocation cannot duplicate accepted work; an interruption resumes from retained progress.
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Delivery planning — shared invocation boundary

Toolkit and platform callers should use the same saved-workflow implementation. At refinement, define the workflow version, associated objective, permitted input references, operating limits, and run identity, plus returned status, checked result, evidence, coverage, usage, and actionable failures. Verify equivalent manual and application results with existing duplicate and interruption protections. Platform presentation and scheduling must not be required to call the reusable capability. Select concrete package/API surfaces against available source; this does not claim the historical toolkit alpha was recovered. Existing prerequisites and acceptance remain in force.
<!-- SECTION:NOTES:END -->
