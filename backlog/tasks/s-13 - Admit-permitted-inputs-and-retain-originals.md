---
id: S-13
title: Admit permitted inputs and retain originals
status: Done
assignee:
  - '@codex'
created_date: '2026-10-14 22:59'
updated_date: '2026-10-15 02:29'
labels:
  - toolkit
  - platform
  - shared-core
  - goal-reference-workflow
milestone: m-2
dependencies:
  - S-12
  - S-04
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
ordinal: 6
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Original roadmap story: S13. Original priority: P0. Work type: implementation.

## Business outcome

As a data owner, I need original source files and responses preserved, so that cleaning cannot destroy evidence or prevent another approach.

## Scope

Admit permitted unfamiliar files or connector responses; retain their unchanged contents and identities; record collection context, permissions, and required handling limits.

## Owned surface

Raw-input admission, retained snapshots, and access context. High risk: loss or unauthorized data movement.

## Prerequisites

S-12, S-04.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Retrieve the unchanged original after processing and link derived rows to it. A denied, malformed, or unsupported input receives a clear disposition without replacing an accepted source.
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Add immutable admission for bounded PostgreSQL source responses using the existing source grants and saved objective. Preserve each original response value and its source row identity before preparation, with source/table, goal-version and schema context. 2. Keep originals in the local application store and identify them by content digest; derived records must refer to the retained snapshot and original row identity. Repeated admission must reuse the accepted content. 3. Reject denied, malformed, unsupported or over-limit inputs without replacing accepted originals. Expose guarded retrieval for the shared workflow; whole-source collection and reconciliation are S-23. 4. Verify unchanged retrieval, row linkage, access revocation, malformed/unsupported cases and accepted-original preservation with disposable PostgreSQL checks. Stop when S-13 acceptance passes; do not treat an admitted response as a complete workload.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Selected after S-22 completion. Only S-13 is active. The source is the agreed local PostgreSQL reference; the contract preserves source responses without claiming CSV collection or analytical completion. No new paid calls.

Passed disposable PostgreSQL checks: exact original byte retrieval through the authenticated API after a synthetic transformation; exact negative decimals, nulls and duplicate-looking rows retained; derived rows resolve original identities; repeated admission reuses content; malformed, nested, duplicate-ID, denied and over-limit responses cannot replace accepted originals. Revoked grants block metadata and original downloads. Synthetic admission checks do not establish real-data collection. Graphify callers checked; repository dead-code check passed.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Shared runtime preserves unchanged connector responses with source context and stable row links. The platform API retrieves originals only under current source permission. Admission, retrieval, lineage and denial checks passed. Whole-source collection remains S-23.
<!-- SECTION:FINAL_SUMMARY:END -->
