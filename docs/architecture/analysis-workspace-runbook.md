# Local continuous analysis workspace

Current measured results and remaining blockers are recorded in [analysis acceptance](analysis-acceptance.md).

The application lets a manager confirm a question, select permitted data, compare prediction methods, and inspect updated answers. The hosted analyst is `openai/gpt-6.1-sol` through OpenRouter Responses, restricted to OpenAI with fallback disabled. Local Decide handles classification; CatBoost and TabICLv2 handle predictions. No local planning language model is used.

## Setup

Use the canonical BackIntel checkout. Preserve the Olist services, data volumes, original `aegra.json`, and legacy validation manifest. The new `compose.analysis.yml` uses port 2028 and an isolated database on port 55438. Docker needs the selected 8GB allocation; the worker is capped at 5GB and two CPU threads.

Reuse the pinned model image already attached to the capability demo as `backintel-analysis-base:local`. If unavailable, build `Dockerfile.runtime` with `BACKINTEL_WITH_MODELS=1` and that tag. This preserves the approved model-library versions.

```sh
cd apps/web
npm ci
npm run build
cd ../..
python3 -m scripts.analysis_demo weights
docker compose -f compose.analysis.yml build
docker compose -f compose.analysis.yml up -d --wait
python3 -m scripts.analysis_demo provision
python3 -m scripts.analysis_demo schedule
python3 -m scripts.analysis_demo open --role manager
```

`provision` reuses the existing `BackIntel OpenRouter` Keychain item and writes only an ephemeral runtime copy into tmpfs. It stores opaque manager, analyst, and viewer access credentials in Keychain. The launcher opens a credential fragment and the frontend immediately removes it from browser history. Credentials never enter reports, source files, model context, or Git. Re-provision and reopen access after a container restart rotates ephemeral local credentials.

## Sources

Original files live under `~/Library/Application Support/BackIntel/Datasets/{Commerce,Support,Churn,Credit,Maintenance}`. Model weights and prepared artifacts live under ignored `artifacts/Models`. Source access and terms must be acknowledged before ingestion. No command accepts competition rules on behalf of the user.

```sh
python3 -m scripts.analysis_demo acquire --domain commerce --acknowledge-terms
python3 -m scripts.analysis_demo acquire --domain support --acknowledge-terms
python3 -m scripts.analysis_demo acquire --domain maintenance --acknowledge-terms
```

Churn requires confirmation of the original-author rights. Credit requires accepted Kaggle Home Credit competition rules and locally downloaded `application_train.csv` and `bureau.csv`. A blocked source stays blocked. Dataset attribution and terms are retained in source receipts.

The source screen confirms terms and imports registered files. Original archives are preserved. Source changes create new hashed snapshots; duplicate imports reuse the same snapshot. Records retain domain-specific features and source hashes instead of being converted to review records. Text-rich sources use a bounded 10,000-record cohort selected by stable identity hash. Original row counts and cohort counts are distinct. Credit uses a bounded deterministic applicant cohort and streamed bureau histories. FD001 keeps engine boundaries and official test labels.

## Daily use

Managers create and confirm standing goals, start initial model comparisons, approve a selected candidate, pause/resume goals, and apply source corrections. Analysts ask follow-ups and propose corrections. Viewers inspect permitted findings. The backend enforces all permissions; application clients cannot use core Aegra APIs to bypass them.

Hourly Aegra scheduling checks registered sources, starts affected goals, and dispatches pending durable jobs. Unchanged sources cause no frontier calls. Retraining needs 128 newly eligible labels and a day between candidates. Promotion always requires a manager. Review notes do not change source facts until a manager applies a correction.

New questions and notification thresholds create goal versions and require reconfirmation. Default change thresholds are five percentage points for classification targets and five target units for regression. Failed refreshes preserve the last completed answer. Findings distinguish observations, estimates, and hypotheses. Static arrivals and synthetic tickets are simulations, not proof of a live business connection.

The suite enforces $25 total, $5 per domain, and $1 per run. A run is limited to six frontier calls, twelve tool calls, and ten minutes. Reservations are durable before requests; actual provider charges replace reservations. An interrupted or unresolved paid request blocks further paid work until reconciled. CPU model comparisons have a thirty-minute limit. Unmeasured local compute cost remains explicitly unavailable.

## Evidence and readiness

Working-tree checks are development evidence. Required product evidence must match an approved exact candidate commit. Missing real datasets, model weights, frontier charges, browser evidence, or exact-candidate evidence yields `blocked`. A successful fixture check never proves real-model acceptance. Legacy Jev acceptance is preserved separately and is not satisfied by Decide.

Use `scripts/validation/check_analysis.py` for durable functional and source/model evidence. Report each domain separately. No aggregate product score, autonomous lending decision, production identity, live bank connector, external notification, deployment, or publication is implied.

## Run the benchmark

After setup, run `docker compose -f compose.analysis.yml exec -T runtime python -m scripts.analysis_benchmark`. This runs source-gated real comparisons and three independently checked frontier questions per available domain. It retains blocked domains and never approves a model replacement. Review candidates in React and promote the chosen predictor separately. Durable results are under `artifacts/Models/Analysis/benchmark-evidence.json`; the final real validator also requires complete five-domain evidence.

## Updated behavior

Source refresh requests return a durable run ID. Read `/api/v1/runs/{id}` and its events for progress. Long jobs reconnect to progress; the serial worker drains pending arrivals. Follow-up answers appear in Conversation and do not replace the standing answer. Threshold notifications compare matching group means. Promoted predictor routes are immutable. Corrections update group values and invalidate predictors trained on the corrected record.

Managers can read `/api/v1/runs/{id}/requests` and reconcile an uncertain charge through `POST /api/v1/requests/{request_id}/reconcile`. This reads provider telemetry and never repeats inference. A missing provider response identity remains blocked. Budget admission uses the approved model catalog pricing before a paid request.

The analysis validation manifest covers static, schema, semantic, workflow, visual, operational, and security checks. Each invocation saves durable evidence outside Git and can write its manifest sidecar with `--evidence-path`. Working-tree checks never establish exact-commit readiness. Credit and churn remain blocked until their source permissions are confirmed.
