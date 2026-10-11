# BackIntel ordered user-story backlog

Updated October 10, 2026. Planning document for the [product roadmap](README.md). The product goal is to help a person or agent complete a permitted business task, check the result, and save work that can run again.

The [current sprint](current-sprint.md) commits S01 verification and a bounded source-discovery task under S02. Full S02 recovery and S03 installation retain their own dependency and completion conditions.

**Immediate delivery goal:** qualify the existing toolkit alpha after clarifying the current PoC. An independent developer must be able to install it, complete commerce and support analyses, inspect the evidence, and resume interrupted work within known limits.

## Planning status and operating rules

- S01–S31 are local planning labels, not AgentShift or GitHub issue IDs. No external tickets are created by this document.
- These are proposed delivery increments, not calendar sprint commitments. Owners, capacity, estimates, implementation surfaces, and dates must be assigned at refinement. Unstarted stories remain in **Refine**; S01 is **Done** and full S02 is **Blocked**, as recorded in the [Sprint 1 review](sprint-1-review.md); conditional expansion stories are an option backlog.
- Use AgentShift for execution tracking when authorized. Read existing records before creating or updating them and retain verified mappings.
- Begin with S01 and S02. Do not rebuild an allegedly completed alpha from chat descriptions. Recover its source and check what can be reused.
- Pull a story only when its dependencies, owner, bounded session scope, expected result, access, and applicable tests are clear. S02 requires verified access to the reported candidate; that access is currently unverified.
- Use at most three started stories, including work under review, validation, demonstration, or a started blocked state. This is a ceiling, not a target. Dependencies govern pull order.
- Finish each story by showing its stated user outcome and material failure case. A dependency blocks the affected work; it does not erase independent progress.

## Increment sequence

| Increment | User outcome | Stories | Start condition | Review demonstration |
| --- | --- | --- | --- | --- |
| 1. Establish the working baseline | A developer knows what works and can install the recovered toolkit. | S01–S03 | Existing PoC documents and the alpha recovery locator are available. | Show the capability inventory and install the reconciled candidate from a clean environment. |
| 2. Protect access, spending, and progress | A developer can run bounded work without losing results or exceeding authority. | S04–S06 | The candidate is reconciled and installable. | Deny an unauthorized request, stop work at a spending boundary, then interrupt and resume one accepted job. |
| 3. Qualify the developer alpha | An external developer gets checkable commerce and support answers from an actual agent. | S07–S11 | Access, spending, and recovery checks pass; required inputs and any live-call authority are available. | Run both examples, show an unsupported or unsuccessful hypothesis, independently reproduce the installation, and review the release candidate. |
| 4. Prepare an unfamiliar export | A user supplies messy data and receives a checked answer without a bespoke importer. | S12–S17 | The toolkit alpha is qualified; one bounded unfamiliar-input task and expected outcomes are selected. | Transform the unfamiliar export, check its meaning and totals, answer the question, and show how ambiguity is handled. |
| 5. Repeat the accepted workflow | A user or application can rerun accepted work and receive safe updates. | S18–S21 | The unfamiliar-input workflow is correct and useful. | Save it, invoke it again, trigger it from an event or schedule, and handle a changed input while preserving prior results. |
| 6. Collect from a permitted source | A user can supply scoped access and receive complete, refreshable information. | S22–S24 | The reusable workflow works; one source and its access/collection limits are agreed. | Configure one connection, collect all permitted pages, then collect an update without losing or duplicating records. |
| 7. Expand for demonstrated needs | Selected users gain additional integrations, input types, or operating capacity. | Selected S25–S31 | A concrete user need, owner, completion target, and capacity exist for the selected story. | Demonstrate the selected new workflow or measured customer benefit. This increment does not commit all expansion options together. |

Every increment has a terminal review: classify committed stories as Done, Blocked, or Cancelled; record the user-visible result and remaining dependency; then explicitly choose the next increment or return to refinement. Do not silently carry unfinished work forward.

## Increment 1 — Establish the working baseline

### Know what works today

**S01 · P0 · Work type: research · Depends on: none.**

**Status:** Done. Recorded demo checks and capability clarification are complete. Hudson accepted the documented result and continuation on October 10, 2026.

**Story:** As a developer or reviewer, I need an accurate capability inventory, so that I choose the right entry point and understand what its results mean.

**Tasks:** Check the recorded demo, current workspace, and reported toolkit separately; identify real, simulated, historical, and missing behavior; reconcile the inventory with run instructions and the roadmap.

**Acceptance and demo:** A newcomer can identify how to run each supported surface and what it establishes. A simulated analyst response and a saved model result remain clearly distinguished from new execution. Missing evidence remains visible.

**Owned surface:** Capability inventory, architecture, run instructions, and roadmap documentation. Preserve existing source and private artifacts.

### Recover and reconcile the existing alpha

**S02 · P0 · Work type: manual-task · Depends on: none; requires candidate access.**

**Status:** Blocked. The bounded source-discovery task is complete. The reported cloud ZIP is not accessible here and its exact commit/branch are unavailable in GitHub; retrieval precedes source reconciliation.

**Story:** As a maintainer, I need the existing alpha source and relevant results, so that we continue completed work rather than recreate it.

**Tasks:** Locate the reported candidate; preserve and check its contents and original identity; compare its package and interfaces with canonical source and record the integration decision.

**Acceptance and demo:** Show the recovered source, package, examples, and relevant run records. Identify what can be reused and what remains unverified. If the bundle is unavailable or inconsistent, record that dependency without claiming recovery or reconstructing missing work from summaries.

**Owned surface:** Recovery copy and a scoped integration of alpha source and documents. Excludes destructive replacement of canonical source or private data.

### Install the toolkit from a clean environment

**S03 · P0 · Work type: implementation · Depends on: S02.**

**Story:** As an agent developer, I need a reliable installation and quickstart, so that I can begin without the team's private workspace.

**Tasks:** Reconcile package dependencies; document the LangGraph setup and example entry points; identify required inputs and separately configured credentials.

**Acceptance and demo:** Install the identified candidate in a clean environment and open both examples. A missing required input or dependency produces useful instructions. Installation does not silently discover credentials or initiate paid analysis.

**Owned surface:** Recovered toolkit packaging, dependency declarations, examples, and quickstart. Exact files are assigned after S02.

## Increment 2 — Protect access, spending, and progress

### Use only permitted information and actions

**S04 · P0 · Work type: implementation · Depends on: S03.**

**Story:** As a data owner, I need source and role permissions enforced, so that an agent uses only the information and actions I allowed.

**Tasks:** Reuse existing permission controls in toolkit entry points; check allowed, denied, and expired access; ensure source text cannot grant additional authority.

**Acceptance and demo:** An allowed user accesses the intended source. An unauthorized or expired request cannot inspect data or publish a result. Instructions embedded in source content cannot alter access policy.

**Owned surface:** Toolkit source admission and tool authorization using existing access controls. High risk: data exposure.

### Control spending and explain charges

**S05 · P0 · Work type: implementation · Depends on: S03.**

**Story:** As a budget owner, I need bounded and explainable analysis spending, so that work cannot silently exceed the agreed limit.

**Tasks:** Reconcile relevant existing campaign charges and authority; expose reservations and measured usage; check exhausted limits, unknown charges, and overlapping admissions.

**Acceptance and demo:** A permitted request reserves within the cap and settles recorded usage. Exhausted limits or unresolved charges prevent new paid admissions; overlapping requests cannot overspend. Fixtures test these paths before any separately authorized live calls. Unmeasured local compute remains unknown rather than zero.

**Owned surface:** Existing budget and usage controls exposed through toolkit calls. High risk: financial correctness. This story grants no new spending allowance.

### Resume accepted work after interruption

**S06 · P0 · Work type: implementation · Depends on: S03, S04, S05.**

**Story:** As an agent developer, I need interrupted work to resume safely, so that I keep accepted results without unnecessary repeated calls or charges.

**Tasks:** Reuse durable jobs and retained evidence; resume partial work; exercise duplicate submission, cancellation, and uncertain provider outcomes.

**Acceptance and demo:** Interrupt a bounded job, restart it, and retrieve the accepted result. Replaying accepted work creates no second result or charge. An uncertain paid operation is reconciled or visibly blocked before repetition; cancellation has a clear terminal state.

**Owned surface:** Toolkit job continuation and existing recovery paths. High risk: lost work or duplicate charges.

## Increment 3 — Qualify the developer alpha

### Complete the commerce analysis

**S07 · P0 · Work type: implementation · Depends on: S03, S04, S05.**

**Story:** As an agent developer, I need a working commerce example, so that I can see the agent choose analytical steps and test a business hypothesis.

**Tasks:** Admit the example inputs; let the actual agent select approved analysis tools; compare the proposed prediction method with the predefined baseline, including whether text adds useful information.

**Acceptance and demo:** The real agent produces a source-backed answer and comparable evaluation results. Numbers reconcile with an independent expected calculation. Missing inputs or an unsuccessful hypothesis produce an honest result. Label synthetic inputs and recorded replay correctly.

**Owned surface:** The reconciled commerce example and approved analytical tools. Preserve evaluation boundaries and prevent future outcomes entering prediction inputs.

### Complete the support analysis

**S08 · P0 · Work type: implementation · Depends on: S03, S04, S05.**

**Story:** As an agent developer, I need a working support example, so that I can compare estimated resolution time with a simple baseline and inspect the underlying cases.

**Tasks:** Run the support workflow through actual agent-selected tools; retain original messages and interpretations; compare the candidate with the frozen baseline and show limitations.

**Acceptance and demo:** Findings and estimates trace to the selected support inputs and evaluation cases. Unsupported numerical claims are rejected or corrected. Missing information and a retained baseline are valid outcomes. Synthetic tickets are not presented as customer-performance evidence.

**Owned surface:** The reconciled support example, its source links, and comparison outputs.

### Verify findings and ask a follow-up

**S09 · P0 · Work type: implementation · Depends on: S07, S08.**

**Story:** As a reviewer, I need to inspect evidence, uncertainty, and follow-up answers, so that I can check a finding before recording a decision.

**Tasks:** Expose relevant source and calculation references; support a scoped follow-up and correction through the existing interface; show how corrected evidence affects the result and predictor validity.

**Acceptance and demo:** Trace a numerical finding to its source, ask a follow-up, and record a decision. A correction creates an inspectable updated result. Missing evidence, model disagreement, and insufficient information remain explicit; an invalidated predictor is not silently treated as current.

**Owned surface:** Existing toolkit result, evidence, follow-up, correction, and human-review interfaces. Reuse current interfaces before proposing a new one.

### Reproduce the examples independently

**S10 · P1 · Work type: manual-task · Depends on: S06, S09.**

**Story:** As a new developer, I need to reproduce both examples independently, so that adoption does not depend on help from the implementer.

**Tasks:** Assign an independent tester; install from documented source or package without private workspace files; run both examples and the documented recovery journey.

**Acceptance and demo:** The independent developer completes setup, checks the findings, and resumes work within the declared limits. Missing credentials have a clear setup or blocked disposition. Record friction and fix material quickstart defects before qualification.

**Owned surface:** Quickstart, installation, example, and recovery instructions plus the independent reproduction record. Tester is not yet assigned.

### Review and release the qualified alpha

**S11 · P1 · Work type: implementation · Depends on: S10.**

**Story:** As an early adopter, I need a coherent reviewed release, so that the source, package, instructions, and demonstrated behavior agree.

**Tasks:** Identify the final source and package; run their required hosted checks and release review; prepare release notes and publish only under established release authority.

**Acceptance and demo:** Required checks and review pass for the same candidate. The released package installs and reproduces the documented examples. Record the actual publication and remaining limits. A green check or merge alone does not establish a published release; missing publication authority leaves release pending.

**Owned surface:** Alpha release candidate, packaging, documentation, and authorized publication. Version is selected during refinement; the reported `0.1.0a2` remains a historical candidate label.

## Increment 4 — Prepare an unfamiliar export

### Define the business question and operating limits

**S12 · P1 · Work type: implementation · Depends on: S11.**

**Story:** As a business user, I need to state the question, population, period, and permitted information, so that BackIntel works toward the result I actually need.

**Tasks:** Capture the objective and expected output; identify relevant sources and limits; resolve ambiguity that materially changes the answer.

**Acceptance and demo:** Show the saved question and revisable plan. A materially ambiguous unit, population, or time period receives clarification rather than an invented assumption. Routine preparation does not require a decision at every step.

**Owned surface:** Goal and planning interface for one selected unfamiliar-data task.

### Admit the export and retain the original

**S13 · P1 · Work type: implementation · Depends on: S12, S04.**

**Story:** As a data owner, I need the original export preserved, so that cleaning cannot destroy evidence or prevent another approach.

**Tasks:** Admit a permitted unfamiliar file; retain its unchanged contents and identity; record collection context, permissions, and required handling limits.

**Acceptance and demo:** Retrieve the unchanged original after processing and link derived rows to it. A denied, malformed, or unsupported input receives a clear disposition without replacing an accepted source.

**Owned surface:** Raw-input admission, retained snapshots, and access context. High risk: loss or unauthorized data movement.

### Understand fields and table relationships

**S14 · P1 · Work type: implementation · Depends on: S13.**

**Story:** As an analyst, I need BackIntel to interpret unfamiliar fields, units, identities, and relationships, so that preparation reflects the business meaning.

**Tasks:** Inspect types, missingness, units, dates, keys, and candidate relationships; propose meanings and mappings; retain unresolved ambiguity.

**Acceptance and demo:** Correctly interpret a selected unfamiliar schema with independently known meanings. Ambiguous dates, units, identities, or joins remain explicit rather than being silently resolved. No dataset-specific importer is required from the user.

**Owned surface:** Source profiling and semantic preparation definitions for the selected task.

### Prepare data inside an isolated workspace

**S15 · P1 · Work type: implementation · Depends on: S14.**

**Story:** As a business user, I need BackIntel to create and repair preparation steps, so that I do not manually write cleaning code for each export.

**Tasks:** Plan bounded transformations; execute generated or configured preparation code in an isolated workspace; retain accepted steps and repair a demonstrated failure within the operating limits.

**Acceptance and demo:** Produce reusable tables from the unfamiliar input. Demonstrate a recoverable transformation error and a refused unauthorized file or network operation. The user does not supply a bespoke importer; source content cannot expand tool authority.

**Owned surface:** Preparation workspace, execution boundary, and retained preparation code. High risk: generated execution and data access.

### Check that preparation preserves meaning

**S16 · P1 · Work type: implementation · Depends on: S15.**

**Story:** As an analyst, I need checked records, totals, units, and joins, so that a transformation that executes successfully cannot quietly change the answer.

**Tasks:** Reconcile retained and excluded records; check identities, units, missingness, and business totals; detect a join that duplicates quantities or money.

**Acceptance and demo:** Prepared data matches an independent expected result. A double-counting join, mixed unit, or unexplained exclusion fails the check and prevents a misleading accepted answer. Retain the reason and affected records.

**Owned surface:** Preparation correctness checks and exclusion records. High risk: materially wrong business results.

### Answer the question from the prepared data

**S17 · P1 · Work type: implementation · Depends on: S16.**

**Story:** As a business user, I need an explained answer from the newly prepared data, so that unfamiliar inputs lead to useful work rather than only cleaned tables.

**Tasks:** Build the task-specific analysis snapshot; use its checked definitions in analytical tools; produce findings and useful artifacts with evidence and limitations.

**Acceptance and demo:** Answer the selected question correctly using the unfamiliar schema and prepared tables. Every material claim traces to the relevant snapshot. Insufficient data produces an explicit limitation; an estimate or hypothesis is not presented as an observed fact.

**Owned surface:** Analysis snapshot, dynamic table consumption, findings, and output artifacts. Reuse existing analytical tools where their contracts fit.

## Increment 5 — Repeat the accepted workflow

### Save a reusable, versioned workflow

**S18 · P1 · Work type: implementation · Depends on: S17.**

**Story:** As an application owner, I need the accepted procedure saved, so that future runs do not depend on reconstructing a conversation.

**Tasks:** Package input requirements, connection references, transformations, table definitions, checks, dependencies, outputs, and limits; retain version history; exclude credentials from the package.

**Acceptance and demo:** Load the package in a new permitted execution context and inspect its input/output contract and original source links. A missing dependency receives a clear disposition. The package contains references to secrets, not secret values.

**Owned surface:** Workflow package and versioned execution contract.

### Invoke the workflow manually or from an application

**S19 · P1 · Work type: implementation · Depends on: S18, S06.**

**Story:** As a user or application developer, I need a callable workflow, so that I can repeat accepted work with new authorized inputs.

**Tasks:** Expose stable manual and application entry points; validate input and workflow versions; reuse unchanged accepted results where valid.

**Acceptance and demo:** Invoke the same saved workflow manually and through the application interface. Both return equivalent checked results with run identity. A duplicate invocation cannot duplicate accepted work; an interruption resumes from retained progress.

**Owned surface:** Workflow invocation interfaces and durable execution. Exact interfaces are selected at refinement.

### Invoke from an event or schedule

**S20 · P1 · Work type: implementation · Depends on: S19.**

**Story:** As an operations user, I need event and scheduled invocation, so that recurring work runs within its granted limits without manual repetition.

**Tasks:** Connect one selected event and one bounded schedule; enforce source, expiry, and spending policy at execution time; retain invocation history and clean up the test schedule.

**Acceptance and demo:** An actual short-lived schedule runs when due and not before; a permitted event starts the same workflow. Duplicate events reuse accepted work. Expired authority or exhausted limits prevent new admissions rather than silently bypassing controls.

**Owned surface:** Existing event/scheduler entry points and workflow admission. External delivery requires its own authority.

### Handle changes without losing the last useful answer

**S21 · P1 · Work type: implementation · Depends on: S19.**

**Story:** As a returning user, I need changed data and definitions handled safely, so that an update does not erase useful work or silently corrupt the next answer.

**Tasks:** Detect changed columns, meanings, records, and corrections; create a workflow version or seek material clarification when needed; retain earlier accepted results through failed refreshes.

**Acceptance and demo:** Process a selected source change and show which results were reused or replaced. A materially incompatible schema blocks or repairs the affected step visibly. Failed refresh or interruption preserves the last accepted answer and source history.

**Owned surface:** Change detection, workflow versions, refresh, correction, and stale-result handling.

## Increment 6 — Collect from a permitted source

### Configure a scoped connection

**S22 · P1 · Work type: implementation · Depends on: S18.**

**Story:** As a data owner, I need BackIntel to configure a connection from documentation and scoped access, so that I do not write an extraction routine manually.

**Tasks:** Select one source and collection contract; reuse an existing connector or configure a bounded extraction; keep credentials outside generated code and packages.

**Acceptance and demo:** Configure and check one permitted source. Incorrect or insufficient access produces a clear result. Collection and any transmission remain within source permissions and the agreed data policy.

**Owned surface:** Selected connector configuration, source registration, and connection references. High risk: external access and credentials.

### Collect complete and traceable information

**S23 · P1 · Work type: implementation · Depends on: S22, S13.**

**Story:** As an analyst, I need complete permitted records with source links, so that findings are not based on a silently partial or duplicated collection.

**Tasks:** Fetch the required pages; check completeness and duplicate identities; retain original responses and collection boundaries.

**Acceptance and demo:** The collected snapshot reconciles with an independent expected set. A missing page, interrupted collection, or enforced limit is visible; partial results are not labeled complete. Duplicate records do not inflate the answer.

**Owned surface:** Selected extraction workflow, collection checks, raw snapshots, and lineage.

### Collect incremental changes and refresh the result

**S24 · P1 · Work type: implementation · Depends on: S23, S20, S21.**

**Story:** As an operations user, I need new and changed source records incorporated, so that a recurring answer stays current without unnecessary full recollection.

**Tasks:** Retain collection progress; apply the selected source's update and deletion semantics; invoke the saved workflow and recover an interrupted update.

**Acceptance and demo:** Add and change known records, then show the correct refreshed answer and retained originals. Repeated or interrupted collection does not lose or duplicate accepted records. Failed collection preserves the last useful result and identifies staleness.

**Owned surface:** Incremental extraction, source-change admission, refresh, and recovery for the selected connector.

## Increment 7 — Conditional expansion backlog

Select these stories from demonstrated user needs. They are not a promise to implement every framework, connector, input type, or scale target in one sprint. Each requires a bounded target and owner before it can become Ready.

### Use another agent framework

**S25 · P2 · Work type: implementation · Depends on: S11 and a selected framework/use case.**

**Story:** As an agent developer, I need the same analytical tools in another framework, so that I can adopt BackIntel without replacing my existing agent application.

**Tasks:** Select Agno or OpenAI Agents SDK based on a concrete need; adapt the existing tool contracts; document and run one complete example. Refine the other integration as a separate later instance of this story.

**Acceptance and demo:** The selected framework completes a documented analytical workflow with equivalent evidence, limits, and recovery. An unsupported operation or denied request remains explicit. The working core is reused.

**Owned surface:** One selected framework adapter and its example. No blanket framework replacement is selected.

### Connect a selected business system or database

**S26 · P2 · Work type: implementation · Depends on: S24 and a selected source/use case.**

**Story:** As a business-system owner, I need one useful source connected, so that BackIntel can answer a real operational question from that environment.

**Tasks:** Select one workflow and source, such as SAP, ServiceNow, Snowflake, Databricks, or a database; establish access and data meanings; reuse the collection/preparation contract.

**Acceptance and demo:** The selected connector completes its agreed business workflow, reconciles source totals, and handles missing access or changed inputs. Selection of one connector does not commit delivery of all named systems.

**Owned surface:** One source adapter and its concrete end-to-end workflow. High risk: business-data permissions and meaning.

### Use documents alongside structured information

**S27 · P2 · Work type: implementation · Depends on: S17, S18 and selected document requirements.**

**Story:** As a business user, I need relevant document information included, so that the answer can use evidence that is not already in tables.

**Tasks:** Select supported document types and one task; retain originals and cited passages; connect extracted information to the checked analysis definitions.

**Acceptance and demo:** Complete the selected task with traceable passages and correctly linked facts. Missing text, uncertain interpretation, and hostile document instructions receive explicit handling without altering authority.

**Owned surface:** Selected document ingestion and evidence integration. Supported formats remain to be chosen.

### Process information near its source

**S28 · P2 · Work type: implementation · Depends on: S24 and an agreed on-site/data-movement policy.**

**Story:** As a data owner, I need work performed near sensitive information, so that only permitted data or results leave that environment.

**Tasks:** Define the permitted processing and transmission boundary; configure one on-site worker; retain recoverable jobs and allowed result delivery.

**Acceptance and demo:** Complete one authorized workflow within the agreed boundary. An attempted forbidden transmission is denied. Connection loss retains progress and a clear recovery state. Fully local model reasoning is a separate design decision.

**Owned surface:** Selected on-site execution and permitted data movement. High risk: privacy and remote access.

### Process a larger workload within stated limits

**S29 · P2 · Work type: implementation · Depends on: S19 and an agreed workload/resource target.**

**Story:** As an analyst, I need a larger workload completed within known limits, so that I can judge whether BackIntel fits my data volume.

**Tasks:** Agree representative size and completion targets; measure the existing path; fix the demonstrated capacity constraint while preserving correctness and recovery.

**Acceptance and demo:** Complete the selected workload with checked results and observed time, memory, and cost boundaries. Exceeding a declared limit gives a useful terminal or resumable state instead of a false completion claim.

**Owned surface:** The demonstrated workload constraint and affected execution path. No general scale claim follows from one workload.

### Support multiple users without crossing boundaries

**S30 · P2 · Work type: implementation · Depends on: S19, S04, S05 and an agreed concurrent-user target.**

**Story:** As an application owner, I need multiple users to work safely, so that their data, permissions, jobs, and budgets remain separate.

**Tasks:** Agree the representative concurrency target; exercise distinct roles and source scopes; resolve demonstrated contention while preserving admission and recovery guarantees.

**Acceptance and demo:** Concurrent permitted users complete the selected workflows without cross-user disclosure or overspending. An attempted cross-user access is denied. Report observed capacity rather than inferring it from the current worker configuration.

**Owned surface:** Selected multi-user execution, isolation, and capacity constraints. High risk: access and concurrent financial admission.

### Measure usefulness in an agreed pilot

**S31 · P2 · Work type: research · Depends on: a selected delivered workflow and pilot authority.**

**Story:** As a product owner, I need measured user usefulness, so that release decisions follow observed results rather than activity or assumed savings.

**Tasks:** Select the pilot audience and workflow; agree success targets before collecting results; compare task completion, total human effort, material mistakes, and known operating costs with the existing approach.

**Acceptance and demo:** Present the agreed comparison with limitations and a next product decision. Count checking and correction work as human effort. Unmeasured costs and unsupported value claims remain explicit; a synthetic demonstration cannot substitute for user-value evidence.

**Owned surface:** Authorized pilot design and result report. Outreach and customer messages require explicit authority; none are sent by this plan.

## Shared delivery contract

These defaults apply to every story. Story-specific refinements add only what its outcome and risk require.

**Source and destination:** Parent destination is BackIntel and the numbered increment above. Acceptance sources are the [canonical roadmap](README.md), the relevant [autonomous workflow concept](../research/autonomous-workflow-concept.txt), and the recovered toolkit contract when available. The separate [five-domain goal](analysis-workspace-testing-goal.md) retains its own acceptance and original authority; its blocked Credit case is not automatically a dependency of a two-example alpha.

**Ownership and readiness:** Owner and final integrator are unassigned. The product owner confirms priorities and consequential scope choices. Assign each story a bounded session scope, precise owned files/interfaces, applicable prerequisites, and an independent expected result before Ready. Unselected enterprise sources, document formats, privacy policies, and capacity targets stay in refinement. No sprint dates or point estimates are invented.

**Dependencies and parallel work:** The lists above identify blocked-by relationships; the reverse blocks relationship is every story that lists the current label. Create verified native relations when authorized tracker records exist, retaining textual relationships if native readback is unavailable. No parallel implementation across shared interfaces or overlapping files. Name an integration owner before combining separate work.

**Invariants:** Preserve raw inputs and accepted evidence; enforce permissions and spending limits; do not leak credentials; do not duplicate accepted results or uncertain paid operations; keep synthetic, replayed, and actual execution distinct; do not silently substitute datasets, providers, or evaluation criteria; keep unsupported claims and material uncertainty visible.

**Testing and demo:** Use a bounded permitted input with an independent expected result and the stated negative case. Run the smallest appropriate correctness, workflow, access, cost, recovery, or visual check for the changed behavior; mandatory repository checks still apply. Bind material results to the relevant candidate and inputs. Reuse unchanged evidence only where it remains applicable; rerun affected behavior after a material change. The demo record states the actor, starting state, actual result, limitation, relevant time/cost, and cleanup. Fixtures never establish a required live outcome.

**Implementation delivery:** Resolve exact files after candidate recovery. Use a suitable isolated checkout when needed, the `codex/` branch prefix, one bounded story per PR where practical, and the dependency order above. Record candidate, prerequisite branch, shared-file conflicts, integration owner, and authorized publication steps at refinement. No branch, worktree, PR, tracker record, live call, or publication is created by this document.

**Done and stop:** Done requires the story's stated result, required direct checks, and meaningful demonstration, including applicable human acceptance. Required missing inputs or authority produce a specific blocked disposition; demonstrated failures require a scoped fix. A missing required check is not a pass. Stop when the stated outcome exists and required checks pass; unrelated improvements become separately accepted follow-up work. If publication is part of the story, retain the actual publication result separately from qualification and source merge.

**Scope boundary:** Increments 1–3 qualify the bounded developer alpha. Arbitrary new-source preparation starts in Increment 4. Full five-domain live acceptance, production readiness, and measured customer savings are separate claims and cannot be inherited from alpha qualification.

## Current planning focus

Start by refining **S01: Know what works today** and **S02: Recover and reconcile the existing alpha**. Their owned surfaces can remain separate: documentation/inventory versus candidate recovery. Pull S03 after verified recovery and integration decisions. Do not open every future story at once.

Recovery lead: “Review testing and demo workflows,” chat `01a10eb2-7340-7052-bf28-f16577c3901a`, reported `/workspace/backintel-agent-toolkit-0.1.0a2-candidate.zip`. Current availability and contents remain unverified. The [roadmap source section](README.md#source-decisions-and-supporting-plans) retains the other decision records.
