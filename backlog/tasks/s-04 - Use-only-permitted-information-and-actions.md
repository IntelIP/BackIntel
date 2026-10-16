---
id: S-04
title: Use only permitted information and actions
status: Done
assignee:
  - '@codex'
created_date: '2026-10-14 22:58'
updated_date: '2026-10-15 06:21'
labels:
  - toolkit
  - platform
  - shared-core
  - goal-reference-workflow
milestone: m-0
dependencies:
  - S-01
references:
  - >-
    backlog/tasks/s-38 -
    Deliver-one-checked-Databricks-answer-through-the-toolkit-and-platform.md
documentation:
  - docs/ROADMAP.md
  - docs/roadmap/README.md
  - docs/roadmap/agile-backlog.md#shared-delivery-contract
priority: high
type: task
ordinal: 1
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Original roadmap story: S04. Original priority: P0. Work type: implementation.

## Business outcome

As a data owner, I need source and role permissions enforced, so that an agent uses only the information and actions I allowed.

## Scope

Reuse existing permission controls in the selected runtime, generated-code, and connector entry points; check allowed, denied, and expired access; ensure source text cannot grant additional authority.

## Owned surface

Selected runtime source admission and tool authorization using existing access controls. High risk: data exposure.

## Prerequisites

S-01; requires an identified candidate and agreed access policy.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 An allowed user accesses the intended source. An unauthorized or expired request cannot inspect data or publish a result. Instructions embedded in source content cannot alter access policy.
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Refine the selected access policy: local PostgreSQL, retail_raw only, read-only access, a currently permitted principal, local output, and source text cannot change policy. 2. Reuse runtime authorization and add the smallest shared source-policy and PostgreSQL access boundary needed for this source; keep secrets outside objectives and source content. 3. Verify actual reads plus denied, expired, revoked and out-of-scope access on isolated PostgreSQL, including the acceptance boundary. 4. Record the result before connector configuration/discovery in S-22. No new provider spending.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Selected after S-12 completion. Candidate is the current BackIntel runtime. Owned surface: shared source permissions, the minimal PostgreSQL read-only access boundary, and focused checks. Stop when permitted source reads work and unauthorized, expired or source-injected changes cannot inspect data or produce an accepted result. S-22 will configure/discover the connection; S-39 proves the full workflow.

Added an operator-managed source grant table separate from the business objective, plus shared local-PostgreSQL metadata/preview access. The boundary reuses current principal checks, restricts the schema and named connection, requires an unprivileged read-only database identity, blocks nonlocal addresses and DSN options, holds policy locks during reads, and rejects expiry before returning data. Analysis publication now rechecks the same source authority. Actual PostgreSQL checks exercised allowed reads, hidden schemas, denied/revoked/expired principals and grants, expiry during a read, write-capable identities and instruction-bearing source rows. Fixtures contain synthetic rows and analysis replies; no Kaggle workload has yet been executed. The initial 70-test run had one assertion mismatch: the existing runtime retains a cancellation receipt rather than null. Updated the assertion to require cancellation, no analytical tables, no accepted finding, and no successful last-result pointer; the focused rerun is pending. No further provider calls were made.

Added operator-managed connection grants and shared PostgreSQL source access, separate from objectives and source rows. Actual isolated PostgreSQL checks passed for permitted metadata/preview reads, schema denial, revoked/expired principal and source grants, expiry during a read, nonlocal/privileged/write-capable connections, and instruction-bearing source content. Result acceptance rechecks the grant; a revoked source produced a cancellation receipt with no analytical tables or accepted finding. The original 70-test run had one receipt-shape assertion corrected; the focused rerun passed. The source rows and analysis body in these checks were explicitly synthetic; this verifies the selected access boundary, not the Kaggle workflow or autonomous connection setup. S-22 and S-39 retain those obligations. Graph index updated; no paid calls.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Added operator-managed connection grants and shared PostgreSQL source access, separate from objectives and source rows. Actual isolated PostgreSQL checks passed for permitted metadata/preview reads, schema denial, revoked/expired principal and source grants, expiry during a read, nonlocal/privileged/write-capable connections, and instruction-bearing source content. Result acceptance rechecks the grant; a revoked source produced a cancellation receipt with no analytical tables or accepted finding. The original 70-test run had one receipt-shape assertion corrected; the focused rerun passed. The source rows and analysis body in these checks were explicitly synthetic; this verifies the selected access boundary, not the Kaggle workflow or autonomous connection setup. S-22 and S-39 retain those obligations. Graph index updated; no paid calls.
<!-- SECTION:FINAL_SUMMARY:END -->
