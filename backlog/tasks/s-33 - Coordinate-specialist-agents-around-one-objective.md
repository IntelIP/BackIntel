---
id: S-33
title: Coordinate specialist agents around one objective
status: To Do
assignee: []
created_date: '2026-10-14 22:59'
updated_date: '2026-10-16 02:03'
labels:
  - needs-refinement
  - platform
  - post-reference
milestone: m-5
dependencies:
  - S-19
  - S-32
  - S-04
  - S-05
  - S-06
references:
  - docs/retail-reference-workflow.md
  - docs/roadmap/agile-backlog.md
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

## Next staged delivery

Introduce actual specialist agents only for a bounded workflow where their distinct responsibilities are useful. The user supplies one objective; the product manages discovery, preparation, analysis, checking, and handoffs over shared controls.

## Decisions before selection

Select the objective, useful specialist responsibilities, shared input versions, conflict-resolution policy, and total operating limits. Agent count and implementation framework remain execution-time choices.

These refinements record future work. Hudson selects one implementation story at a time; no implementation, model spending, live scheduling, commit, publication, or deployment is authorized by this planning update.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Multiple actual agents complete one bounded workflow with a checkable combined result. Show an interrupted specialist, a rejected finding, and duplicate work without losing accepted progress or repeating an uncertain charge. An agent cannot expand another agent's permissions. Role labels or simulated responses alone do not establish a coordinated-agent implementation.
- [ ] #2 The owner can inspect a shared plan showing each actual specialist contribution, its input version, progress, accepted or rejected finding, and share of the total usage. The combined answer passes the selected independent check.
- [ ] #3 A disagreement identifies the conflicting evidence and is resolved by the agreed checking policy or surfaced as a specific unresolved question. It cannot silently become an accepted fact, and another specialist cannot bypass the original authority or budget.
<!-- AC:END -->
