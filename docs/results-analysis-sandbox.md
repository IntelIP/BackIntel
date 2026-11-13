# Analysis sandbox implementation results

## Reproducible evaluation package — 2026-11-13 UTC

The expanded four-case runner, source builders, independent graders and original two-case
recovery demonstration are now packaged with their tests and specifications. Current setup
and opt-in commands use SmolVM; historical Docker evidence below remains unchanged.

An isolated checkout of the staged package installed from the frozen Python 3.12 lockfile
and passed 187 tests (15 optional skips). The documented four-case command then passed all
four scripted cases through the actual graph and SmolVM, with three exported report bundles,
zero provider calls and 53.982 seconds of summed trial latency. This is integration evidence,
not a new live Sol score. Its retained output is
`data/output/analysis-suite-20261113T044202200578Z/`.

The runtime-evidence verification also passed all six existing stores with 99,441 orders
per store, accepted valid evidence and rejected a broken second evidence item. File evidence
executed in SmolVM. Source data was not reloaded, no model was called and the original service
state was restored. See `results/runtime-validation-smoke.json`.

The case inputs, independent numerical references, tolerances and grading rules are unchanged.
Prompt/refusal refinements and their measured candidate results are separate work; these
packaging checks do not establish reliability or close the version acceptance gate.

Date: 2026-11-11 America/New_York (run identifiers use 2026-11-12 UTC).
Project: BackIntel, experimental v0.0.1. Working branch: `codex/backintel-v2`.
The runtime and Sol default were merged into `main` by [PR #4](https://github.com/IntelIP/BackIntel/pull/4)
as `dfd8c90` on 2026-11-12 UTC. Hosted PR and post-merge CI passed. The expanded evaluation
scripts, detailed evidence documents and v0.0.1 metadata reset remain local pending changes;
this is not a versioned production release. Earlier sections below are dated checkpoints.
The current local runtime is SmolVM; see the [migration receipt](#smolvm-migration--2026-11-12-utc).
The [four-case Sol rerun](#live-sol-on-smolvm--2026-11-12-utc) passed three of four cases;
the energy case exposed a structured-completion/export failure. The subsequent
[targeted energy fix and rerun](#energy-completion-fix-and-live-rerun--2026-11-12-utc)
passed and delivered its bundle. The other three cases have not been rerun on this candidate.

## Delivered behavior

The opt-in Deep Agents specialist receives a structured business brief and assigned source,
uses persistent SmolVM shell/Python execution, and emits a reproducible report specification.
The historical measurements below used Docker unless explicitly marked SmolVM.
A separate clean renderer produces HTML, offline Plotly charts, PNG/SVG, CSV and XLSX from
that specification. The original benchmark analyst remains separate; automatic delegation
is disabled. See [runtime and commands](analysis-sandbox.md),
[environment](sandbox-environment.md), [artifact contract](analysis-artifacts.md), and
[model research](analysis-model-selection.md).

The image includes Python 3.12.16, the existing analytical/database packages, Matplotlib
3.11.2, Plotly 7.1.0, openpyxl 3.1.5 and shell utilities. Dependency hashes and installed OS
versions are recorded. Tested binary wheels require no runtime compiler or downloads.
Ordinary/large profiles allow 2 GiB/2 CPUs and 4 GiB/3 CPUs respectively. These are ceilings,
not reservations of currently idle capacity. Large concurrent scheduling is not implemented.

## Direct checks

| Check | Observed result |
| --- | --- |
| Final ordinary Python suite | 118 passed, 11 optional tests skipped |
| Real Docker isolation/resource suite | 6 passed; read-only sources/root, blocked public network, assigned peers, quotas, cancellation, recovery and export |
| Renderer tests with plotting dependencies present | 14 passed; five chart families, CSV/XLSX consistency, malformed data, bounded output, text injection and integrity checks |
| Final scripted graph/demo | Both report and missing-cost cases passed; 12 delivered files, independent numbers, error recovery, image-tool delivery and source unchanged |
| Deliberately wrong numerical control | Rejected despite structurally consistent output |
| Browser rendering | Report and inline Plotly SVG rendered offline in fresh headless Chromium; screenshots inspected for readable labels and values |
| Static checks | Ruff lint/format, Vulture, lock validation and diff whitespace passed |
| Candidate-file secrets check | Gitleaks: no leaks across 135 tracked/non-ignored files; ignored local data and virtualenv excluded, matching checkout scope |

The optional checks overlap the ordinary suite; these counts must not be added together.
The browser check establishes rendered output, not an exhaustive interaction/accessibility
assessment. Workbook cells were opened and compared with openpyxl; no formula recalculation
is needed because this contract writes values and escaped text, not formulas.

The controlled streaming check read all 335,216,663 bytes of a 327,680-row synthetic CSV
under a 256 MiB container limit in about 2.2 seconds, yielding independently known totals.
Cache contributes to cgroup memory and reached that ceiling. This is one infrastructure
workload, not a >=10 GiB or unknown-domain model benchmark.

## Reproducible local evidence

Run `uv run python scripts/run_analysis_demo.py` after building the image.
[The task specification](../evals/analysis/Task.md) defines the fixture and independent oracle.
The final run is `data/output/analysis-demo-20261112T003324883000Z/`:

- `evaluation.json`: all checks, zero provider calls and zero inference cost.
- `report-run/run.json` and `missing-cost-run/run.json`: graph trajectories and identities.
- `report-run/artifacts/report/report.html`: delivered report; `supporting.xlsx`: workbook.
- `manifest.json` beside the report: MIME types, sizes and checksums of the delivered files.

Final image: `sha256:9820b507a21f383ad0af1fac20426a6123ef718df79e35740461ab3ff3087dac`.
The last image rebuild changed only documentation formatting; the sandbox and renderer
suites used predecessor `sha256:fd8018fb3ec973213419a79c62d1a26aeefaa65a6547fa4785317dad15c3e98e`.
The final full demo used the new image and the failed-revision publication fix.
It completed in 9.439 seconds with 140,042,240 bytes (about 134 MiB) peak analyst memory.
This is a single measured run under local contention, not a latency service guarantee.

The earlier successful demo `analysis-demo-20261112T002924589208Z` retains the browser
screenshots under `browser-check/`. Two earlier unsuccessful attempts also remain, recording
the graph-recursion and image/helper mismatch defects repaired during integration.
Source datasets and raw run artifacts are intentionally excluded from Git. The tracked
fixture builder and task reproduce them; local paths are not published artifact links.

## Remaining acceptance

No paid model call, new LangSmith experiment, fine-tuning, commit, push or deployment occurred.
The two-case live LangSmith entry is implemented with serial execution, explicit spend/call
limits, independent grading, frozen references and full failure records. Its provider path
has offline request-shape checks but still needs live acceptance. The proposed broader
sixteen-run model comparison is a plan, not an executed or fully implemented benchmark suite.

Model/endpoint qualification and the owner's new $3 inference allowance are now resolved;
account funding remains necessary, as recorded below. The prior reliability campaign's
allowance was not reused. No model has been declared best
for these tasks. Source-specific large-data acceptance, calibrated narrative/visual grading,
business report packs, automatic orchestration and durable 24/7 operation remain roadmap work.

Linear owns status: INT-450 tool boundary, INT-452 artifact delivery, INT-453 renderers,
and INT-454 live evaluation/release. The reusable benchmark World Skill was updated with
the trusted rendering pattern and verification limits; it remains explicitly unreviewed
agent-authored knowledge and contains no fixture answers.

## Follow-up: broader cases and Responses accounting

The next implementation turn added a runnable controlled comparison across **four cases
and three source fixtures**: messy retail revenue, missing-cost refusal, irregular energy
observations, and weighted service availability. The energy case distinguishes unobserved
periods from zero consumption, normalizes W/kW and timezone offsets, and bounds observation
carry-forward. The operations case handles overlapping outages/maintenance, time clipping,
customer weights and services without an eligible denominator. These are synthetic cases,
not new Kaggle downloads or evidence of unfamiliar real-domain performance.

Independent reference calculations use raw-row integer/Decimal arithmetic or exact
per-second membership; scripted SQL solutions use different methods. Eleven case tests
passed, including an alternate energy calculation, reordered results, incorrect joins,
missing-as-zero, unweighted uptime, units and reference/source changes. The full final
ordinary suite now reports **144 passed, 11 optional skips**. Ruff lint/format, Vulture and
diff-whitespace checks pass.

Run `uv run python -m scripts.run_analysis_comparison` for offline integration. Live
comparison accepts repeated `--model` options, an explicit allowance/reservation, and
optional `--langsmith`. All arms share one budget and frozen case/reference definitions.
Failed, skipped or unclassified cases prevent review eligibility; an incomplete total
charge is recorded as unknown, with known charges reported separately. Scripted runs never
qualify a model for promotion. See [the case specification](../evals/analysis/cases.md).

Actual four-case graph run: `data/output/analysis-suite-20261112T004254648499Z/comparison.json`.
All four cases passed independent grading; three report bundles contain 28 files total.
Combined run latency was 11.084 seconds, with zero provider calls and zero inference cost.
The energy coverage heatmap and service-downtime bar chart were opened and inspected for
readable labels/units. Artifacts are under each case in `arm-0/<case>/artifacts/report/`.
The image is unchanged from the final image recorded above.

The preceding suite attempt `analysis-suite-20261112T004130569166Z` is retained. Its energy
report exposed a verifier false rejection: XLSX round-tripping changed only the final
floating-point digit. Reconciliation now uses the declared numerical tolerance while
preserving null/text types, and a real-XLSX regression accepts that roundoff but rejects a
changed value. No model-quality finding is inferred from that grader defect.

The live adapter also had a concrete defect: langchain-openai's Responses conversion
discarded OpenRouter's reported charge. The dedicated Responses adapter now retains raw
usage, account cost and returned request/provider identifiers. Mock HTTP tests exercise
the real SDK parser and sync/async LangChain callbacks across a tool turn and final answer:
20 input/8 output tokens, 0.002 + 0.003 USD mock charges, zero remaining reservations, and
a third request rejected before transport. These are fixture values, not money spent.
Missing/invalid charges remain unknown; upstream inference cost is not substituted for
the account charge. Token streaming is disabled for this path, and the pinned parser
compatibility tests must accompany dependency upgrades. Live gateway behavior remains
unmeasured. The qualification and funding follow-up below records the current live-entry evidence.

## Follow-up: approved live screen and account funding

The owner approved **$3** for the live comparison. The bounded provenance review selects
native `openrouter/openai/gpt-6-luna` and `openrouter/openai/gpt-6.1-sol`, medium reasoning,
first-party OpenAI routing only, no fallback or retries. The first screen is four cases per
model, one trial per case: eight live runs, deterministic grading, and LangSmith tracing.
The larger sixteen-run campaign is still proposed. See the corrected reasoning and primary
sources in [the model selection record](analysis-model-selection.md).

The authenticated OpenRouter credits endpoint returned HTTP 200 with $395 total credit
and $394.983327373 used: **$0.016672627 remaining**. Both the existing BackIntel inference
credential and operator management credential access that same account balance. LangSmith
authenticated access succeeds. The existing ChatGPT plan adapter is not signed in; no new
login was initiated. These findings establish an account-funding problem, not bad credentials.
No credits were purchased, no temporary key was created, and no paid inference or new
LangSmith experiment ran. The owner was asked to replenish the existing account; the approved
experiment allowance remains $3 regardless of the amount added.

Local preflight also exposed a Docker CLI tag lookup problem: `docker image inspect` failed
for the existing tag while `docker inspect --type=image` resolved it. The sandbox now uses
the latter command. The direct persistent-workspace/boundary/export test passed (1 test,
4.56 seconds) against the existing image. No image rebuild or deployment was needed.

## Follow-up: ChatGPT subscription integration

The owner selected ChatGPT subscription inference instead of replenishing OpenRouter. The
existing plan adapter is now connected to both the analysis CLI and four-case comparison
runner. It uses the current documented authorization/token endpoints and
`chatgpt.tokens.use.direct` permission, public Responses HTTP streaming with `store: false`,
namespaced function tools and a private local credential record. A returning callback that
changes the selected registration is rejected. `backintel chatgpt models` reads the selected
account's visible model catalog before choosing available native model IDs.

The comparison preserves four cases per model, one trial each, medium reasoning, serial
execution, 24 model calls/50 tool calls/900 seconds per case and 192 shared model calls for
two arms. Automatic retries are disabled for this comparison. Subscription or transport
failures stop further admission; there is no paid API fallback. Complete token usage is
required for quality-review eligibility. Per-request API dollar charges remain null and
marked not applicable, never fabricated as zero. Subscription consumption can still count
against the user's plan or account limits. LangSmith's own pricing estimates are not billing
receipts. Sandbox data analysis and rendering continue on local Docker resources.

Verification: **160 tests passed, 11 optional skips**, with Ruff lint and whitespace checks
passing. New checks include real OpenAI SDK SSE parsing in synchronous/asynchronous tool
turns, reasoning continuity, token accounting without invented cost, zero-retry error
handling, shared call limits, mode separation, CLI selection and read-only model discovery.
Mock provider responses are transport evidence, not live model results.

At this checkpoint two OAuth attempts returned `access_denied`; the owner reported selecting
the wrong account. Those attempts saved no credentials and made no inference calls. The
subsequent successful connection and live trials are recorded below. No runtime default has
been promoted, and the implementation remains uncommitted and unreleased.

Official references: [registration and scopes](https://developers.openai.com/siwc/token-sharing-open-source/sign-in),
[models and inference](https://developers.openai.com/siwc/token-sharing-open-source/models-and-inference),
[preview requirements](https://developers.openai.com/siwc/token-sharing-open-source/preview-limitations),
and [errors and recovery](https://developers.openai.com/siwc/token-sharing-open-source/errors-and-recovery).

## Live subscription comparison — completed 2026-11-12 UTC

The owner completed the intended-account sign-in. BackIntel verified native plan permission
and the account catalog's availability of both models, then ran the same four frozen cases
at medium reasoning with the same tools, source files, independent graders and resource limits.

| Case | GPT-6 Luna | GPT-6.1 Sol |
| --- | --- | --- |
| Retail refunds and joined revenue | Pass | Pass |
| Missing costs: justified profit refusal | Pass | Pass |
| Irregular energy and coverage report | Fail: correct aggregate, incomplete report evidence | Pass |
| Weighted service-availability report | Fail: stopped without a completed report | Pass |
| Total | **2/4** | **4/4** |
| Model requests | 32 | 47 |
| Input / output tokens | 295,770 / 7,233 | 473,737 / 11,528 |
| Sum of four trial latencies | 213.941 seconds | 420.141 seconds |

Luna's energy calculation reached the independent reference value, but its total table did
not reproduce from the cited output. After a renderer rejection it returned `cannot_answer`
instead of repairing the evidence. Its service run similarly stopped before delivering the
requested artifacts. These are task failures, not missing-input refusals. Sol completed all
three requested report bundles and correctly refused the deliberately unanswerable profit
question. Four bundles across both arms contain 41 manifest-listed artifacts; each completed
bundle passed numerical, artifact-integrity and workbook reconciliation checks. The Luna
retail bar chart and Sol energy heatmap were visually inspected for readability.

There were **eight model trials plus one retained infrastructure attempt**. The first Luna
service attempt failed during Docker tag lookup before any model call. Only that trial was
rerun, with the same code, image, sources and evaluator, and appended to the existing Luna
experiment. The original failure remains visible with `evaluation_valid=0` and no task score;
no model-quality failure was retried. Its intermittent Docker lookup cause remains a release
follow-up; the recovery and remaining model trials started the existing image successfully.
All actual model trials report source version `d4bd1d846d56c924`
and image `sha256:9820b507a21f383ad0af1fac20426a6123ef718df79e35740461ab3ff3087dac`.

Total reported usage: **79 model requests, 769,507 input tokens and 18,761 output tokens**,
within the 192-call allowance. Inference used the ChatGPT subscription directly. There was
no OpenRouter/API-key fallback or credit purchase. Per-request dollar charges are not
provided by this route and remain null; subscription usage is not described as free.

[Luna experiment](https://smith.langchain.com/o/90b24546-f3e2-4f48-af72-b06e73b27b49/datasets/d2e934c2-77e8-4926-93b3-0bcd644b200d/compare?selectedSessions=c23b9e56-95f4-49bc-ad7c-1eac8fadefbd)
and [Sol experiment](https://smith.langchain.com/o/90b24546-f3e2-4f48-af72-b06e73b27b49/datasets/d2e934c2-77e8-4926-93b3-0bcd644b200d/compare?selectedSessions=bae50b03-b0cf-43e3-9064-5cf705cdbbf8).
Authenticated read-back verified all eight model-trial feedback records and the retained
infrastructure failure. Raw local evidence is under
`data/output/analysis-plan-20261112T020749485158Z/`: `comparison.json`,
`recovery-service-availability/recovery.json`, `langsmith-verification.json` and each `run.json`.
The recovery receipt completes the initial comparison's unresolved service slot without
overwriting the first result.

**Selection conclusion:** Sol is the better specialist candidate on this controlled screen,
at about twice the summed latency. This is one trial per case on three small synthetic
sources, not an unknown-domain, large-data or production-quality guarantee. Narrative claims
and visual aesthetics are not comprehensively graded. The owner subsequently selected Sol as the specialist default, now merged in PR #4.
Automatic delegation and the broader reliability/release milestone remain separate.


## Merged review fixes and local handoff — 2026-11-12 UTC

PR #4 includes all eight code/security review fixes: valid-only capability aggregation,
infrastructure classification for subscription failures, explicit failure for incomplete
acceptance campaigns, collision-resistant experiment files, ad-hoc questions independent
of evaluator references, Docker-only model-generated Python, relocated `/sources` mounts,
and per-run internal networks containing only assigned endpoints.

The committed candidate passed 146 ordinary tests (11 optional skips), Ruff, Vulture and
Gitleaks; the Docker suite passed 8 tests with one large-data opt-in skip. The PR and merged
`main` CI both passed. The local development branch was then fast-forwarded to the same
runtime tree, preserving all 18 pending files. The pending README gained the merged
Docker-only setting; other pending file bytes were preserved before documentation updates.

This closes the sandbox/runtime integration and owner-selected default work. INT-454's
broader artifact/reliability release milestone remains open, including unseen-domain and
large-data model acceptance. Existing live scores retain their original source identity;
they are not relabelled as fresh measurements of the merged code.


The restored full workspace passed **180 tests, 12 optional skips**, plus Ruff and Vulture.
A four-case scripted integration against the merged runtime completed three cases on the
first attempt. The retail case failed at Docker image tag inspection before any model or
tool command, reproducing the previously recorded local Docker startup issue. The local
tag still pointed to the expected immutable image. Only that case was rerun, with the exact
saved brief and unchanged source, reference, code and image; it passed.

Evidence is `data/output/analysis-postmerge-20261112T0348/comparison.json` and
`recovery-sales-refunds/recovery.json` in that directory. The original failed `run.json`
is unchanged; the recovery records its checksum and source-version match. Thus all four
cases are covered across five attempts, with **zero provider calls**. This is integration
evidence, not a new model comparison or a fix for the intermittent Docker daemon lookup.
The latter remains an explicit operational follow-up in INT-454 before broader reliability
acceptance. The historical live Sol/Luna scores are unchanged.

## SmolVM migration — 2026-11-12 UTC

Owner-authorized local migration is implemented on macOS ARM64. Both the benchmark's
`run_python` and the opt-in specialist now execute in SmolVM 1.31.1; final artifact rendering
uses a separate clean VM. `backintel/dev` in Doppler now selects `BACKINTEL_SANDBOX=smolvm`.
GPT-6.1 Sol and its ChatGPT subscription route are unchanged. These checks were run before
committing the migration; PR #4 and its CI results describe the earlier Docker candidate.

The prepared image retains ID
`sha256:9820b507a21f383ad0af1fac20426a6123ef718df79e35740461ab3ff3087dac`.
Its current local archive SHA-256 is
`d12436507cf87f1eb99cc360232e9dc9b2ac0ec8c9addf4167395cdc78ba24a5`.
The pinned runtime distribution, extracted binary and operating constraints are recorded
in [sandbox-environment.md](sandbox-environment.md). Docker remains necessary for preparing
the OCI image and hosting optional database services; prepared file-based execution no
longer performs Docker image lookups or depends on its Linux VM waking from Resource Saver.

The first concurrent cold-start check exposed a separate SmolVM 1.31.1 image-cache race:
the hardlink/copy staging fallback can truncate the shared input when machine creations
overlap. BackIntel now holds a bounded host file lock during image staging only. A real
regression starts two VMs concurrently from a fresh archive, verifies both return `42`,
and verifies the archive hash is unchanged. VM execution remains concurrent. The failed
first four-case attempt remains at `data/output/analysis-smolvm-20261112T155300Z`; its runs
failed during infrastructure setup and made no model calls. They are not model failures.

Final direct verification:

- `doppler run -p backintel -c dev -- uv run backintel sandbox check`: passed; backend
  `smolvm`, Python 3.12.16, public-network probe blocked.
- `BACKINTEL_SMOLVM_TESTS=1 uv run pytest -q --tb=short`: **189 passed, 7 skipped** in
  71.26 seconds. Real VM tests cover root/source write denial, non-root UID, empty effective
  capabilities, no-new-privileges, coding recovery, file/output limits, deadlines, assigned
  service socket isolation, SQLite reads, artifact export, concurrent startup and cleanup.
  Optional live-source and large-input tests remain outside this run.
- Ruff lint and format, Vulture and whitespace checks passed.
- Four-case scripted graph integration: **4/4 passed**, no unresolved cases, **zero provider
  calls**, 61.169 seconds summed recorded latency. Retail refunds, irregular energy and
  service availability each produced independently checked report/chart/workbook bundles;
  missing-cost correctly returned `cannot_answer`. Workbook cells and report values agreed.
- No task-owned `backintel-*` machines remained after completion.

The final comparison is `data/output/analysis-smolvm-20261112T155700Z/comparison.json`,
with per-case `run.json` and retained artifacts. Source version is `4db4fdfda73698e3`.
These four-case results use the separately pending comparison scripts and full local
working tree; the scoped migration commit does not publish that expanded harness.
This is scripted runtime/integration evidence, not a new LangSmith live-model comparison.
Historical Sol 4/4 and Luna 2/4 scores still belong to their original Docker experiments.
Memory records now report sampled VM used memory, including guest overhead; they are not
directly comparable to Docker cgroup high-water marks. Linux/Windows SmolVM distributions,
unseen-domain model quality and large-data acceptance are not claimed. INT-454 remains
In Progress for its broader release/reliability scope.

### Scoped commit verification

The migration was staged separately from the earlier benchmark expansion and versioning
changes. An isolated checkout of that staged snapshot passed **155 tests, 6 optional skips**
with real SmolVM acceptance enabled, in 77.70 seconds. Ruff lint/format, Vulture and Gitleaks
passed. Its runtime source version is `7e3758f52558caca`; the earlier 189-test count and
four-case comparison above include the separately pending evaluation files. No runtime
code changed between the migration checks and commit preparation. The differing source
fingerprint includes the pending `uv.lock` version metadata excluded from this commit.

## Live Sol on SmolVM — 2026-11-12 UTC

The owner requested a fresh live rerun after the migration commit. GPT-6.1 Sol ran through
the ChatGPT subscription at medium reasoning, one trial per case, serially. The original
four-case LangSmith dataset, sources, business briefs, references and graders were reused.
No model, prompt or runtime changes were made during the experiment; no failed trial was
retried. The shared allowance was 96 model calls, with 24 model calls, 50 tool calls and
900 seconds per case. No paid-API fallback, API credit purchase or model judge was used.

[LangSmith experiment](https://smith.langchain.com/o/90b24546-f3e2-4f48-af72-b06e73b27b49/datasets/d2e934c2-77e8-4926-93b3-0bcd644b200d/compare?selectedSessions=f667f6fc-4e8d-4bba-bcbf-fcde7d808d40)
(`backintel-specialist-gpt-6.1-sol-e2bce7f1`).

| Case | Reviewed outcome | Calls | Trial seconds |
| --- | --- | ---: | ---: |
| Retail sales/refunds | Pass: USD 135; category/day tables and delivered bundle agree with references | 11 | 104.521 |
| Missing costs | Pass under the existing refusal criterion: costs/expenses are absent; no profit fabricated | 12 | 86.928 |
| Irregular energy | Fail: correct intermediate calculation/render, but missing structured completion prevented final export | 12 | 110.779 |
| Service availability | Pass: weighted availability 59.43396226415094%; delivered bundle and reconciliations agree | 12 | 117.030 |

**Result: 3/4 passed, one completion-contract failure, zero unresolved cases after trace
classification.** All four trials booted and executed in SmolVM 1.31.1 without startup,
provider, quota or timeout failure. Two verified report/chart/workbook bundles were delivered.
The service downtime chart was opened and checked for readable labels, units and values;
this is a representative visual check, not a comprehensive aesthetic grade.

Energy's final provider response had status `completed` and contained ordinary prose with
no `AnalysisCompletion` call. `run_analysis` consequently received no structured response,
failed validation and never entered its clean renderer/export stage. The trace contains
the expected 2.1791666666666667 kWh and 127/540 meter-minutes, successful reproduction/render
and PNG inspection, but the temporary VM's report is not a delivered artifact. This is a
valid observed end-to-end failure under the existing completion requirement, not a numerical
failure or an invalid infrastructure trial. The unsuccessful attempt remains unchanged.

The automatic grader initially left this failed run unclassified (`evaluation_valid=0`,
`task_pass=null`). After reading its full trajectory, agent review classified it as
`agent_completion_contract` and updated those two LangSmith feedback entries to 1 and 0,
with explanatory comments. Original feedback was captured before the update. Read-back
verified all four stored run states/backends and reviewed scores. This was agent review,
not human calibration. `comparison.json` retains the original provisional results;
`review.json` supplies the reviewed summary and the original record hashes.

Usage was **47/96 model calls**, **468,059 input tokens** and **11,830 output tokens**,
with complete token reporting. Summed trial latency was **419.258 seconds**. Subscription
billing supplies no per-request dollar charge; this is not labelled free inference.
The previous Docker Sol trial passed 4/4 with 47 calls and 420.141 seconds. One trial per
case, with different successful-delivery counts, cannot establish a runtime speed gain or
prove that SmolVM caused the completion failure.

Full trajectories also exposed two narrower improvement opportunities. Every case first
tried to read virtual skill paths through the shell, then recovered with `read_file`.
The missing-cost case correctly refused but unnecessarily rendered a population/schema
report and mentioned temporary artifact paths; refusal outputs are not exported. Its pass
establishes the frozen cost-sufficiency criterion only, not efficient stopping or reliable
artifact delivery claims. Keep that limitation visible rather than silently strengthening
the grader after observing this trial.

Next development target: require a valid terminal completion before accepting a successful
analysis, preserve honest delivery state, and prevent refusal summaries from promising
unexported files. Clarify the distinction between virtual skill files and sandbox files.
Develop and test that candidate separately, then compare it against these retained failures;
do not rerun this baseline until it happens to pass. Broader INT-429/INT-454 acceptance remains
open; these controlled synthetic cases do not establish unfamiliar-domain or large-data reliability.

Evidence directory: `data/output/analysis-sol-smolvm-20261112T162410382489Z/`, containing
`comparison.json`, each `arm-0/<case>/run.json`, two delivered bundles, `review.json`,
`langsmith-feedback-before-review.json` and `langsmith-verification.json`. Runtime commit:
`d62995a`; full working source: `4db4fdfda73698e3`; method: `60464eed3476`. The comparison harness
remains separately pending local work. Its evaluator hash is
`81e82ca777660c5920a582f7b1b18d01dded5eb3e82f7658e4fb6de798918412`; the sole change from the
Docker harness is its documentation's runtime label. Dataset hash
`7294f8c0ca8ea4ef54e1667535e845a4d1cbd8591b82b5d235583cf9ff006615` and case-module hash
`7e2aacfd0d507dac657a8b0f8c7ad126fc682bbfbdfe8a27f22a5c0a68b43cd7` match the original comparison.
Image ID and archive hash match the migration receipt above. No task-owned BackIntel VMs
remained after the run. No code was committed or pushed as part of this rerun.

## Energy completion fix and live rerun — 2026-11-12 UTC

The owner requested a fix for the missing structured completion and a fresh energy trial.
The specialist prompt previously asked for a final result without explicitly requiring the
`AnalysisCompletion` tool. LangChain's ToolStrategy requests a tool call, but the ChatGPT
plan adapter sends automatic tool selection. A normal prose-only model stop could therefore
end the graph with no structured response; validation then failed before export.

The candidate explicitly requires the terminal tool call and adds one recovery prompt when
the model stops without it. Recovery stays in the same graph, retaining the transcript,
model/tool counters, inference allowance and whole-run deadline. A second text-only stop
fails explicitly. It never synthesizes a completion from prose or publishes a report based
only on an intermediate render. Existing completion validation, successful-render checks,
clean rendering and bundle verification remain required. The completion middleware runs
after call accounting (middleware hooks execute in reverse order); a regression caught and
prevented skipping that accounting on a recovery jump.

`scripts/run_analysis_comparison.py --case irregular-energy` selects the requested case while
checking the full existing LangSmith dataset identity. The subscription allowance scales to
24 calls for this single-case run. All case definitions, reference answers and grading logic
are unchanged. No energy-specific answers or calculation hints were added to runtime files.

[LangSmith experiment](https://smith.langchain.com/o/90b24546-f3e2-4f48-af72-b06e73b27b49/datasets/d2e934c2-77e8-4926-93b3-0bcd644b200d/compare?selectedSessions=ff29645c-8e96-4cd8-875c-302ae006acf8)
(`backintel-specialist-gpt-6.1-sol-b26bb9b1`), run `01a1d132-09e0-7070-a491-d46ad33015cc`.

**Result: 1/1 passed.** GPT-6.1 Sol, medium reasoning, ChatGPT subscription, one energy trial
in SmolVM 1.31.1. Sol directly submitted a valid `AnalysisCompletion`; the live run needed
zero recovery prompts. Its clean exported report contains 2.1791666666666667 kWh, 127 observed
of 540 eligible meter-minutes and 23.51851851851852% coverage. All nine meter/window rows,
null-versus-zero semantics, units, chart bindings and workbook reconciliation passed the
unchanged grader. Eight manifest-listed artifacts were delivered, plus the manifest: report
HTML/JSON, heatmap HTML/PNG/SVG, two CSV tables and an XLSX workbook. The PNG was opened and
its labels, units and values were readable. This is not a general visual-aesthetic score.

Usage: **17/24 model calls, 191,455 input and 3,806 output tokens, 141.795 seconds**.
Token reporting is complete; subscription billing does not provide a per-request dollar
charge. There were no trial retries or paid-API fallbacks. The model independently used SQL
interval clipping and Python datetime reconciliation, rendered and inspected the heatmap,
and completed through the terminal tool. The earlier virtual-skill shell lookup mistake
still occurred and recovered through `read_file`; that separate improvement remains open.

Direct verification: the original text-only failure was reproduced in the actual graph.
After the fix, the focused suite passed **23 tests**, including a real SmolVM energy run
that deliberately stopped with prose, recovered once, and exported a reference-matching
bundle. Other checks cover direct completion, repeated prose rejection and the unchanged
model-call cap. The standard suite passed **187 tests with 15 optional skips**; Ruff lint,
format, CI's Vulture check (`--min-confidence 100`) and diff whitespace checks passed.
These overlapping test counts must not be added together.

Evidence: `data/output/analysis-sol-smolvm-energy-fix-20261112T191758439825Z/`, with
`comparison.json`, `arm-0/irregular-energy/run.json`, the exported bundle and
`langsmith-verification.json`. The full trajectory was reviewed; packaged skill results
matched the previously reviewed trace. LangSmith read-back confirmed `completed`, SmolVM,
zero recovery prompts, `evaluation_valid=1` and `task_pass=1`; no score correction was needed.
Working source: `e903bc5341eb19cd`; method: `a544130f2127`; base commit: `d62995a`.
Dataset/case-module hashes match the original four-case run. Harness hash:
`841b8d1236d9050592ce823a4cbc5ae5fe201ca28983e5d849920fea9123e5d7`.
The runtime and image identities match the migration receipt.

Reproduce the selected live run under an authorized ChatGPT subscription allowance:

```bash
doppler run -p backintel -c dev -- uv run python -m scripts.run_analysis_comparison \
  --model chatgpt-plan/gpt-6.1-sol --reasoning medium --langsmith --case irregular-energy
```

This demonstrates one successful candidate trial, not a measured long-run completion rate.
The fallback was exercised by the deterministic SmolVM regression, not by this live run.
The original failed energy attempt and 3/4 baseline remain unchanged; do not combine them
with this selected rerun into a claimed 4/4 candidate experiment. Broader release acceptance
remains open. Changes are local and uncommitted; nothing was pushed or deployed.
