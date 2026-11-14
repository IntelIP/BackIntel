# The 92-response analytical reliability campaign

This is the execution contract for INT-432 and the INT-429 acceptance parent. It uses
the existing comparison runner; it does not introduce a new agent or evaluation framework.
The [machine-readable selection](../benchmarks/improvement/reliability-campaign.json)
contains case identities and gates without expected answers. Linear owns execution status.

## Current native follow-up — 2026-11-14 UTC

The first revised candidate (`d0d476e04fc7f378`) completed 46 new responses within the
existing $5 allowance: 12/12 original, 17/17 development, and 16/17 generation-2 reserved
candidate responses. The 17 fresh baseline responses did not run. The stable-period
answer had correct facts but put its explicit SQL status label in the unit column,
so the independent evidence check rejected it. [Revision checkpoint and all LangSmith
links](../results/reliability-revision-20261114.md) preserve that failure separately.

PR13 now fixes explicit SQL/structured-Python metric/value associations. Its 277 offline
tests and hosted CI pass; it has no live result. Frozen source `9463f7cec50ccc9e` at
`e501bd30be96c0a7291e2c9eec63a32e6d8257a3` has a zero-call generation-3 proposal at
`data/output/reliability-native-refresh-20261114-r3-final/`. It requires 63 new responses and
reuses 29 unchanged baselines. A shared $2.05 cap would keep cumulative usage/reserves
below $6.97681681225; the requested increase from $5 to $7 is pending and supersedes
the earlier $6 request. Current usage/reserves is $4.92681681225. No further inference
or release is authorized by this preparation.
The earlier pre-review generation-3 zero-call freeze remains retained; final preparation
preserves SQLite Boolean compatibility and uses the same unconsumed generation-3 worlds.

The following checkpoints describe the earlier freezes and their historical allocations.

All **92 original planned responses completed**. The original-regression comparison
passed (candidate 12/12 versus baseline 9/12), and development passed (17/17 versus
15/17). Reserved acceptance rejected the candidate (15/17 versus baseline 17/17):
the profit evidence omitted executable unit conversion, and an unavailable-period
report returned answered with null required metrics. [Complete results and LangSmith
links](../results/reliability-native-20261114.md) retain both failures and all comparisons.
The aggregate 44/46 versus 41/46 supported result does not override mandatory regressions.

Goal usage plus retained reservations is $3.51316181225 of the original $5 allowance,
leaving $1.48683818775. PR13 implements both runtime fixes and prepares distinct reserved
worlds; its 263 passing tests are implementation evidence, not live acceptance. The
revised source is `d0d476e04fc7f378` at `661646fe8842e67e6734c2eb887dc056843cbffb`.
A separate frozen proposal originally needed 63 new responses and reused 29 unchanged
baseline records under their actual identities. Its initial $2.15/$6 funding proposal
was superseded by the staged execution and next revision described above. The
original plans and the earlier zero-call revision proposal remain retained unchanged.

The following commands and allocation records describe the completed first native
freeze. Do not execute its already-started directories again. The current revised
proposal is separate at `data/output/reliability-native-refresh-20261114-r2/` and does
not authorize new spending.

The owner-selected routes for the next campaign are `openai/gpt-6-luna` and
`anthropic/claude-haiku-5-5`, using native account credentials and the versioned
conservative token accounting in PR10 (`a0cc73ec381e4778`). Both native adapters have
live verification. These estimates are not invoices or account credit balances.

The remaining partial-disclosure judge defect is fixed. Judge `b44929467d85` matched
all **10/10 frozen controls**, including the six originals and four prospectively authored
sensor contrasts. It uses native JSON output, a clarified partial-disclosure rubric and
high reasoning effort. The benchmark's existing 8192-token output allowance leaves room
for reasoning and a complete assessment. Earlier failed attempts, including one truncated
2048-token assessment, remain unchanged. [Passing experiment](https://smith.langchain.com/o/90b24546-f3e2-4f48-af72-b06e73b27b49/projects/p/37a4b33b-7b2c-4fe8-93f1-1585356b9b33).
The [judge evidence](https://github.com/IntelIP/BackIntel/blob/codex/analyst-judge-context/results/judge-context-validation.md)
is published in PR8 at `b0569942267e9530f0ff77fbd80263111085dbe5`, stacked on PR10.
252 local tests passed with 15 optional skips; [hosted CI passed](https://github.com/IntelIP/BackIntel/actions/runs/43531747031).
This is a targeted evaluator gate, not human calibration or an analyst release result.
The comparison policy still reports method scores without a release threshold.

Native adapter/control checks total $0.24891425 in conservative usage estimates across 43 calls.
Historical reported goal usage is $0.04697181225, with $0.012 retained for previously
unpriced calls. These are separate accounting bases. All future allocations must remain
within the original $5 authorization; no credit purchase is permitted. These amounts
leave $4.69211393775 before campaign allocation. The qualified SmolVM benchmark profile
passed an offline check with public networking blocked.

All three native plans were frozen before any campaign inference at
`data/output/reliability-native-20261114/` in the canonical checkout. The original-regression
batch is complete after explicit interruption recovery: candidate 12/12 fully supported,
baseline 9/12, three improvements and zero frozen quality-gate regressions. The verdict is
`accept_for_review`; [full evidence and recovery accounting](../results/original-regression-native-20261114.md).
The 34-response development and 34-response reserved batches also completed, with
the pass/rejection outcomes recorded above. Baseline
source is `368cd43ab7c6df81`, candidate `1812b58dfccbd6f9`, scorer `c100f51adc12873d`,
judge `b44929467d85`. The machine-readable `native_followup.native_plans` preserves each
manifest/policy hash and selected output path. Historical OpenRouter plans are untouched.

The frozen native allocation is **$1 per batch, $3 total**, with a **$0.05 per-call
reservation** and call ceilings 600 / 850 / 850. The larger reservation replaces the
historical $0.01 proposal for this native configuration; it accommodates the qualified
conservative rates and 8192-token output cap. Each two-arm batch shares its allowance.
Incomplete coverage, infrastructure errors, uncertain accounting or reservation breaches
stop continuation. A valid quality rejection is retained rather than rerun for a pass.

Execute from the PR8 checkout with explicit native overrides after Doppler injection:

```bash
BACKINTEL_MODEL=openai/gpt-6-luna \
BACKINTEL_JUDGE_MODEL=anthropic/claude-haiku-5-5 \
BACKINTEL_SANDBOX=smolvm BACKINTEL_MAX_COMPLETION_TOKENS=8192 \
uv run python scripts/run_improvement_cycle.py --execute \
  --output /absolute/path/to/frozen/batch \
  --max-cost-usd 1 --max-calls 600 --reservation-usd 0.05
```

Use 850 calls for development/reserved. Never invoke an already-started output directory;
the runner deliberately refuses overwriting its execution record. The aggregate admission
record is `campaign-freeze.json`. The original interrupted batch keeps its full $1
allowance encumbered; the separately bounded recovery used $0.4056835 of a $1 cap.
The recovery’s `recovery-plan.json` and `final-accounting.json` preserve that distinction.
Prior usage plus completed recovery and retained reservations total $1.71356956225 against
the original $5 authorization. No old manifest, policy, output or expected grade changed. Completed experiments determine analyst quality; freezing
92 responses and passing judge controls do not establish that campaign results have passed.

The OpenRouter settings, source identities and prepared plan hashes below are **historical
preparation only, not executable instructions for the native campaign**. Keep them intact.
The fresh native plans above supersede these for execution. Do not relabel the old plans
or swap their providers in place.

## What is being compared

The baseline is analyst logic from `cb963fdefc6e5d2daf9779f6726a2c199ed195ee`.
The runner overlays that revision's `agent.py`, `tools.py`, `contracts.py` and runtime
skills onto the current evaluator and dependencies. The candidate is the reviewed current
analyst. Both run with the same current SmolVM runtime, data, models, grader and comparison
policy. This isolates analyst-logic changes; it does not reproduce the historical Docker
environment or compare Luna against the separate Sol reporting specialist.

- Analyst: `openrouter/openai/gpt-6-luna`.
- Method judge: `openrouter/anthropic/claude-haiku-5.5`.
- Host/runtime: the qualified macOS ARM64 SmolVM path.
- Data access: explicitly bound local SQLite stores. This campaign does not qualify other
  database deployments or perform an artifact-specialist evaluation.
- Human calibration remains waived. Method ratings are reported separately and have no
  new acceptance threshold. Independent numerical/evidence/refusal checks retain their
  existing mandatory gates and tolerances.

## Fixed coverage

| Batch | Cases | Trials per arm | Arms | Responses | Additional gate |
| --- | ---: | ---: | ---: | ---: | --- |
| Original regression | 6 | 2 | 2 | 24 | Demonstrated improvement, no material regression |
| Controlled development | 17 | 1 | 2 | 34 | All mandatory cases pass, no material regression |
| Reserved acceptance | 17 | 1 | 2 | 34 | All mandatory cases pass, no material regression |
| Total | 40 distinct cases | | | 92 | |

The original selection preserves three observed failures: missing-cost query loops,
broken cited Python evidence, and duplicate/inconsistent report metrics. It also preserves
three healthy controls. See the existing evaluator-owned
[original manifest](../benchmarks/improvement/original-regression.json).

All 34 controlled fixtures are separate generated worlds; they are not 34 independent
customer domains. Reserved answers and outcomes stay outside analyst and coding-worker
inputs. Freeze the candidate before running reserved cases. If reserved results inform a
revision, they become regression evidence and a fresh reserved variant is required before
claiming unseen acceptance.

## Offline preparation

Prepare from the final reviewed evaluator checkout after its live judge validation. A
plan prepared before that revision is final is only a dry run and must not be executed.
The same final candidate source must supply all three plans. The existing runner records
source, scorer, judge, reference, dependency and policy identities and snapshots both arms.
The campaign runner pins OpenRouter requests to the selected model vendor's own provider,
disables fallback and records `model_routing=first_party_only` for each stage. This applies
equally to both analyst arms and the judge, without changing general application defaults.

Set `BACKINTEL_DATA_DIR` to the isolated prepared data directory. It must contain verified
copies of the three historical databases from the original manifest. The controlled
builder creates its own named fixtures there; do not point it at another active run's data.
Use a fresh output root for every candidate and retain all earlier attempts.

```bash
export BACKINTEL_MODEL=openrouter/openai/gpt-6-luna
export BACKINTEL_JUDGE_MODEL=openrouter/anthropic/claude-haiku-5.5
export BACKINTEL_SANDBOX=smolvm
export BACKINTEL_DATA_DIR=/absolute/path/to/isolated/data

uv run python scripts/run_improvement_cycle.py --prepare-only --candidate-source current \
  --base-ref cb963fd --scenario-manifest benchmarks/improvement/original-regression.json \
  --split development --trials 2 --output data/improvement/reliability-92/originals
uv run python scripts/run_improvement_cycle.py --prepare-only --candidate-source current \
  --base-ref cb963fd --split development --trials 1 --no-require-improvement \
  --output data/improvement/reliability-92/development
uv run python scripts/run_improvement_cycle.py --prepare-only --candidate-source current \
  --base-ref cb963fd --split acceptance --trials 1 --no-require-improvement \
  --output data/improvement/reliability-92/reserved
```

The three prepared policies contain all selected cases as mandatory. The original batch
requires improvement; the development and reserved batches allow both arms to pass, but
never allow a criterion to regress. No score or tolerance is changed after seeing outputs.

## Readiness and spending

The integrator must reconcile prior goal spending, any retained unknown charges and live
provider credit before admission. The existing $5 total authorization is not an account
balance. No credit purchase follows from preparing this plan. A reasonable bounded allocation
for review is $1 per batch ($3 total), with per-call reservation $0.01 and call ceilings of
600 / 850 / 850 respectively. These are proposed admission limits, not predicted charges or
guarantees that every case will finish. Freeze final allocations in the execution record.

The current runner uses a shared dollar `RunBudget` within each two-arm batch. The operator
must account for all three batches against the goal allowance; unknown charges or an
exceeded reservation stop subsequent paid calls. Calls inside an answer are counted too:
92 responses are not 92 model calls. Live provider availability and source/VM readiness must be
checked before execution. Preserve the approved vendor/provenance boundary.

ChatGPT subscription usage has no per-request dollar charge. Replacing this campaign's
analyst with the subscription route would change its model/provider comparison and would
not satisfy the runner's dollar-completeness contract. Do not silently make that substitution.

Execute one frozen batch at a time only after readiness is recorded. Use the existing
`--execute`, `--max-cost-usd`, `--max-calls` and `--reservation-usd` options, with its exact
prepared output path. A nonzero exit can mean a valid rejected candidate; inspect the saved
comparison rather than treating every nonzero exit as infrastructure failure. Never rerun
until a favorable result appears.

## Evidence retained

Keep each `manifest.json`, `policy.json`, source snapshot, stage log, raw record, LangSmith
experiment link, usage ledger and final comparison. Verify complete case/trial coverage,
immutable source fingerprints and accounting before interpreting results. Report original,
development and reserved results separately. Green CI or a passing judge-control experiment
does not complete this campaign or authorize a release.

The initial offline preparation on 2026-11-13 verified all three historical source hashes,
rebuilt all 34 controlled fixtures, passed 26 independent SQL reference checks (the other
eight cases require refusal rather than a numerical answer), and enumerated exactly 92
unique batch/arm/trial/case rows with zero model calls. That confirms data/selection readiness;
the corrected evaluator freeze and funded execution are separate remaining steps.

The subsequent preparation captured candidate source `2ccaa2f068afb33b`, baseline source
`3f436698d412c8c1`, scorer `ba972f36ad0d9f1c` and judge `94a36eb150da` in all three plans.
Offline read-back validated each manifest/policy, both snapshots and all bound data hashes.
The machine-readable campaign selection retains the full plan and runner hashes.

These snapshots are **preparation only; do not execute**. The categorical caveat evaluator
has offline checks but still needs live validation. The last integrator-reported judge
request failed with HTTP 402 and no individual charge; the account had approximately
$0.00731 remaining. Funding, charge reconciliation and final batch allocation must be
resolved before calls. Any further evaluator change requires fresh plan directories.

The verified sandbox receipt identifies SmolVM 1.31.1 and the prepared image/archive; the
benchmark Python profile is 768 MiB, one CPU and a 120-second command limit. It is distinct
from the Sol specialist's two-CPU/two-GiB profile. Binary/archive hashes were checked without
starting a VM. Reconfirm the same identities before execution; this preparation is not a
fresh VM acceptance run.

Local evidence is retained in the preparation worktree at
`data/reliability-preparation-20261113/final-verification.json` and `final-plans/`.
Superseded pre-record-preservation plans remain in `plans/`, marked not to execute.
