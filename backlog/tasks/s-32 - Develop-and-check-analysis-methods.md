---
id: S-32
title: Develop and check analysis methods
status: Done
assignee:
  - '@codex'
created_date: '2026-10-14 22:59'
updated_date: '2026-10-16 03:03'
labels:
  - toolkit
  - platform
  - shared-core
  - post-reference
milestone: m-3
dependencies:
  - S-18
  - S-05
  - S-15
  - S-16
references:
  - docs/retail-reference-workflow.md
  - docs/roadmap/agile-backlog.md
documentation:
  - docs/ROADMAP.md
  - docs/roadmap/README.md
  - docs/roadmap/agile-backlog.md#shared-delivery-contract
priority: medium
type: task
ordinal: 16
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Original roadmap story: S32. Original priority: P1. Work type: implementation.

## Business outcome

As a business owner, I need BackIntel to develop an appropriate analytical approach, so a useful new question does not require a separate data-science coding project.

## Scope

Let the agent propose hypotheses, calculations, features, classifications, and prediction candidates. Generate bounded code when needed, run it in the permitted isolated workspace, check it independently, and compare with a simple baseline. Preserve evaluation data and prevent future outcomes or iterative test-set tuning from contaminating comparisons. Retain code, inputs, checks, and method versions.

## Owned surface

Planning, generated analysis code, independent checking, method comparison, and retained method versions. The selected task bounds search effort and cost.

## Prerequisites

S-18, S-05, S-15, S-16 and an agreed method-acceptance policy.

## Next staged delivery

First proposed product story after the PostgreSQL reference workflow. BackIntel has answered one question using an accepted calculation; this story establishes development of a new method when the existing fixed tools cannot answer the selected question. The reusable method and its evidence must serve both the toolkit and platform.

## Selected evaluation policy

Hudson selected and confirmed a forecast of four complete weeks of total net invoice value in GBP across all countries, including signed cancellations, from the retained historical retail source. All rows must reconcile; partial boundary weeks are excluded from forecasting and remain accounted for. The source timezone is unknown.

The baseline repeats the latest four complete weeks. Generate two executable candidates in one model request. Use 44 earlier weeks for development, four separate weeks for validation, and the final four complete weeks for one reserved evaluation. Select by mean absolute weekly error, requiring a strict improvement over the baseline; ties retain it. Freeze selection before final evaluation, and do not use final outcomes for tuning or reselection. Report point forecasts, observed error, and uncertainty without claiming calibrated intervals or operational reliability.

Hudson approved one live OpenRouter request capped at USD 0.25 after reviewing its concrete scope. Only the policy and earlier weekly totals, dates, and row counts go to the model. Existing per-request, objective, domain, suite, isolated-execution, and job time limits also apply. Human approval for predictor promotion remains required. Commit, push, publication, deployment, and further development stories are separate selections.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 For a selected question that the fixed tool catalog cannot answer, the agent develops and tests a method without a user-written analysis script. Demonstrate a checkable result, a rejected or unhelpful candidate, uncertainty, and a retained baseline when appropriate. Method selection follows the agreed policy; current human approval for predictor promotion remains unless explicitly changed. Neither accuracy gains nor causation are assumed.
- [x] #2 The selected question and method-acceptance policy are saved before the search starts, including target and units, relevant population and period, baseline, candidate limits, spending limits, and who may promote a predictor. Missing material choices visibly prevent dependent work.
- [x] #3 Baseline and candidate methods are compared on the same agreed measures and protected evaluation data. For a time-based prediction, later outcomes are unavailable during fitting; candidate tuning is separate from the final evaluation. The result reports uncertainty, measured execution time, and known cost without assuming an improvement.
- [x] #4 The agent creates the required candidate method rather than only selecting an existing fixed tool. Each accepted or rejected candidate retains its code or executable definition, inputs, checks, version, result, and reason. An unhelpful candidate is rejected and the baseline remains available when no candidate meets the agreed policy.
- [x] #5 The accepted method can be saved and invoked through the shared toolkit and platform with equivalent outputs and supporting evidence, while preserving access, spending, isolated-execution, and recovery controls.
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Save the approved all-country GBP four-week forecast policy, including cancellations, last-four-weeks baseline, protected chronological evaluation, candidate limits, and unchanged human promotion authority. Keep paid-call allowance at zero until a concrete request is approved.
2. Reuse retained meaning-checked source pages to build an exact weekly series, reconcile all rows and amounts, and identify incomplete boundary weeks. Persist training, validation, and final-test boundaries before candidate generation.
3. Add one bounded method-study operation to existing durable jobs and provider accounting. Have the live agent generate two Python forecast candidates; run their code only through the existing isolated, network-disabled runner. Freeze selection on validation error before evaluating the reserved final four weeks once.
4. Retain candidate code, input and policy hashes, execution receipts, comparisons, rejection reasons, uncertainty, and spending. Preserve interrupted progress, deduplicate repeated requests, and block uncertain charges or invalid authority.
5. Extend the saved-workflow path and authenticated API/platform controls to inspect, save, and invoke the selected evaluation workflow without another model request. Do not promote a predictor without explicit approval.
6. Run focused checks for exact aggregation, chronological separation, unsuitable candidates, safe execution, replay/recovery, denied access, accounting, and toolkit/platform equivalence. Then run the full historical-data demonstration and real browser flow.
7. Record observed results, known costs, remaining uncertainty, and all five acceptance dispositions. Complete S-32 only when the live method-development and saved invocation requirements pass.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Execution selected by Hudson through the active goal. Refining a four-week net-invoice-value forecast and comparing a genuinely generated method with a baseline. Evaluation-policy confirmation requested; paid method calls require a separately prepared request and approval. Existing uncommitted S-38/S-39 work is preserved. No commit or push is part of this goal.

Hudson confirmed the forecast scope: four complete weeks of total GBP net invoice value across all countries including cancellations; repeat the latest four weeks as baseline; choose by average weekly error using earlier data; reserve the final four complete weeks for one unseen check. Predictor promotion still requires approval. Owned surfaces: runtime/source_methods.py, existing sandbox/provider/job/workflow/API integration, platform method-study controls, focused checks, and S-32 documentation. Existing code handles fixed connected-data sums and registered predictors; no connected chronological generated-method search was found.

Implemented the shared forecast study and app comparison panel. The confirmed policy fixes two generated candidates, one model request, earlier-week selection, a protected final period, and human promotion authority. Offline unit checks and the web build pass. Full retained-data integration is in progress; no S-32 paid request has run.

Acceptance evidence, October 15, 2026:

1. The live model generated two Python methods. Both executed successfully in the network-disabled sandbox with confirmed cleanup. Validation mean absolute weekly errors were GBP 36,070.565232536195 and GBP 36,816.59889471501, versus baseline GBP 28,591.565. Both candidates were rejected; the baseline was retained. This demonstrates method development and rejection, not an accuracy gain or causation.
2. The retained run and method contract save the confirmed question, GBP target, population, partial-week handling, 44/4/4 chronological periods, two-candidate/one-call limits, USD 0.25 allowance, and human promotion requirement before generation. Zero allowance was refused and the app disables starting without a positive allowance.
3. Only the 44 development weeks were sent to the model and candidate execution. Selection was saved before the final four weeks were evaluated. The retained baseline's final mean absolute weekly error was GBP 89,655.475. Completed study stages took 89.147 seconds. One live call cost USD 0.03369069; local compute cost remains unavailable. No calibrated interval or future reliability is claimed.
4. Both candidates retain their exact code, hashes, history hashes, isolated-execution receipts, predictions, errors, reasons, and method-study version. Repeated study admission on the same protected source evaluation and a second provider call were refused. Final outcomes caused no tuning or additional model requests.
5. The selected version was saved and invoked through the toolkit, authenticated API, and real browser. Browser save/run values matched the toolkit; invocation used zero additional model calls. Source revocation denied result access. A simulated proposal check resumed after interruption following fixed selection. The live retained run also recovered from a pre-dispatch admission failure; that failed attempt sent no inference request, and total S-32 live inference remained one call.

Authoritative evidence: /Users/hudson/Library/Application Support/BackIntel/Validation/S32Live-20261015/{study-result.json,workflow-package.json,forecast-result.json,browser-result.json,forecast-platform.png,runtime-result.dump,validation.py,browser-check.js}. Study 08f463288faa6444548a191203fd4fcc933f03178dc4e23d475fcd800c792e4c. Saved workflow 07869f4fa1ef975523b06e23750c9441106067d1c7bb7b4ff7f0de87f267cfd8.

Focused checks: eight source-method/workflow/answer unit checks; nineteen web checks; production web build; changed-runtime Python syntax; dead-code check. Graphify was updated and the shared method dependencies inspected. The actual browser check, rather than the build alone, established save/run equivalence. Existing uncommitted work remains preserved. No predictor promotion, commit, push, deployment, or later story was performed.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
BackIntel can develop and check forecasting methods for the confirmed retail question, retain the simpler method when generated candidates lose, and save the selection for toolkit and platform reuse. The live study rejected both generated candidates on validation error and retained repeating the latest four weeks. Its final average weekly error was GBP 89,655.475; one model call cost USD 0.03369069. Real browser save/run results matched the toolkit with zero further inference. The report and saved-workflow guidance record exact evidence, protected periods, recovery, and known limitations. This is a bounded local historical demonstration. Predictors remain unpromoted, and operational reliability on other questions is unestablished.
<!-- SECTION:FINAL_SUMMARY:END -->
