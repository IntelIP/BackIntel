# Controlled analysis cases, version 1

Status: controlled development suite, implemented and agent-reviewed. No human calibration.
The four-case live comparison completed on 2026-11-12 UTC; see
[the measured results and limitations](../../docs/results-analysis-sandbox.md#live-subscription-comparison--completed-2026-11-12-utc).
This specification does not establish broader reliability or release acceptance.

The 2026-11-12 [Sol rerun on SmolVM](../../docs/results-analysis-sandbox.md#live-sol-on-smolvm--2026-11-12-utc)
retained these same inputs, reference answers and acceptance rules. It passed 3/4 after
trace classification: the energy trial returned prose without structured completion, so
its correct intermediate report was never exported. Existing refusal grading remains
narrow; it does not assess unnecessary work or temporary artifact-path claims.

The subsequent [targeted completion fix and live energy rerun](../../docs/results-analysis-sandbox.md#energy-completion-fix-and-live-rerun--2026-11-12-utc)
passed with the same case data, references and graders. Only energy was rerun on that candidate;
the original four-case result remains 3/4. Use `--case irregular-energy` on the comparison
runner to select it while retaining full-dataset identity validation.

This suite adds concrete analytical tasks to the isolated analysis specialist. It contains **four cases over three small synthetic SQLite fixtures**: retail sales, facilities energy and service operations. The profit-refusal case deliberately reuses the sales fixture. These are development cases with evaluator-written solutions, not four unseen datasets, production data, large-data performance evidence or a statistical model ranking.

The implementation is [`scripts/analysis_cases.py`](../../scripts/analysis_cases.py); the serial graph runner is [`scripts/run_analysis_comparison.py`](../../scripts/run_analysis_comparison.py). The renderer contract is [`artifact-contract.md`](../../src/backintel/agent_files/docs/artifact-contract.md). The original two-case demonstration remains available separately.

## Data and evaluator separation

`build_cases(new_directory)` writes read-only source files under `sources/`, private JSON references under `private-references/`, and a manifest. Each case exposes an `AnalysisBrief` and a `SQLiteStore` mounting **only its assigned source file**. The brief includes business definitions, requested tables/units/chart bindings and limitations; it includes no expected numerical values or solution queries. Fixture builders, this document, references, graders and SQL reference solutions stay evaluator-side. A synthetic fixture is not independently sourced ground truth; its declared definitions make its expected answer inspectable.

The manifest records the source file SHA-256, canonical source-row content SHA-256, private-reference SHA-256, brief SHA-256, and case-module SHA-256. The runner records its own evaluator fingerprint. Source/reference hashes are checked during grading, including refusal cases. Each reference stores its table values, requirements and explicit numeric tolerance. The original sales builder/oracle is imported from `run_analysis_demo.py`; preserve that file and the repository revision when reproducing a run. A manifest is run provenance, not proof of analytical correctness.

SQLite engine versions can encode identical rows into different file bytes. A changed
source-byte fingerprint cannot reuse an existing frozen LangSmith dataset; retain the
original fixture/environment or use a separately named dataset and report the difference.
Selecting only one case still validates the entire four-case dataset identity.

Each answerable case has two distinct calculation paths:

| Path | Purpose | Access |
| --- | --- | --- |
| Raw-row stdlib oracle | Generates frozen expected values independently of the reference SQL | Evaluator only |
| Executable SQL solution, `reference_queries(case_id)` | Demonstrates solvability through the existing read-only Store | Evaluator only |
| `scripted_spec(case)` | Executes that SQL and creates an artifact specification from returned rows | Scripted integration only |
| Live specialist | Discovers schema and writes its own calculations from source and brief | Source, brief, sandbox tools and packaged documentation |

The scripted solution is privileged: it is useful for testing the graph, evidence reproduction and renderer, and cannot measure model reasoning. A live run must never receive that solution or the hidden reference.

## Task 1: sales-refunds

**Business request:** Report delivered-order net revenue by category and day, with a total metric, charts and supporting sheets for 1–3 November 2026. All money is USD. Exact duplicate line rows must count once, cancelled orders are excluded, and multiple refunds must be summed per line before subtracting refunded quantity. Prices are integer cents. Revenue does not establish profit.

**Source:** `sales.sqlite`, tables `orders`, `lines`, `catalog`, `refunds`. The fixture contains an exact repeated line, a cancelled order and split refunds. It has no costs or expenses.

| Required table | Columns and units | Frozen expected rows |
| --- | --- | --- |
| `categories` | `Category`, `Revenue` (USD) | Home 75; Outdoor 40; Essentials 20 |
| `daily` | `Date`, `Revenue` (USD) | 2026-11-01: 35; 2026-11-02: 50; 2026-11-03: 50 |
| `total` | `Revenue` (USD) | 135 |

Required metric: `total`, row 0, `Revenue`. Required charts: category bar chart (`Category` → `Revenue`) and daily line chart (`Date` → `Revenue`). Table/column/row presentation order is flexible.

The independent oracle iterates deduplicated raw lines, aggregates raw refunds and calculates integer cents. The SQL solution deduplicates and preaggregates before joining. A realistic wrong control directly joins raw lines to refunds and reports 190 USD; the grader rejects it even though it can form a structurally valid report.

## Task 2: missing-cost

**Business request:** Calculate net profit for the same delivered orders. **Expected outcome:** `cannot_answer`, with a reason identifying missing or required product costs/expenses. It must not relabel revenue as profit or deliver a substitute profit report.

The same `sales.sqlite` source and its limitations are used. There is no numerical reference solution. The deterministic refusal check requires a cost/expense/COGS term and an absence/requirement term; this is a narrow machine check, not a semantic judge of every possible refusal. A helpful reason such as “Product costs are required to calculate profit” passes; a generic “I cannot answer” does not.

## Task 3: irregular-energy

**Business request:** Report observed energy and time coverage for every assigned meter and hourly window, including empty observations, for 2026-03-15 00:00–03:00 UTC. Produce a coverage heatmap, observed-energy metric and supporting sheets.

**Source:** `energy.sqlite`, tables `meters`, `readings`, `windows`. Three meters and three hourly windows define nine required rows. Readings include irregular timing, W/kW units, a timestamp with a UTC offset, valid zero power, bad/null samples, freshness gaps, a pre-window reading, an exclusive-end reading and a meter with no readings.

Definitions supplied to the specialist:

1. Normalize instants to UTC and power to watts. A good, non-null sample is constant until the next observation for its meter, including a bad/null observation, but for at most 15 minutes.
2. Clip those intervals to half-open reporting windows. Integrate `watts × seconds / 3,600,000` to kWh. Do not interpolate or fill uncovered time.
3. A valid zero-power interval counts as covered time. No valid covered interval means `Energy=null`, not zero.
4. Include every inventory-meter/window pair. Coverage is covered time divided by eligible time. The total denominator includes all assigned meters over the full reporting duration.

`energy_by_window` requires `Meter`, `WindowStart`, `Energy` (kWh), `CoveredMinutes` (minutes), `CoveragePercent` (%). Instants below abbreviate the required full UTC strings `2026-03-15T00:00:00Z`, `...01:00:00Z`, `...02:00:00Z`.

| Meter | Window UTC | Energy, kWh | Covered minutes | Coverage, % |
| --- | --- | ---: | ---: | ---: |
| alpha | 00:00 | 0.6166666667 | 37 | 61.6666666667 |
| alpha | 01:00 | 0.375 | 15 | 25 |
| alpha | 02:00 | 0.125 | 15 | 25 |
| beta | 00:00 | 0.3125 | 30 | 50 |
| beta | 01:00 | 0.75 | 30 | 50 |
| beta | 02:00 | null | 0 | 0 |
| gamma | 00:00 | null | 0 | 0 |
| gamma | 01:00 | null | 0 | 0 |
| gamma | 02:00 | null | 0 | 0 |

`energy_total` requires one row: `Energy` = 2.1791666666666667 kWh; `ObservedMeterMinutes` = 127 meter-minutes; `EligibleMeterMinutes` = 540 meter-minutes; `CoveragePercent` = 23.51851851851852%. The metric binds to its `Energy` cell. The heatmap binds `energy_by_window`, x=`WindowStart`, y=`Meter`, z=`CoveragePercent`.

The independent oracle parses timestamps with stdlib `datetime` and integrates interval intersections with `Decimal`. The reference SQL uses window functions and interval clipping. Tests also execute a different minute-grid solution; it is exact for these whole-minute fixture endpoints and accepted by the same grader. Missing/bad readings prevent full-window consumption estimates. Tariffs, costs, forecasts and causal conclusions are outside the supplied data.

## Task 4: service-availability

**Business request:** Reconcile per-service and customer-weighted fleet availability outside planned maintenance during 2026-10-01 00:00–01:00 UTC. Include every service and provide a downtime chart and supporting sheets.

**Source:** `availability.sqlite`, tables `services`, `reporting_window`, `incidents`, `maintenance`. It contains overlapping and adjacent outages, overlapping maintenance, incidents crossing reporting boundaries, a fully maintained service, and a service with no incidents. Incident/calendar completeness is an explicit synthetic fixture assumption. In this fixture an eligible service with no incident was available.

Definitions supplied to the specialist:

1. Use half-open UTC intervals, clipped to the reporting window. Union each service’s maintenance intervals; eligible time excludes their union.
2. Union each service’s outages and intersect with eligible time. Neither outage overlaps nor maintenance overlaps count twice.
3. Per-service availability is `100 × (eligible − downtime) / eligible`; return null when eligible time is zero.
4. Fleet availability is `100 × (1 − Σ(weight × downtime) / Σ(weight × eligible))`. Do not average service percentages. Weights express exposure, not affected headcount or revenue loss.

`service_availability` requires:

| Service | EligibleMinutes (minutes) | DowntimeMinutes (minutes) | Availability (%) | Weight (customer-weight) |
| --- | ---: | ---: | ---: | ---: |
| api | 50 | 37 | 26 | 5 |
| batch | 50 | 15 | 70 | 2 |
| chat | 0 | 0 | null | 1 |
| search | 60 | 0 | 100 | 3 |

`fleet_availability` requires one row: `WeightedEligibleMinutes` = 530 weighted-minutes, `WeightedDowntimeMinutes` = 215 weighted-minutes, `Availability` = 59.43396226415094%. The metric binds to this `Availability` cell. The bar chart binds `service_availability`, x=`Service`, y=`DowntimeMinutes`.

The independent oracle counts raw outage/maintenance membership for each second; this is exact for the fixture’s whole-second endpoints. The SQL solution segments interval endpoints and sums eligible pieces. The naive average of eligible service percentages gives 65.3333333333%, which the grader rejects. These fixed synthetic intervals do not establish production monitoring completeness, root causes or revenue impact.

## Acceptance and limits

`verify_case_report` compares required columns by name and rows as an unordered multiset, accepts equivalent calculations, requires declared units and metric/chart bindings, and applies numeric tolerance `rel=1e-9, abs=1e-8`. It distinguishes null, zero and booleans; missing population rows and duplicate rows fail. Additional supporting tables are allowed. It does not demand the reference SQL, a fixed tool sequence, chart titles or prose wording.

Numerical task grading is one layer. Artifact schema validation, executed evidence reproduction, clean-VM regeneration, bundle hashes and CSV/XLSX reconciliation are separate runtime/runner checks. A structurally consistent report can still be numerically wrong. These deterministic graders do not score narrative quality, visual aesthetics, unsupported causal prose, production reliability or unseen-domain generalization. The scripted reports explicitly identify their evaluator-written calculations.

Prepare fixtures only, with no provider calls:

```bash
uv run python -m scripts.analysis_cases data/output/analysis-cases-v1
```

Run the focused independent-oracle and wrong-control checks:

```bash
uv run pytest tests/test_analysis_cases.py -q
```

Run the four cases through the actual graph using privileged scripted reference actions; the output directory must be new and the analysis sandbox image must already be built:

```bash
uv run python -m scripts.run_analysis_comparison --output data/output/analysis-comparison-scripted
```

The latter exercises infrastructure at zero model-provider cost. A live comparison is a separate mode requiring explicitly qualified model endpoints, reasoning settings and finite budget options. It receives only sources and business briefs. Identical frozen cases allow a useful next comparison, but four controlled cases with one trial each cannot support a broad competence claim; future held-out tasks should vary source domains, ambiguity, scale and real data quality without leaking evaluator solutions.
