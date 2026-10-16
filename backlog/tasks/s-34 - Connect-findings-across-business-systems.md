---
id: S-34
title: Connect findings across business systems
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
  - S-24
  - S-26
  - S-33
references:
  - docs/retail-reference-workflow.md
  - docs/roadmap/agile-backlog.md
documentation:
  - docs/ROADMAP.md
  - docs/roadmap/README.md
  - docs/roadmap/agile-backlog.md#shared-delivery-contract
priority: medium
type: task
ordinal: 22
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Original roadmap story: S34. Original priority: P1. Work type: implementation.

## Business outcome

As a business owner, I need permitted systems to contribute to and receive useful findings, so I can answer a question across business boundaries without manually moving data between tools.

## Scope

Select at least two sources and one permitted result destination for a concrete workflow. Discover relevant information, reconcile identities, units and update timing, prepare checked cross-source relationships, and deliver agreed results or events. Scope any write-back action separately from read access; retain source and delivery history.

## Owned surface

Selected additional connectors, shared business definitions, cross-source preparation, and permitted result delivery. Further connectors remain individually selected tasks; no universal connector coverage is claimed.

## Prerequisites

S-24, S-26, S-33 and selected source/destination permissions.

## Next staged delivery

Answer one business question using at least two permitted business systems, then deliver the agreed finding to one authorized destination. Reuse the shared workflow and specialist coordination instead of manually exporting and joining information.

## Decisions before selection

Select the systems, result destination, permitted actions, shared business definitions, and independent expected result. The existing S-26 Databricks prerequisite remains unchanged; choosing a different integration path requires an explicit refinement decision rather than silently treating PostgreSQL as proof of Databricks access.

These refinements record future work. Hudson selects one implementation story at a time; no implementation, model spending, live scheduling, commit, publication, or deployment is authorized by this planning update.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Complete the selected cross-system question with reconciled joins and evidence from each source. Deliver to the authorized destination and verify receipt without duplicate effects on replay. A conflicting identity, unavailable source, or forbidden destination is handled explicitly. Source permissions do not implicitly authorize business-record changes.
- [ ] #2 The selected cross-source answer documents how identities, units, currency where relevant, and update times were reconciled. Ambiguous or unmatched records remain visible, and a material unresolved relationship prevents an unsupported combined finding.
- [ ] #3 Delivery retains the accepted result identity and confirmation from the permitted destination. Replaying a delivery does not duplicate its effect; read permission alone never grants write-back or permission to notify other people.
<!-- AC:END -->
