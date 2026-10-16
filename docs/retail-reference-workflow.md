# PostgreSQL retail reference workflow

Verified locally on 15 October 2026 for S-38 and S-39. A business owner can save a question and operating limits, then obtain a checked answer from a permitted PostgreSQL source. The same saved procedure runs through the developer toolkit and the platform.

## Business question and result

Which products and countries contributed most to net invoice value over the complete recorded period, and how much did cancellations reduce it?

| Measure | Checked result |
| --- | ---: |
| Source rows collected and processed | 541,909 |
| Excluded, failed, or pending rows | 0 |
| Product-code groups checked | 4,070 |
| Country groups checked | 38 |
| Net invoice-line value, GBP | 9,747,747.934 |
| Value without C-prefixed cancellations, GBP | 10,644,560.424 |
| Signed cancellation value, GBP | -896,812.49 |
| Reduction from those cancellations, GBP | 896,812.49 |
| Leading stock-code group | DOT: GBP 206,245.48 |
| Leading country | United Kingdom: GBP 8,187,806.364 |

Every group and total matched the independently calculated CSV expectation using exact decimal arithmetic. The platform shows ten groups plus ties and discloses that all groups remain in the saved evidence. DOT is a stock-code group; this result does not establish it as an individual merchandise product.

The historical period is 2010-12-01 08:26 through 2011-12-09 12:50. The timezone is unknown and the final month is partial. Invoice-line value is not audited revenue or profit. No business target or measured business benefit is claimed.

## What ran

A live model created and revised the plan, interpreted aggregate field profiles, and selected the calculation method. BackIntel discovered the permitted source, collected every row, retained originals, prepared the data in an isolated process, checked preserved meaning, and calculated the answer. Four model calls were used across planning, interpretation, and method selection. Model requests contained the objective, schema meanings, and aggregate profiles, without raw retail rows or identifier values.

The accepted version was saved with its contracts and secret references. A new source collection ran through the saved procedure without new model calls. The command line, platform API, and real browser returned the same accepted run. A separate full-data recovery check terminated a worker after 2,000 retained rows; a fresh process reused that work and finished the remaining 539,909 rows in 101.112 seconds. Repeated invocation reused the result. Revoked source access denied invocation and result access.

The final browser check passed for the answer, complete-coverage disclosure, saved-workflow invocation, source details, and history, with no page errors. The initial browser assertions were corrected to follow the ten-groups-plus-ties display, match the selector's accessible label, and permit the temporary server's exact local write origin. Only browser verification was repeated; the completed data pipeline was retained. All 17 web interaction tests and the production build passed before this browser check.

## Source, scope, time, and cost

- Dataset: [Kaggle ecommerce-data](https://www.kaggle.com/datasets/carrie1/ecommerce-data), derived from [UCI Online Retail](https://archive.ics.uci.edu/dataset/352/online+retail), DOI 10.24432/C5BW33.
- Attribution: Chen, D. (2015). Online Retail. UCI Machine Learning Repository.
- UCI license: CC BY 4.0. Kaggle's license field is Unknown; the two source statements are retained separately.
- CSV SHA-256: `d07aec9960083af2339975a3f9d3b26313b342dcd9f86cce0b919b1cde639a44`. Size: 45,580,638 bytes. Encoding: ISO-8859-1. The source manifest retains retrieval and license evidence.
- Dedicated source database: `backintel_retail_source`; role: `retail_reader`; schema: `retail_raw`; permitted action: SELECT. The original integration verified denied INSERT/UPDATE/DELETE privileges and a rejected zero-row DELETE.
- Collection: 28.361 seconds and 271 retained pages. Saved workflow: 101.527 seconds, including preparation (46.156 seconds) and meaning validation (31.628 seconds). These are separate recorded scopes, not a complete setup-time measurement.
- Measured retained runtime database size after the browser check: 132,880,063 bytes. This includes retained prior demonstration state and is not incremental per-run storage.
- Configured preparation limits: one CPU, 1 GiB memory, 300 seconds per isolated execution, 32 processes, 100 MiB input, 300 MiB output, and 16 MiB temporary storage. Source objective limits: 900-second timeout and 100 MiB source bytes. Configured caps are not measured utilization.
- Actual peak memory, CPU usage, source-bootstrap time, and complete processing-wall time were not retained after the original browser assertion failed. Local compute cost remains unmeasured.
- Provider-reported total: USD 0.063327825 across four completed requests (planning 0.03186612; interpretation 0.02111769; calculation method 0.010344015). The saved-workflow demonstration and browser checks made zero new model calls. No cloud infrastructure was provisioned.

## Evidence and remaining work

The [integration receipt](</Users/hudson/Library/Application Support/BackIntel/Validation/S39Reference-20261015/reference-evidence.json>) links coverage, timings, limits, and accounting. The [browser receipt](</Users/hudson/Library/Application Support/BackIntel/Validation/S39Reference-20261015/browser-evidence.json>) records the real UI result. The [source-query evidence](</Users/hudson/Library/Application Support/BackIntel/Validation/S39Reference-20261015/source-query-evidence.json>) retains source discovery, collection identity, query metadata, and snapshot references. The [workflow package](</Users/hudson/Library/Application Support/BackIntel/Validation/S39Reference-20261015/workflow-package.json>) contains the versioned procedure. The [member review](</Users/hudson/Library/Application Support/BackIntel/Validation/S39Reference-20261015/member-acceptance-review.json>) records all 15 story dispositions. Full artifacts and database archives remain outside Git in this validation directory.

- Workflow version: `c8bebd638e882b833eb9f840094b7199d94436728dba167da25654722b2bba41`.
- Accepted run: `54bb3045aa0f69a2db920018a29a3ffe031ddc417aba0d6665654681f732432e`.
- New collection: `06a29492143cd7d4965a5da7a55b53030ec31a65cbd87e90d1c159d12675db35`.
- Recovery evidence: [S-19 receipt](</Users/hudson/Library/Application Support/BackIntel/Validation/S19InvocationAttempt2-20261015/invocation-evidence.json>).
- Independent expectation: [S-16 full answer](</Users/hudson/Library/Application Support/BackIntel/Validation/S16MeaningCheck-20261014/independent-expected-answer.json>).
- Final database archive: `browser-verified-result.dump`. Disposable databases, server, and browser were stopped after verification.

A source owner still exposes the source and grants access. An operator supplies the local runtime and approved credential references. The business owner confirms the question, limits, and any new model spending. Changed objectives, incompatible inputs, and missing dependencies need a newly checked workflow version.

Original invoice/customer/product identity semantics, quantity units, cancellation-to-original linkage, and other signed adjustments remain documented uncertainties. No joins were accepted because this scenario has one table. The workflow preserves every row and unusual signed value rather than silently resolving these uncertainties. Earlier interpretation caveats about checking hashes and dates describe that stage; the later full-source checks verified the pinned hash and actual date extrema.

This establishes one local historical PostgreSQL workflow. Databricks, continuous updates, broad autonomous method development, coordination among agents, additional source systems, and sustained multi-user scale remain roadmap work. No commit, push, merge, release, deployment, or demonstrated business-value claim is included.


## Forecast method study

The October 15, 2026 local S-32 demonstration asked BackIntel to develop a four-week forecast of total net invoice value in GBP across all countries, including signed cancellations. One live model request generated two executable Python methods. Both ran successfully in the isolated workspace, but neither beat the agreed simple comparison on validation data. BackIntel therefore retained the simple comparison; no accuracy improvement or predictor promotion is claimed.

The model received 44 earlier weekly aggregates, from December 6, 2010 through October 3, 2011. Selection used the four weeks starting October 10 through October 31. The final four weeks starting November 7 through November 28 were reserved until selection was fixed. Candidate code received only earlier history. The saved contract, individual code hashes, execution receipts, predictions, errors, and rejection reasons remain in the retained study.

| Method | Average weekly validation error (GBP) | Decision |
| --- | ---: | --- |
| Repeat the latest four weeks | 28,591.57 | Retained |
| Robust local trend with rolling-origin ensemble selection | 36,070.57 | Rejected |
| Damped transaction-volume forecast multiplied by smoothed net value per row | 36,816.60 | Rejected |

On the reserved final period, the retained method's average weekly error was **GBP 89,655.48**. It predicted GBP 996,405.82 in total against GBP 1,355,027.72 observed. This is one historical evaluation period, with point forecasts and no calibrated prediction intervals. Its result did not trigger another search or change the selection.

All 541,909 source rows reconcile to GBP 9,747,747.934. Forecasting uses 52 complete calendar weeks containing 514,059 rows. The 27,850 rows in partial boundary weeks remain accounted for in reconciliation and are excluded from forecasting. Source timezone remains unknown.

The live request cost **USD 0.03369069**, against the separately approved one-call, USD 0.25 allowance. Completed study stages took **89.147 seconds**; this is not a measure of setup time or all failed attempts. Local computing cost is unavailable. Saving and invoking the selected workflow through the toolkit, authenticated API, and actual browser returned equivalent forecast values with **zero additional model calls**. The saved forecast concerns December 2011 and is not a prediction of current customer activity.

The checks also refused a zero allowance and a second method request on the same protected evaluation data, enforced the single-call limit, and denied access after source permission was revoked. An earlier simulated proposal check resumed after an injected interruption following selection. The live run also resumed its retained policy after a pre-dispatch permission fix; the blocked attempt sent no inference request. Both the simulated exercise and the live result remain distinguishable. Predictor promotion still requires human approval.

Local evidence is retained under `/Users/hudson/Library/Application Support/BackIntel/Validation/S32Live-20261015`:

- `study-result.json`: live generated methods, policy, source reconciliation, comparisons, uncertainty, and charge.
- `workflow-package.json` and `forecast-result.json`: saved method version and its manually invoked output.
- `browser-result.json` and `forecast-platform.png`: real browser save/run checks and the rendered result.
- `runtime-result.dump`: accepted runtime evidence and paid-request history for restoration.
- `validation.py` and `browser-check.js`: reproducible checks; the live script refuses a fresh paid attempt when one already exists and requires reuse of the retained database.

Study: `08f463288faa6444548a191203fd4fcc933f03178dc4e23d475fcd800c792e4c`. Saved workflow: `07869f4fa1ef975523b06e23750c9441106067d1c7bb7b4ff7f0de87f267cfd8`. See [saved-workflow guidance](saved-workflows.md#forecast-method-studies) for the shared toolkit and application entry points. These results establish the bounded local demonstration; they do not establish continuous operation, deployment, or reliability on other questions.
