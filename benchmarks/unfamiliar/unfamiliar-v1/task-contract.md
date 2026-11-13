# Unfamiliar-domain task contract

Draft frozen task definitions, 2026-11-13; INT-441. No live run is authorized or reported.
The source manifest and question files have exact byte identities. All 18 fixed references
are independently calculated. Raw-file isolation and mapped fixed-reference grading now have
an [offline executable check](../../../docs/research/unfamiliar-package-integration.md);
general discovery/refusal verification and the execution allowance remain pending. This is not a complete acceptance
campaign or a claim that all INT-441 acceptance criteria have been implemented.

## Inputs and split

- Development: transportation and building energy, seven tasks each. Exact questions are
  in `development-tasks.json`.
- Reserved: weather, seven tasks. The precise specification is retained privately at
  `data/unfamiliar-v1/evaluator/reserved-task-spec.json`; its SHA-256 commitment and case IDs
  are in `reserved-task-commitment.json`. Reserved answers and their implementation are
  evaluator-private; only hashes and coverage appear in `reference-receipt.json`.
- Group every derived source variant with its original domain. Do not create a reserved
  split by randomly moving rows from the development source.
- The evaluated agent receives one question/business brief, read-only raw files or qualified
  stores, and ordinary source dictionaries. It never receives this evaluator specification,
  quality-profile results, reference code, expected values, Kaggle solutions or private truth.
- Package only that domain's explicitly listed assets into each run. Never mount the shared
  acquisition parent `data/unfamiliar-v1/raw/`: it contains both development and reserved
  assets. The package Store enforces per-file mounts; any campaign must use that qualified
  path. Directory naming alone is not access isolation.
- The implementation worker may inspect development failures. It must not read the reserved
  data, profile or precise questions while changing the candidate. The evaluator alone owns
  that material until a candidate is frozen. Public model pretraining exposure is unknown;
  "cold-start" means no BackIntel-specific adaptation to the reserved domain.

## Coverage

| Domain | Six challenge categories | Seventh task |
| --- | --- | --- |
| Transportation | Population/window definition; signed grouped totals; grain-preserving lookup join; duration quantiles; equal-window comparison; refusal without expense data | Bounded service report |
| Building energy | Observed-minute coverage; power-to-energy conversion; submeter reconciliation; coverage-qualified ranking; temporal comparison; refusal without tariff data | Bounded energy report |
| Reserved weather | Coverage/sentinels; unit conversion; attribute-aware aggregation; ranked observations; temporal comparison; refusal without operational outcome data | Bounded environmental report |

All 21 tasks are mandatory for their named capability claim. Report per-domain and per-case
outcomes; an average across domains cannot conceal a failed refusal, broken evidence or
unsupported material finding. Fewer than five discovery findings is acceptable, including a
well-supported conclusion that available data does not justify further findings.

## Deterministic acceptance under INT-443

The fixed references are implemented and reconciled, with executable evaluator-mapped
fact grading. General discovery and refusal-explanation verification remain open. See the
[reference handoff](../../../docs/research/unfamiliar-reference-handoff.md) for exact scope.

For answered challenges, grade status, named metric identity, unit, grain, requested
population/time window, numerical correctness, executable evidence and delivery separately.
Counts and set membership must match exactly. Numeric comparisons use unrounded values with
absolute tolerance 1e-6 in the requested output unit and relative tolerance 1e-8; formatting
rounding alone is not a failure when the full-precision supporting value is retained. Exact
rank ties follow the question's secondary ordering; mathematically equivalent calculations
are valid. Quantiles use the specified linear-interpolated definition, not whichever default
a library happens to choose. Null/unknown is distinct from zero.

The reference author independently calculates values using repository-owned Python/Polars
over the raw source. A separately written SQL path verifies consequential totals, populations,
unit conversions and boundaries. Neither path may copy the analyst's generated query.
Both share source bytes, so agreement does not establish original source truth. Retain the
two calculation implementations, their hashes and reconciliation results outside agent mounts.

Refusal cases pass only when the answer identifies the actual missing inputs and declines
the exact requested unsupported metric. An answerable alternative may be described as such,
but must not be substituted as the requested result or published as a successful report.

For every discovery report, independently reproduce **each material numerical claim** and
check its source membership, denominator, units and time range. Verify that charts, CSVs and
workbook cells agree with the checked tables, and that references to delivered files resolve
inside the exported manifest. Unsupported material facts or causal claims fail the task;
novelty, verbosity, attractive prose and number of findings do not earn correctness credit.
Reasonable alternative findings pass if supported. The reference author must not prescribe
a single preferred narrative or treat speculative warnings as mandatory caveats.

Any method/caveat judge is advisory and versioned separately; deterministic criteria remain
mandatory. Human calibration remains waived, so do not claim human-agreement calibration.
Before scoring, freeze the executable criterion definitions and harmless display-rounding
policy; never relax tolerances or revise a hidden expected answer after seeing a candidate.
An incorrect oracle requires a separately versioned correction applied equally to both arms,
with the original records retained.

## Execution boundaries for the later campaign

Use the existing LangSmith/specialist harness once the generic data-folder path is qualified.
Retain the owner-selected `chatgpt-plan/gpt-6.1-sol` specialist at medium reasoning for both
arms; this preparation does not select a new model or change the benchmark analyst default.
The proposed controlled profile reuses 2 CPUs, 2 GiB RAM, 24 model calls, 50 tool calls and a
900-second per-task deadline. No network, source writes or run-time package installation is
permitted. Actual image, memory/disk quotas, model route and reasoning must be recorded in
the frozen plan. These proposed limits do not provision resources or spend an allowance.

Start with one baseline trial for each development task, diagnose failures, and make a
general revision. Freeze it before one candidate trial per development task and the seven
reserved tasks. This is **21 unique tasks and 35 planned responses**, not 35 independent
domains. Model/provider, input visibility and graders must match between paired arms. A
model change needs its own comparison. No paid execution begins without a finite, recorded
allowance and working provider readiness; there is currently no allowance assigned to this
domain campaign.

Exhausting a correctly configured task's bounded memory/calls/deadline is an observed
capability failure, not a discarded unlucky trial. An unavailable provider, corrupted source,
failed VM boot or broken harness is infrastructure-invalid with null quality scores. Preserve
both kinds of attempt. There are no automatic task retries; after a diagnosed environment
repair, a separately identified replacement may run with unchanged source/candidate/criteria,
and the invalid original stays visible. Do not continue an experiment with unknown charges.

An exposed reserved failure becomes regression/development evidence for a later cycle.
Repairing it does not restore its unseen status; replace the future reserved challenge before
claiming another cold-start result. Release acceptance remains separate from preparing this
task package or completing a no-gain experiment.
