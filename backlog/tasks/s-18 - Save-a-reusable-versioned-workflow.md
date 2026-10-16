---
id: S-18
title: 'Save a reusable, versioned workflow'
status: Done
assignee:
  - '@codex'
created_date: '2026-10-14 22:59'
updated_date: '2026-10-15 06:21'
labels:
  - toolkit
  - platform
  - shared-core
  - goal-reference-workflow
milestone: m-2
dependencies:
  - S-17
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
ordinal: 13
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Original roadmap story: S18. Original priority: P0. Work type: implementation.

## Business outcome

As an application owner, I need the accepted procedure saved, so that future runs do not depend on reconstructing a conversation.

## Scope

Package input requirements, connection references, transformations, table definitions, checks, dependencies, outputs, and limits; retain version history; exclude credentials from the package.

## Owned surface

Workflow package and versioned execution contract.

## Prerequisites

S-17.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Load the package in a new permitted execution context and inspect its input/output contract and original source links. A missing dependency receives a clear disposition. The package contains references to secrets, not secret values.
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Reuse the existing immutable evidence store for workflow packages and version history. Package the accepted objective, permitted source reference, schema and field meanings, preparation recipe, generated analysis method, required checks, input/output contracts, operating limits, runtime dependencies, and original-source/evidence references. Export references only; never copy connection credentials or retail records into the package.
2. Provide shared save/load/inspect functions and authenticated platform save/download/history routes. Validate package digest, saved provenance, current source authorization, and required dependencies. Report missing or changed dependencies clearly; retain every previous version.
3. Verify an exported real-workflow package in a fresh permitted process, inspect its source links and contracts, test missing dependencies/changed package/denied access/version retention, and exercise the platform controls. S-19 owns actual saved-workflow invocation and equivalent manual/platform reruns.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Selected after S-17 completed. Use S17LiveAnswerAttempt2-20261015/live-answer-result.dump as the latest accepted real-data state. No additional paid inference is required to package the accepted procedure. Only S-18 is active.

S-18 passed on 2026-10-15. The accepted real answer is packaged as immutable version a1307420589a7c71799430109733e7caa8d4f91b2afbe507bcadc46e2d94317c. The export contains objective/input/output contracts, interpretation, preparation recipe, generated method, checks, limits, pinned dependencies, a secret reference, and 271 original-source links. A fresh Python process loaded it successfully. Authenticated platform save, inspect, download, and source-link reads passed. Duplicate saves reused the version; altered packages and revoked access were refused; a missing preparation image was reported explicitly; two versions were retained in a separate synthetic dependency-history test. The database for continued real work is /Users/hudson/Library/Application Support/BackIntel/Validation/S18Workflow-20261015/workflow-ready.dump, saved BEFORE the synthetic unavailable version. workflow-package.json and workflow-evidence.json are alongside it. No provider calls or charges occurred; measured packaging/check time was 8.323 seconds. Pure package checks, 17 platform interaction checks, production build, dead-code check and diff check passed; Graphify updated and source/API registrations were exercised. Also fixed connected-source history rendering when its registered-dataset snapshot ID is null.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Saved a reusable, versioned real workflow with secret references and complete source links. Verified fresh-process loading, platform save/inspect/download, unchanged-version reuse, retained version history, missing-dependency disposition and access revocation. Continue from S18Workflow-20261015/workflow-ready.dump; S-19 owns invocation.
<!-- SECTION:FINAL_SUMMARY:END -->
