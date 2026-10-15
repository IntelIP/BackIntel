# BackIntel product roadmap and delivery plan

Updated October 14, 2026 after Hudson clarified the full autonomous-product objective. Start with [the roadmap](../ROADMAP.md) for priorities and [the system design](../SYSTEM_DESIGN.md) for current foundations and proposed behavior. This update supersedes toolkit-first sequencing; it preserves completed work and earlier decisions as history.

[Backlog.md tasks](../../backlog/tasks) own story acceptance, dependencies, and status. The [task index](agile-backlog.md) retains the legacy story mapping and shared delivery contract. Delivery groups are proposed increments, not calendar commitments. The [current sprint](current-sprint.md) remains Sprint 4, Done for its local support-script scope; this migration does not open a new implementation sprint.

## Product outcome

BackIntel should let a business owner supply a question, business measures and targets, permitted connections, and operating limits. Agents then discover and collect information, build pipelines, profile, clean, transform and classify data, develop and evaluate analysis and prediction methods, explain results, and maintain them continuously.

The user should not need to implement each importer, configure every processing step, split inputs into manual batches, or use a separate coding assistant whenever a new analysis is needed. Coordinated specialist agents, cross-system communication, complete-workload processing, and operation at an agreed scale belong to the product. Implementation remains staged.

Databricks is the reference business-system example. The first actual question, data, access, and measurable operating targets still need refinement. No live connection or deployment is established by choosing that example.

Automation of data-engineering and data-science tasks is the intended value. Demonstrating saved time, lower cost, better decisions, or replacement of a manual workflow requires measured user outcomes. The system may correctly conclude that data is insufficient, a hypothesis fails, or a simple baseline is preferable.

## Current position

| Area | Status | What the evidence supports |
| --- | --- | --- |
| Recorded demonstration | Confirmed | [PR #2](https://github.com/IntelIP/BackIntel/pull/2) merged the consolidated demo into `main` at `c6de6ae`. It shows saved findings and review decisions using synthetic data and historical results. |
| Supplied app installation | Confirmed historical result | [Sprint 2](sprint-2-review.md) restored `f5e2b6` from a supplied ZIP and opened its recorded demo in a fresh Python environment. This is separate from toolkit installation. |
| Fresh support calculation | Confirmed locally | [Sprint 3](sprint-3-review.md) and [Sprint 4](sprint-4-review.md) deliver a CSV calculation, supporting records, and reports. Sprint 4 replaced the support screen with a script at Hudson's request. |
| Known-dataset analysis workspace | Confirmed implementation; limited historical evaluation | Approved-tool selection, snapshots, evidence, comparisons, permissions, spending limits, durable jobs, and recovery exist. Historical model runs retain their original candidate and scope. |
| Reported toolkit alpha | Blocked source access; contents unverified | The reported `0.1.0a2` candidate has not been recovered here. Recovery remains a dependency of its reconciliation and installation only. |
| Full five-domain live acceptance | Blocked in the recorded campaign | Credit inputs and five live analyst cases remained blocked. This is a separate acceptance scope. |
| Autonomous business-system pipeline | Planned | Generic discovery, unfamiliar-data preparation, generated analytical methods, Databricks integration, coordinated agents, and continuous adaptation are not demonstrated by the current source. |
| Complete workloads and operating scale | Unverified | Current classification and prediction use bounded cohorts. No agreed deployment-scale or concurrent-user result is established. |
| Customer value | Unverified | Saved manual effort, operating economics, and customer adoption have not been demonstrated by the recorded demos. |

See the [capability inventory](../demo/PoCStatus.txt) and [current architecture](../architecture/current-system.md) for historical details. A fresh source read for this planning update does not renew old application-test results.

## Decisions retained from the chats

- **October 14 — current product scope:** Hudson clarified end-to-end autonomous data engineering and analysis, autonomous method development, continuous operation, coordinated agents, communication between business systems, and scale. Databricks is the reference scenario. This supersedes the earlier toolkit-first order and the treatment of source integration and capacity as optional late expansion.
- **October 14 — delivery approach:** Keep development infrastructure and product implementation in independently useful stages. Hudson manually selects and starts development tasks; this does not limit the product's intended autonomy.
- **October 9 — earlier priority:** Hudson selected qualification of the existing toolkit before unfamiliar-data work in “Review BackIntel roadmap status.” Retain the recovery and qualification work, but it is no longer a blanket prerequisite for independent autonomous-product development.
- **October 11 — completed app slice:** Hudson approved installation of the available app for Sprint 2. That result did not close toolkit recovery or installation.
- **October 12 — completed calculation slices:** Hudson approved fresh local support analysis using fictional tickets and no paid calls, then requested a script after the browser delivery. Preserve the calculation, evidence, and reports; do not treat it as autonomous analysis or prediction.
- **Earlier toolkit contract:** LangGraph with commerce and support examples was the developer-alpha starting point; reusable interfaces for Agno and OpenAI Agents SDK were retained. This does not settle the full autonomous product's runtime or client/service split.
- **Continuing product principles:** Let agents choose appropriate work, retain evidence and uncertainty, check methods against baselines, preserve useful work, and distinguish simulations, historical results, live execution, qualified releases, deployment, and adoption.

## Toolkit and platform delivery

BackIntel has two delivery surfaces with a shared implementation core. The toolkit lets a developer or another agent call reusable capabilities from its own application. The platform lets a business owner supply an objective and have BackIntel organize, run, explain, and maintain the work. Both remain part of the plan.

| Work area | Work to execute | Observable result |
| --- | --- | --- |
| Toolkit | Recover and qualify the reported alpha; establish its installation, dependencies, callable interfaces, examples, evidence, and release scope. Expose further qualified shared capabilities through the selected toolkit interface. Add other framework adapters only when needed. | A developer can install an identified candidate and run its declared capabilities without the team's private workspace or the platform's user interface. Existing alpha qualification does not prove the wider autonomous scope. |
| Shared core | Implement permitted collection, data preparation and classification, checks, analysis and prediction, method development, saved workflow versions, whole-workload processing, permissions, spending controls, and recovery. | Toolkit and platform callers use the same underlying behavior and receive consistent results, evidence, coverage, usage, and error information. |
| Agent platform | Capture objectives; discover sources; plan and coordinate work; present results; trigger updates and repair; communicate with approved systems; support users and agreed operating scale; measure real use. | A business owner gets a checked, continuously maintained answer without designing each pipeline or commissioning each new analysis. |

Task labels make this division selectable in the existing backlog. `toolkit` selects toolkit work, `platform` selects platform work, and `shared-core` marks work used by both. Shared tasks carry all three labels and have one task record, one implementation, and one applicable completion check. The labels describe delivery scope, not a new task status or permission to start.

### Existing task allocation

| Delivery scope | Native stories | Purpose |
| --- | --- | --- |
| Toolkit only | S-02–S-03, S-07–S-11, S-25 | Candidate recovery, installation, commerce and support examples, follow-ups, independent reproduction, release qualification, and optional framework integration. |
| Shared core | S-01, S-04–S-06, S-13–S-19, S-22–S-24, S-27–S-29, S-32 | Baseline, controls, reusable data and analytical capabilities, saved invocation, source collection, complete workloads, optional source-side execution, and generated methods. |
| Platform only | S-12, S-20–S-21, S-26, S-30–S-31, S-33–S-36 | Business objectives, continuous operation, the integrated Databricks reference, coordinated agents and systems, multiple users, capacity, independent operation, and measured value. |

Shared allocation means the capability must be reusable; it does not move platform ownership of objective planning, agent assignments, schedules, or user experience into an already existing toolkit. Shared method-development work includes reusable agent capabilities as well as tools. Actual package boundaries and client/service interfaces remain refinement decisions against available source.

### Execution sequence and handoffs

1. **Define one result that both delivery surfaces can support.** Refine S-12 into a specific business question, permitted sources, full workload, expected answer checks, and operating limits. Identify the reusable capability the toolkit should expose and the business result the platform should present. Keep missing business inputs explicit.
2. **Make the first shared workflow reliable.** Apply S-04–S-06 controls to the selected path; establish S-22 access; then follow the native dependencies for collection, preparation, checking, and complete-workload analysis. Save the workflow through S-18. Refine the invocation contract before implementing S-19, and satisfy S-19's existing prerequisites before starting it.
3. **Join the toolkit capability to the platform experience.** S-19 demonstrates equivalent checked results through manual and application invocation, including run identity, evidence, duplicate protection, and interruption recovery. S-26 demonstrates the selected complete Databricks business workflow. This is the first integrated delivery target; it does not establish generated methods, continuous adaptation, or multi-agent scale.
4. **Add autonomous methods and continuous operation.** S-32 develops and checks missing analysis methods. S-20–S-21 and S-24 keep accepted workflows current and handle changes. Continuous operation can follow a saved workflow without waiting for every new method. Extend document use through S-27 when the selected question needs it.
5. **Coordinate, scale, and prove independent use.** S-33–S-34 coordinate specialists and permitted systems; S-30 and S-36 establish user separation and sustained operating targets. S-35 packages the declared autonomous runtime for independent operation; S-31 measures useful work and remaining human effort. A toolkit release and a platform deployment retain their own qualification and authorization.

The historical toolkit path remains S-02 → S-03 → S-07/S-08 → S-09 → S-10 → S-11, with the native shared-control prerequisites also applying. It can advance when actual candidate access is available. Do not repeat recovery searches without a new lead or reconstruct that candidate from summaries. Missing alpha access blocks its qualification chain; available-source shared and platform work follows its own dependencies.

This is a delivery sequence, not a new sprint, calendar promise, or instruction to run both tracks concurrently. Hudson selects one bounded development task at a time. Package extraction and deployment separation occur only when required by a selected deliverable; the service diagram is not a requirement to build every microservice first.

## Milestones and observable completion

All six product milestones below are intended scope. Pull one bounded story at a time in the local development pilot. Shared controls apply from the first runnable path. Dependencies, not the numeric story labels, govern work order.

| Milestone | User outcome | Complete when | Story mapping |
| --- | --- | --- | --- |
| **1. Understand the objective and discover permitted data** | The owner provides the result needed and access; BackIntel identifies the relevant data and plans the work. | One selected business question has explicit definitions, population, period, targets, permitted actions, limits, and answer checks. The agent inspects the permitted source interface and configures a checked connection without requiring a user-written extraction routine. | S-12, S-04–S-05, S-22 |
| **2. Complete one business-system pipeline** | The owner receives a checked answer without manually building the pipeline. | The Databricks reference scenario processes the complete agreed workload: collect, preserve originals, profile, clean, classify where relevant, transform, join, validate, analyze, explain, and save an executable workflow. No bespoke importer or manual chunking is required from the user. Coverage, evidence, limits, rerun, and interruption recovery are demonstrated. | S-13–S-19, S-23, S-26, S-29, S-06 |
| **3. Develop and compare analysis methods** | The owner can ask a question requiring more than the fixed tool catalog. | The agent proposes and implements a bounded method, checks it independently, compares with an appropriate baseline, preserves evaluation boundaries, and accepts or rejects it under a declared policy. Unsupported prediction, uncertainty, and failed hypotheses remain explicit. | S-32 |
| **4. Keep answers and target progress current** | The owner receives continuing analysis as business information changes. | Permitted events/schedules run the saved workflow, collect incremental changes, detect schema/quality changes and method deterioration, repair routine failures within limits, and show freshness and target progress. Material ambiguity or exhausted authority escalates; failed refreshes preserve the last accepted answer. | S-20–S-21, S-24 |
| **5. Coordinate agents and systems at scale** | Several specialists complete larger, connected workflows without the owner managing every handoff. | Coordinated agents share definitions, state, evidence, dependencies, and budgets; cross-source identities and permitted result delivery work; concurrent workloads meet agreed correctness, throughput, latency, freshness, recovery, and cost targets. Documents or text are included where the selected business workflow needs them. | S-27, S-30, S-33–S-34, S-36 |
| **6. Demonstrate independent operation and user value** | Another user can operate BackIntel and assess which manual tasks it replaces. | An independent user installs and runs the declared autonomous scope without private implementation files. An agreed pilot compares completion, human effort including corrections, errors, time, and known costs against the existing workflow. Actual release and deployment remain separately recorded outcomes. | S-35, S-31 |

Continuous-operation work can proceed after the saved pipeline exists; it need not wait for every new analytical method. Whole-workload coverage is required in milestone 2. Milestone 5 establishes the separately agreed sustained capacity and concurrency claims.

### First reference scenario and open targets

Refine **S-12** next. Record one business question and its expected result, the business definition of each metric and target, a permitted Databricks source boundary, and the workload that must complete. Then select the smallest eligible implementation story. This planning update does not choose an actual customer dataset or invent credentials, result values, or performance targets.

Before implementation depends on them, establish volume and change rate; completion time and freshness; concurrent users and agents; permitted data movement; resource and spending caps; result destinations; and the cases requiring a person. These are inputs to a useful delivery contract, not a request to build every stage together. Sampling for model evaluation must be explicit and cannot stand in for processing the operational workload.

## Toolkit alpha: preserved supporting work

The reported toolkit remains worth recovering and qualifying. S-02 owns the current source-recovery status; S-03 and toolkit-specific example/release work retain that dependency. S-04–S-06 reuse current controls for whichever identified candidate is being implemented; independent source work can proceed without the missing bundle.

| Supporting work | Completion condition | Dependency |
| --- | --- | --- |
| Recover and reconcile the alpha: S-02 | Preserve candidate source and run records, compare interfaces with current source, and record a reviewable reuse decision. | Actual candidate access. |
| Install and qualify examples: S-03, S-07–S-10 | A new developer installs the identified candidate, runs actual agent-selected commerce and support analyses, checks findings, and resumes within declared limits. | Recovered source and the applicable shared controls. |
| Review and release: S-11 | Source, package, examples, required checks, and release review agree on the identified candidate; record actual authorized publication. | Successful reproduction and release authority. |

Historical locator: `/workspace/backintel-agent-toolkit-0.1.0a2-candidate.zip`, reported commit `f0a3d2573fb3da9469d81e35691f60a42a0d9a1b`. The source chat reported **In review**, with independent reproduction, hosted checks, and release review still remaining. These are recovery leads, not verified local artifacts. Do not rebuild the candidate from summaries or repeat completed recovery searches without a new lead.

Additional framework adapters (S-25) and source-side execution (S-28) remain selectable implementation options when a concrete need or data policy requires them. They do not make the core autonomy, multiple-source workflow, or scale outcomes optional. No framework replacement, hosting vendor, new storage platform, or priced infrastructure is chosen here.

## How to maintain and use this roadmap

1. **Keep one authority for each fact.** Product outcomes and decisions live here; priorities link from [the roadmap](../ROADMAP.md); task details, acceptance, dependencies, and status live in [Backlog.md](../../backlog/tasks). The [task index](agile-backlog.md) links the 36 migrated stories. Dated reviews retain their original scope.
2. **Choose a useful small result.** Each story needs a beneficiary, bounded outcome, dependencies, owner, expected result, and direct completion check. Keep one active task in the pilot. A milestone is not permission to implement all its stories at once.
3. **Preserve prior work.** Keep completed demonstrations, the support script, toolkit recovery records, and the separate five-domain acceptance goal. None alone demonstrates the autonomous product.
4. **Report actual capability.** State what works, what is simulated or missing, and the next useful result. Use the smallest sufficient direct verification for the change. A merge or green check is not deployment, adoption, or measured benefit.
5. **Keep authority explicit.** Use AgentShift only when current tracking work is authorized. This plan creates no tracker records, live connections, schedules, paid runs, external messages, releases, merges, or deployments.

## Source decisions and supporting plans

- **Current October 14 clarification** — this local-development-pilot chat; establishes the autonomous business-system objective, Databricks reference, method development, coordinated agents, continuous operation, and scale.
- **“Review BackIntel roadmap status”** — [chat `01a122ee-58f9-7771-b179-dabfeac85c5d`](codex://threads/01a122ee-58f9-7771-b179-dabfeac85c5d); records earlier toolkit priority, completed bounded app/script slices, and whole-workload concerns. A client/service architecture was a proposal, not a settled product decision.
- **“Review testing and demo workflows”** — chat `01a10eb2-7340-7052-bf28-f16577c3901a`; reported the toolkit candidate and original alpha goal/sprint documents in its cloud workspace.
- **“Resume BackIntel work locally”** — chat `01a10f20-51ca-7aa3-9070-410f6271255d`; preserves the local recovery handoff.
- [Autonomous workflow concept](../research/autonomous-workflow-concept.txt) — October 7 product intent and research. Its original deferred priority is superseded; its workflow and semantic-correctness requirements remain relevant.
- [Goal-driven analysis workspace plan](analysis-workspace-testing-goal.md) and [benchmark campaign](BenchmarkCampaign.txt) — separate five-domain and historical-candidate acceptance scopes.
- [Issue-review demo plan](v0.1.0-development-roadmap.md) and [repository recovery plan](poc-recovery-plan.md) — historical scope and preservation context.
