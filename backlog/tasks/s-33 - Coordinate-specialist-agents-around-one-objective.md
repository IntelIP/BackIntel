---
id: S-33
title: Coordinate specialist agents around one objective
status: To Do
assignee: []
created_date: '2026-10-14 22:59'
updated_date: '2026-10-15 00:21'
labels:
  - needs-refinement
  - platform
milestone: m-5
dependencies:
  - S-19
  - S-32
  - S-04
  - S-05
  - S-06
documentation:
  - docs/ROADMAP.md
  - docs/roadmap/README.md
  - docs/roadmap/agile-backlog.md#shared-delivery-contract
priority: medium
type: task
ordinal: 21
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Original roadmap story: S33. Original priority: P1. Work type: implementation.

## Business outcome

As a workflow owner, I need specialists to coordinate discovery, preparation, analysis, and checking, so I do not manage their handoffs or reconcile conflicting results myself.

## Scope

Add a coordinator with a shared plan, versioned inputs, explicit responsibilities, dependencies, job ownership, evidence, and budget accounting. Invoke specialists when useful; resolve conflicting findings or escalate material uncertainty. Keep retries and concurrent external actions within existing authority.

## Owned surface

Coordination and specialist interfaces over the durable workflow. Agent count, framework, and process topology follow the selected workload rather than being fixed by this story.

## Prerequisites

S-19, S-32, S-04, S-05, S-06.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Multiple actual agents complete one bounded workflow with a checkable combined result. Show an interrupted specialist, a rejected finding, and duplicate work without losing accepted progress or repeating an uncertain charge. An agent cannot expand another agent's permissions. Role labels or simulated responses alone do not establish a coordinated-agent implementation.
<!-- AC:END -->
