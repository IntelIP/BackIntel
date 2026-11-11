---
name: analysis-method
description: "How to turn a business question into a reproducible, evidence-backed answer from a data store. Read before any analysis."
---

# Analysis method

## 1. Pin the question down
- Identify the metric (count, sum, average, share, ranking), the grain (per order, per
  customer, per line item), the population (which rows), and the period.
- Write the conventions you will apply. Typical ones: exclude cancellations or returns,
  exclude rows with no customer when counting customers, exclude non-product line items
  (postage, fees, adjustments) from product sales, de-duplicate exact duplicate rows.
- If the question states conventions, follow them literally even if you would choose others.

## 2. Inspect before you compute
- `list_tables`, then `describe_table` for every table you will use. Note types: dates stored
  as text, ids stored as text or integer, prices per unit versus per line.
- Check how the mess shows up: negative quantities, zero prices, null ids, codes that are not
  products, duplicate rows, statuses other than the one you need.

## 3. Compute in one reproducible query
- Prefer a single aggregate query that outputs the final answer. Cast integers to REAL before
  division. Group and order explicitly. Apply a LIMIT only for rankings.
- When a question needs two numbers (a ratio, a difference), compute both in the same query.
- Use `run_python` when you need percentiles, correlations, cohorts or window logic that is
  awkward in the dialect. Print the final numbers.

## 4. Check once
- Re-derive the number a second way, or check an invariant (parts sum to the total; shares
  sum to 1; counts are not larger than the population).
- If two formulations disagree, find out why before answering; usually a convention differs.

## 5. Answer
- `value`: the unrounded number. `unit`: what it counts (GBP, orders, customers, days, share).
- `method`: filters, joins, formula, conventions, in two to five sentences.
- `evidence`: the exact SQL or Python that produces the number. Paste it verbatim.
- `caveats`: data limits that matter for the reading (e.g. "21% of rows have no customer id
  and were excluded"; "dataset covers Dec 2009 to Dec 2011 only").
- `cannot_answer` when a required field does not exist in the data. Say what is missing.
  Do not substitute a proxy unless the question allows it; if you use a proxy, name it.
