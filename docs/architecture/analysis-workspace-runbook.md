# Local continuous analysis workspace

Current measured results and remaining blockers are recorded in [the current validation campaign](analysis-validation-campaign.md). Earlier benchmark evidence remains in [historical analysis acceptance](analysis-acceptance.md).

For the subsequent cloud setup fixes, actual IBM Telco comparison, prepared import/acquisition commands, and exact user-only configuration steps, see [setup and benchmark unblocking](analysis-unblock-report.md).

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

## Restored local checkout

The October 4 resume ZIP is restored at `/Users/hudson/Documents/GitHub/BackIntelLocalResume`, based on `f5e2b693476541ce9fb7598d5d759a28b74af2b3`. It contains the analysis workspace, not the later agent toolkit candidate. The existing checkout at `/Users/hudson/Documents/GitHub/BackIntel` retains its source changes.

The ignored `.env` selects the separate `backintel-local-resume` Docker project and reuses existing dataset files and model weights. Start it and open manager access without changing stored Keychain grants:

```sh
cd /Users/hudson/Documents/GitHub/BackIntelLocalResume
OPENROUTER_API_KEY= docker compose -f compose.analysis.yml up -d --wait
python3 -m scripts.analysis_demo open --role manager
```

Provider credentials and paid scheduling remain disabled for this recovery. Reconcile earlier cloud spending into this workspace's ledger under the existing $10 cap before enabling paid work. Source confirmations still apply. Home Credit files and the later agent toolkit source are missing. Local run receipts do not establish release readiness.

## Sources

Original files use `BACKINTEL_DATASET_DIR` with domain subdirectories `{Commerce,Support,Churn,Credit,Maintenance}`; the Mac default is `~/Library/Application Support/BackIntel/Datasets`. Compose's portable default is ignored `private/Datasets`. Model weights and prepared artifacts use `BACKINTEL_MODEL_DIR` (Compose defaults to ignored `artifacts/Models`). Source access and terms must be acknowledged before ingestion. No command accepts competition rules on behalf of the user.

```sh
python3 -m scripts.analysis_demo acquire --domain commerce --acknowledge-terms
python3 -m scripts.analysis_demo acquire --domain support --acknowledge-terms
python3 -m scripts.analysis_demo acquire --domain maintenance --acknowledge-terms
```

The owner authorized the five named datasets for benchmarking and testing on October 4. Retain that scope and dataset attribution in the source receipts. Home Credit downloads still require the Kaggle account's competition access and the files `application_train.csv` and `bureau.csv`; the acquisition helper does not provide account access.

The source screen confirms terms and imports registered files. Original archives are preserved. Source changes create new hashed snapshots; duplicate imports reuse the same snapshot. Records retain domain-specific features and source hashes instead of being converted to review records. Text-rich sources use a bounded 10,000-record cohort selected by stable identity hash. Original row counts and cohort counts are distinct. Credit uses a bounded deterministic applicant cohort and streamed bureau histories. FD001 keeps engine boundaries and official test labels.

## Daily use

Managers create and confirm standing goals, start initial model comparisons, approve a selected candidate, pause/resume goals, and apply source corrections. Analysts ask follow-ups and propose corrections. Viewers inspect permitted findings. The backend enforces all permissions; application clients cannot use core Aegra APIs to bypass them.

Hourly Aegra scheduling checks registered sources, starts affected goals, and dispatches pending durable jobs. Unchanged sources cause no frontier calls. Retraining needs 128 newly eligible labels and a day between candidates. Promotion always requires a manager. Review notes do not change source facts until a manager applies a correction.

New questions and notification thresholds create goal versions and require reconfirmation. Default change thresholds are five percentage points for classification targets and five target units for regression. Failed refreshes preserve the last completed answer. Findings distinguish observations, estimates, and hypotheses. Static arrivals and synthetic tickets are simulations, not proof of a live business connection.

The assigned validation campaign enforces $10 total, $5 per domain, $1 per run, and $0.25 per request. At most 200 requests may be admitted, with one request in flight. A run is limited to six frontier calls, twelve tool calls, and ten minutes. Reservations are durable before requests; actual provider charges replace reservations. An interrupted or unresolved paid request blocks further paid work until reconciled. CPU model comparisons have a thirty-minute limit. Unmeasured local compute cost remains explicitly unavailable.

## Evidence and readiness

Working-tree checks are development evidence. Required product evidence must match an approved exact candidate commit. Missing real datasets, model weights, frontier charges, browser evidence, or exact-candidate evidence yields `blocked`. A successful fixture check never proves real-model acceptance. Legacy Jev acceptance is preserved separately and is not satisfied by Decide.

Use `scripts/validation/check_analysis.py` for durable functional and source/model evidence. Report each domain separately. No aggregate product score, autonomous lending decision, production identity, live bank connector, external notification, deployment, or publication is implied.

## Run the benchmark

After setup, run `docker compose -f compose.analysis.yml exec -T runtime python -m scripts.analysis_benchmark`. This runs source-gated real comparisons and three independently checked frontier questions per available domain. It retains blocked domains and never approves a model replacement. Review candidates in React and promote the chosen predictor separately. Durable results are under `artifacts/Models/Analysis/benchmark-evidence.json`; the final real validator also requires complete five-domain evidence.

## Updated behavior

Source refresh requests return a durable run ID. Read `/api/v1/runs/{id}` and its events for progress. Long jobs reconnect to progress; the serial worker drains pending arrivals. Follow-up answers appear in Conversation and do not replace the standing answer. Threshold notifications compare matching group means. Promoted predictor routes are immutable. Corrections update group values and invalidate predictors trained on the corrected record.

Managers can read `/api/v1/runs/{id}/requests` and reconcile an uncertain charge through `POST /api/v1/requests/{request_id}/reconcile`. This reads provider telemetry and never repeats inference. A missing provider response identity remains blocked. Budget admission uses the approved model catalog pricing before a paid request.

The analysis validation manifest covers static, schema, semantic, workflow, visual, operational, and security checks. Each invocation saves durable evidence outside Git and can write its manifest sidecar with `--evidence-path`. Working-tree checks never establish exact-commit readiness. The current campaign record distinguishes verified offline workflows from stages needing live inputs and credentials.

## Portable offline campaign

Use Python 3.12, Node 22.22.2 or Node 24.15.0 or newer, and local disposable PostgreSQL/Redis services. Install the pinned test/runtime dependencies, build the web app, and install the pinned browser:

```bash
python -m pip install -r requirements.testing.txt
npm ci --prefix apps/web
npm run build --prefix apps/web
npm run test:receipt --prefix apps/web
(cd apps/web && npx playwright install chromium)
```

Set `BACKINTEL_VALIDATION_ADMIN_URL` to the local PostgreSQL admin URL and `BACKINTEL_VALIDATION_REDIS_URL` to the local Redis URL through the environment. Set `NODE_PATH` to the absolute `apps/web/node_modules` directory. For a system Chromium installation, optionally set `BACKINTEL_CHROMIUM_EXECUTABLE` to its absolute executable path.

Set `BACKINTEL_VALIDATION_POSTGRES_CONTAINER` to that local PostgreSQL container's name or ID to add the full dump/restore proof. This invokes its own `pg_dump`/`pg_restore` over the local Docker daemon; passwords pass through the subprocess environment and are redacted from logs. Hosted CI supplies its service-container ID.

```bash
python scripts/validation/run_analysis_offline.py --mode unit --output artifacts/AnalysisValidation/local-unit
BACKINTEL_UNIT_OUTPUT=artifacts/AnalysisValidation/local-regression python scripts/validation/check_units.py
python scripts/validation/run_analysis_offline.py --mode e2e --broker-recovery --output artifacts/AnalysisValidation/local-e2e
```

The component suite uses pinned Vitest, React Testing Library, jsdom, and V8 coverage. It writes `apps/web/coverage/test-results.json` and `coverage-summary.json`. This report supplements the browser matrix; a broad coverage percentage alone is not acceptance. Build before starting E2E and keep the built assets stable for the entire run.

`--broker-recovery` creates a uniquely named Redis container from the locally available `redis:7.2.5-alpine` image, binds a random loopback port, and enforces 128MB, half a CPU, and 64 PIDs. It stops and restarts only that owned container, proves durable admission through the outage, and removes it afterward. The existing Redis service is preserved. Docker settings are unchanged; no image is pulled by this check. Omit the flag to use the provided Redis URL and record broker interruption as untested.

Each output directory must be new so failures are preserved. Each invocation creates its own `backintel_*_test` database and removes it afterward. E2E uses port 2028 by default (`--port` changes the listen port); browser writes currently allow origins at port 2028, so use the default for the rendered journey. E2E creates synthetic inputs for all five adapters and substitutes only provider/model responses. It runs the real Aegra API, PostgreSQL, Redis worker, and native scheduler. Receipt `mode: fixture` and synthetic source caveats prevent this evidence from qualifying as a live model benchmark. Unit execution rejects external provider transport and does not discover provider credentials. The all-module regression runner uses the same local admin binding, creates a separate database per Python test module, clears provider bindings, records test/skip counts, and removes each owned database. Analysis modules receive their required analysis database flag rather than silently skipping their database cases.

The E2E receipt records the five import/goal/answer/evidence/follow-up paths and independent group/count/mean oracles, a failed answer, model approval and prediction fixtures, source correction and internal notification, six desktop/mobile role journeys, keyboard evidence inspection, and a bounded native-clock cron. It also kills the fixture runtime during a running import, restarts it, and verifies that the same job completes in its second attempt with no provider requests. The owned-broker case stops Redis during admission, observes the queued PostgreSQL job and dispatch-pending event, restarts Redis, and resumes the same accepted job without provider calls. When configured, it dumps the fixture database, restores it into a fresh database, compares evidence/results/provider identities, and removes that database. It removes its server, access file, owned Redis prefix, native cron, and primary test database. Receipts contain candidate commit, dirty state, dependency/configuration fingerprints, fixture ledger, timings, memory boundary, cleanup, and artifact hashes. Keep evidence from a dirty tree identified as such.

The `analysis-quality.yml` workflow runs static checks and these offline campaigns on pull requests. Hosted CI has not been run by this local campaign. Paid campaigns require their recorded authorization, actual permitted source files and model weights, current pricing, and an injected analyst credential. Ordinary CI does not receive provider secrets.

## Expiry and error privacy

A manager can set `expires_at` with a timezone through `PATCH /api/v1/principals/{id}`. The API and queued-work admission recheck expiry using the database clock. Omitted expiry preserves the existing setting; explicit null removes it. Existing local grants remain without expiry until configured. Managers can change grants only for sources within their own scope; worker grants are excluded from this endpoint.

Configured analyst, access-file, database URI, and bearer credentials are redacted before errors are written to API responses, source errors, run results, events, or append-only application evidence. Synthetic-secret regression checks verify these paths. General host logs and live-provider echo behavior still require review in the real campaign.
