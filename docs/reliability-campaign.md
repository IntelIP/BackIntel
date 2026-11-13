# The 92-response analytical reliability campaign

This is the execution contract for INT-432 and the INT-429 acceptance parent. It uses
the existing comparison runner; it does not introduce a new agent or evaluation framework.
The [machine-readable selection](../benchmarks/improvement/reliability-campaign.json)
contains case identities and gates without expected answers. Linear owns execution status.

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
