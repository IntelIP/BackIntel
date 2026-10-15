---
id: S-07
title: Complete the commerce analysis
status: To Do
assignee: []
created_date: '2026-10-14 22:58'
updated_date: '2026-10-15 00:21'
labels:
  - needs-refinement
  - toolkit
milestone: m-7
dependencies:
  - S-03
  - S-04
  - S-05
documentation:
  - docs/ROADMAP.md
  - docs/roadmap/README.md
  - docs/roadmap/agile-backlog.md#shared-delivery-contract
priority: medium
type: task
ordinal: 29
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Original roadmap story: S07. Original priority: P1. Work type: implementation.

## Business outcome

As an agent developer, I need a working commerce example, so that I can see the agent choose analytical steps and test a business hypothesis.

## Scope

Admit the example inputs; let the actual agent select approved analysis tools; compare the proposed prediction method with the predefined baseline, including whether text adds useful information.

## Owned surface

The reconciled commerce example and approved analytical tools. Preserve evaluation boundaries and prevent future outcomes entering prediction inputs.

## Prerequisites

S-03, S-04, S-05.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 The real agent produces a source-backed answer and comparable evaluation results. Numbers reconcile with an independent expected calculation. Missing inputs or an unsuccessful hypothesis produce an honest result. Label synthetic inputs and recorded replay correctly.
<!-- AC:END -->
