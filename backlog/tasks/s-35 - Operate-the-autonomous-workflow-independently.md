---
id: S-35
title: Operate the autonomous workflow independently
status: To Do
assignee: []
created_date: '2026-10-14 22:59'
updated_date: '2026-10-16 02:03'
labels:
  - needs-refinement
  - platform
  - post-reference
milestone: m-6
dependencies:
  - S-24
  - S-26
  - S-32
  - S-33
  - S-34
  - S-30
  - S-36
references:
  - docs/retail-reference-workflow.md
  - docs/roadmap/agile-backlog.md
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

## Next staged delivery

Demonstrate that another user can operate the selected autonomous platform workflow from the documented distribution candidate, without the implementer's private environment. Shared toolkit calls remain part of the declared workflow; this does not qualify the unavailable historical toolkit alpha or authorize a release.

## Decisions before selection

Select the distribution candidate, clean supported environment, independent operator, required credentials and source setup, and declared workflow. The separate historical toolkit path remains S-02 through S-03 and its existing qualification stories.

These refinements record future work. Hudson selects one implementation story at a time; no implementation, model spending, live scheduling, commit, publication, or deployment is authorized by this planning update.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 The user installs the identified candidate, grants the intended access, supplies the business objective, receives a checked answer, and observes refresh and recovery. Record the human configuration and intervention still required. Private workspace files or hardcoded demonstration responses cannot supply missing behavior. Required review/checks apply to the same candidate; actual publication and deployment are separate authorized outcomes.
- [ ] #2 The independent operator uses only the documented candidate, dependencies, and their permitted credential references to install, start, run, inspect, and recover the declared workflow. Any implementer intervention or undocumented setup is recorded and resolved before independent-operation acceptance.
- [ ] #3 Instructions explain expected outputs, remaining human decisions, spending and source limits, failure recovery, and shutdown. Successful local installation does not imply publication, deployment elsewhere, or qualification of an unavailable toolkit candidate.
<!-- AC:END -->
