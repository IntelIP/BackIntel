# BackIntel improvement acceptance specification

Status: agent-reviewed specification; business definitions and acceptance scope approved
by the owner on 2026-11-10. Human calibration is explicitly waived for this goal; human
explanation labels remain blank. See the [recorded owner decision](improvement-goal.md#owner-decision-recorded-on-2026-11-10).
This specification adds focused contrast cases to the existing 73-scenario benchmark.
It does not replace or rescore historical results. No live model result is claimed here.

## Owner-approved business definitions

1. **Repeat purchasing:** identify a person with `customer_unique_id` in Olist (the generated
   fixtures use `customer_person_id`); count distinct orders across all statuses where the
   question specifies that population. Report the repeat-person share and mean orders per
   person. This describes purchase recurrence in the available extract, not causal churn
   reasons, customer lifetime value, or purchases elsewhere.
2. **Delivery and satisfaction:** include delivered orders with observed delivery timestamps;
   calculate exact elapsed fractional days. Late means actual delivery strictly after the
   estimate. Average reviews over review rows when requested, disclose uncovered orders and
   multiple-review weighting, and make descriptive association claims only.
3. **Category/seller performance:** use delivered item revenue excluding freight under the
   existing convention; disclose missing/untranslated categories. Call it revenue performance.
   Net profit requires an expense/cost ledger of the same period and accounting scope. The new
   complete-ledger fixture explicitly defines net profit as posted revenue less all posted
   expenses and supplies period-coverage records; this synthetic definition is not an assertion
   that every real business's profit can be calculated from two exports.

The owner approved these three scopes on 2026-11-10. Any subsequent material change must
update the relevant question, reference and tests before new model comparisons. Missing
costs should cause a useful refusal; they must not be filled by an invented margin.

## New controlled environments

`backintel.bench.acceptance.build_acceptance(settings, split=...)` creates 17 cases for
`development` and 17 parallel reserved variants for `acceptance`. Variants change values,
periods and financial/report table names. These small generated worlds isolate specific
failure mechanisms; they are not a substitute for a representative customer-data pilot.

Every case binds a separate opaque `sqlite:bi_*` store via the existing `Scenario.store`
contract. The analyst can inspect only that store. Complete cost ledgers in one case cannot
be used to answer a different missing-cost case. Runtime schemas contain ordinary business
columns and ledger coverage, never reference answers or labels identifying negative cases.

| Case family | Required behavior |
|---|---|
| Signed revenue, including refunds | Answer the requested sum and convert minor currency units correctly. |
| Full-period cost ledger | Calculate the explicitly defined net profit; do not refuse merely because the word profit appears. |
| Missing expense ledger | Decline, name the required expenses/cost information, and do not substitute revenue. |
| Partially covered expense ledger | Decline the full-period profit calculation and explain the coverage gap. |
| Zero net profit with complete data | Return numeric zero with evidence; zero is not missing. |
| Repeated export rows | Deduplicate at the requested business identifier and preserve signed refunds. |
| Delivery/review report | Return each requested metric once, with correct populations and executable evidence. |
| Repeat purchasing report | Use person identity and distinct order grain; cite programs that actually run. |
| Causal review improvement | Decline an unsupported causal effect while explaining what evidence would be needed. |
| Stable delivery and shifted delivery | Avoid a false alarm for stable data; detect a shift under the stated rule. |
| Delayed observations and follow-up | Hide future outcomes in the first snapshot; revise metrics and alert once the next scheduled snapshot contains the late deliveries. |
| Duplicate shipment export | Keep order-level metrics unchanged after deduplication. |
| Entire current period unobserved | Explain that the comparison cannot be calculated; do not turn missingness into zero duration. |
| Sales-mix-only versus actual price change | Compare within SKU under the fixed equal-weight definition; changing quantities alone must not trigger a price alert. |

The delivery late-arrival pair compares the same purchased cohorts at two scheduled cutoffs
seven days apart. The first snapshot has two pending current-period orders and no material
alert; the next has all four observations and a material alert. Truth includes the original
unseen event times only in the private manifest. This measures detection at the first
scheduled snapshot with sufficient observed evidence; it does not claim a production alert
latency. Price replay adds a business change beyond the original Olist delivery intervention.

## Reference construction and isolation

References are calculated from fixture records using Python integer/Decimal/date operations.
Every answerable reference is cross-checked through separately written SQLite SQL at build
time. A mismatch aborts construction. Negative cases have documented missing-information
conditions; a bare declaration of answerability is not enough.

Generated databases live under `data/stores/sqlite`, already outside Git. Evaluator-owned
manifests are `benchmarks/acceptance/acceptance-v1/{development,acceptance}.json` and contain
reference answers, check queries and planting declarations. They must never be mounted in
the analyst sandbox or included in the improvement worker's editable workspace. Only that
case's SQLite file is mounted. The manifest records logical content and physical SQLite
checksums; `verify_acceptance_data(suite, settings)` detects changed fixture files before
or after a trial.

The reserved suite must not be used to tune a candidate. Freeze the candidate before its
first reserved run. If a revealed acceptance failure is used to develop the next fix, that
case becomes a regression case; create and reserve an additional independent variant for
the next acceptance decision. The current broad-access development team is not itself an
access-control boundary. The improvement runner must enforce its worker file allowlist.

## Fixed evaluation and promotion criteria

Each mandatory answered case must match its independent reference, reproduce every cited
evidence item, and satisfy the answer contract. Counts are exact; currency answers allow
half a penny, and report ratios/durations allow absolute error of one millionth so a
six-decimal representation of a recurring fraction is accepted. Each mandatory unanswerable case must
produce a useful refusal naming the actual missing requirement, without an invented value.
A structured refusal alone is not enough to establish explanation quality.

Both development and reserved sets contain answerable controls so a refusal-heavy candidate
cannot improve by declining everything. Promotion must show no regression on the agreed
existing baseline controls. Preserve per-case outcomes, all failed trials and the original
experiment rather than selecting the most favorable retry. Repeat critical cases when the
observed nondeterminism could change acceptance; document the preselected trial count.

Method and caveat scores remain separate from numerical correctness. The owner approved
this scope and waived human calibration; method-judge scores remain uncalibrated against
human labels. This waiver does not change the mandatory checks above or imply that a
candidate has passed them. The evaluator/loop workstream owns the frozen
comparison manifest, judge-version handling, repetition policy, budget gates and the final
accept/reject decision. This specification does not invent a global production reliability target.

### Original failures and healthy controls

[original-regression.json](../benchmarks/improvement/original-regression.json) preserves
six original questions and references with explicit SQLite bindings and exact data-file
fingerprints. It selects the missing-cost query loop, the September 2017 repeat report
with broken evidence, and the March 2018 delivery report with duplicate metrics. The
controls are the ordinary repeat-purchasing report, delivery/satisfaction report, and
delivered-order count. No historical response or score is substituted for a fresh baseline.

The initial runtime comparison preselects two trials for each original case because the
missing-cost question already behaved differently across recorded runs. Both trials are
retained; they do not establish a population success rate. The controlled development and
reserved suites initially use one trial each. Additional repetitions require an observed
uncertainty that could change acceptance, with a declared plan before rerunning.

The original-case comparison requires an improvement as well as all mandatory passes and
no regression. Controlled and reserved validation require mandatory passes and no regression;
they need not each contain a newly fixed case if both versions already handle them. These
policies are frozen before results. A candidate must pass the relevant comparisons together;
a favorable result in one suite does not override a failure in another.

## Direct verification completed

- Both splits build reproducibly with 13 answerable SQL cross-checks and four genuine
  missing-information cases each.
- Checks cover separate store visibility, zero versus unknown, partial ledger coverage,
  post-cutoff observations, later information arrival, duplicate and mix false alarms,
  and detection of modified fixture files.
- The previous 73 scenario definitions and their results remain unchanged.

These checks establish fixture/verifier readiness only. Model performance and automated-worker
isolation must be measured by their owning workstreams. Owner approval of the definitions
does not constitute human labeling of model responses.
