---
id: S-33
title: Coordinate specialist agents around one objective
status: Done
assignee:
  - '@codex'
created_date: '2026-10-14 22:59'
updated_date: '2026-10-17 00:20'
labels:
  - platform
  - post-reference
milestone: m-5
dependencies:
  - S-19
  - S-32
  - S-04
  - S-05
  - S-06
references:
  - docs/retail-reference-workflow.md
  - docs/roadmap/agile-backlog.md
documentation:
  - docs/ROADMAP.md
  - docs/roadmap/README.md
  - docs/roadmap/agile-backlog.md#shared-delivery-contract
priority: medium
type: task
ordinal: 21
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Original roadmap story: S33. Original priority: P1. Work type: implementation.

## Business outcome

As a workflow owner, I need specialists to coordinate discovery, preparation, analysis, and checking, so I do not manage their handoffs or reconcile conflicting results myself.

## Scope

Add a coordinator with a shared plan, versioned inputs, explicit responsibilities, dependencies, job ownership, evidence, and budget accounting. Invoke specialists when useful; resolve conflicting findings or escalate material uncertainty. Keep retries and concurrent external actions within existing authority.

## Owned surface

Coordination and specialist interfaces over the durable workflow. Agent count, framework, and process topology follow the selected workload rather than being fixed by this story.

## Prerequisites

S-19, S-32, S-04, S-05, S-06.

## Next staged delivery

Introduce actual specialist agents only for a bounded workflow where their distinct responsibilities are useful. The user supplies one objective; the product manages discovery, preparation, analysis, checking, and handoffs over shared controls.

## Decisions before selection

Select the objective, useful specialist responsibilities, shared input versions, conflict-resolution policy, and total operating limits. Agent count and implementation framework remain execution-time choices.

These refinements record future work. Hudson selects one implementation story at a time; no implementation, model spending, live scheduling, commit, publication, or deployment is authorized by this planning update.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Multiple actual agents complete one bounded workflow with a checkable combined result. Show an interrupted specialist, a rejected finding, and duplicate work without losing accepted progress or repeating an uncertain charge. An agent cannot expand another agent's permissions. Role labels or simulated responses alone do not establish a coordinated-agent implementation.
- [x] #2 The owner can inspect a shared plan showing each actual specialist contribution, its input version, progress, accepted or rejected finding, and share of the total usage. The combined answer passes the selected independent check.
- [x] #3 A disagreement identifies the conflicting evidence and is resolved by the agreed checking policy or surfaced as a specific unresolved question. It cannot silently become an accepted fact, and another specialist cannot bypass the original authority or budget.
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Use the saved complete-period retail objective, its permitted PostgreSQL connection, and existing exact invoice-value checks. Three actual specialists own source interpretation/preparation, calculation-method selection, and independent finding review; the platform owns their shared plan and handoffs.
2. Reuse the current durable job and request ledger. Pin goal/source/input versions, persist each specialist contribution and request identity, and enforce one shared run limit of six provider calls and an explicit spending cap. Read-only tools cannot change another specialist's authority. An unresolved charge blocks retries.
3. Automatically collect, interpret, prepare, validate, calculate, and independently check the complete permitted dataset. Conflicting findings must fail the deterministic source/coverage/amount checks or remain an explicit review question; preserve the last accepted answer.
4. Expose one start action and an inspectable shared plan through the application, API, and toolkit entrypoint, including input versions, per-specialist progress, accepted/rejected findings, evidence, and measured/reserved usage.
5. Run focused offline contract/recovery checks, web checks/build, the required dead-code and Graphify checks. Prepare the actual request data and budget before asking for any new paid inference allowance. Demonstrate a live multi-agent answer and fault-injected interruption, rejected finding, duplicate request, and denied permission without losing progress or repeating charges.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Selected after S-40 commit 106b7eb under the user's execution goal. Reuse the existing retail question and definitions, including cancellations, full workload, and source precision. Disagreements resolve only through the agreed exact checks; unresolved business meaning requires review. Model/provider identity remains the existing configured account. No new paid calls are authorized yet; six-call scope and request contents will be prepared before requesting a bounded allowance. No new framework, deployment, external tracker, or permanent schedule is part of this story.

S-33 continuation: added scripts/validation/workflow_coordination_cases.py and --coordination fixture|live to run_workflow_triggers.py. Intended local demonstration covers all 541909 records, independent checking, API progress, and duplicate reuse with clearly simulated model decisions. It has NOT passed yet: S33Fixture-20261016A failed native startup because repository .venv lacks aegra_api. The retained Sprint2 .venv is also unusable (aegra_api, psycopg, and httpx missing); attempt B must not be treated as validation. Evidence lives under the private BackIntel/Validation directory. Sessions 3771 and 73923 were still finishing setup/cleanup at handoff. Recover the existing working interpreter from the earlier S24 validation invocation before retrying. Earlier backend/web/build checks remain the verified results. No S-33 provider calls, spending, commit, push, or deployment. Remaining: full-data fixture run; complete-workflow interruption/rejection/source-permission checks; rendered browser check; prepare and obtain a new allowance for six real specialist calls capped at USD0.50; final documentation and acceptance. Keep In Progress. Local approved S-40 commit remains 106b7ebd4dd58388ef94467bb7f07322e567c680.

S-33 runtime follow-up: created a working Python 3.12 test environment from requirements.testing.txt at the private Validation/S33Runtime path. Confirmed and removed the orphan from failed attempt A; attempts C and D cleaned up their disposable database/server. Fixed toolkit identity handling to authenticate BACKINTEL_ACCESS_TOKEN. The real worker uses a separate process, so simulated decisions and interruptions now run inside that worker. Integration D reached the intended interruption but exposed immutable save_step preventing progress transitions; specialist state now uses a scoped update while source/stage evidence stays immutable. All 21 focused backend checks passed including the sandbox; the five coordination checks passed again after the progress fix. E is the current full-data fixture attempt, with actual-source reconciliation, recovery, duplicate reuse, toolkit/API/browser views, intentional wrong-total rejection, revoked-source access, and simulated uncertain-charge retry blocking. No live model calls or new Git publication. Six live calls capped at USD0.50 remain separately unapproved.

Integration E confirmed accepted data progress survives the injected interruption, then found an independent-check adapter mismatch: retained_input returns a payload wrapper and parse_response returns an envelope/hash pair. Fixed the checker to use that real interface; its focused test now exercises the actual parser instead of mocking it. All five coordination checks pass after this change. Full fixture attempt F is running (session 97947; private Validation/S33Fixture-20261016F). The current Python runtime is Validation/S33Runtime/bin/python with BACKINTEL_PREPARATION_IMAGE=sha256:46d93453a2a426ca456854ee8ba188202b547015674515b04ec742067eb484bf. Dead-code check, Graphify update, and diff whitespace check passed for the corrected code. E cleaned up its database and server. No S-33 paid requests have been made. Obtain a separate six-call, USD0.50 maximum allowance only after the full local demonstration passes.

S-33 live attempt S33Live-20261016 stopped at the semantic-unit guard before producing an accepted answer. Both provider requests are complete, with measured charges USD 0.003179385 and 0.02246409 (total 0.025643475); no uncertain charge remains in this attempt. The data specialist proposed GBP per source quantity unit, while supported units must quote the saved objective. Reused the existing interpretation rules in the data specialist and restricted checking instructions to the checking specialist; validation and business definitions remain unchanged. Five coordination checks passed; the 15 database-dependent source checks in that invocation were skipped, not claimed as passes. Dead-code and Graphify updates passed. The corrected harness restores the failed archive without resaving an answer from an older goal version, preserves earlier request accounting, and accepts a per-run spending cap. S33RecoveryFixture-20261016 (session 15068) is checking the full original dataset after accepting data and analysis contributions, with no new provider calls. The proposed next live attempt would make six new requests, bringing S-33 to eight total, with a new-run cap of USD 0.47 and combined spending below USD 0.50. Two additional requests beyond the original allowance require approval; none have been sent. The prepared private wrapper S33Retry-20261016.py refuses an existing output directory. Keep S-33 In Progress and all live acceptance criteria unchecked.

Corrected recovery completed successfully: S33RecoveryFixture-20261016/summary.json reports passed over all 541909 historical rows, with all three simulated contributions accepted, interruption/response reuse, duplicate reuse, independent reconciliation, toolkit/API/browser agreement, deliberately incorrect finding rejected, revoked-source denial, and simulated uncertain-charge retry blocking. Original provider accounting was preserved; zero new model calls. Disposable database and native server were stopped. The five focused coordination tests, dead-code check, Graphify update, and whitespace check passed; 15 separately invoked database-dependent tests were skipped and are not counted as passes. Documentation and private S33Retry-20261016.py are ready. Awaiting the explicit request for two additional calls (eight total) while retaining the USD0.50 overall limit; the prepared new attempt is capped at USD0.47 and restores S33Live-20261016/runtime-result.dump. No new commit, push, deployment, or live retry. S-33 remains In Progress, with actual-agent acceptance incomplete.

Hudson approved two additional S-33 requests, raising the total allowance to eight requests while retaining USD0.50 overall. The corrected full-data recovery check has passed. Started the prepared S33Retry-20261016.py wrapper (session 46657), restoring S33Live-20261016/runtime-result.dump into a disposable environment and writing the new attempt to S33Live-20261016B. This attempt permits six requests, two per specialist, capped at USD0.47; the prior two completed requests cost USD0.025643475 and remain retained. Only the objective, field meanings, aggregate profiles, and check results may be sent. No raw rows or identifier values. Do not restart this paid attempt if observation times out. Inspect the existing session and retained ledger. No commit, push, deployment, or permanent schedule is authorized. S-33 acceptance remains pending the actual live result.

S-33 completed on 2026-10-16. S33Live-20261016B/summary.json reports a passed live demonstration with three actual accepted specialists, two provider requests each, over all 541909 historical retail records with zero excluded, failed, or pending rows. Independent exact checks matched net invoice value GBP9747747.934, signed cancellations GBP-896812.49, every product/country group, and the recorded period. The analysis specialist resumed its retained response after an injected interruption without repeating a charge or losing the accepted data contribution; duplicate invocation reused the same run. Toolkit, authenticated API, and desktop/mobile browser agreed on accepted contributions, input/evidence versions, and measured costs. A separately simulated incorrect-total scenario produced an explicit net_invoice_value conflict and preserved the last accepted answer in the real browser. Revoked source permission was denied, and a simulated unresolved charge blocked retry. Earlier provider accounting remained intact. Six new requests cost USD0.041770575; the earlier rejected two-request attempt cost USD0.025643475. Combined-allowance.json confirms eight total requests costing USD0.067414050, within the approved USD0.50 overall limit and USD0.47 new-run cap. No raw records or identifier values were sent. The final runtime archive was retained; disposable database and native server were removed. Five focused coordination tests, prior 23 web tests and production build for unchanged UI code, required dead-code and Graphify checks, and final whitespace check passed. The earlier invocation with 15 database-dependent tests skipped is not counted as 15 passes. docs/saved-workflows.md and docs/retail-reference-workflow.md contain usage, results, exact costs, and limitations. S-40 commit 106b7ebd4dd58388ef94467bb7f07322e567c680 remains HEAD. S-33 implementation and completion metadata remain uncommitted; no new push, deployment, permanent schedule, or broader system/scale claim.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Three live specialists now complete the saved retail workflow through one shared job, with visible contributions, retained progress, independent checks, and controlled spending. Verified all 541909 rows, interruption and duplicate reuse, rejected findings without replacing the accepted answer, denied permissions, and blocked uncertain-charge retries through local toolkit/API/browser checks. Actual successful inference used six requests; eight including the earlier rejected attempt cost USD0.067414050 total. Evidence: S33Live-20261016B/summary.json, combined-allowance.json, shared-progress.json, checked-answer.json, rejected-progress.json, browser receipts, and runtime-result.dump. Demonstrated locally on historical PostgreSQL data; production scale, additional business systems, and deployment remain outside this result.
<!-- SECTION:FINAL_SUMMARY:END -->
