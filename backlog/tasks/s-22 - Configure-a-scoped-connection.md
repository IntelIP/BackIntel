---
id: S-22
title: Configure a scoped connection
status: Done
assignee:
  - '@codex'
created_date: '2026-10-14 22:59'
updated_date: '2026-10-15 02:23'
labels:
  - toolkit
  - platform
  - shared-core
  - goal-reference-workflow
milestone: m-1
dependencies:
  - S-12
  - S-04
  - S-05
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
ordinal: 5
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Original roadmap story: S22. Original priority: P0. Work type: implementation.

## Business outcome

As a data owner, I need BackIntel to configure a connection from documentation and scoped access, so that I do not write an extraction routine manually.

## Scope

Inspect the permitted source catalog, schemas, API documentation, and available tools; identify relevant data and a collection contract; reuse an existing connector or generate and test bounded extraction; keep credentials outside generated code and packages.

## Owned surface

Selected connector configuration, source registration, and connection references. High risk: external access and credentials.

## Prerequisites

S-12, S-04, S-05.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Configure and check one permitted source without requiring the user to write extraction code or choose every routine step. The agent discovers only within the granted scope. Incorrect or insufficient access produces a clear result. Collection and any transmission remain within source permissions and the agreed data policy.
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Use the existing source-policy boundary and native PostgreSQL driver for the agreed online-retail-postgres reference. 2. Add durable automatic connection discovery before ingestion, with no model call and no user-written extraction query. Persist the permitted table/field catalogue and show it in the platform. Pin discovery to the objective version; preserve the source-policy checks at reads and acceptance. 3. Supply the public historical Kaggle snapshot through a separately provisioned local PostgreSQL demo source using a read-only identity. Source-owner bootstrap is distinct from agent collection. Keep credentials out of objectives, generated code, task files and packages. 4. Verify actual automatic discovery over the selected source, plus wrong/insufficient access. Source collection and semantic interpretation remain S-13/S-14; full integrated acceptance remains S-39.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Selected after S-12, S-04 and S-05 completion; S-06 is also complete. Owned surface: source registration/demo bootstrap, the durable connection-discovery operation, API and platform result display, and focused verification. The supported source is local PostgreSQL with operator-managed credential references and retail_raw scope. The two-call live planning authorization is consumed; no new paid call is authorized.

Passed: the real PostgreSQL demonstration restored the previously saved live objective and plan, loaded all 541,909 pinned CSV rows through a separate source-owner bootstrap, and discovered one permitted table with nine fields through the runtime and platform API. No provider requests were made. Artifacts: /Users/hudson/Library/Application Support/BackIntel/Validation/S22Discovery-20261014/discovery-evidence.json and both database dumps. The isolated source was removed after retaining these artifacts. Source collection and analytical answers remain unfinished. Local compute cost is unmeasured. Focused source-permission/runtime/API checks passed, including revoked and ungranted result/evidence access, goal revisions, native database privileges and repeated-request identity. Platform interaction tests and production build passed. Graphify dependencies were refreshed and inspected.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
BackIntel can discover the selected local PostgreSQL source without user-written extraction code. The platform displays the permitted source fields, and source grants govern reads and saved discovery results. Real-data metadata discovery, denied-access paths and UI checks passed; collection and analysis remain subsequent stories.
<!-- SECTION:FINAL_SUMMARY:END -->
