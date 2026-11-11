# Benchmark data fitness

Measured on the local canonical copies on 2026-11-10/11. This is an agent-authored,
use-specific assessment, not owner review or certification of the original source systems.
The exact checks, file fingerprints, SQL and results are in
[`results/data-quality.json`](../results/data-quality.json). Reproduce with:

```python
from pathlib import Path
from backintel.settings import Settings
from backintel.bench.quality import write_quality_report
write_quality_report(Settings.from_env(), Path("results/data-quality.json"))
```

## What the data can support

Olist supports historical descriptive analysis of orders, items, payments, delivered
orders, reviews, customer identities and seller/category sales. Online Retail II supports
line-level sales, cancellations, invoice baskets and identified-customer purchase patterns.
Both datasets lack a complete expense/cost ledger. Neither supplies a causal assignment
mechanism. Their fields do not establish business net profit, profit growth, or the causal
reason a customer did not return.

The data is fit for the specified historical capability tests if each question's grain,
filters and exclusions are followed. It does not establish customer-specific production
fitness. TPC-H exercises synthetic analytical scale; it does not expand real-world business
coverage. New generated contrast cases test data sufficiency and failure behavior, not an
additional real business.

## Material findings and their analytical consequences

| Observation | Measured evidence | Consequence and required handling |
|---|---|---|
| Customer identity differs from customer-table row identity | 99,441 Olist customer rows represent 96,096 distinct `customer_unique_id` values | Repeat purchasing must group by the person identifier, not `customer_id`; a row is associated with an order. |
| A delivered status is not sufficient to calculate a duration | 8 of 96,478 delivered orders have no customer delivery date (0.0083%) | Exclude them from duration metrics; retain the different denominators in status counts. |
| Reviews do not cover all eligible delivered orders | 646 of 96,470 eligible orders have no review (0.67%); the join yields 96,353 review rows | Review averages describe observed review rows. Do not present them as all-order satisfaction. |
| Review grain is not one row per order | 547 orders have multiple review rows; review IDs have 814 copies beyond their first occurrence | Use the explicitly requested review-row weighting; duplicate review ID does not by itself authorize dropping a row. |
| Payments are not one row per order | 2,961 orders have multiple payment rows | Aggregate payments and items separately before joining order-level totals; joining raw children multiplies rows. |
| Some categories are unavailable | 610 products have a null category | Define category exclusions and coverage explicitly; do not infer absent categories. |
| Retail customer identity is often missing | 243,007 of 1,067,371 UCI lines have no customer ID (22.77%) | Customer behavior claims cover identified customers; sales totals can include anonymous rows when the question allows. |
| Retail exports contain duplicate business rows | 34,335 surplus identical rows (3.22%), ignoring the provenance-only `source_sheet` column | Apply deduplication only where specified. Identical lines can have business meaning; silent global deduplication changes the question. |
| Cancellation prefix and negative quantity are different rules | 22,950 negative-quantity rows; 19,494 cancellation-prefix rows; 3,457 negative-quantity rows have no cancellation prefix | Preserve signed quantities for net revenue; use the exact stated cancellation/cleaning rule. Do not treat every negative row as source corruption. |
| Nonpositive prices occur | 6,207 retail lines have price <= 0 | The cleaning scenario excludes these explicitly. Other scenarios retain them; do not apply a universal cleaning rule. |
| Core Olist joins reconcile | No orphan rows in orders→customers, items/payments/reviews→orders, items→products, or items→sellers | These checks support join coverage, but do not justify arbitrary many-to-many joins or prove source semantics. |

Geolocation has 261,831 surplus identical rows among 1,000,163 rows. It is excluded from
the evaluated Olist stores, so this does not affect the current numerical scenarios. If
geolocation enters the product, its repeated zip-code/location grain must be handled first.
There are no exact duplicate rows in the other profiled Olist tables and no duplicate
keys under the listed order/item/payment/product/customer/seller key definitions. There
are no negative durations among the eligible Olist delivered orders.

## Independent reference verification

Twelve existing numerical references matched separately written SQLite calculations:
seven Olist checks cover status count, person identity, delivery duration, late review
weighting, repeat share and missing/duplicate observations; five UCI checks cover total
rows, period revenue, duplicate surplus, signed net revenue and missing IDs.

These are selected load-bearing calculations, not a claim that every reference has had
human review. Independence is computational: SQLite SQL versus the existing Polars
oracle. Both paths use data derived by the same acquisition/canonicalization code, so
agreement does not independently validate that shared transformation. Source checksums
verify the downloaded bytes, not the truth of the business records.

Canonical timestamps have no timezone attached. Existing elapsed-duration questions use
those recorded timestamps consistently; a customer-facing timezone interpretation needs
source/business confirmation. Historical replay hides post-cutoff observed deliveries and
reviews but cannot reconstruct every undocumented source-system status transition.

## Owner decisions still needed

The proposed definitions and acceptance boundary are in
[`acceptance-spec.md`](acceptance-spec.md). Human review is still required for important
business definitions and explanation scoring. No owner approval, human calibration,
production confidence interval, or customer pilot is claimed by these automated checks.
