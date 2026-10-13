# BackIntel product roadmap and delivery plan

Updated October 12, 2026. This is the maintained roadmap entry point. It brings together the repository plans and decisions from other BackIntel chats. It does not certify a release or start implementation work.

Use the [ordered user-story backlog](agile-backlog.md) for the step-by-step delivery plan: seven proposed increments, individual tasks and acceptance checks, and explicit dependencies. Increment scope becomes a sprint commitment only after owners and capacity are assigned.

The [current sprint](current-sprint.md) is Sprint 4, now Done for its approved local app scope. A reviewer can select a support-ticket CSV, run a fresh calculation, inspect the supporting tickets, and save a checked report from the current app. The [Sprint 4 review](sprint-4-review.md) records setup, browser results, and limits. The [Sprint 3 review](sprint-3-review.md) records the preceding local calculation, and the [Sprint 2 review](sprint-2-review.md) preserves the recorded demo setup checks. The separate toolkit recovery and installation stories, S02/S03, remain unfinished.

The [Sprint 1 review](sprint-1-review.md) records the verified browser demo and saved-review restart. Hudson accepted the result and continuation on October 10. Source discovery is complete; alpha recovery is blocked on retrieving the reported cloud ZIP.

## Product outcome

BackIntel should help a person or an agent complete a business task using permitted information. It should collect and prepare the information, check the work, explain the result with evidence, and save a workflow that can run again after the information changes.

Analysis, hypothesis testing, and prediction comparisons are parts of this product. A useful result can be a finding that a simple method remains preferable, that the information cannot answer the question, or that more information is needed. Users should eventually be able to supply unfamiliar data without commissioning a new importer for every dataset.

The first external audience is developers adding analytical tools to agents. The initial toolkit should make two bounded workflows easy to install, run, inspect, and resume. Broader autonomous data work follows that foundation.

## Current position

| Area | Status | What the evidence supports |
| --- | --- | --- |
| Published demonstration | Confirmed | [PR #2](https://github.com/IntelIP/BackIntel/pull/2) merged the consolidated demo source into `main` at `c6de6ae`. Reviewers can inspect saved findings and record decisions. The recorded demo uses synthetic data and historical results. |
| Supplied app demo installation | Confirmed | [Sprint 2](sprint-2-review.md) restored source `f5e2b6` from the supplied ZIP and opened its recorded demo in a fresh Python environment. The missing-file setup remedy worked. This is the older saved app, not toolkit qualification or new analysis. |
| Fresh support check in the current app | Confirmed locally | [Sprint 4](sprint-4-review.md) runs uploaded closed-ticket records through local statistics, shows evidence, and saves a checked report. Fictional changed-input browser checks passed. This is not AI reasoning or toolkit qualification. |
| Known-dataset analysis workspace | Confirmed implementation; limited historical evaluation | Saved questions, permitted sources, prepared snapshots, evidence, follow-ups, corrections, predictor comparisons, durable jobs, and recovery exist. Four domains ran actual local predictors in the October 6 campaign. These results retain their original source revision and scope. |
| Agent toolkit alpha | Blocked source access; candidate contents unverified | The chat reports a `0.1.0a2` candidate at commit `f0a3d2573fb3da9469d81e35691f60a42a0d9a1b`. Its cloud ZIP is not accessible in this local chat; GitHub could not resolve the exact commit or branch on October 10. Retrieve the bundle before reconciliation or installation. |
| Full five-domain live acceptance | Blocked | Credit inputs and five live analyst cases remained blocked in the consolidated campaign. Publishing the demo did not complete this acceptance. |
| Autonomous collection and preparation | Planned | Generic acquisition, preparation of unfamiliar data, dynamic table relationships, and reusable agent-created workflow packages are not demonstrated by the current workspace. |
| Customer value and complete operating cost | Unverified | Customer accuracy, time saved, commercial savings, concurrent-user capacity, and complete operating cost remain unestablished. |

Use the [PoC scope and evidence](../demo/PoCStatus.txt) and [current architecture](../architecture/current-system.md) for the implemented boundaries. Historical test results are not qualification of a later revision.

## Decisions retained from the chats

- Clean up and clarify the existing proof of concept before expanding. Preserve useful source, history, datasets, models, and evidence.
- Qualify the existing toolkit alpha first after that cleanup. Hudson confirmed this priority in “Review BackIntel roadmap status” on October 9.
- On October 11, Hudson approved testing installation of the available app for Sprint 2. Preserve the separate toolkit work on the roadmap rather than treating the app demo as its completion.
- On October 12, Hudson approved a fresh local support analysis for Sprint 3, using fictional tickets and no paid calls. Keep its observed-statistics result separate from prediction and autonomous agent execution.
- On October 12, Hudson approved Sprint 4 to run that fresh support calculation from the current app, inspect its records, and save a report. Its local app review is complete; toolkit qualification remains separate.
- Start the developer alpha with LangGraph and self-contained commerce and support examples. Preserve reusable analytical interfaces for later Agno and OpenAI Agents SDK integrations.
- Let the agent select appropriate analytical steps. Show evidence, uncertainty, missing information, unsuccessful hypotheses, and cases where the baseline remains preferable.
- Keep the broader autonomous-data direction: unfamiliar inputs, checked preparation, reusable tables and workflows, repeated invocation, recovery, and permitted collection.
- Keep recorded demonstrations, simulated workflows, actual local models, live analyst runs, release qualification, and production operation distinct.

## Milestones and observable completion

The order below follows the confirmed toolkit-first priority. Later milestones are planned scope, not dated release commitments.

| Milestone | User outcome | Complete when |
| --- | --- | --- |
| **0. Understand the current PoC** | A reviewer or developer can choose the right demonstration and understand its limits. | Entry points, capability status, architecture, run instructions, and preserved work are clear. Demo publication is complete; remaining cleanup must identify a concrete problem before changing or removing code. |
| **1. Qualify the existing toolkit alpha** | An external developer can install BackIntel, equip an agent with its tools, and complete commerce and support analyses. | The recovered candidate is reconciled with canonical source; both examples use actual agent-selected steps; findings and comparisons are independently checkable; limits and recovery work; a new developer reproduces both examples without private workspace files; the identified candidate passes its required hosted checks and release review. |
| **2. Prepare an unfamiliar export** | A user supplies a messy export and a business objective without needing a bespoke importer. | BackIntel preserves the original, interprets fields, produces checked reusable tables and an analysis snapshot, explains an answer with evidence, and saves the working procedure. Ambiguous meaning is retained or escalated. Generated preparation code runs within an appropriate isolated workspace. |
| **3. Invoke the saved workflow again** | A person, application, event, or schedule can reuse accepted work after a source change. | Updated inputs run through the saved workflow; changed columns and meanings receive appropriate handling; unchanged work is reused; interruptions resume without duplicate accepted results or uncertain repeated paid operations; earlier useful results remain available. |
| **4. Collect from a permitted source** | A user provides source documentation and scoped access instead of manually preparing every export. | BackIntel configures and checks one extraction workflow, including pagination, completeness, duplicates, and incremental changes. Collected originals remain traceable. Access and data movement stay within the granted limits. |
| **5. Expand for demonstrated needs** | More agent frameworks and business environments can use the working core. | Each selected integration or source has a concrete user workflow, suitable access controls, runnable setup, and a direct completion check. Candidate areas include Agno, OpenAI Agents SDK, databases, SAP, ServiceNow, Snowflake, Databricks, documents, on-site processing, larger workloads, and concurrent work. These are options, not commitments to deliver every connector. |

Additional agent integrations may follow the alpha alongside the later data milestones when a concrete need justifies them. No framework replacement or new storage platform is selected by this roadmap.

The two-workflow alpha and the five-domain workspace campaign have separate completion conditions. A qualified alpha would not establish full five-domain acceptance, autonomous preparation, or production readiness.

## Toolkit alpha: first backlog items

These are proposed stories for planning. Owners, estimates, and tracker records remain unassigned. Keep at most three stories actively in progress; a dependency blocks the affected story rather than every independent task.

| Priority | User story | Tasks and direct completion check | Starting dependency |
| --- | --- | --- | --- |
| P0 | As a maintainer, I can continue the existing alpha without losing or recreating its work. | Recover the candidate source and relevant run records; compare its interfaces with the canonical workspace; preserve both; produce a reviewable integration decision and update the capability inventory. | Access to the reported cloud candidate. |
| P0 | As an agent developer, I can run both examples and understand their findings. | Provide installation and tool instructions; exercise actual agent selection; check numerical claims, evidence, missing-data behavior, and retained baselines; demonstrate bounded spending and interruption recovery. | Reconciled alpha source and its declared execution prerequisites. |
| P1 | As a new developer, I can reproduce the alpha and judge whether to adopt it. | Complete the quickstart from a clean environment without private artifacts; verify the findings; record required hosted checks and release review for the same candidate; prepare coherent source, package, examples, and documentation. | Both workflows work and their package is ready for independent reproduction. |

Historical recovery locator: “Review testing and demo workflows” reported `/workspace/backintel-agent-toolkit-0.1.0a2-candidate.zip`, with goal and sprint documents named `agent-toolkit-alpha-goal.md` and `agent-toolkit-alpha-sprint.md`. These are cloud-chat locators, not confirmed files in this local checkout.

That chat marked the candidate **In review**, with independent developer reproduction, hosted CI, and release review still remaining. Preserve that disposition until the candidate itself is recovered and checked. Its historical planning estimate is not a current delivery date.

## How to maintain and use this roadmap

1. **Use one current entry point.** Maintain this document as the repository roadmap. Link detailed goals and campaign records beneath it. Preserve older plans as history, and identify a superseded focus explicitly.
2. **Plan around a user outcome.** Each story needs a beneficiary, a concrete result, dependencies, an owner, and a completion check. Choose the next small deliverable from the active milestone rather than starting every future capability.
3. **Track work in AgentShift when authorized.** Read current records first, retain verified issue IDs, and map stories to their milestone. This document creates no tracker records and assumes no existing mapping.
4. **Report progress plainly.** State what users can do, what remains simulated or blocked, the relevant evidence, and the next useful result or decision. Update status when an outcome changes; code activity alone is not completion.
5. **Review the actual journey.** Demonstrate the intended workflow and its material failure handling. Use the smallest sufficient direct check for the changed behavior. Repeat a broader check only when a requirement, failure, or material change demands it.
6. **Keep delivery states separate.** Proposed, in progress, in review, qualified, and released describe different outcomes. A chat report is a lead to preserved work. A merged source change is not package release or production deployment. Record the actual release or deployment when it occurs.
7. **Keep decisions and authority visible.** Record changes to milestone scope and order here. The roadmap itself grants no additional authority for paid runs, tracker writes, external publication, merges, or deployment.

Immediate focus: finish the PoC capability inventory, recover the reported alpha candidate, and qualify that existing work before expanding into unfamiliar-data preparation. No release date is committed.

## Source decisions and supporting plans

- **“Review testing and demo workflows”** — chat `01a10eb2-7340-7052-bf28-f16577c3901a`. Defines the toolkit opportunity, goal, Agile stories, and reported candidate execution. The original alpha documents were saved in its cloud workspace.
- **“Resume BackIntel work locally”** — chat `01a10f20-51ca-7aa3-9070-410f6271255d`. Continues local recovery and confirms the consolidated demo merge. It does not establish publication of the separate alpha candidate.
- **“Review BackIntel roadmap status”** — chat `01a122ee-58f9-7771-b179-dabfeac85c5d`. Reconciles the roadmap sources and records the October 9 toolkit-first priority.
- [Autonomous workflow concept](../research/autonomous-workflow-concept.txt) — October 7 product intent, current limitations, cleanup priority, and deferred preparation/reuse/acquisition sequence.
- [Goal-driven analysis workspace plan](analysis-workspace-testing-goal.md) — the separate five-domain development and acceptance goal; retain its original authority and campaign limits.
- [Consolidation benchmark campaign](BenchmarkCampaign.txt) — methods and completion conditions for the historical consolidated candidate.
- [Issue-review demo plan](v0.1.0-development-roadmap.md) — retained earlier GitHub issue-review focus. It is not the current overall product roadmap.
- [Repository recovery plan](poc-recovery-plan.md) — historical consolidation and preservation record.
