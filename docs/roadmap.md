# BackIntel: background-intelligence product roadmap

Planning revision: 2026-11-14. Executive sponsor and product owner: **Hudson Aikins**.
[Linear owns delivery status and assignments](https://linear.app/intelip/project/backintel-0287c22fe5a7).
This document owns scope and acceptance. Versions are capability targets, not release
announcements, completion percentages, or promised dates.

## Executive decision

Build a persistent business and operational analyst that understands approved data and
procedures, identifies opportunities to reduce costs or increase revenue, helps managers
improve performance, and follows up on outcomes.

The operating cycle is **observe → investigate → recommend → record the decision →
follow up → measure**. A separate engineering cycle evaluates changes to the agent.
Dashboards and workbooks communicate the work. Business value and model quality are
different measurements.

Current source is experimental **v0.0.1**. Bounded read-only analysis, SmolVM execution,
calculation checks, local artifacts, Streamlit generation and optional visual review exist.
Persistent organizational memory, continuous missions, customer hosting and opportunity
follow-through are planned. There is one analyst graph per invocation. The specialist
remains GPT-6.1 Sol. Current SmolVM qualification is macOS ARM64.

## Product principles

- Each mission has an outcome, owner, counter-metrics, source scope, attention policy,
  spending/compute limits, and delegated authority.
- Connect relevant permitted systems incrementally. Correct access does not prove correct
  joins, metric meaning, freshness, completeness or procedure applicability.
- Version metric definitions and SOPs; preserve source-attributed organizational memory.
- Separate observations, hypotheses, estimated benefit and realized outcomes. A proposed
  saving is not money saved. A before/after change is not automatically causal.
- Investigation is autonomous within scope. Source writes, spending, external communication
  and production changes require their own delegated permissions.
- Optimize management value including review/correction burden. Activity volume is not value.
- Preserve the existing Deep Agents, SmolVM, model and LangSmith foundation. New providers,
  runtime subagents, infrastructure, fine-tuning and paid campaigns require justified scope.

## Users and first workflow

| User | Job to be done | Surface | Evidence of value |
| --- | --- | --- | --- |
| Executive / owner | Set priorities and choose interventions | Missions and outcome review | Defensible decisions and measurable benefits |
| Operations / program manager | Find and resolve recurring problems | Opportunities, investigations, follow-ups | Useful signals with less preparation/correction |
| Data / process owner | Make source meanings and procedures dependable | Sources, metric dictionary, SOP history | Incorrect joins and stale definitions rejected visibly |
| Administrator | Control access, costs and continuity | Workspace and operating controls | Isolation, recovery, retention and spending work |

**Planning assumption:** start with IntelIP delivery operations, using permitted Linear and
GitHub history and delivery SOPs. Confirm the actual workflow and business owner in INT-447
before live/paid execution. This is not a claim of an installed connector or customer.
Reuse existing Infrastructure Engine metric definitions where relevant. Assess process
bottlenecks; do not infer individual productivity from commit counts.

Later domain packs: franchise sales/labor/waste/service; fleet availability/turnaround;
program cost/staffing/milestones; startup retention/support/unit economics. Each requires
its own source, metric, SOP and evaluation contract. No universal-domain qualification.

## Frozen foundation and migration of the plan

The benchmark remains frozen by owner direction. Preserve results and unfinished acceptance
in [foundation history](roadmap-foundation-history.md). Do not restart the historical
92-response or domain/scale campaigns merely to advance a version. Reuse applicable checks;
unrun work remains unrun, and material failures relevant to a pilot must be fixed or excluded.

Basic SOP context moves from the old v0.4 plan to v0.0.5. Controlled improvement proposals
move from v0.5 to v0.4. Opportunity/decision/outcome history becomes explicit product work.
Unfamiliar-domain and large-data milestones remain qualification tracks for their claimed
scope; neither is a blanket prerequisite for a small-data internal pilot.
Historical issues are not silently closed or relabeled as passed.

## Accountability

Hudson owns priorities, data/deployment authority and continue/stop/release decisions.
The integrator owns coordination and the evidence-backed recommendation. Roles below are
assigned responsibilities, not invented staff. Hudson is the only verified project member;
execution workers remain unassigned until dispatch and capacity are known.

| Responsible role | Deliverables | Relevant skills |
| --- | --- | --- |
| Product owner — Hudson | Mission, constraints, pilot and release decisions | Product judgment, actual workflow ownership |
| Product / engineering integrator | Refinement, dependencies, integration and scope | product-ops-sync, codex-system-design, ponytail |
| Data and context engineer | Source contracts, metrics, SOPs and memory | data quality, validate-data, langchain-rag when needed |
| Runtime / platform engineer | Persistent jobs, sandbox, recovery, isolation | Deep Agents / LangGraph persistence, credential-management |
| Analyst engineer | Investigation, recommendations, outcome accounting | ai-engineering, analytical skills, tool-design |
| Evaluation engineer | Independent truth, replay and LangSmith gates | eval-engineering, evaluation, advanced-evaluation |
| Frontend engineer | Manager workspace, reports, landing experience | frontend-design, accessibility, ui-quality-review |
| Release / operations engineer | Deployment readiness, operating trials, support | pr-workflow, operational verification |

## Version milestones

See [evaluation gates G1–G8](engine-evaluations.md). All releases require their applicable
mandatory correctness, permission and regression checks. Version numbering does not
require serial execution of unrelated qualification work.

| Version | Goal / responsible role | Deliverable and exit condition | Existing work |
| --- | --- | --- | --- |
| **v0.0.1** | Honest foundation / Integrator + Evaluation | Frozen evidence and supported pilot scope reconciled; unrun cases remain unrun; relevant regressions and limits visible | INT-429–438, INT-451; baseline scope story |
| **v0.0.2** | Unfamiliar data / Data + Evaluation | Named-domain ingestion and transfer qualification with independent references and separate held-out results | INT-439–445 |
| **v0.0.3** | Larger workloads / Platform + Data | Real ≥10 GiB evidence only when that support is claimed; declared compute, limits and graceful failures | INT-398, INT-446 |
| **v0.0.4** | Inspectable analysis / Analyst + Frontend | Dashboard, chart and workbook values reconcile; mobile/desktop inspection and downloads pass G3 | INT-452–454 |
| **v0.0.5** | Organization-aware analysis / Data + Analyst | Mission/metric definitions, applicable SOP context, durable attributed memory and contextual report pass G1–G3 | INT-455–457, INT-465; S04 |
| **v0.1.0** | One useful shadow workflow / Product + Evaluation | Chronological replay completes an opportunity/decision/follow-up cycle; G1–G4 as applicable; explicit pilot verdict | INT-447–449; S06 |
| **v0.2.0** | Continuing mission / Platform | Durable jobs, triggers, investigation queue, qualified worker and recovery pass G5; ≥72 real hours with a recovery exercise | INT-458–460; S05 |
| **v0.3.0** | Useful signals / Analyst + Data | Named connectors, meaningful detection, attention policy and authorized delivery meet frozen G1/G4/G5 targets | INT-461–464 |
| **v0.4.0** | Outcomes and adaptation / Analyst + Evaluation | Outcome accounting and replay-tested improvement proposals pass G6/G7; one complete outcome assessment | INT-469; S09; INT-466–467 only for enabled methods |
| **v0.5.0** | Managed beta / Frontend + Platform | Workspace, opportunity inbox and one qualified funding route; G1–G8; ≥3 approved goals over ≥7 real days | INT-468, INT-471; S12 |
| **v0.6.0** | Organizational boundaries / Platform | Tenant/source isolation, credential lifecycle, retention/deletion and restore demonstrated across workspaces | INT-472; S13 |
| **v0.7.0** | Affordable operating envelope / Platform + Evaluation | Declared concurrency, capacity and cost per useful cycle measured; overload bounded and usage reconciled | INT-472; S14 |
| **v0.8.0** | Reusable domain packs / Data + Analyst | A second workflow onboards without core changes; separate semantics, transfer evidence and no first-workflow regression | S15 |
| **v0.9.0** | Release candidate / Release + Evaluation | Supported matrix, runbooks, rollback and 30-day protocol frozen; required gates pass | INT-472–473 |
| **v1.0.0** | Supported background analyst / Hudson + Release | ≥30 real days meet predeclared operating/business targets; complete incidents, costs, support and outcome record | INT-474 |

Optional forecasting and fine-tuning do not block a useful descriptive-analysis engine.
v1 remains bounded to named sources/workflows and read-only business systems, with
manager-approved interventions recorded and assessed. No universal autonomy claim.

## User stories

| ID | User story | Owner / target | Acceptance |
| --- | --- | --- | --- |
| S01 | As an owner, I can state an outcome and its limits so the engine knows what good means. | Product / v0.0.5 | Objective, counter-metrics, owner, sources, cadence, budget, escalation and review date required before live admission. INT-447/455. |
| S02 | As a data owner, I can define joins, time zones and freshness so conclusions reflect the business. | Data / v0.0.5 | Duplicate joins, missing partitions/costs and incompatible grain lead to explicit limitations or refusal. INT-455/461. |
| S03 | As a manager, I can provide procedures so recommendations follow applicable rules. | Context / v0.0.5 | Effective versions cited; conflicts, stale documents, revoked access and document injection handled. INT-465. |
| S04 | As a manager, corrections and past decisions persist so the engine does not repeat known mistakes. | Context / v0.0.5 | Facts/hypotheses/preferences separated; origin and effective dates; correction, expiry, restart and access checks. |
| S05 | As a manager, the engine selects useful questions so I need not write every prompt. | Analyst / v0.2 | Prioritize materiality, uncertainty, effort and attention cost; remember tried/rejected approaches; bounded exploration and legitimate no-action results. |
| S06 | As a manager, I can inspect, accept, defer or reject an opportunity so work has an owner and next step. | Product + Analyst / v0.1 | Evidence, estimate assumptions, uncertainty, owner, due date and reason; valid durable transitions; update duplicate observations. |
| S07 | As an owner, approved missions continue while no chat is open. | Platform / v0.2 | Persistent schedule, deduplication, readiness and leases; visible terminal state; cancellation and bounded concurrent admission. INT-458–460. |
| S08 | As a manager, I receive significant updates without repetitive interruption. | Analyst / v0.3 | Severity, quiet hours, digest/cooldown, recipient authorization, new evidence and pause tested. INT-462–464. |
| S09 | As an executive, I can distinguish estimated benefit from what happened after an action. | Analyst / v0.4 | Baseline, intervention date, observation window, costs and confounders; negative/inconclusive outcomes remain visible. |
| S10 | As an operator, agent improvements are tested before changing behavior. | Evaluation / v0.4 | Independent replay, same allowed inputs, intentionally regressing control, accept/reject/invalid verdict and rollback. INT-469. |
| S11 | As a manager, I can control missions and review opportunities in one workspace. | Frontend / v0.5 | Real persistent actions, useful failures, secure downloads, keyboard/mobile usability. INT-468. |
| S12 | As an administrator, I can select supported managed or customer-funded inference and inspect usage. | Platform / v0.5 | Qualify one route first; account isolation, revocation, limits, truthful credits/usage, no silent paid fallback; keys outside generated code. |
| S13 | As a customer, data, memories and outputs respect assigned roles. | Platform / v0.6 | Cross-workspace read/write/search/download, revocation, retention/deletion and restore checks. |
| S14 | As an operator, concurrent missions stay within compute and spending limits. | Platform / v0.7 | Admission, fairness, bounded backlog, overload/cancellation and bill reconciliation at declared workload. |
| S15 | As another team, I can onboard a different process without changing the engine core. | Data / v0.8 | Versioned source/metric/SOP pack, unseen time/entity cases and first-workflow regressions. |
| S16 | As a prospect, I understand the direction and current availability before evaluating it. | Frontend / current increment | Honest current/planned distinction; illustrative examples labeled; accessible navigation and local mission-brief download; no fake lead submission. |

Opportunity lifecycle: discovered → investigating → proposed → accepted/deferred/rejected →
implemented (manager-confirmed) → measuring → closed/reopened. A rejection keeps its reason;
material new evidence can reopen it. Closure can record no gain or an inconclusive result.

## Delivery sequence

Two-week planning cycles are a coordination cadence, not an estimate or calendar promise.
At refinement assign a real worker, scope source changes, size the story against capacity,
and take only ready work. Demonstrate a vertical outcome at each review.

| Sequence | Sprint goal | Work | Demo / exit |
| --- | --- | --- | --- |
| A | Make the mission and promise concrete | S01, baseline scope, S16 | Usable mission brief, accurate benchmark scope |
| B | Understand the organization | S02–S04, INT-456–457 | Current SOP and prior correction change analysis appropriately; numbers reproduce |
| C | Complete a shadow investigation | S06, INT-448–449 | Historical observation → opportunity → decision → follow-up assessment |
| D | Keep the mission alive | S05/S07, worker qualification | No-prompt trigger, restart, duplicate event, pause and exhausted budget |
| E | Prove operational usefulness | S08/S09 | Real signals, suppressed noise, follow-up, measured review burden |
| F | Deliver the managed beta | S10–S12, INT-471 | Workspace, funded jobs, tested improvement and seven-day operating report |

Capability chain: mission → sources/context → verified analysis → shadow decision →
durable mission → operational outcomes → managed beta. Landing work is independent.
Remove the old blanket unfamiliar-domain prerequisite from pilot entry, preserving all
workflow-relevant correctness and supported-scale requirements.

Definition of ready: user outcome, accountable role/worker, data and authority, dependencies,
acceptance cases, evidence layer, and finite execution envelope are known.
Definition of done: implementation, direct checks, review and required CI; evidence and limits
linked; rollback ready; release/deployment only when authorized. Plans and mocks are not live
capabilities. One successful model response is not sustained operation.

## Executive scorecard and decision gates

At each milestone present: supported capability delta; G1–G8 results; useful/false/missed
signals with denominators; correction effort; operating cost and latency; observed outcomes;
and a continue/narrow/fix/stop recommendation.

Proposed pilot defaults: ≥50% reduction in total preparation/review/correction time for an
equivalent recurring review; ≥80% useful opportunities among those assessed; no critical
miss in declared acceptance cases; operation inside the agreed budget. Freeze or replace
these values before the trial. They are planning targets, not measured achievements,
population guarantees, or implicit approval of new spending.

The historical waiver of human judge calibration remains. Ordinary operator decisions and
usefulness feedback are business evidence, not fabricated calibration. Without that feedback,
business usefulness remains unestablished.

## Architecture and commercialization

The analyst becomes a bounded worker behind a persistent mission/job coordinator. The
coordinator owns permissions, budgets, schedules, leases and history. Trusted renderers
publish inspectable artifacts. The workspace reads durable state; LangSmith records
traces and independent feedback.

Managed and customer-funded inference are separate from sandbox compute, storage and support.
The local subscription connection is not a multi-customer billing integration. Qualify
provider routes, terms, model/vendor provenance, accounting and secrets before offering
funding options. A private deployment can still send context to its configured model provider.

This plan creates no cloud resources, external notifications, customer access or paid runs.
No hosting vendor, new database or model is selected by example. Runtime delegation remains
disabled until a specific measured need justifies it.

## References

[Hone engine model](https://hone.com/blog/introducing-engines/) and
[simulation research](https://hone.com/blog/closing-the-gap/) inform outcome ownership and
replay-tested changes; their reported results are not BackIntel results.
[LangChain context engineering](https://www.langchain.com/blog/context-engineering-challenges-late-2026)
identifies open problems; [proactive agents](https://www.langchain.com/blog/proactive-agents)
provides scheduling patterns, not a requirement to change the current stack.
See [implementation](../README.md), [sandbox](sandbox-environment.md),
[evaluation gates](engine-evaluations.md), and [historical plan](roadmap-foundation-history.md).

## Linear delivery index

The [product plan in Linear](https://linear.app/intelip/document/backintel-background-intelligence-product-plan-and-release-gates-v001-e8419da3f6f6) mirrors this roadmap and the
evaluation definitions. Milestones carry the version goals. Existing completed work remains
unchanged; new stories are planned work, not implemented capability.

| Issue | Deliverable | Version / responsible role |
| --- | --- | --- |
| [INT-499](https://linear.app/intelip/issue/INT-499/reconcile-frozen-evidence-with-the-supported-operating-pilot-scope) | Reconcile frozen evidence with the supported operating-pilot scope | v0.0.1 / Integrator + Evaluation |
| [INT-500](https://linear.app/intelip/issue/INT-500/persist-attributed-organizational-memory-and-manager-corrections) | Persist attributed organizational memory and manager corrections | v0.0.5 / Data and context engineer |
| [INT-501](https://linear.app/intelip/issue/INT-501/track-opportunities-manager-decisions-and-follow-up-commitments) | Track opportunities, manager decisions and follow-up commitments | v0.1.0 / Analyst engineer + Product owner |
| [INT-502](https://linear.app/intelip/issue/INT-502/select-useful-investigations-within-mission-and-attention-budgets) | Select useful investigations within mission and attention budgets | v0.2.0 / Analyst engineer |
| [INT-503](https://linear.app/intelip/issue/INT-503/qualify-an-execution-worker-for-continuous-missions) | Qualify an execution worker for continuous missions | v0.2.0 / Runtime / platform engineer |
| [INT-504](https://linear.app/intelip/issue/INT-504/measure-intervention-outcomes-without-turning-estimates-into-savings) | Measure intervention outcomes without turning estimates into savings | v0.4.0 / Analyst engineer + Evaluation engineer |
| [INT-505](https://linear.app/intelip/issue/INT-505/qualify-inference-funding-secret-isolation-and-workspace-usage) | Qualify inference funding, secret isolation and workspace usage accounting | v0.5.0 / Runtime / platform engineer |
| [INT-506](https://linear.app/intelip/issue/INT-506/enforce-workspace-isolation-retention-and-recoverable-state) | Enforce workspace isolation, retention and recoverable state | v0.6.0 / Runtime / platform engineer |
| [INT-507](https://linear.app/intelip/issue/INT-507/measure-capacity-and-cost-per-useful-operating-cycle) | Measure capacity and cost per useful operating cycle | v0.7.0 / Runtime / platform engineer + Evaluation engineer |
| [INT-508](https://linear.app/intelip/issue/INT-508/qualify-a-reusable-operating-domain-pack-on-a-second-workflow) | Qualify a reusable operating-domain pack on a second workflow | v0.8.0 / Data and context engineer + Analyst engineer |
| [INT-509](https://linear.app/intelip/issue/INT-509/deliver-the-background-intelligence-product-roadmap-and-landing) | Deliver the background-intelligence product roadmap and landing experience | v0.0.1 / Product integrator + Frontend engineer |

The mission decision is [INT-447](https://linear.app/intelip/issue/INT-447), the shadow-pilot
decision is [INT-449](https://linear.app/intelip/issue/INT-449), beta acceptance is
[INT-471](https://linear.app/intelip/issue/INT-471), and v1 acceptance is
[INT-474](https://linear.app/intelip/issue/INT-474). These decision issues are assigned to
Hudson. Engineering roles are named; worker allocation and estimates happen at refinement.

Native dependencies connect these tasks to the existing implementation backlog. INT-449
now depends on scoped foundation evidence, contextual reports, reserved pilot cases and the
opportunity lifecycle. Optional unfamiliar-domain, scale and statistical work remains visible
without becoming an unrelated universal pilot/beta blocker.
