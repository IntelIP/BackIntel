---
id: S-09
title: Verify findings and ask a follow-up
status: To Do
assignee: []
created_date: '2026-10-14 22:59'
updated_date: '2026-10-15 00:21'
labels:
  - needs-refinement
  - toolkit
milestone: m-7
dependencies:
  - S-07
  - S-08
documentation:
  - docs/ROADMAP.md
  - docs/roadmap/README.md
  - docs/roadmap/agile-backlog.md#shared-delivery-contract
priority: medium
type: task
ordinal: 31
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Original roadmap story: S09. Original priority: P1. Work type: implementation.

## Business outcome

As a reviewer, I need to inspect evidence, uncertainty, and follow-up answers, so that I can check a finding before recording a decision.

## Scope

Expose relevant source and calculation references; support a scoped follow-up and correction through the existing interface; show how corrected evidence affects the result and predictor validity.

## Owned surface

Existing toolkit result, evidence, follow-up, correction, and human-review interfaces. Reuse current interfaces before proposing a new one.

## Prerequisites

S-07, S-08.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Trace a numerical finding to its source, ask a follow-up, and record a decision. A correction creates an inspectable updated result. Missing evidence, model disagreement, and insufficient information remain explicit; an invalidated predictor is not silently treated as current.
<!-- AC:END -->
