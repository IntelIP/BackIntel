# Continuous analysis acceptance

Recorded October 2, 2026. Overall result: **blocked**. This is a local working-tree demonstration on `codex/poc-foundation-20260929`, based on commit `c4565a00f4e073d09f626fbdda134feffed5cb14`. It is not exact-commit acceptance, publication, or deployment.

Managers can register sources, confirm goals, request analysis, inspect calculations, compare predictors, approve a predictor route, and review history in the local React workspace. Follow-ups preserve the standing answer. The isolated runtime is available at `http://127.0.0.1:2028`; use the role launcher described in the [runbook](analysis-workspace-runbook.md).

## Domain evidence

| Domain | Current result | Real evidence |
| --- | --- | --- |
| Commerce | passed for available-source benchmark | Three independently checked answers; real Decide, simple text baseline, CatBoost, and TabICLv2 comparisons. |
| Support | passed for available-source benchmark | Three independently checked answers; real Decide and predictor comparisons using intake information. Synthetic tickets remain labeled. |
| Maintenance | passed for available-source benchmark | Three independently checked answers; real predictors, separate train/test engine identities, and all 100 official FD001 test cases. |
| Churn | blocked | Source permission remains unconfirmed; no import or substitution. |
| Credit | blocked | Home Credit competition access and rules remain unconfirmed; no import or substitution. |

Commerce and maintenance show measured improvements in these selected cohorts. Support gains are small. No production benefit is established.

| Method | Commerce ROC AUC / Brier error | Support mean absolute error, hours | Maintenance mean absolute error, cycles |
| --- | --- | --- | --- |
| Constant baseline | 0.5000 / 0.1574 | 30.9283 | 41.2512 |
| Simple text | 0.8947 / 0.1288 | 31.6699 | — |
| CatBoost, facts | 0.5476 / 0.1607 | 30.8087 | 19.7603 |
| TabICLv2, facts | 0.4890 / 0.1595 | 29.6607 | 17.7215 |
| CatBoost, facts and Decide | 0.8531 / 0.1033 | 30.1561 | — |
| TabICLv2, facts and Decide | 0.8659 / 0.0906 | 29.8248 | — |

Higher ROC AUC is better; lower Brier and absolute error are better. Commerce uses 512 training, 128 calibration, and 256 test records. Support has 130 eligible test records after chronological and entity restrictions. Maintenance has 512 training, 128 calibration, and 100 official test engines. Calibration results are stored separately in model manifests. Decide improves commerce probability error, while simple text has the highest commerce ROC AUC. Decide does not improve the support TabICLv2 result.

Recorded frontier charges total **$0.046259235**, including historical interrupted/partial runs. No charge is unresolved. Local compute dollar cost is unmeasured. Real model process peaks are approximately 4.40 GiB for the text scenarios, within the configured 5 GiB worker ceiling. These measurements do not establish simultaneous workload capacity.

## Required checks

| Evidence | Result | Boundary |
| --- | --- | --- |
| Static build, dead-code checks, compilation | passed | Working tree. |
| Validation contract schema | passed | Manifest shape. |
| Functional checks | passed | Deterministic fixtures cover adapters, budgets, partial resume, failed refresh, candidate threshold/daily limit, corrections, promotion, and permissions. |
| Security checks | passed | Focused permission, evidence isolation, budget, correction, resume, and unapproved provider-response checks. Routing refusal uses a labeled fixture response. |
| Rendered React journeys | passed | Commerce, manager/analyst/viewer, desktop/mobile, follow-ups, review/history, and calculation inspection. Screenshots inspected. |
| Five-domain semantic and real-operation gates | blocked | Churn and credit are unavailable. |
| Complete five-domain continuous scenarios | blocked | Available fixtures and recovery evidence do not establish every required real journey across all five domains. Live source-text instruction resistance and full five-domain rendered journeys remain required. |
| Exact-candidate validation | blocked | Uncommitted tree; no exact candidate commit; validation CLI unavailable on PATH. |

The benchmark receipt is stored outside tracked source at `artifacts/Models/Analysis/benchmark-evidence.json`. Durable validator evidence is under `~/Library/Application Support/BackIntel/Evidence/Analysis`; manifest sidecars are under `artifacts/AnalysisValidation`. The existing legacy Olist acceptance record remains separate. No autonomous lending decision, production identity, bank connector, external notification, or model promotion is implied by this report.

Latest validator invocations:

- Static: `a906ebfcbf8049889f0aea44174dc6d8/evidence.json`.
- Schema: `89f5df791e4b4bfcbe4efdc2ad047c58/evidence.json`.
- Functional: `8c7e05c741e6460082036e4d9ea38062/evidence.json`.
- Security: `87223481bda844e599a9eae504c24c2d/evidence.json`.
- Rendered: `31cb517ab4264142baa43164d9c3f5ae/evidence.json` and its `Browser` screenshots.
- Semantic: `a6b222814c904503990a5ad697c9149d/evidence.json`.
- Real operation: `5f171de16aef4d3e88046c1c3a0a05a2/evidence.json`.

These paths are relative to the durable evidence directory above. Functional and security logs explicitly distinguish fixture controls from real-provider results.

Finish by confirming source permissions, importing the selected datasets, completing the remaining real scenarios, and validating an authorized exact commit. Publication needs its separately authorized workflow.
