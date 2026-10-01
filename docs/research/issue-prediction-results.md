# First actual issue-prediction test

**Result:** local predictions and historical evaluation now run on a bounded real-data sample. **Neither model beat the simple baseline.** This resolves the two blocks for an exploratory facts-only test, not for the full application or the planned 112-case evaluation.

## What ran

- Selected the earlier 20 January candidates for training and the first eight currently searchable February issues for testing, before model execution. Excluded two missing original snapshots without replacement: #201663 and #203938.
- Trained on **19 issues**: seven recorded response gaps and twelve other outcomes. Tested on **seven later issues**: five gaps and two other outcomes.
- Ran the existing pinned CatBoost 1.2.10 and TabICL 2.2.0 classifier implementations locally, with two CPU threads and the already downloaded, hash-verified TabICLv2 checkpoint.
- Used creation-time title/body lengths, code-block presence, link count, hour, and weekday. No future comments, issue identifiers, outcomes, or model-generated text findings entered the inputs.
- Both saved models/context reproduced their predictions after restoration. No paid calls, GitHub writes, or operational model activation occurred.

## Historical evidence repaired

The public archive index was missing January 6, 2024, at 22:00 UTC. The full original hourly file was recovered and scanned. All **432 hourly slots** across January 1–9 and February 1–9 are now represented by the index or recovered file.

All relevant indexed creation, comment, and close/reopen records were reconciled with original archive payloads. Forty-nine original hourly files were fully scanned; total event counts matched the index in all 48 overlapping hours. Historical commenter roles came from the original payloads. Available GitHub comments and state histories were cross-checked. Missing originals remained excluded.

Labels mean **open at seven days without a qualifying maintainer comment recorded in this frozen public history**. This establishes observable source coverage; it cannot establish that GitHub captured every event or that no private work occurred. Source limits remain visible. All January training outcomes were available before any February test issue opened.

## Results

| Method | Probability error: lower is better | Actual gaps among first three selected |
| --- | --- | --- |
| Training-frequency baseline | 0.324 | 2 |
| CatBoost | 0.356 | 1 |
| TabICLv2 | 0.388 | 2 |

Probability error is the Brier score. The baseline gives every issue the training gap rate (36.8%); ties follow creation order. The oldest-first policy also found two gaps in its first three cases. No model was selected or tuned using these test results.

All methods predicted below 50% for every test case; all missed the five actual gaps at that threshold. Seven test cases cannot support a general accuracy claim. The training/test gap rates differ substantially (7/19 versus 5/7). Keep the baseline comparison and expand the frozen evaluation before considering operational use.

## Inspect or reproduce

The local evidence folder is `~/Library/Application Support/BackIntel/Evidence/IssuePredictionTest/`.

- `report.html`: seven actual prediction cards, original text, later outcomes, and method comparison. This is an inspection artifact, not the finished reviewer application.
- `predictions.json`, `cohort.json`, and `checks.json`: scores, excluded records, model identities, and direct checks.
- `evidence-manifest.json`: retained file hashes, including the research scripts and source replies. Third-party issue text remains outside the repository.
- `collect.py` retrieves/caches sources; `prepare.py` rebuilds labels and creation-only inputs; `predict.py` invokes existing local predictors; `report.py` renders stored results without inference.

Offline verification: run `python3 "$HOME/Library/Application Support/BackIntel/Evidence/IssuePredictionTest/report.py"`. Model reproduction from the BackIntel checkout: set `BACKINTEL_MODEL_DIR="$PWD/artifacts/Models"` and `PYTHONPATH="$PWD"`, then run `.venv/bin/python "$HOME/Library/Application Support/BackIntel/Evidence/IssuePredictionTest/predict.py"`. Source retrieval is separate; neither command contacts a paid provider.

Direct checks passed for label boundaries, bot/author exclusions, close/reopen ordering, future-field exclusion, time-separated evaluation, identical comparison cases, saved-model replay, and offline cohort reproduction. Peak model-process memory was approximately 748 MiB; the model loop including restoration took 8.36 seconds. Local compute cost is unpriced.

The original research execution did not change application runtime files. It was recorded against source hashes. Browser visual review, paid text interpretation, the full 112-case study, and integration into the standing background workflow remained outside that result.

## Review workspace replay

The seven retained cases passed a separate offline check through the review API and an isolated database. The check verified creation-only features against the original archived reports. Each packet preserved the opening text, issue identity, and stored prediction. Later outcomes stayed hidden until an explicitly labelled test decision was saved. Decisions survived a service restart; duplicate saves and stale source references were rejected. The live demo database was not written.

The check found and repaired a prediction handoff defect: changing the cohort order could attach an estimate to the wrong issue. The adapter now requires the exact cohort hash, matching case identities and order, complete prediction vectors, finite probabilities, and agreement with the per-case scores. Eight focused regression checks passed. These results apply to the uncommitted working tree based on `8b6c0a71e5dc9a3cd6d0840937b81631e6f15fa8`; exact-commit readiness remains blocked.

Local replay evidence is under `artifacts/validation/IssueWorkflow/Run8b6c0a7/`: `VerifyReplay.py`, `WorkflowResults.json`, `PacketsBeforeReview.json`, `PacketsAfterReview.json`, and the recorded working-tree patch. The replay used stored actual predictions and made no new model or paid provider calls. A fresh public-data model run awaits separate dataset approval.

Full agent readiness remains blocked. The five required semantic findings—failure, reproduction steps, expected/actual behavior, environment, and regression claim—are not produced. The public-case finding remains a rule-based suggestion. Automatic processing of later public-issue events is unfinished. Displaying a historical outcome after a test decision does not verify that processing. The recorded prediction comparison still fails to show improvement over the baseline.

Sources: [GH Archive](https://www.gharchive.org/), original hourly files listed in local evidence, [GitHub REST](https://docs.github.com/en/rest/issues), and [ClickHouse's public archive index](https://play.clickhouse.com/). Retrieval and execution: September 29, 2026 UTC.
