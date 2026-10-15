---
id: S-35
title: Operate the autonomous workflow independently
status: To Do
assignee: []
created_date: '2026-10-14 22:59'
updated_date: '2026-10-15 00:21'
labels:
  - needs-refinement
  - platform
milestone: m-6
dependencies:
  - S-24
  - S-26
  - S-32
  - S-33
  - S-34
  - S-30
  - S-36
documentation:
  - docs/ROADMAP.md
  - docs/roadmap/README.md
  - docs/roadmap/agile-backlog.md#shared-delivery-contract
priority: medium
type: task
ordinal: 25
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Original roadmap story: S35. Original priority: P1. Work type: manual-task and implementation.

## Business outcome

As a new user, I need a reproducible installation and operating instructions, so I can run the declared autonomous workflow without the implementer's private environment.

## Scope

Package the identified runtime, interfaces, workflow definitions, and dependencies; document connections, permissions, limits, results, freshness, recovery, and material escalation. Have an independent user run the declared scope. Select any client/service split through a separate justified design decision.

## Owned surface

Autonomous-product packaging, entry points, operating guidance, and independent reproduction. This does not depend on recovering the separate historical toolkit candidate.

## Prerequisites

S-24, S-26, S-32, S-33, S-34, S-30, S-36.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 The user installs the identified candidate, grants the intended access, supplies the business objective, receives a checked answer, and observes refresh and recovery. Record the human configuration and intervention still required. Private workspace files or hardcoded demonstration responses cannot supply missing behavior. Required review/checks apply to the same candidate; actual publication and deployment are separate authorized outcomes.
<!-- AC:END -->
