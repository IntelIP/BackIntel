# BackIntel repository recovery and first integrated PoC

Date: 2026-09-26. Status: consolidation, integrated runtime transition, and scoped deletion complete; required total-cost acceptance remains blocked.

Current checkout: `/Users/hudson/Documents/GitHub/BackIntel`. Main now includes the complete implementation chain and preserved design work. The inventory below records the pre-recovery state; use the [maintained repository map](../architecture/repository-map.md) for current source ownership. Original design changes were committed on `recovery/design-preservation`; an independent working-file copy and Git bundle are retained under `~/Library/Application Support/BackIntel/Recovery/20260926T170122`.

## Current recovery result

The user approved the explicit local switch-and-delete scope. The maintained backend is `/Users/hudson/Documents/GitHub/BackIntel`; the separate website is preserved. All eight historical worktree folders and their `bint*` branch references were deleted after confirming clean state, preserved commit ancestry, credential access, and lack of application/container dependencies. Generated Python caches, redundant local validation outputs, stale Graphify indexes, and the superseded Docker image were removed. Required historical evidence and the old runtime image archive remain in the single recovery set.

The installed runtime candidate is `741773df289866437b067c306d6fefea1b415691`. All three Compose services now identify the canonical checkout and retain the original PostgreSQL/Redis volumes. Fresh recorded-data processing completed after client disconnect. Its report is byte-identical to the independently checked and visually validated report. A graceful container restart preserved accepted output; replay reused the artifacts. Observation, usage-event, and accepted-partition counts were unchanged. No new provider calls occurred, and the running service has no provider credential enabled. This is not a hard-crash recovery or model-quality claim.

Evidence is under `~/Library/Application Support/BackIntel/Evidence/PoCRecovery`: `canonical-runtime.json`, `cutover-acceptance.json`, `cleanup-receipt.json`, and the original exact-candidate validation. Live report/receipt output is under sibling `PoCReports`. The coordinated recovery set is under `~/Library/Application Support/BackIntel/Recovery/20260926T170122/runtime-cutover`; it includes the Git bundle, application/checkpoint database dumps, Redis volume snapshot, and previous runtime image archive. Credentials are preserved in macOS Keychain; README documents the non-secret service names and startup commands.

Required total-cost acceptance remains blocked: the earlier input `100` has no confirmed unit, and local-compute pricing and actual human-review time remain unknown. Technical operation and cleanup do not depend on resolving that accounting input. Full v0.1.0 release acceptance remains outside this bounded milestone.

The post-cleanup workspace audit still reports 22 issues outside the approved BackIntel scope: unrelated folder naming, Tabellio worktree registrations, and obsolete paths in generated IntelIP output. Those projects were left unchanged. The bounded audit log is retained as `PoCRecovery/workspace-audit.log`; this is not a claim that the whole workspace is clean.

The inventory and diagnosis below record the initial state, not the current folder layout.

## Outcome

Give a Marketplace Seller Performance Analyst one maintained local checkout and one reproducible workflow: load approved Olist facts, submit a bounded review batch, finish processing in the background, compare accepted semantic observations, and inspect a source-linked seller/category review with explicit coverage, unknowns, and costs.

Use the existing [historical immediate execution goal](capability-reference.md#immediate-execution-goal--finish-sprint-1). This is the first integrated PoC milestone, not completion of the roadmap's full v0.1.0 release. Prediction experiments, generated-code sandboxes, and a permanent dashboard retain their later gates.

## Pre-recovery repository inventory

Eight sibling directories are linked worktrees of one local backend repository. They are a linear development history, not eight separate services. All eight implementation worktrees were clean when inspected. Main contains modified and untracked design work. No backend Git remote or branch upstream is configured.

| Checkout under `/Users/hudson/Documents/GitHub` | Branch / head | Role |
| --- | --- | --- |
| `backintelligence` | `main` / `caa7bee` | Canonical Git repository; initial research commit plus uncommitted research, architecture, roadmap, and ignore changes |
| `BackIntelValidation` | `bint2-validation` / `acd6ac1` | Validation bootstrap |
| `BackIntelOlistProfile` | `bint3-olist-source-profile` / `aadc1f1` | Approved Olist source profile |
| `BackIntelRelationalFacts` | `bint4-olist-relational-facts` / `b121eb7` | PostgreSQL facts, reconciliation, lineage |
| `BackIntelMonthlyReport` | `bint5-monthly-seller-report` / `82db5fe` | Historical monthly calculations and HTML/JSON report |
| `BackIntelBackgroundRuntime` | `bint6-background-runtime` / `e5cca47` | Aegra/LangGraph runtime proof |
| `BackIntelReplaySafe` | `bint7-replay-safe` / `1440c64` | Partition admission and result ledger |
| `BackIntelCostLedger` | `bint9-cost-ledger` / `053b249` | Usage and known-cost events |
| `BackIntelSemanticEvidence` | `bint9-jev-measurement` / `39b86c9` | Latest cumulative implementation, Jev observations and signal comparisons |

`IntelIP/BackIntelWebsite` is a separate dirty website checkout on `feat/backintel-landing`, with a local PortfolioSiteTemplate origin. Preserve its independent ownership; backend consolidation does not imply website integration.

The live Compose runtime identifies `BackIntelSemanticEvidence` as its working directory. Its runtime, PostgreSQL, and Redis containers are healthy; `http://127.0.0.1:2026/health` reports database, checkpointer, and store connected. Health does not prove the complete PoC workflow or exact image/source identity.

## Why the map is misleading

Graphify was queried for graph statistics, central nodes, and neighboring relationships. Its 70-node, 126-edge graph is built at `caa7beecd3ac399e7f9a1a93174142ed2094d429`; source nodes cover five research files with old root-relative paths. It does not map the implementation now at `39b86c98d0754711eeb1e956c2bcfa61f2d8d715`.

Main never received the cumulative implementation. Each sequential ticket retained another visible worktree. Important design decisions are uncommitted on main, while runtime code and external evidence live elsewhere. The latest implementation has no tracked root README providing a complete startup/demo path.

## Implemented and observed state

| Surface | Evidence and limit |
| --- | --- |
| Olist facts and monthly report | Existing independent check records `passed`, 22 metric rows and 10 source examples. This is historical evidence for that report candidate, not a fresh validation of the latest integrated system. |
| Durable execution | Live runtime is healthy. Existing fault-matrix evidence is tied to `1440c64`; it includes a pending cancellation retest. Do not promote all recovery claims to the latest candidate. |
| Real Jev integration | Saved OpenRouter evidence records two accepted batches, five reviews each, ten successful model calls. Labels await human adjudication; samples do not establish representative trends or model accuracy. No inference was invoked during this analysis. |
| Cost | Saved measured provider charges total `$0.000296142`. Local compute and human-review costs remain unpriced; total-cost status is unknown. |
| Latest validation | Existing exact-commit evidence at `39b86c9` reports six required validators passed. These cover contract/schema checks, facts tests, and offline Jev tests; they do not establish integrated workflow, live quality, UI acceptance, or complete cost/recovery readiness. |
| Presentation | Report renderer produces HTML/JSON. Saved Reflex prototype evidence is blocked for an uncommitted candidate and explicitly lacks human acceptance. Current implementation must not inherit that prototype's readiness claims. |

## Prioritized fixes

1. **Restore one integration home.** Preserve main's design changes and the complete commit chain, then integrate the existing latest implementation. Reconcile changed design files rather than overwriting them. Proposed canonical backend name: `BackIntel`; rename only after checking path consumers and coordinating the live runtime. Keep website separate.
2. **Connect the existing workflow.** `aegra.json` exposes a synthetic partition graph and a separate real-review enrichment graph. `runtime/review_graph.py` already builds and compares semantic snapshots. `scripts/data/seller_review.py` independently renders fact-based reports and does not consume those semantic snapshots. Add the smallest orchestration/result contract that produces one inspectable changed finding and its evidence.
3. **Fix ambiguous category attribution.** `runtime/signals.py:59-63` excludes null categories before counting categories; `:81-82` then attributes a review when one known category remains. An order containing a known category plus an unknown category can therefore appear unambiguous. Preserve unknowns and align semantic grouping with the facts/report attribution contract. This is confirmed source behavior; incidence in the current dataset was not measured.
4. **Make setup reproducible.** `runtime/bootstrap.py:12` assumes the application database and base facts schema already exist, applying only migrations 0002–0005. Document and compose the actual provisioning, migration, loading, and run steps without adding a second runtime. Fresh setup must use an isolated local database and must not overwrite the current demonstration data.
5. **Validate the actual integrated candidate.** The current manifest runs facts and Jev unit tests but omits the existing cost and replay test suites and does not require an end-to-end run. Add focused checks for the integrated flow, category ambiguity, replay, cancellation/restart, and evidence/cost disposition. Keep required unknowns blocked.

## Options and recommendation

| Option | Consequence |
| --- | --- |
| Consolidate the cumulative branch into the canonical backend | Recommended. Retains existing functionality and commit history; requires preserving dirty design work and coordinating runtime paths. |
| Keep latest worktree as the permanent home | Less immediate movement, but leaves canonical main, research, and navigation split unless separately reconciled. |
| Rebuild as multiple services or start a new repository | Adds integration and migration work without evidence of a PoC need. Not recommended. |

Keep existing Python, PostgreSQL, Aegra/LangGraph, and report renderer. Introduce no new service, agent framework, frontend framework, or generic orchestration layer for this milestone.

## Three sequential work packages

Only one package starts at a time. Each owns a focused session; unresolved dependency work blocks the next package.

| Package | Outcome and acceptance | Dependencies / forbidden outcomes |
| --- | --- | --- |
| 1. Recover and consolidate | One canonical integration checkout contains all eight implementation commits plus reconciled design work; README explains source, startup, demo, and evidence paths; maintained repo map points at actual code. Recheck tracked and ignored files, worktree ownership, and runtime path references before moving anything. | Preserve dirty files, local commits, active runtime, and separate website. Reuse an available checkout. No new ticket-per-worktree chain. |
| 2. Complete the first demo loop | One documented command/workflow submits a bounded approved Olist review batch, finishes after client disconnect, compares prior/current accepted signals, and renders one source-linked change with counts, coverage, ambiguity, and interpretation limits. Category-attribution regression passes. | Package 1; stable input/result contract. Reuse recorded real observations with explicit provenance where possible; fixtures must remain labelled. New live inference needs explicit provider/budget authority. |
| 3. Verify and simplify | Exact integrated commit passes the required direct checks; replay creates no duplicate accepted result; a bounded restart/cancellation check has a terminal disposition; report claim traces to source and semantic versions; required cost telemetry is known or blocks the relevant acceptance. | Package 2. Retire redundant worktrees only after preserving work, checking processes, and satisfying worktree lifecycle/approval rules. Current local commits have no remote backup, and active runtime checkout is protected. |

## Done and stop conditions

The goal is complete when a single maintained backend checkout and its documented local workflow reproduce the bounded source-to-background-job-to-changed-review loop, required validation passes on its exact candidate, and remaining folders have an explicit retained or safely retired disposition.

Stop for a material source/attribution conflict, missing authority for a required paid call or infrastructure change, unrecoverable local work, or a failed required check. Unknown required cost stays blocked. A healthy server, passing unit tests, generated screenshots, and ten successful calls cannot individually establish completion.

The full release still separately requires adjudicated semantic quality, a measured human baseline, conditional predictor work, stakeholder acceptance, and its other approved roadmap gates. Do not describe this PoC milestone as those outcomes.

## Authority

The user approved local implementation, runtime transition, credential preservation, and the explicit scoped deletion plan. Those local actions are complete. Paid inference, publication, remote deployment, Plane writes, unrelated-project cleanup, and external messages remain separately gated.

## Evidence locators

- Git: `git worktree list --porcelain`, `codex-repo-snapshot`, per-checkout status/remotes, and `git log --all` inspected on 2026-09-26.
- Current implementation: [runtime graph](/Users/hudson/Documents/GitHub/BackIntel/runtime/graph.py), [review graph](/Users/hudson/Documents/GitHub/BackIntel/runtime/review_graph.py), [signals](/Users/hudson/Documents/GitHub/BackIntel/runtime/signals.py), [report](/Users/hudson/Documents/GitHub/BackIntel/scripts/data/seller_review.py), [validation manifest](/Users/hudson/Documents/GitHub/BackIntel/tabellio.validation.json).
- [Integrated runtime acceptance](</Users/hudson/Library/Application Support/BackIntel/Evidence/PoCRecovery/cutover-acceptance.json>) and [cleanup receipt](</Users/hudson/Library/Application Support/BackIntel/Evidence/PoCRecovery/cleanup-receipt.json>).
- [Historical pre-integration exact-commit evidence](</Users/hudson/Library/Application Support/BackIntel/Evidence/BINT10/exact-39b86c98d0754711eeb1e956c2bcfa61f2d8d715/evidence.json>).
- [Report independent check](</Users/hudson/Library/Application Support/BackIntel/Evidence/BINT5/independent-check.json>).
- [Real Jev comparison](</Users/hudson/Library/Application Support/BackIntel/Evidence/OpenRouterJev/real-jev-batch-comparison.json>) and [cost summary](</Users/hudson/Library/Application Support/BackIntel/Evidence/OpenRouterJev/cost-summary.json>).
- [Historical fault matrix](</Users/hudson/Library/Application Support/BackIntel/Evidence/BINT8/exact-1440c64e15647a1208d73554157adbcdf207c6cd-fault-matrix.json>) and [Reflex prototype limits](</Users/hudson/Library/Application Support/BackIntel/Evidence/ReflexPilot/prototype-observation.json>).
