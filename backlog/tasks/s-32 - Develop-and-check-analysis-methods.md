---
id: S-32
title: Develop and check analysis methods
status: To Do
assignee: []
created_date: '2026-10-14 22:59'
updated_date: '2026-10-15 00:21'
labels:
  - needs-refinement
  - toolkit
  - platform
  - shared-core
milestone: m-3
dependencies:
  - S-18
  - S-05
  - S-15
  - S-16
documentation:
  - docs/ROADMAP.md
  - docs/roadmap/README.md
  - docs/roadmap/agile-backlog.md#shared-delivery-contract
priority: medium
type: task
ordinal: 16
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Original roadmap story: S32. Original priority: P1. Work type: implementation.

## Business outcome

As a business owner, I need BackIntel to develop an appropriate analytical approach, so a useful new question does not require a separate data-science coding project.

## Scope

Let the agent propose hypotheses, calculations, features, classifications, and prediction candidates. Generate bounded code when needed, run it in the permitted isolated workspace, check it independently, and compare with a simple baseline. Preserve evaluation data and prevent future outcomes or iterative test-set tuning from contaminating comparisons. Retain code, inputs, checks, and method versions.

## Owned surface

Planning, generated analysis code, independent checking, method comparison, and retained method versions. The selected task bounds search effort and cost.

## Prerequisites

S-18, S-05, S-15, S-16 and an agreed method-acceptance policy.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 For a selected question that the fixed tool catalog cannot answer, the agent develops and tests a method without a user-written analysis script. Demonstrate a checkable result, a rejected or unhelpful candidate, uncertainty, and a retained baseline when appropriate. Method selection follows the agreed policy; current human approval for predictor promotion remains unless explicitly changed. Neither accuracy gains nor causation are assumed.
<!-- AC:END -->
