---
id: S-15
title: Prepare data inside an isolated workspace
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
  - S-14
  - S-05
  - S-06
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
ordinal: 9
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Original roadmap story: S15. Original priority: P0. Work type: implementation.

## Business outcome

As a business user, I need BackIntel to create and repair preparation steps, so that I do not manually write cleaning code for each export.

## Scope

Plan bounded transformations; execute generated or configured preparation code in an isolated workspace; retain accepted steps and repair a demonstrated failure within the operating limits.

## Owned surface

Preparation workspace, execution boundary, and retained preparation code. High risk: generated execution and data access.

## Prerequisites

S-14, S-05, S-06.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
Classifications must retain source links and uncertain or unclassified records; the agent cannot silently invent labels needed for the answer.

- [x] #1 Produce reusable tables from the unfamiliar input. Demonstrate a recoverable transformation error and a refused unauthorized file or network operation. The user does not supply a bespoke importer; source content cannot expand tool authority.
- [x] #2 Classifications must retain source links and uncertain or unclassified records; the agent cannot silently invent labels needed for the answer.
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Derive a bounded, reusable preparation recipe from the accepted semantic proposal and complete collection; preserve identifiers, missing values, signs, exact decimal precision, source row links and unresolved meanings. The system supplies the recipe; the user supplies no importer or preparation code. 2. Reuse the host-side Docker sandbox with a separately bounded preparation profile. Run only configured conversions in an immutable local image, without network, secrets, writable host mounts or extra capabilities. Keep defaults for existing artifact workloads unchanged. 3. Retain the recipe, sandbox receipt and prepared pages through existing durable steps. Repair a demonstrated conversion failure once by retaining the source value and an explicit unresolved marker; no silent exclusions or invented classes. 4. Add the preparation operation and its summary to the existing shared runtime and platform. Verify denied file/network operations, error repair, source links, revoked grants and retained results with synthetic cases, then prepare all 541,909 real rows from the saved S-14 database without provider calls. S-16 owns independent semantic acceptance before analysis; do not claim a checked business answer here.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Selected under S-38 after S-14, S-05 and S-06 passed. Only S-15 is active. Reuse runtime/sandbox.py and the accepted live interpretation; one remaining paid interpretation revision is not needed for this configured preparation stage. No provider calls are planned.

The real source preparation completed all 541,909 rows in 55.283 seconds (7.313 seconds inside the isolated worker); excluded, failed, pending and unresolved rows were all zero. Provider calls and provider cost were zero; local compute cost remains unmeasured. The platform API showed the prepared result and resolved retained originals. Image: sha256:46d93453a2a426ca456854ee8ba188202b547015674515b04ec742067eb484bf; worker limits: 1 CPU, 1 GiB memory, 300 seconds, no network. Evidence and restorable database: /Users/hudson/Library/Application Support/BackIntel/Validation/S15Preparation-20261014/. Synthetic database checks demonstrated one conservative repair, exact decimals, missing/unknown retention, source links, denied access and no duplicate sandbox execution on repeat. Actual sandbox attempts to read host files, overwrite inputs and connect externally were refused. Platform interactions (15 tests), web build, dead-code and diff checks passed; Graphify callers confirmed the shared service path. No independent semantic acceptance or business answer is claimed yet.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
BackIntel now derives a preparation recipe from its accepted interpretation and executes bounded conversions in an isolated workspace. Real complete-data execution and synthetic error-repair/isolation checks passed. Every prepared page links to its unchanged original; uncertain categories and failed conversions remain visible. S-16 must independently check meaning before analysis.
<!-- SECTION:FINAL_SUMMARY:END -->
