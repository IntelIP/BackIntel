---
id: S-38
title: Deliver one checked business-data answer through the toolkit and platform
status: Done
assignee: []
created_date: '2026-10-15 01:15'
updated_date: '2026-10-15 06:27'
labels:
  - goal
  - toolkit
  - platform
  - goal-reference-workflow
dependencies:
  - S-39
references:
  - docs/ROADMAP.md
  - docs/SYSTEM_DESIGN.md
  - docs/roadmap/agile-backlog.md
  - docs/retail-reference-workflow.md
priority: high
type: feature
ordinal: 2035
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
## User story and goal

As a business owner, I want to give BackIntel one business question and scoped PostgreSQL access, so that it can create, check, run, and save the required analysis without asking me to build its importer, cleaning scripts, or batches. Developers and other applications must be able to invoke the same accepted workflow through the toolkit.

This goal groups 15 existing user stories into one delivery outcome. Their original IDs, acceptance criteria, dependencies, and delivery labels remain authoritative. Shared work is implemented once. The completed S-01 baseline is the common prerequisite. This goal record is a completion checkpoint, not a second implementation of S-39; its native dependency on S-39 includes the complete member dependency chain.

## User stories and delivery stages

### 1. Define the result and establish safe access

A business owner supplies the objective and permitted access. BackIntel has an explicit question, a revisable plan, operating limits, recovery behavior, and a checked connection.

| Existing user story | Prerequisites |
| --- | --- |
| [S-12 — Define the business question and operating limits](<s-12 - Define-the-business-question-and-operating-limits.md>) | S-01 |
| [S-04 — Use only permitted information and actions](<s-04 - Use-only-permitted-information-and-actions.md>) | S-01 |
| [S-05 — Control spending and explain charges](<s-05 - Control-spending-and-explain-charges.md>) | S-04 |
| [S-06 — Resume accepted work after interruption](<s-06 - Resume-accepted-work-after-interruption.md>) | S-04, S-05 |
| [S-22 — Configure a scoped connection](<s-22 - Configure-a-scoped-connection.md>) | S-12, S-04, S-05 |

### 2. Build and save the shared workflow

BackIntel collects the complete agreed workload, preserves originals, understands and prepares unfamiliar data, checks its meaning, answers the question, and saves the reusable procedure.

| Existing user story | Prerequisites |
| --- | --- |
| [S-13 — Admit permitted inputs and retain originals](<s-13 - Admit-permitted-inputs-and-retain-originals.md>) | S-12, S-04 |
| [S-23 — Collect complete and traceable information](<s-23 - Collect-complete-and-traceable-information.md>) | S-22, S-13 |
| [S-14 — Understand fields and table relationships](<s-14 - Understand-fields-and-table-relationships.md>) | S-13 |
| [S-15 — Prepare data inside an isolated workspace](<s-15 - Prepare-data-inside-an-isolated-workspace.md>) | S-14, S-05, S-06 |
| [S-16 — Check that preparation preserves meaning](<s-16 - Check-that-preparation-preserves-meaning.md>) | S-15 |
| [S-29 — Complete the workload without manual batching](<s-29 - Complete-the-workload-without-manual-batching.md>) | S-16, S-23 |
| [S-17 — Answer the question from the prepared data](<s-17 - Answer-the-question-from-the-prepared-data.md>) | S-16, S-23, S-29 |
| [S-18 — Save a reusable, versioned workflow](<s-18 - Save-a-reusable-versioned-workflow.md>) | S-17 |

### 3. Demonstrate the toolkit and platform result

A developer can invoke the saved capability, and a business owner can obtain the same checked answer through the platform using a permitted PostgreSQL source.

| Existing user story | Prerequisites |
| --- | --- |
| [S-19 — Invoke the workflow manually or from an application](<s-19 - Invoke-the-workflow-manually-or-from-an-application.md>) | S-18, S-06 |
| [S-39 — Complete the PostgreSQL commerce reference workflow](<s-39 - Complete-the-PostgreSQL-commerce-reference-workflow.md>) | S-19, S-22 |

## First selection and missing inputs

Start with S-12 refinement. Specify the business question; metric definitions, units, target, population and period; permitted PostgreSQL environment and source scope; expected answer and independent check; complete-workload boundary; output destination; freshness, time, resource and spending limits; and conditions requiring the owner's decision. These inputs are not supplied by this planning record and must not be invented. Discover reusable approved access before requesting credentials; keep secret values out of task records.

S-12 refinement is the first bounded deliverable. S-12's runtime acceptance also requires a saved question and an agent-created plan; writing the scenario alone does not complete that story. Select subsequent implementation slices only after their prerequisites and material inputs are satisfied. Keep at most one implementation story active at a time. Labels such as needs-refinement remain start gates.

## Completion boundary

The final demonstration must use an actually permitted PostgreSQL source and cover the entire agreed workload. Fixtures may support local development, but cannot satisfy live-source acceptance. Partial data, denied access, exhausted limits, unresolved uncertainty, and unknown costs remain visible. No live connection or spending permission is established by this plan.

The toolkit's historical alpha recovery and installation chain remains separate; missing historical source does not block independent work on available source. Autonomous method development, continuous updates, coordination among agents, additional business systems, and sustained multi-user scale remain later roadmap outcomes. This first goal retains their future scope without requiring every proposed service now.

## Runnable goal prompt

Complete this BackIntel delivery goal in /Users/hudson/Documents/GitHub/Products/BackIntel by working through its 15 linked user stories, one eligible implementation story at a time. Begin with S-12 refinement, preserve each story's native prerequisites and acceptance, and record researched implementation plans only when selecting the work. Deliver one checked, complete PostgreSQL workflow that the toolkit can invoke and the platform can run from a business objective. Save and rerun the workflow, demonstrate interruption recovery and denied-access handling, and verify the result against an independent expected answer on the permitted live source. Reuse existing code and shared capabilities. Record progress and specific external blockers without substituting fixtures or planning documents for the requested result. Follow AGENTS.md and existing commit, push, spending, credential, data-access, and deployment boundaries. Mark this goal Done only when its member stories and the goal acceptance criteria are satisfied.

## Selected source and authorized scope change

The user requested a Kaggle dataset within BackIntel's illustrated domains, then confirmed that no Databricks workspace is active and requested an open-source alternative. Use the historical UCI Online Retail snapshot distributed as Kaggle carrie1/ecommerce-data in a dedicated local PostgreSQL database, accessed through a scoped read-only identity. S-39 now owns this first connected-source demonstration. [S-26 — complete the Databricks reference workflow](<s-26 - Complete-the-Databricks-reference-workflow.md>) remains a later integration and retains its original acceptance criteria. This goal does not claim that Databricks has been demonstrated. The selected question and operating contract live in S-12.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 The selected scenario records the question, metric definitions and units, target, population, period, complete workload, permitted sources and actions, output destination, expected answer checks, freshness, resource/spending limits, and escalation conditions. The platform saves the objective and an agent-created plan; missing material inputs are resolved or explicitly block dependent work.
- [x] #2 Source permissions, budget controls, and recovery are exercised on the selected path. Denied or expired access and untrusted source instructions cannot expand authority. Exhausted limits or unresolved charges prevent new paid work, with measured usage or explicit unknowns recorded.
- [x] #3 The agent discovers and collects the complete agreed workload, preserves originals and source links, understands unfamiliar fields and relationships, cleans and classifies where required, combines and checks the data, and produces a checkable answer. Coverage reconciles collected, processed, excluded, failed, and pending records; the user supplies no bespoke importer, preparation script, or manual batches.
- [x] #4 The accepted workflow is saved with a versioned input/output contract and can run in a new permitted context. Toolkit/manual application invocation and the platform produce equivalent checked results with run identity and supporting evidence. Saved artifacts contain secret references rather than secret values.
- [x] #5 An interrupted run resumes retained progress. Repeated invocation cannot duplicate accepted results or charges, and an uncertain paid operation is reconciled or visibly blocked before repetition. Insufficient access and a material data-quality failure have clear outcomes.
- [x] #6 The integrated demonstration runs against an actually permitted PostgreSQL source and matches an independent expected answer for the selected scenario. Record observed time, resources, known costs, coverage, and remaining human intervention. Fixtures and historical demonstrations are labeled and cannot close this live-source criterion. The source connection is local PostgreSQL over real historical Kaggle data; it is not current business activity or a Databricks integration.
- [x] #7 All 15 linked stories meet their own current acceptance criteria, and their evidence and dispositions are recorded in the authoritative task files. S-39 and this goal remain open while required live access, inputs, checks, or implementation are missing. No merge, release, deployment, or business-value claim is implied by planning or local tests.
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Progress checkpoint 2026-10-15: S-17 and S-18 now meet their acceptance criteria. Live generated analysis over all 541,909 rows matched every independent product/country group and exact total; the analysis-method call cost USD 0.010344015. The accepted real workflow was saved, exported, and loaded in a fresh permitted process, with original-source links, secret references, immutable versions, explicit dependency failures and denied-access behavior checked. Continue from /Users/hudson/Library/Application Support/BackIntel/Validation/S18Workflow-20261015/workflow-ready.dump and workflow-package.json. Detailed evidence and dispositions are in the member task files. S-19 invocation, S-39 integrated connected-source demonstration, and this goal's final acceptance remain unfinished. S-38 is not complete; no commit, push or deployment occurred.

Final goal acceptance review: (1) S-12 saved objective, limits and two real plan creation/revision responses. (2) S-04/S-05/S-06 verified source authority, expiry, untrusted instructions, caps, uncertain charges and durable recovery; four completed live requests total USD 0.063327825. (3) S-13/S-22/S-23/S-14/S-15/S-16/S-29/S-17 and S-39 collected and checked every row, retained original links and exact meanings, and reconciled the full answer without manual batches. (4) S-18/S-19 saved immutable contracts, secret references and dependency guidance; S-39 ran the same version with a fresh collection through toolkit/API/browser. (5) S-19 real interruption at 2,000 rows resumed the remaining 539,909; duplicate and revoked-access checks passed; S-05/S-06 retained uncertain-charge protections and S-16 retained material-quality-failure outcomes. (6) S-39 real dedicated PostgreSQL source and independent full answer passed; measured timings/storage, configured limits and explicit unknown utilization/cost are documented. (7) All 15 member stories are Done with checked criteria; latest CLI readback is member-acceptance-review.json. See docs/retail-reference-workflow.md. Remaining roadmap work and human setup are explicit; no deployment or broad autonomous-platform completion is claimed.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Delivered one checked business-data answer through the shared toolkit and local platform. A saved business objective led to a real agent-created plan, field interpretation and calculation method; the complete PostgreSQL workload was collected, checked, answered, saved, rerun and recovered after interruption. All 15 member stories and seven goal criteria are satisfied with source, calculation, recovery, browser and accounting evidence in docs/retail-reference-workflow.md. Total model cost USD 0.063327825. This is a historical local reference workflow; continuous operation, wider systems and multi-agent scale remain future work. Changes remain uncommitted and no deployment was performed.
<!-- SECTION:FINAL_SUMMARY:END -->
