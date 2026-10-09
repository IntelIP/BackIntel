**BackIntel goal: validate and complete the goal-driven analysis workspace**

Drafted October 3, 2026. This is a proposed execution goal. The budget below applies when the owner assigns the goal for execution; drafting it starts no paid tests.

Execution update, October 4: the owner assigned this goal and authorized all five named datasets for benchmarking and testing. The $10 campaign cap is active. The development source has been recovered into the isolated `codex/backintel-analysis-validation` branch. Dataset downloads, model artifacts, and live analyst execution depend on the cloud environment's network and credential availability. See [the current campaign record](../architecture/analysis-validation-campaign.md) for fresh evidence; the historical handoff below describes the starting state.

**Goal to assign**

Complete and validate BackIntel's goal-driven analysis workspace from the latest saved implementation. Demonstrate that a user can admit permitted data, save a business question, receive a correct source-backed analysis, compare eligible predictors, ask a follow-up, and receive an updated result after a source change. Work must survive interruption, enforce roles and spending limits, and retain inspectable evidence. Deliver reviewable implementation commits, a reproducible operator runbook, and an acceptance report identifying what passed, failed, and remains blocked.

Execute the phases below in dependency order. Fix demonstrated defects and rerun the affected checks. Continue independent work when one dataset or service is blocked. Full five-domain acceptance requires evidence for commerce, support, maintenance, credit, and churn. A verified three-domain candidate is useful progress, but does not complete that five-domain goal.

**Starting evidence and scope**

- The latest handoff reports five adapters, a hosted GPT analyst, local Decide interpretation, CatBoost/TabICLv2 comparisons, durable jobs, protected APIs, and React.
- Commerce, support, and maintenance reportedly passed real-model comparisons and nine known-answer questions in total. Build, functional, security, and rendered checks reportedly passed. Reuse those receipts only where their candidate, inputs, configuration, and tested behavior match the new run.
- Credit/Home Credit and churn/Telco source-use confirmations remain outstanding. Public availability and the repository's MIT license do not establish dataset-use permission.
- The newest enhancement was saved as uncommitted work in `/Users/hudson/Documents/GitHub/BackIntel`. This cloud checkout is the older PoC at `2330c70`. Recover and verify the newer implementation before treating this checkout as the enhancement.
- Relevant handoff files are `docs/architecture/analysis-workspace-runbook.md`, `docs/architecture/analysis-acceptance.md`, `docs/architecture/goal-driven-analysis.md`, and `docs/architecture/current-system.md` in the newer working copy. Their contents have not been verified in this cloud checkout.
- Preserve the installed Olist runtime and its private data. Use isolated test databases, queues, ports, and output directories. The enhancement uses Decide for interpretation; preserve existing Jev behavior with regression checks rather than adding a new Jev benchmark to this goal.

**Execution authority when this goal is assigned**

Local implementation edits, necessary project-local dependency setup, isolated test infrastructure, regression fixes, and local commits are in scope. Use the existing approved sources and attached environment. Paid requests must use the approved analyst provider/model and the campaign limits below. Additional datasets still require their source terms to be confirmed. Do not alter machine-wide Docker settings or replace an existing service to make a test pass.

Release tags, package publication, production deployment, new paid cloud infrastructure, repository publication/push, and messages to customers or other people require separately established authorization. Prepare the local review result first. Internal application notifications are part of the test workflow; external delivery is outside this campaign.

**Testing framework**

| Layer | Framework and execution | What its evidence establishes |
| --- | --- | --- |
| Backend unit and contracts | Keep the existing Python test runner; the current PoC uses `unittest`. Add focused fixtures and parameterized cases using established project conventions. | Isolated business rules, schemas, numeric checks, permissions, and budget decisions. |
| React components | Use the enhancement's existing runner; if absent, introduce Vitest and React Testing Library in the frontend. | Forms, accessible states, validation, loading, errors, evidence controls, and role-dependent actions. |
| Integration | Real disposable PostgreSQL, Redis, Aegra/LangGraph, and HTTP APIs; replace only the hosted model boundary with a deterministic adapter. | Persistence, migrations, worker behavior, authorization, scheduling, and accounting across actual services. |
| Simulation | Small synthetic datasets, fixed seeds, explicit model fixtures, controllable clocks, and fault injection. | Repeatable workflow behavior and failure handling under known inputs. |
| Real data and local models | Permitted frozen datasets, pinned Decide/CatBoost/TabICLv2 versions, chronological or entity-separated evaluation, independent answer oracles. | Data correctness and measured model behavior within the evaluated sample. |
| Browser end-to-end | Playwright driving React through the normal API, real workers, actual local models, and bounded real hosted analyst calls. | The complete user journey through the running product. |
| Candidate validation | Extend the existing Node validation runner and manifest to require the relevant evidence above. Update schema/runner support together if new validator categories are needed. | One identified clean candidate satisfies the declared campaign checks. |

Give tests explicit groups such as `unit`, `integration`, `simulation`, `local_models`, `e2e_offline`, `e2e_paid`, and `recovery`. Keep paid execution behind an explicit entrypoint and approved campaign record. Ordinary unit, pull-request, and offline integration jobs must not discover a provider credential and make paid calls automatically.

Use `passed`, `failed`, and `blocked` as distinct outcomes. An unavailable dependency is blocked. A demonstrated contract violation is failed. An optional skip must retain its reason and must not satisfy a required gate. Label every receipt with its data type and model execution mode: synthetic, recorded replay, or live. A real model on synthetic data remains a synthetic-data test.

**Phase 0 — Recover the candidate and freeze the acceptance contract**

Inventory the latest working copy, its branch and base commit, local changes, running services, datasets, model files, and existing evidence. Preserve unrelated work. Capture an implementation snapshot or local commit so the recovered enhancement has an identity. Transfer only source and permitted configuration to another environment; keep raw licensed datasets, credentials, and restricted model artifacts outside Git. If the latest source cannot be obtained, report that dependency and complete independent planning rather than recreating it from the old PoC.

Map each required behavior to a test and evidence artifact. Record source permission, file fingerprints, schema, units, time cutoff, eligibility, role, model versions, prompt/question versions, dependency versions, and budgets. Before running comparisons, freeze the evaluation split, baseline, metrics, numeric tolerances, and activation rule.

Prepare at least ten frozen answer cases per available domain, covering totals, filters, rankings, missingness, and time boundaries, plus five negative/ambiguous cases covering unavailable information, invented numbers, unsupported claims, insufficient evidence, and hostile source text. Derive expected answers independently from raw input or a separately reviewed query; do not import the application helper being tested as the oracle. Select representative cases for repeat live runs before inspecting results.

**Gate:** the actual enhancement is recovered; the test matrix and campaign budget are recorded; source permissions are explicit; every critical acceptance behavior has a planned test. Credit and churn retain blocked source entries until confirmed.

**Phase 1 — Unit, component, and contract checks**

Test adapter schemas, malformed records, duplicate identities, nulls, units, date parsing, and source lineage. Protect train/test engine identities and chronological boundaries. Test that outcomes and future corrections cannot enter earlier feature inputs.

Test the analyst's permitted tools, structured outputs, evidence requirements, refusal/abstention, and bounded tool loops. Regress the invented-number defect: numerical claims need unit-aware absolute/relative tolerances and explicit rounding rules, with wrong-but-nearby values rejected. Accept valid wording variation while checking facts and citations.

Test budget reservation, settlement, rejection, unknown charge handling, cancellation, and retries. Test role permissions and goal reconfirmation after material budget or policy changes. Test React source setup, goal editing, follow-ups, loading, blocked and failed states, evidence inspection, and retention of the last completed answer after a failed refresh.

Use coverage to find gaps. Require normal and failure branches for money, permissions, lineage, and replay safety; a broad coverage percentage alone is not acceptance.

**Gate:** all required unit/component checks pass, each fixed defect has a meaningful regression case, and this layer makes no paid requests.

**Phase 2 — Integration against actual services**

Run migrations in a fresh disposable test database. Exercise the real HTTP API, database, broker, worker, and scheduler with a deterministic hosted-model adapter. Check role boundaries, allowed queries/tools, accepted evidence, durable job admission, receipt retrieval, and source correction propagation.

Submit work and disconnect the client; verify that accepted jobs continue and results remain retrievable. Deliver duplicate work and repeat submissions; verify one accepted result and no duplicated ledger effects. Run concurrent admissions against a nearly exhausted budget to prove the cap cannot be exceeded by a race. Bound scheduler discovery and verify the actual Aegra cron routes used by the implementation.

**Gate:** cross-service contracts pass on an isolated environment; one documented setup/start/check procedure works twice; no test depends on the demonstration database or manual table repair.

**Phase 3 — Simulated end-to-end scenarios**

Run the normal user/API flow with small synthetic inputs and deterministic provider fixtures. Cover first import, saved goal, analysis, prediction comparison, evidence review, follow-up, source arrival, correction, threshold crossing, acknowledgment, stale data, recovery, and clearing an attention condition. Changing a clock or due timestamp belongs to this simulated layer and must be recorded as such.

Inject schema errors, missing data, model refusal, malformed output, timeout, worker loss, broker loss, partial completion, expired authorization, and budget exhaustion. Confirm bounded retries, partial resume, preserved completed results, and useful failed/blocked states. Verify that the system does not claim a new result when processing failed.

**Gate:** the scenario matrix passes reproducibly with explicit simulation labels and zero paid-provider spend. These results establish plumbing and failure behavior, not real analyst quality or native-clock scheduling.

**Phase 4 — Real-data correctness and local-model evaluation**

Start with the three permitted domains. Reconcile source totals, join grain, missingness, duplicates, identities, eligible populations, and lineage. Independently recompute the frozen answer cases. Confirm zero/missing/empty distinctions, ranking direction, and correct denominators. Run Decide on actual permitted text and CatBoost/TabICLv2 on eligible structured inputs.

Compare a simple baseline, facts-only predictors, and facts-plus-Decide predictors on the same frozen evaluation cases. Use classification or regression metrics appropriate to the target, disclose class balance and sample size, and report resource use and uncertainty. Keep development/tuning records separate from the final holdout. Freeze repeated-run seeds where supported; use tolerances for valid numerical variation.

Do not require Decide features or a sophisticated predictor to win. Report mixed results and support an explicit baseline/no-predictor decision when the activation rule is not met. Correct answers and valid evidence are required even when prediction adds no value. Nine earlier answer checks are smoke evidence, not broad accuracy evidence.

**Gate:** data and known-answer checks pass, prediction choices follow the frozen rule, and the evidence states the evaluated population and limitations. Add credit/churn only after their permissions and inputs are available.

**Phase 5 — Bounded real end-to-end user journeys**

First price and reserve a small live smoke run. Then execute each required journey through the running browser interface and normal API. Use the actual hosted GPT analyst, actual local interpretation/predictors where required, actual services, and a new traceable campaign identity. Replaying a previous provider response is a separate replay test.

For each eligible domain demonstrate this sequence: source admission; saved goal and confirmed limits; real analysis; evidence inspection; eligible model comparison; follow-up; new source/correction; refreshed answer; and an internal attention event when the declared rule is met. Verify the evidence links against the selected source and cutoff rather than merely checking that links exist.

Use an actual short-lived native-clock schedule for at least one refresh. Verify due/not-yet-due behavior through the implemented scheduler. Bound the schedule and remove it at completion. Run representative operator, manager, and read-only browser journeys on desktop and mobile, including keyboard evidence access, long labels, loading, empty/error states, and denied actions. Repeat the preselected live cases within budget to expose variation; assess factual/evidence invariants rather than exact prose.

**Gate:** each required domain has a complete browser-to-worker-to-model-to-result receipt, independently checked answers, real scheduling evidence, and reconciled provider usage. All required cases must be tested; if the approved budget cannot cover the matrix, report a blocked gate rather than silently shrinking it.

**Phase 6 — Recovery, security, and operating limits**

Restart a worker during pending work; resume a partial analysis; cancel pending work; restore the application's evidence into a fresh isolated database; and verify accepted results and original provider identifiers after replay. A recovery that reuses accepted observations should make zero additional paid requests. Any deliberately new request still needs a reservation within the same campaign.

Verify cross-role/task access denial, query/tool restrictions, unsafe source-text handling, secret redaction, token expiry, and notification limits. Exercise budget exhaustion, concurrent reservations, unknown billing, retry limits, and expiry through actual enforcement paths. Confirm that cancellation or a spend stop prevents new admissions and accounts for already admitted work.

Capture runtime, memory peak, CPU use, model-load time, disk/output growth, and cleanup outcomes. Run local model stages sequentially on constrained hosts; start with two CPU threads and explicit per-process/container limits fitted to observed capacity. Do not silently substitute a paid remote model after a local resource failure. Remove this campaign's temporary databases, services, schedules, and credentials after preserving permitted evidence.

**Gate:** critical recovery and authorization cases pass, no unresolved high-impact correctness/security defect remains, provider accounting is reconciled, and the bounded run leaves a documented cleanup state.

**Phase 7 — Validate one clean candidate and hand it off**

Commit the fixes and final test definitions locally. Validate the resulting clean commit with pinned dependencies and the same data/model/configuration fingerprints. Run the relevant suite once from a fresh checkout or clean test environment. Reuse earlier expensive evidence only when its identified source/configuration and execution code remain unchanged; record the relevance decision. Rerun affected live cases when behavior changes. Working-tree evidence cannot be relabeled as a different commit's result.

Configure CI to run unit, component, integration, simulation, and applicable offline browser tests automatically. Keep paid-provider campaigns manually dispatched with the approved budget, credentials, concurrency limits, and durable evidence upload. A locally prepared CI workflow is not a hosted CI pass; hosted execution and pushes follow established repository authorization. Check the final candidate and its hosted status when available.

Deliver the test matrix, machine-readable summary, acceptance report, runbook, model comparison, provider ledger, resource report, browser traces/screenshots, recovery/cleanup receipts, and local commit identifiers. Make instructions runnable from a clean environment; identify private inputs and separately approved models required for live reproduction.

**Gate:** the clean candidate passes the required matrix and has reproducible evidence. Five-domain acceptance is `passed` only when all five domains and cross-cutting gates pass. Otherwise give a precise failed/blocked disposition with the independently verified domain results and the smallest remaining dependency.

**Proposed campaign budget and run limits**

Recommended cap: **$10 USD of new paid-provider spend for this entire campaign**, covering all domains, calls, retries, failed attempts, and repair reruns together. The owner can replace this amount before assigning the goal. Prior reported provider charges of $0.04626 are historical and must be verified separately; do not reuse their allowance as new authority.

| Allocation | Maximum new provider spend |
| --- | ---: |
| Preflight and live smoke | $1.00 |
| Required live acceptance journeys | $6.00 |
| Recovery checks and affected-case repair reruns | $2.00 |
| Contingency within the same hard cap | $1.00 |
| **Total** | **$10.00** |

These are spending limits, not a quoted completion cost. Before dispatch, estimate cost from the approved provider's current prices, token/request limits, and the frozen case matrix. If the matrix cannot fit, make that concrete before spending. Phase allocations can be reassigned with a recorded reason inside the same approved total; contingency does not increase the cap.

- Paid execution stays disabled until this goal is explicitly assigned with its nonzero budget and approved model scope. Offline phases may proceed under their ordinary local execution authority.
- Enforce a maximum of 200 paid attempts, one concurrent paid request initially, at most six model requests per investigation, at most $0.25 reserved per request, and at most $1.00 per individual live journey. These are additional bounds; the $10 campaign limit still applies first.
- Price the maximum possible request cost and persist its reservation atomically before dispatch. Enforce input/output token limits. Known charges plus all pending or uncertain reservations must remain within the campaign cap. Settlement replaces a reservation; it is not added to the same reservation twice.
- Count failed requests, permitted retries, and interrupted calls. Allow at most one retry for a classified transient error when the provider semantics prevent an ambiguous duplicate charge and budget remains. Do not retry an ambiguously billed request blindly; reconcile it first.
- Retain call identity, task/source scope, model, price basis, tokens, reserved maximum, actual charge or uncertainty, timestamps, outcome, and settlement. Do not log secrets or unnecessary source text. At 80% usage, report remaining required cases and preserve funds for completion/recovery.
- Stop admitting paid work when a cap, expiry, unresolved billing ambiguity, or source/permission limit is reached. Preserve receipts and a resumable handoff. Continue useful independent offline work; expanding a budget requires the owner to approve a new limit.
- Set bounded job deadlines: initially 15 minutes per integration/browser journey, 60 minutes per local-model batch, and 30 minutes per recovery scenario. Tune locally before paid execution and document the limits. A timeout is a failure/blocker with evidence, not permission for an unbounded retry.
- Use existing local/attached infrastructure. The $10 allowance does not cover new rented compute or deployment. Report measured resource use and any known attached-environment charges separately. Distinguish measured provider charges from estimated/unpriced compute and human review; unknown total operating cost must not be reported as zero.

**Evidence record and reporting**

For each test retain: campaign/test identity; candidate commit or working-tree fingerprint; dependency, image, model, prompt, and configuration versions; permitted source fingerprint and cutoff; execution mode; roles; expected result and its independent oracle; observed outcome; timing; resource use; provider ledger references; relevant trace/artifact paths; cleanup state; and failure/blocker reason. Keep private data and sensitive receipts outside the public repository and produce a safe review summary.

After each phase report the gate result, demonstrated changes, outstanding dependencies, measured spend, unsettled reservations, and next useful action. Recheck only affected evidence after a repair; do not repeatedly rerun a passing expensive campaign without a new defect or changed behavior. Save a handoff before session limits or an infrastructure interruption.

**Definition of done**

All required domains and cross-cutting checks pass on the identified candidate; real execution and simulation evidence remain distinguishable; numerical answers and cited evidence reconcile; predictor decisions follow the frozen evaluation; browser workflows, native-clock refresh, durable recovery, permissions, and budget enforcement pass; provider spend is reconciled within the cap; and the clean-environment runbook, reviewable commits, and safe evidence bundle are delivered.

Claims of customer accuracy, employee time savings, commercial readiness, or fully measured operating cost require their own evidence. This campaign proves the declared analysis-workspace behaviors within its data and test scope.
