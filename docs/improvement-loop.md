# BackIntel supervised improvement loop

This workflow uses the existing LangSmith runner and model factory. It prepares a coding
proposal and evaluates it under a separately controlled policy. Its `accept_for_review`
result is not permission to commit, merge, deploy, buy credits or change providers.

## Roles and boundaries

The analyst receives its business question and read-only data access. It cannot see the
oracle, acceptance answers or grader. The coding worker receives only an operator-written
failure brief and the explicitly allowlisted runtime files; it is a model call with no
filesystem, shell, browsing or other execution tools. A structured replacement-file reply
is a proposal. It does not run or edit anything by itself.

The evaluation process holds the full case definitions, reference answers and frozen
comparison policy. It validates and applies proposals in an operator-created isolated
checkout, then runs the unchanged evaluators. Keep reserved case values and full answer
traces out of the worker's brief. Worktree separation alone is not a read-access boundary;
this worker's isolation comes from its explicitly supplied message context and absent tools.

The runtime edit allowlist covers `agent.py`, `tools.py`, `answer_validation.py` and
`agent_files/`. Each invocation supplies a narrower exact path set. Prefer a single skill
or prompt file for a prompt defect. `apply_candidate` rejects non-allowlisted paths,
symlinks that escape the workspace, and source files changed since the proposal. Changes
still need semantic review: a path allowlist alone does not prove a patch preserves policy.

## Operation

1. Build the development or reserved suite with
   `backintel.bench.acceptance.build_acceptance(settings, split=...)`. Check generated store
   fingerprints before and after experiments using `verify_acceptance_data`.
2. Construct `Harness.build(settings, dataset=suite.dataset, store_id=..., scenarios=suite.scenarios,
   data_version=suite.data_hash, budget=budget)`. Use one shared `RunBudget` for the authorized
   batch, including analyst, judge and coding calls. Scenario-specific stores use `Scenario.store`.
3. Before asking a worker for a patch, save a `ComparisonPolicy.document()` outside its context.
   It locks the case/trial set, mandatory cases, reference/data/scorer/judge identity, and any
   accepted quality, time or cost ceilings. `ComparisonPolicy.from_document` checks its hash.
   Its fingerprint is a drift check, not authentication against an operator who can rewrite it.
4. Run the original analyst through the **same frozen evaluator** as the candidate. Historical
   experiments remain history; a missing scorer/data fingerprint does not establish comparison
   compatibility. `run_langsmith` syncs the explicitly supplied scenario set into its own dataset
   and records source and reference versions, actual working-tree state and run IDs.
5. Call `propose_candidate(files, failure_brief, model_id=approved_model, budget=budget)`. This is
   the actual coding-model operation. Save its structured result, input/base hashes and usage.
   Examine the proposed changes, then use `apply_candidate(proposal, isolated_checkout)`.
   The caller creates the authorized task branch; these functions never commit or push.
6. Verify the patch with focused offline checks, then run candidate cases with the same policy.
   Pass both JSONL record lists to `compare_records`. Each repetition has an explicit zero-based
   `trial`; missing, duplicated or extra case/trial pairs invalidate the comparison.
7. Review the comparison. `invalid_comparison` means coverage, data, grader or accounting cannot
   support the claim. `reject` means a mandatory case failed, a former passing criterion regressed,
   a required ceiling failed, or no formerly failing case improved. `accept_for_review` requires
   the fixed checks to pass and remains subject to human review. Record all attempts; never replace
   a failed run with a favorable retry. A revised candidate starts another explicitly bounded cycle.

The comparison currently covers deterministic correctness/evidence/refusal and optionally an
agreed method score threshold, per-case latency ceiling and total model cost ceiling. It exposes
per-case regressions and improvement plus baseline/candidate usage. It makes no significance claim
from a single run. Choose repetitions when observed variability can affect the decision.

## CLI examples

These offline commands prepare data and review artifacts without model calls. Choose fresh
output paths so previous evidence is retained.

```bash
uv run backintel acceptance build --split development
uv run backintel quality --output results/quality-review-01.json
uv run backintel improve review --records results/raw/selected-review-records.jsonl --output results/human-review-01
uv run backintel improve calibrate --packet results/human-review-01/packet.json --labels results/human-review-01/human-labels.json --judges results/human-review-01/judge-ratings.json --output results/calibration-01.json
uv run backintel improve compare --baseline results/raw/baseline.jsonl --candidate results/raw/candidate.jsonl --policy results/comparison-policy.json --output results/comparison-01.json
```

The following are paid operations. Set `BACKINTEL_APPROVED_BATCH_USD` to the amount explicitly
authorized for this invocation before running them; examples do not grant spending approval.
The sanitized brief should describe behavior, not reveal reserved questions or answers. Point
`--workspace` at the isolated candidate checkout prepared by the operator.

```bash
doppler run -p backintel -c dev -- uv run backintel acceptance run --split development --trials 1 --max-cost-usd "$BACKINTEL_APPROVED_BATCH_USD"
doppler run -p backintel -c dev -- uv run backintel improve propose --workspace /path/to/candidate --files src/backintel/agent_files/lead.md --brief /path/to/sanitized-failure.txt --output results/proposal-01.json --max-cost-usd "$BACKINTEL_APPROVED_BATCH_USD"
uv run backintel improve apply --proposal results/proposal-01.json --workspace /path/to/candidate
```

`propose` performs one bounded coding invocation. `apply` is separate, checks the original
file hashes, and only changes the supplied runtime files. `compare` and `calibrate` return
nonzero exit status when their required acceptance/review conditions are not met. The caller
must keep the shared overall allowance across separate CLI invocations; each command's
budget is local to that invocation.

For one reproducible cycle with a shared allowance, use the isolated runner. Preparation
copies the current evaluator and locked dependencies, overlays only the runtime from `cb963fd`,
and creates a separate candidate copy. It pins cases, trials, data, scorer, judge and comparison
policy before the worker sees its sanitized brief. Both scores are freshly measured; historical
results are never substituted for a paired baseline.

```bash
uv run python scripts/run_improvement_cycle.py --prepare-only --output data/improvement/cycle-02 --base-ref cb963fd --split development --trials 1 --brief benchmarks/improvement/failure-brief-query-loop.md --files src/backintel/agent_files/lead.md
# Paid operation, only after its total allowance has been explicitly approved:
doppler run -p backintel -c dev -- .venv/bin/python scripts/run_improvement_cycle.py --execute --output data/improvement/cycle-02 --max-cost-usd "$BACKINTEL_APPROVED_BATCH_USD" --max-calls 500 --reservation-usd 0.05
```

Preparation makes no API calls. Execution uses the existing Python environment and snapshot
`PYTHONPATH`, without installing dependencies. It runs baseline, a real coding-model proposal,
candidate and comparison in sequence, retaining stage logs, per-call accounting and proposal
hashes. The overall allowance includes analyst, judge and worker calls. Unknown charges, failed
stages or exhausted admission stop later stages. Fresh output directories prevent overwriting
prior attempts. The automatic runner permits only prompt/skill Markdown edits on development
cases; executable Python proposals use the separate propose/review/apply workflow. Reserved
acceptance follows a frozen candidate and cannot supply the improvement worker's feedback.

The distinct `--candidate-source current` mode measures the runtime fixes already in this
working tree. It freezes that current candidate, overlays `cb963fd` only in the baseline, and
executes baseline then candidate with no coding stage. Both sides still use the current frozen
evaluator. Original regression cases, controlled development and reserved validation have
separate plans and output directories:

```bash
uv run python scripts/run_improvement_cycle.py --prepare-only --candidate-source current --output data/improvement/runtime-originals-01 --scenario-manifest benchmarks/improvement/original-regression.json --split development --trials 2
uv run python scripts/run_improvement_cycle.py --prepare-only --candidate-source current --output data/improvement/runtime-development-01 --split development --trials 1 --no-require-improvement
uv run python scripts/run_improvement_cycle.py --prepare-only --candidate-source current --output data/improvement/runtime-reserved-01 --split acceptance --trials 1 --no-require-improvement
```

Use the same explicitly budgeted `--execute --output ...` invocation for each prepared plan;
its allowance covers the two experiments in that plan. The default comparison requires a
newly fixed case. `--no-require-improvement` is available only for the current-runtime mode:
controls/reserved cases can pass on both versions, while every mandatory case must still pass
and no criterion may regress. This choice is frozen before results. Reserved output is
validation evidence and must not become a new tuning brief.

An explicit scenario manifest is copied into the plan and identified by its full file hash.
It contains `schema: 1`, `dataset`, `split`, full `scenarios` with explicit SQLite bindings,
`stores` keyed by store ID with data-directory-relative `path`, `sha256` and `size_bytes`,
`reference_hash` from `reference_version(scenarios)`, and `data_hash` from `fingerprint(stores)`.
Original reference-source hashes and selection rationale can accompany those fields. The
loader checks the scenario identity and exact SQLite bytes before and after trials. This
controlled path supports SQLite only; it does not silently claim remote-store equivalence.

### Controlled rejection demonstration

`scripts/run_rejection_demo.py` reuses the completed, passing trial-0 `olist-l1-01` row
from a compatible original-regression baseline. It checks the manifest's data/reference
hashes, scorer, judge, dependencies, sandbox and complete accounting before any external
call. The policy, unchanged baseline row, original record/file hashes and exact control
source/hash are saved before execution. Prior baseline cost is disclosed separately from
new spending; the baseline is not rerun.

The candidate deliberately returns zero with runnable `SELECT 0` evidence. It is labeled
`controlled-negative-fixture` throughout; no analyst model is constructed or called. The
existing method judge still runs under a one-call budget, and LangSmith records the control.
The comparison must reject its mandatory correctness regression. This demonstrates the
rejection path, not an observed LLM regression or model-quality improvement.

```bash
# Without --execute, this validates inputs without model calls or LangSmith writes.
doppler run -p backintel -c dev -- uv run python scripts/run_rejection_demo.py --baseline /path/to/completed-baseline.jsonl --output data/improvement/rejection-demo-01 --max-cost-usd "$BACKINTEL_APPROVED_BATCH_USD" --execute
```

Use a fresh output directory and an explicitly approved allowance. A successful demonstration
exits zero and saves `comparison.json` with verdict `reject` plus `execution-result.json`
with the experiment link and newly reported usage. Invalid compatibility, judge failure,
unknown charges or an unexpected comparison outcome do not count as a demonstrated rejection.

## Usage and spending

`UsageTracker` records completed model callbacks, including calls made before a graph fails.
It counts each provider usage object once. It keeps error calls with missing usage unknown rather
than assigning them zero cost. Custom harnesses without callbacks fall back to partial message
usage and explicitly mark accounting incomplete. Each new record includes separate analyst and
judge usage and `total_reported_cost_usd` / `total_cost_complete`. Totals cover provider-reported
model API usage, not LangSmith charges or computer costs. No-answer grading incurs no judge call.

`RunBudget(limit_usd, max_calls, reservation_usd)` checks admission **before** every model call.
Concurrent calls reserve their allowance under a lock. Reported cost settles reservations. An
unknown charge or a response above its reservation prevents further calls. `can_admit()` lets the
caller stop subsequent trials; admission is checked again atomically at each model request.
Requested cases reached after exhaustion remain recorded as invalid/not attempted with null grades,
not zero-scored capability failures. A required judge that fails or cannot be funded invalidates
the comparison while retaining deterministic scores for diagnosis. Provider transport failures
are likewise infrastructure-invalid. Budgeted analyst,
judge and coding calls disable SDK retries (`max_retries=0`). The provider can still charge a
request whose usage it does not return. A per-call reservation is an operator assumption, not an
absolute provider billing cap; use a provider-side key limit for a strict monetary ceiling.

## Human calibration

`write_review_packet(records, new_output_directory)` produces:

- `review.md`: readable answers, exact cited code and blank anchored 0/1/2 criteria. No model grades.
- `packet.json`: immutable review inputs and their hashes.
- `human-labels.json`: unfilled human labels, reviewer and timestamp.
- `judge-ratings.json`: model ratings stored separately to avoid influencing the initial review.

Use actual owner/domain-reviewer labels. Controlled counterexamples must carry an explicit
`source_kind`. Missing labels stay missing. `assess_calibration` checks packet identity and returns
coverage, per-criterion disagreements, exact agreement and mean absolute rating difference.
It does not manufacture a pass threshold, human approval or population-level reliability claim.
An old rubric's judgments cannot certify a new rubric; version and re-check material rubric changes.

## Direct verification and sources

The focused offline tests exercise candidate acceptance and rejection, grader/coverage drift,
unknown cost, failed-graph usage, budget admission, controlled worker outputs, source conflicts,
and incomplete/tampered human review. Mocked worker calls establish orchestration behavior only.
A real paid coding-model invocation plus real baseline/candidate LangSmith runs is required to
claim a completed improvement cycle. Human calibration additionally requires submitted labels.

This follows LangSmith's [evaluation workflow](https://docs.langchain.com/langsmith/evaluation),
[experiment comparisons](https://docs.langchain.com/langsmith/compare-experiment-results), and
[human feedback guidance](https://docs.langchain.com/langsmith/improve-judge-evaluator-feedback).
The `evaluator_info` feedback field and callback signatures were checked against installed
LangSmith 0.14.17 and LangChain Core source. Current dependency pins remain in `uv.lock`.
