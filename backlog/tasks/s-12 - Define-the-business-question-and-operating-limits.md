---
id: S-12
title: Define the business question and operating limits
status: Done
assignee:
  - '@codex'
created_date: '2026-10-14 22:59'
updated_date: '2026-10-15 06:21'
labels:
  - platform
  - goal-reference-workflow
milestone: m-1
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
type: spike
ordinal: 4
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Original roadmap story: S12. Original priority: P0. Work type: research and implementation.

## Business outcome

As a business owner, I need to state the result, business measures, targets, and permitted systems, so BackIntel can plan the work without requiring me to design its pipeline.

## Scope

Refine the selected PostgreSQL commerce reference scenario: question, metric definitions, population, period, target, source scope, allowed actions and destinations, whole-workload boundary, expected checks, freshness, resources, and spending. Record unknown inputs honestly. Then implement objective capture and a revisable plan in the selected task; ask only about ambiguity that materially changes the result or authority.

## Owned surface

First reference-scenario contract and the goal/planning interface. Refinement is the next small deliverable; runtime implementation remains a separate selected task. No live connection is created by this plan.

## Prerequisites

S-01.

## Selected reference scenario

The user asked for a Kaggle dataset within the existing domains, then requested an open-source data-connection alternative because no Databricks workspace is available. Use the commerce domain with Kaggle carrie1/ecommerce-data (UCI Online Retail) and a separately named local PostgreSQL source. S-39 owns the connected PostgreSQL demonstration; S-26 remains the later Databricks integration.

Business question: Which products and countries contributed most to net invoice value over the complete recorded period, and how much did cancellations reduce it?

- Metric: exact sum of Quantity multiplied by UnitPrice, in GBP, grouped separately by StockCode and Country. Preserve source decimal precision for reconciliation; round only the displayed currency. This is reported invoice-line value, not audited revenue or profit.
- Cancellations: InvoiceNo beginning with C, case-insensitively, following the original source definition. Report signed cancellation value separately; do not relabel every negative quantity as a confirmed customer return.
- Population and period: every row in the pinned file, December 1, 2010 through December 9, 2011. Dates are local source wall-clock values with unknown timezone. The closing month is partial. No current-business or prospective prediction claim is allowed.
- Target: establish a descriptive baseline, reconcile all records and totals, and identify the highest contributing groups with ties retained. No owner growth target or alert threshold has been supplied; do not invent one.
- Quality rules: preserve original rows and source-row identity, including missing CustomerID or Description. Flag negative prices, zero prices, and duplicate-looking lines; do not silently deduplicate or exclude them. Report coverage and the effect of any explicitly justified alternative treatment.
- Access and output: local public dataset files and the dedicated demo PostgreSQL database only. The workflow uses a scoped read-only source identity. Bootstrap/loading runs as the separate demo owner. Output goes to local BackIntel evidence/report storage; no publication or notification is authorized.
- Freshness: the pinned historical snapshot is immutable. Identify its source period and hash in every accepted result. Continuous ingestion is later work.
- Operating limits: retain existing runtime request/run/concurrency caps. No new paid model calls are authorized by this refinement; use local/offline checks until a concrete paid run is approved. Do not create cloud infrastructure. Measure actual local time/resources; unknown cost stays unknown.
- Expected answer check: independently calculate exact totals and grouped results from the unchanged CSV, then reconcile the connected PostgreSQL workflow against that expectation. The research profile is an input check, not proof that BackIntel has executed the workflow.
- Material escalation: ambiguous metric interpretation, inaccessible source, changed data hash, unexplained exclusion, conflicting totals, unauthorized access, or unavailable approved model/spending must remain visible and block dependent acceptance.

## Dataset evidence

Kaggle: https://www.kaggle.com/datasets/carrie1/ecommerce-data
Original provider: https://archive.ics.uci.edu/dataset/352/online+retail
Citation: Chen, D. (2015). Online Retail. UCI Machine Learning Repository. DOI 10.24432/C5BW33.

The original provider grants CC BY 4.0; the Kaggle card lists its license as Unknown. Retain attribution and the original-provider license source. Kaggle's archive was downloaded successfully without authentication. The unchanged CSV and source-manifest.json are outside Git under /Users/hudson/Library/Application Support/BackIntel/Datasets/Commerce/OnlineRetail.

CSV SHA-256: d07aec9960083af2339975a3f9d3b26313b342dcd9f86cce0b919b1cde639a44.
Observed: 541909 rows, 8 columns, 38 countries; 135080 missing CustomerID values and 1454 missing Description values. There are 9288 C-prefixed cancellation lines, 10624 negative-quantity lines, 2515 zero-price lines, and 2 negative-price lines. The original provider's no-missing-values metadata conflicts with the downloaded file; actual file observations govern preparation.
The independent preliminary exact total is GBP 9747747.934; C-prefixed cancellation lines sum to GBP -896812.49. These figures describe the pinned source file, not a completed autonomous run.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 For refinement, produce a bounded scenario and identify the first eligible implementation story with its prerequisites. For the runtime, show the saved question and an agent-created plan. The user supplies the objective and access, not an importer, transformations, or a list of analytical tool calls. Ambiguous units, identities, or target definitions are resolved or visibly held open.
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Use the selected public commerce snapshot and PostgreSQL reference source to finish the scenario contract; preserve unknown business thresholds and existing spending authority.
2. Extend the existing saved-goal API, goal versioning, and goal screen to capture the business objective, metric, population/period, source scope, limits, and open questions. Preserve current goals and their contracts.
3. Replace the definitions-only proposal for this path with a persisted, revisable agent-generated plan using the existing provider and accounting boundaries. Research the admission/charge path before wiring the planner; no model call is authorized merely by saving a goal.
4. Verify objective/plan persistence, revisions, invalid or ambiguous inputs, and access/budget failures with focused checks. Label simulated provider responses explicitly.
5. Obtain any missing concrete live-model authorization only after the executable candidate and request limits are ready. Do not mark S-12 Done on the scenario document alone. Once S-12 acceptance is met, select S-04 and then follow native dependencies toward S-39.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Delivery planning — toolkit and platform

Refine one business question that both delivery surfaces can support. Record the shared execution inputs and expected checked result, then the business-owner experience the platform must deliver. Keep source access, metric definitions, full-workload scope, freshness, resource/spending limits, and live-versus-fixture evidence explicit. Unknown values remain open; identify the first eligible implementation story after refinement. See docs/roadmap/README.md#toolkit-and-platform-delivery. This is planning guidance; runtime implementation is not started.

S-38 execution started. S-01 is Done; S-12 is the single active member, assigned to @codex. The user selected Kaggle data and authorized an open-source connection alternative. Dataset download/profile and source research are complete. Current source confirms create_goal saves fixed configured definitions and analysis_graphs.resolve returns them without generating a plan; runtime implementation remains required. No application code, live model call, commit, or push has occurred in this execution turn.

S-12 implementation progress: saved connected-source objectives now include metric, population, period, target, read scope, checks, freshness, resource limits, and unresolved questions. New goals default to zero model spending. Planning uses the existing persisted job and provider-accounting path, with manager authorization, version/cancellation checks, cache/replay protection, and no source tools. Goal revisions hide obsolete proposals. The platform form displays and edits objectives and labels simulated plans. Python 3.12 checks passed against a disposable PostgreSQL database, including saved plan readback, same-request replay, revision invalidation, and access/spending denials; 11 other database tests were skipped by their existing environment gates. All 15 frontend tests and the frontend build passed. The graph index was updated. No paid call or connected retail-data analysis has run. Acceptance remains unchecked pending a real agent-created plan; S-38 and S-39 remain incomplete. The old local Python 3.11 environment cannot install the pinned Aegra runtime; use the installed Python 3.12 interpreter through uv with requirements.testing.txt. Next: prepare and request approval for a bounded live planning run, then finish this story before selecting the next dependency.

Hudson explicitly approved up to two live planning calls through the existing BackIntel OpenRouter account, capped at US$0.50 total, on 2026-10-14. Scope is the saved retail objective and operating limits only; no raw retail records. This supersedes the earlier offline-only boundary solely for this bounded planning demonstration. The reproducible entrypoint is scripts/validation/run_objective_planning.py; its default check-only mode passed with zero provider requests and retained a PostgreSQL archive plus receipt outside Git. Live execution is now in progress; do not infer approval for further paid workflow calls.

Added business-objective capture and persisted agent planning. Two authorized live calls created and revised the retail plan; both are saved and read back through the platform API. Total provider-reported cost: USD 0.03186612 within the approved USD 0.50; repeated submissions reused run identities. Evidence and database archive: /Users/hudson/Library/Application Support/BackIntel/Validation/S12PlanningLive-20261014/. Recorded duration: 99.032 seconds including database setup; local compute cost is unmeasured. The plan preserves every row, uses exact decimals, explains cancellations, and retains unresolved source/provenance/timezone meanings. Python 3.12/PostgreSQL checks passed (11 other gated checks skipped), all 15 frontend tests passed, and the frontend build passed. No source-data execution or whole-goal completion is claimed.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Added business-objective capture and persisted agent planning. Two authorized live calls created and revised the retail plan; both are saved and read back through the platform API. Total provider-reported cost: USD 0.03186612 within the approved USD 0.50; repeated submissions reused run identities. Evidence and database archive: /Users/hudson/Library/Application Support/BackIntel/Validation/S12PlanningLive-20261014/. Recorded duration: 99.032 seconds including database setup; local compute cost is unmeasured. The plan preserves every row, uses exact decimals, explains cancellations, and retains unresolved source/provenance/timezone meanings. Python 3.12/PostgreSQL checks passed (11 other gated checks skipped), all 15 frontend tests passed, and the frontend build passed. No source-data execution or whole-goal completion is claimed.
<!-- SECTION:FINAL_SUMMARY:END -->
