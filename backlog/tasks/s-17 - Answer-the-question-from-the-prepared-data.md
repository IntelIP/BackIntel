---
id: S-17
title: Answer the question from the prepared data
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
  - S-16
  - S-23
  - S-29
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
ordinal: 12
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Original roadmap story: S17. Original priority: P0. Work type: implementation.

## Business outcome

As a business user, I need an explained answer from the newly prepared data, so that unfamiliar inputs lead to useful work rather than only cleaned tables.

## Scope

Build the task-specific analysis snapshot; use its checked definitions in analytical tools; produce findings, business measures, target progress, and useful artifacts with evidence, coverage, freshness, and limitations.

## Owned surface

Analysis snapshot, dynamic table consumption, findings, and output artifacts. Reuse existing analytical tools where their contracts fit.

## Prerequisites

S-16, S-23, S-29.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Answer the selected question correctly using the unfamiliar schema and prepared tables. Every material claim traces to the relevant snapshot. Insufficient data produces an explicit limitation; an estimate or hypothesis is not presented as an observed fact.
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Generate a bounded analysis method from the saved objective and accepted field meanings, using field bindings and a sum-of-products operation for the agreed invoice-value question. The agent selects source fields and grouping dimensions; the user supplies no analysis code. Constrain the method to the checked source, exact decimal arithmetic, preserved cancellation signs, complete coverage and explicit uncertainties. 2. Execute the method over every checked prepared row, retaining exact totals and all product/country groups, tied leaders, source period, source fingerprint and limitations. Derive every reported fact from retained calculations, not model prose. Expose the method, answer and evidence through the shared runtime and platform. 3. Test invalid mappings, unsupported definitions, denied or changed data, exact arithmetic and complete aggregation with labeled synthetic model proposals. Prepare the exact metadata-only live request and a queued demonstration run. The unused earlier call authorizes only field-interpretation revision; obtain separate explicit authorization for analysis-method generation before sending. 4. Compare the real generated-method answer against the saved independent CSV totals and every product/country group. Record measured provider charges and local timings. S-18 and S-19 own reusable workflow versioning and invocation.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Selected under S-38 after S-16, S-23 and S-29 passed. Only S-17 is active. Use /Users/hudson/Library/Application Support/BackIntel/Validation/S29Recovery-20261014/recovery-result.dump and the independent expected answer in S16MeaningCheck-20261014. No new paid call is authorized for analysis-method generation yet.

Implemented the bounded analysis-method schema, canonical metadata-only request, binding checks, exact signed arithmetic using rational values, complete grouping and tied leaders in runtime/source_answer.py. The shared answer operation and platform result view are wired. Pure calculation/mapping checks passed before final integration; integrated source-permission and platform checks are next. No analysis-method provider call has run. Live method generation still needs separate spending authorization after the concrete request and queued run are prepared. Keep S-17 and S-38 open.

The full answer path passed on 2026-10-15 using an explicitly simulated method over all 541,909 real checked rows. Every one of 4,070 product groups and 38 country groups, all exact totals, and the source period matched S16MeaningCheck-20261014/independent-expected-answer.json. Net invoice value GBP 9747747.934; signed cancellation value GBP -896812.49; value without cancellations GBP 10644560.424. Authenticated platform reads succeeded. Repeated submission reused the accepted result and restored last_success without recalculation or provider calls. Elapsed check time: 25.683 seconds. Pure calculation/binding/revision checks passed; dead-code and diff checks passed; Graphify refreshed and shared answer dispatch/API registrations inspected. The prior 17 platform checks and production build remain valid; no platform code changed since.

Evidence: /Users/hudson/Library/Application Support/BackIntel/Validation/S17Answer-20261015/simulated-answer-evidence.json and simulated-platform-result.json. The database BEFORE any simulated response is answer-ready.dump. method-request.json contains the exact metadata-only request, run 19999718f7a0f3ed8847133d1180f67ae9c54937958e98198a3eef2c0d55d4d4 and request b336ab39be5f0e451cb09893812926cf97e75eceeb728133223c7af34808661b. The simulated-result database is separately named simulated-answer-result.dump. No analysis-method provider call has occurred. Next: obtain separate approval for up to two analysis-method calls, combined cap USD 0.50; restore answer-ready.dump and execute the live request. The one remaining field-interpretation call cannot be used for this different purpose. S-17 stays In Progress and S-38 remains active.

Live analysis-method generation passed on 2026-10-15 after explicit approval for up to two calls, combined USD 0.50. One call consumed USD 0.010344015; no revision was needed. Real-mode answer passed every one of 4,070 product and 38 country group comparisons against the saved independent CSV expectation over all 541,909 rows. Exact totals and historical period matched. Authenticated platform and calculation-evidence reads passed, and repeat submission reused the answer without another charge. Total live method-plus-calculation check: 39.642 seconds. Evidence: /Users/hudson/Library/Application Support/BackIntel/Validation/S17LiveAnswerAttempt2-20261015/live-answer-evidence.json, live-platform-result.json, provider-results.json, and live-answer-result.dump. A prior local harness attempt stopped at receipt-format comparison before provider dispatch; the corrected harness normalized stored decimal charge representation. No runtime correction or extra provider request was needed. One analysis-method revision call remains authorized within USD 0.489655985, but cannot be repurposed. S-18 is next.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
BackIntel generated the analysis method through the live provider, calculated the complete historical retail answer, and exposed evidence-linked findings through the platform. All exact totals, 4,070 product groups, and 38 country groups matched the independent expectation. One call cost USD 0.010344015; repeated invocation reused the accepted result. Full evidence is retained in S17LiveAnswerAttempt2-20261015.
<!-- SECTION:FINAL_SUMMARY:END -->
