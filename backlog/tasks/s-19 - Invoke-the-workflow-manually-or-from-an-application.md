---
id: S-19
title: Invoke the workflow manually or from an application
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
  - S-18
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
ordinal: 14
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Original roadmap story: S19. Original priority: P0. Work type: implementation.

## Business outcome

As a user or application developer, I need a callable workflow, so that I can repeat accepted work with new authorized inputs.

## Scope

Expose stable manual and application entry points; validate input and workflow versions; reuse unchanged accepted results where valid.

## Owned surface

Workflow invocation interfaces and durable execution. Exact interfaces are selected at refinement.

## Prerequisites

S-18, S-06.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Invoke the same saved workflow manually and through the application interface. Both return equivalent checked results with run identity. A duplicate invocation cannot duplicate accepted work; an interruption resumes from retained progress.
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Add one shared saved-workflow invocation boundary: Python invoke(version, actor, input_ref=None), a manual module command, and POST /api/v1/workflows/{version}/runs. Validate the immutable workflow version, current source grant, objective version, complete input collection and dependencies. Pin the workflow/input digest into the existing durable run identity; do not issue model requests when reusing an accepted method.
2. Run preparation, independent meaning checks and exact calculation through the existing implementations inside one durable workflow job. Retain preparation pages and completed stage results, enforce limits and authorization, preserve the last useful answer on failure, and publish a checked result with workflow version, input reference, run identity, evidence, coverage and usage. A permitted replacement collection uses the same saved method after input-contract checks.
3. Wire platform run controls and the shared command. Verify manual/platform equivalence on all 541,909 real rows, duplicate result/charge protection, a real interrupted worker with retained-page recovery, and explicit denial or failure for invalid versions, unauthorized or incomplete inputs, changed schemas and failed preparation. Label synthetic edge cases. Run focused checks and keep S-39 as the final integrated demonstration.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Delivery planning — shared invocation boundary

Toolkit and platform callers should use the same saved-workflow implementation. At refinement, define the workflow version, associated objective, permitted input references, operating limits, and run identity, plus returned status, checked result, evidence, coverage, usage, and actionable failures. Verify equivalent manual and application results with existing duplicate and interruption protections. Platform presentation and scheduling must not be required to call the reusable capability. Select concrete package/API surfaces against available source; this does not claim the historical toolkit alpha was recovered. Existing prerequisites and acceptance remain in force.

Selected after S-18 completed. Existing job admission, durable pages, independent validators and calculation are the shared implementation. Start from S18Workflow-20261015/workflow-ready.dump. New workflow versions will pin the refactored execution components; preserve the earlier saved version in history. No additional model spending is required.

S-19 passed on 2026-10-15. The platform admitted a durable workflow run, its real worker terminated immediately after committing 2,000 prepared rows, and a fresh manual `python -m runtime.source_workflows run VERSION` process resumed the same run. It reused exactly 2,000 rows, finished the remaining 539,909, passed independent meaning checks, and matched all 4,070 product groups, 38 country groups and exact monetary totals against the saved CSV expectation. An explicit-input platform invocation reused the same run and returned the identical checked result; denied access was refused. No provider requests or charges occurred. Restart through accepted answer took 101.112 seconds. The fresh workflow version is c8bebd638e882b833eb9f840094b7199d94436728dba167da25654722b2bba41; the earlier package remains in history with an explicit dependency-version disposition. Evidence and the next database are /Users/hudson/Library/Application Support/BackIntel/Validation/S19InvocationAttempt2-20261015/invocation-evidence.json and workflow-invocation-result.dump. Focused method/package/meaning checks passed; the unrelated optional database case was skipped there, while the real workflow exercised PostgreSQL directly. Seventeen platform interaction checks, production build, dead-code and diff checks passed; Graphify refreshed and shared callers reviewed. A dispatcher indentation error in the first attempt was caught before processing and fixed before the successful check. See docs/saved-workflows.md for the shared API and manual entry points.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
The same saved workflow now runs through Python, the manual command and the platform. Real interruption recovery and duplicate invocation passed over all 541,909 rows with identical checked results and zero added provider cost. Exact verification and the restored database are retained in S19InvocationAttempt2-20261015.
<!-- SECTION:FINAL_SUMMARY:END -->
