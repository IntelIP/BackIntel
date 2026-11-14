# One real-data business-analysis demonstration

## Owner decision — 2026-11-14 UTC

Freeze the reliability benchmark and select one useful real dataset. The prior
63-response rerun is shelved and its $7 request withdrawn. Preserve old results and
failures. This demonstration takes priority over adding similar controlled cases;
it does not establish that the reliability candidate passed release acceptance.

## Selected data

**NYC TLC yellow taxi trip records, January–March 2025, plus taxi-zone lookup.**
Downloaded from the [official TLC distribution](https://www.nyc.gov/site/tlc/about/tlc-trip-record-data.page).
It contains **11,198,026 reported trip records**, 189,478,400 bytes
(189.48 MB decimal), and 265 lookup rows. Files remain unchanged; exact URLs, SHA-256,
schema and source-suitability SQL are in the [selection manifest](../benchmarks/demonstrations/nyc-yellow-q1-2025.json).
This is a practical multi-million-row demonstration, not the separate >=10 GiB scale qualification.

| File | Rows | Downloaded bytes |
| --- | ---: | ---: |
| taxi_zone_lookup.csv | 265 lookup rows | 12,331 |
| yellow_tripdata_2025-01.parquet | 3,475,226 | 59,158,238 |
| yellow_tripdata_2025-02.parquet | 3,577,543 | 60,343,086 |
| yellow_tripdata_2025-03.parquet | 4,145,257 | 69,964,745 |

Grain is a reported trip row; the files do not provide a unique trip identifier.
Distance is in miles, monetary amounts in USD, and pickup/dropoff times are recorded
without timezone offsets. Treat timestamps as NYC local civil time for the demonstration,
state that assumption, and handle the March daylight-saving boundary when interpreting durations.

The [official dictionary](https://www.nyc.gov/assets/tlc/downloads/pdf/data_dictionary_trip_records_yellow.pdf)
provides field/payment meanings. The dictionary text was inspected through the web parser;
its direct binary download returned HTTP 403 and the PDF is not in the local package.
The [NYC Open Data FAQ](https://www.nyc.gov/opendata/get-started/FAQs) describes permitted
use; retain [NYC terms](https://www.nyc.gov/main/terms-of-use), attribution, snapshot and
transformation notes. TLC warns that source accuracy is not guaranteed. Do not label
these upstream files as covered by the repository's MIT license.

## Why this data

Transportation offers a different business problem from Olist retail: temporal peaks,
zone joins, spatial patterns, airport trips, fare components and operational tradeoffs.
TLC green taxi January 2023 was previously prepared in INT-440; this selected yellow-taxi
period is a new slice, not a claim that the entire source family or training corpus is unseen.
UCI Online Retail II was considered but repeats the retail domain. Reuse the existing
source family and official distribution rather than a Kaggle mirror with additional access steps.

Source checks found 86 rows outside their file's named month, 29,495 nonpositive durations,
535,497 negative fares, and 2,263,749 missing passenger counts across the quarter.
All pickup/dropoff IDs match the unique lookup, including its unknown-location categories.
These are suitability findings, not a cleaning policy: negative amounts may represent
adjustments, and plausible duplicates lack a guaranteed identity key. Preserve raw records
and require explicit, reconciled eligibility choices in the eventual analysis.

## Single business brief

> You advise a hypothetical NYC taxi operations manager using historical Q1 2025 records.
> Describe where and when recorded activity and gross fare receipts concentrate, how
> patterns vary across the quarter, and which operational hypotheses deserve a limited
> follow-up trial. Discover the schemas and data-quality issues yourself. State eligible
> populations, exclusions, units and uncertainty. Deliver a concise executive report,
> polished charts and a supporting workbook with reproducible calculations.

Use the existing GPT-6.1 Sol specialist and SmolVM configuration. Mount only raw files
and ordinary data documentation, read-only, with network disabled. Keep source-selection
notes, profiling results, evaluator checks and expected findings outside the agent inputs.
No completed analysis, solution notebook or answer-specific prompt is supplied.

Expected deliverables: an HTML report with 3–5 prioritized findings, approximately five
clear charts (daily trend, hour/day heatmap, zone comparison, trip/fare distribution,
and an appropriate geographic or borough view), plus an XLSX workbook of supporting
aggregates, definitions and exclusions. A chart form may change when the data supports
a better explanation. Exported figures and workbook tables must agree with the report;
inspect the rendered artifacts for readable typography, units, accessible colors and clipping.

Recorded trips do not measure unmet demand or available fleet capacity. Passenger charges
are not operator profit; costs and idle time are absent. Cash tips are unrecorded, so tip
comparisons must respect payment coverage. No causal effect of congestion pricing is
established by a quarter of observational data. Recommendations are testable hypotheses.

## Bounded stopping condition

Run one first-pass artifact task, preserve its full output and LangSmith trace, and make
at most one bounded repair if a material execution or output defect warrants it. Independently
recompute three consequential displayed claims and reconcile exported aggregates. Inspect
the report/charts/workbook directly. Then deliver the artifacts and a useful/limited/failed
assessment with concrete remaining defects in Linear. Do not generate additional worlds,
repeat for a favorable score, or turn this into another qualification campaign.

This task has selected and downloaded the data with **zero model calls**. The artifact run,
its call/time allowance and any paid judge usage must be recorded separately before execution;
the withdrawn reliability allocation is not funding for a different experiment. Existing
subscription/model credentials and sandbox are retained; no provider change is proposed.

Local files: `data/output/dataset-discovery-20261114/nyc-yellow-q1-2025/` in the canonical
checkout. `acquisition.json` and `suitability-checks.json` preserve local evidence separately
from agent-visible raw assets. The wider three-domain and large-data roadmaps remain later work.
