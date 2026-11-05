---
id: S-34
title: Connect findings across business systems
status: Done
assignee:
  - '@codex'
created_date: '2026-10-14 22:59'
updated_date: '2026-10-18 19:23'
labels:
  - platform
  - post-reference
milestone: m-5
dependencies:
  - S-24
  - S-38
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

## Selected local demonstration
Use the historical retail PostgreSQL reference (S-38) and a separately running local service containing explicitly labeled demonstration cancellation targets. Answer which countries exceed a 10% demonstration cancellation-value target, then deliver the accepted finding to an explicitly permitted local inbox. No real business targets, business-record changes, external notifications, additional paid model calls, or Databricks access are implied.

## Shared definitions
The rate is negative signed C-prefix cancellation value divided by value without cancellations, using the retained exact-precision GBP method. The denominator is the signed sum of non-cancellation invoice lines, not audited revenue. Compare exact values; round only display. A nonpositive denominator or positive signed cancellation amount needs review. Service-owned country IDs carry explicit exact source-country mappings; do not silently normalize or infer aliases. Targets must cover the entire source calendar-date period, 2010-12-01 through 2011-12-09 inclusive. Record the historical source period, collection version, target version, publication and retrieval times separately. Source timezone remains unknown. Unmatched, conflicting, or ambiguous relationships remain visible and block an unsupported combined result.

## Owned surface and plan boundary
Reuse the saved, checked workflow and specialist independent reconciliation. Add a bounded local target-service connector, retained cross-source findings, and separately authorized delivery with persistent receipts and duplicate protection. Select further connectors separately. Source read access never grants delivery or write-back authority.

## Prerequisites
S-24, S-38, S-33 and selected local source/destination permissions. Hudson approved this alternative on 2026-10-18. S-26 remains open for actual Databricks integration; this trial does not satisfy it.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Complete the selected cross-system question with reconciled joins and evidence from each source. Deliver to the authorized destination and verify receipt without duplicate effects on replay. A conflicting identity, unavailable source, or forbidden destination is handled explicitly. Source permissions do not implicitly authorize business-record changes.
- [x] #2 The selected cross-source answer documents how identities, units, currency where relevant, and update times were reconciled. Ambiguous or unmatched records remain visible, and a material unresolved relationship prevents an unsupported combined finding.
- [x] #3 Delivery retains the accepted result identity and confirmation from the permitted destination. Replaying a delivery does not duplicate its effect; read permission alone never grants write-back or permission to notify other people.
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Finish S-27 before activating this story. Reuse the existing PostgreSQL collection, saved workflow, source grants, and independent specialist calculation check.
2. Implement one bounded local HTTP target-service contract with explicit country mappings, currency, effective dates, version, and demonstration labels; retain the received source and its digest.
3. Combine checked country totals and target definitions in a callable shared module/API. Persist the accepted result and request identity. Show unresolved mappings and source failures explicitly; do not deliver incomplete findings.
4. Authorize the local result destination independently and retain its receipt. Retry the same delivery identity after interruption without duplicating its effect.
5. Run the real historical PostgreSQL workload against the local target service, compare the country results with an independent SQL calculation, and verify identity conflicts, unavailable source, forbidden destination, lost acknowledgement, and duplicate replay. No new model calls. Run focused tests and required dead-code, patch, and relationship checks; document demonstrated scope.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
2026-10-18: Hudson approved the recommended local alternative: historical retail PostgreSQL plus a separate local service containing explicitly labeled demonstration cancellation targets, answering which countries exceed a 10% demonstration cancellation-value target and delivering findings locally. Refine this local prerequisite to S-38 while preserving S-26 for actual Databricks. No paid S-34 calls, business-record writes, or external notifications are authorized. Keep S-34 To Do until S-27 finishes.

S-27 is complete. Starting the approved local two-system demonstration under the recorded plan; zero new model allowance. Owned files: runtime/cross_systems.py, migration 0017, thin analysis API routes, local demonstration service and validation cases, focused tests, and existing documentation. Stop when the selected full-data result and delivery/replay/failure checks pass.

Implemented the selected local target connector, exact country comparison, retained target/source evidence, independently authorized delivery, durable idempotent receiver, and authenticated API/shared Python entry points. Focused reconciliation/permission tests pass; dead-code and patch checks and the dependency graph refresh pass. Full real-source acceptance is running in Validation/S34CrossSystems-20261018A; no paid model requests. Pending: inspect full calculation, SQL parity, delivery/restart/failure results before closing acceptance.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
The approved S-34 trial passed on 2026-10-18. `S34CrossSystems-20261018C` collected all 541,909 PostgreSQL records and reproduced the accepted calculation; `S34CrossSystems-20261018D` reused that completed collection and repeated the final comparison and delivery checks with corrected observation timestamps. Independent SQL reconciled all 38 country categories. Eight exceeded the explicitly synthetic 10% target: Singapore, USA, Hong Kong, Bahrain, Czech Republic, Portugal, Spain, and Saudi Arabia. These are demonstration comparisons, not actual business-policy breaches. Lost acknowledgement, receiver restart, and retries produced exactly one retained inbox effect. Conflicting identities/mappings, missing coverage, currency mismatch, unavailable sources, and revoked permissions were rejected. There were zero new model calls or charges. Evidence is retained under `~/Library/Application Support/BackIntel/Validation/` in those two directories; all trial servers were stopped. Actual Databricks remains S-26. Focused unit checks, native database/API acceptance, dead-code, patch, and Graphify checks passed.
<!-- SECTION:FINAL_SUMMARY:END -->
