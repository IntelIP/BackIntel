---
id: S-12
title: Define the business question and operating limits
status: To Do
assignee: []
created_date: '2026-10-14 22:59'
updated_date: '2026-10-15 00:21'
labels:
  - needs-refinement
  - platform
milestone: m-1
dependencies:
  - S-01
documentation:
  - docs/ROADMAP.md
  - docs/roadmap/README.md
  - docs/roadmap/agile-backlog.md#shared-delivery-contract
priority: high
type: spike
ordinal: 4
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Original roadmap story: S12. Original priority: P0. Work type: research and implementation.

## Business outcome

As a business owner, I need to state the result, business measures, targets, and permitted systems, so BackIntel can plan the work without requiring me to design its pipeline.

## Scope

Refine one Databricks reference scenario: question, metric definitions, population, period, target, source scope, allowed actions and destinations, whole-workload boundary, expected checks, freshness, resources, and spending. Record unknown inputs honestly. Then implement objective capture and a revisable plan in the selected task; ask only about ambiguity that materially changes the result or authority.

## Owned surface

First reference-scenario contract and the goal/planning interface. Refinement is the next small deliverable; runtime implementation remains a separate selected task. No live connection is created by this plan.

## Prerequisites

S-01.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 For refinement, produce a bounded scenario and identify the first eligible implementation story with its prerequisites. For the runtime, show the saved question and an agent-created plan. The user supplies the objective and access, not an importer, transformations, or a list of analytical tool calls. Ambiguous units, identities, or target definitions are resolved or visibly held open.
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Delivery planning — toolkit and platform

Refine one business question that both delivery surfaces can support. Record the shared execution inputs and expected checked result, then the business-owner experience the platform must deliver. Keep source access, metric definitions, full-workload scope, freshness, resource/spending limits, and live-versus-fixture evidence explicit. Unknown values remain open; identify the first eligible implementation story after refinement. See docs/roadmap/README.md#toolkit-and-platform-delivery. This is planning guidance; runtime implementation is not started.
<!-- SECTION:NOTES:END -->
