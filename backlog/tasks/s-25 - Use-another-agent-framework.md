---
id: S-25
title: Use another agent framework
status: To Do
assignee: []
created_date: '2026-10-14 22:59'
updated_date: '2026-10-17 01:27'
labels:
  - needs-refinement
  - toolkit
milestone: m-8
dependencies:
  - S-35
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
As an agent developer, I need the same analytical tools in another framework so I can adopt BackIntel without replacing my existing agent application. Hudson selected LangChain/LangGraph, then Agno and Mastra for bounded local integration trials. Reuse the authenticated platform interface and checked retail workflow. The child trials use the completed S-19 interface; S-35 remains the release qualification prerequisite. Local scripted-model trials do not complete independent installation, release qualification, or live model evaluation.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 The selected framework completes a documented analytical workflow with equivalent evidence, limits, and recovery. An unsupported operation or denied request remains explicit. The working core is reused.
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
User selected LangChain/LangGraph for a bounded local trial. Preserve the independent-operation prerequisite for full qualification; use a child spike for the local experiment.

Selected local trials are complete: S-25.01 LangChain/LangGraph, S-25.02 Agno, and S-25.03 Mastra. Each uses the existing authenticated saved workflow; no analytical engine replacement or paid model call was needed. See docs/saved-workflows.md for setup, artifacts and limits. Parent S-25 remains To Do with S-35 as the independent-operation/release qualification prerequisite; scripted local trials do not satisfy that broader gate.
<!-- SECTION:NOTES:END -->
