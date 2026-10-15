---
id: S-25
title: Use another agent framework
status: To Do
assignee: []
created_date: '2026-10-14 22:59'
updated_date: '2026-10-15 00:21'
labels:
  - needs-refinement
  - optional
  - toolkit
milestone: m-8
dependencies: []
documentation:
  - docs/ROADMAP.md
  - docs/roadmap/README.md
  - docs/roadmap/agile-backlog.md#shared-delivery-contract
priority: low
type: task
ordinal: 34
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Original roadmap story: S25. Original priority: P2. Work type: implementation.

## Business outcome

As an agent developer, I need the same analytical tools in another framework, so that I can adopt BackIntel without replacing my existing agent application.

## Scope

Select Agno or OpenAI Agents SDK based on a concrete need; adapt the existing tool contracts; document and run one complete example. Refine the other integration as a separate later instance of this story.

## Owned surface

One selected framework adapter and its example. No blanket framework replacement is selected.

## Prerequisites

S-35 or S-11, depending on the selected interface; requires a selected framework/use case.

This is an alternative prerequisite: choose the relevant interface during refinement, then set S-35 or S-11 as the native dependency. Both are not required.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 The selected framework completes a documented analytical workflow with equivalent evidence, limits, and recovery. An unsupported operation or denied request remains explicit. The working core is reused.
<!-- AC:END -->
