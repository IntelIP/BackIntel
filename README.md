# BackIntel

The [interactive decision workspace demo](frontend/README.md) lets a reviewer inspect a finding, open evidence and record a decision. React and the Python Reflex alternative share one local review API.

BackIntel targets a recurring operational problem: before a team can decide what needs attention, someone must gather scattered records, read free-text notes, reconcile changes, judge significance, and assemble a review people can trust. New information can make that review stale and force the same work again. This is the problem hypothesis we are testing; its frequency and cost still need validation with a real team.

The intended outcome is a current, prioritized review package showing what changed, what might happen next, what evidence supports each finding, and what still needs human judgment. BackIntel automates preparation and follow-up through approved data admission, structured interpretation, prediction, attention tracking, and reports. Operations analysts and supervisors retain responsibility for investigation, intervention, and business decisions.

The current implementation is a predefined background workflow with model-assisted interpretation and prediction. Code controls its sequence, schedules, and permissions. It is developed against synthetic scenarios; the existing Olist PoC remains an optional integration example. Whole-job replacement, real-world predictive accuracy, and staff time saved have not been demonstrated.

- [Current roadmap](docs/roadmap/v0.1.0-development-roadmap.md) — six steps to test and demonstrate issue review
- [Detailed capability reference](docs/roadmap/capability-reference.md) — full acceptance contract and supporting research
- [Current repository map](docs/architecture/repository-map.md)
- [Recovery plan and cleanup record](docs/roadmap/poc-recovery-plan.md)

## Run the capability simulation

The [active goal](docs/roadmap/v0.1.0-development-roadmap.md) requires real Jev interpretation and real CatBoost/TabICLv2 execution on synthetic data, followed by analysis, attention and useful stakeholder reports. Actual local predictors, durable follow-ups and report packaging now work with clearly labelled Jev fixtures. One actual Jev probe passed; the complete two-scenario Jev run remains unfinished. The command below is a development fixture; its simulated answers cannot satisfy final completion. Google TabFM is a separate model choice.

```sh
python3 -m scripts.simulate
```

Two synthetic domains use one engine: JSON support tickets and CSV equipment readings. No dataset download, model key, server, or dependency installation is needed. Reports and JSON outputs appear in `~/Library/Application Support/BackIntel/Evidence/Simulation`.

The scenarios exercise mapped ingestion, source lineage, rule-based simulated extraction, comparisons, missing observations, injected failure/retry, duplicate replay, simulated schedule events, acknowledgment/staleness/recovery, and audience-specific reports. Each artifact labels its synthetic inputs and simulation boundaries. Forecast output is an unevaluated linear stand-in; generated-code execution is deferred.

Use `--scenario support` or `--scenario equipment` to select one; use `--output /absolute/path` to choose another output location. `python3 -m unittest discover -s tests -p test_simulation.py -v` runs the offline workflow checks.

The new `capability_simulation` graph also plugs into the existing LangGraph/PostgreSQL runtime. Its registration is source code until an approved runtime update; the offline command already exercises the same core functions.

The durable development journey uses a separate local service, preserving the installed Olist service and its data:

```sh
.venv/bin/python -m scripts.capability_demo --development --demo-id demo-v1 --verify-recovery --wait
```

This builds the isolated service from `Dockerfile.runtime` and starts it on localhost:2027. Both synthetic scenarios complete durable source changes, comparisons, prediction-driven attention, model-update controls, audience reports and actual sandbox execution of a fixed generated-view fixture. The command restarts only the isolated runtime while work is pending, verifies replay, then packages scoped HTML/JSON/CSV reports, source code, execution logs and review receipts. Exported HTML is read-only and links to local evidence files, so it can be read without the viewer. It uses simulated predictors; final real-model acceptance remains separate.

Use a fresh demonstration ID for `--verify-recovery`. To resume or replay that same stream, reuse its ID without that flag. Inspect with `python3 -m scripts.capability_demo --status --demo-id demo-v1`. Add `--serve` to the command to open the scoped local viewer after packaging; it prints a loopback login URL and the path to private one-hour audience tokens. Stop the viewer with Ctrl-C. The native scheduler stops after the bounded run, or after two minutes if the client disconnects. Each invocation retains its own receipt directory under `artifacts/validation/CapabilityDemo/<demo-id>/Attempt...`; the isolated database volume retains recovery state.

## Approved local model and sandbox checks

Real CatBoost and TabICLv2 now execute classification and regression on synthetic structured features. The full facts-plus-real-Jev comparison remains unfinished. Model use requires the matching local approval record and pinned weights; it never authorizes paid Jev calls. The original Olist runtime stays separate.

After preparing the approved `.venv`, model directory and a dedicated `test_` database, run:

```sh
export BACKINTEL_MODEL_DIR="$PWD/artifacts/Models"
export BACKINTEL_APP_DATABASE_URL="$BACKINTEL_TEST_DATABASE_URL"
OMP_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2 MKL_NUM_THREADS=2 HF_HUB_OFFLINE=1 \
  .venv/bin/python -m scripts.validation.check_real_models
.venv/bin/python -m scripts.validation.check_sandbox
```

The sandbox check uses the existing local `backintel-capability-demo-runtime` image and actually attempts prohibited operations. Results are retained under `artifacts/validation/RealPredictors` and `artifacts/validation/Sandbox`. These checks establish subsystem behavior on an uncommitted working tree, not final acceptance. The sandbox returns an untrusted candidate for later review; it does not publish a report.

The optional model-enabled image also runs both predictors on CPU, using the approved local weights and two threads. Build it with `BACKINTEL_WITH_MODELS=1 docker compose -f compose.capabilities.yml build runtime`, then start the isolated service with `docker compose -f compose.capabilities.yml up --detach --wait --no-build runtime`. The default image build omits model dependencies. No provider credential is configured by Compose.

Prepare committed synthetic histories through that service without spending money:

```sh
.venv/bin/python -m scripts.real_capabilities prepare \
  --scenario support --demo-id real-demo-v1 --request-id history-preparation
```

Repeat with `--scenario equipment` for the second domain. Reusing the same request and demonstration identities replays the completed stage. `interpret` requires the exact source hash, a separately approved provider authorization and an ephemeral runtime credential. `compare` rejects incomplete or simulated Jev history and unknown actual charges. The stages now include the durable follow-up path described below; the complete real-run driver remains unfinished. Receipts remain under `artifacts/validation/RealPipeline`.

Actual Linux model checks and file/checkpoint recovery passed in `artifacts/validation/RealPredictorsLinux` and `artifacts/validation/RealModelRecovery`. Recovery restored the approved files into a temporary directory and reproduced all 24 recorded predictions. That earlier check used the existing isolated evidence database. Combined recovery now reproduces 50 predictions and replays 90 completed jobs from restored database and model files, using Jev fixtures. Final actual-Jev recovery remains pending.

The real path now also prepares future arrivals and corrections as immutable, time-scoped synthetic records:

```sh
.venv/bin/python -m scripts.real_capabilities prepare_followups \
  --scenario support --demo-id real-demo-v1 --request-id future-source-preparation
```

Future records stay outside earlier feature cutoffs. After separate approval covering the prepared history and future sources, the `start` stage accepts `--authorization <approved-id>` and durably queues interpretation, comparison and follow-ups. Each scenario needs a scope covering 27 source versions. The existing one-request probe cannot authorize this batch. Every paid request still checks its own budget and approval; failed or uncertain requests stop subsequent work for that task.

Both scenarios completed 45 durable jobs with actual local predictors and **fixture Jev responses**. The check advances due timestamps in an isolated test database; it does not prove a live paid Jev journey or native-clock execution of that journey. Corrections invalidate earlier predictions and exclude superseded sources from subsequent training. Replaying all completed jobs changes no records and makes no extra fixture calls. The receipt is `artifacts/validation/RealFollowups/Attempt333bb285ed2d/Followups.json`.

Prepare both scenarios without provider access:

```sh
.venv/bin/python -m scripts.real_demo --demo-id real-driver-v1 --prepare-only
```

This builds the isolated model-enabled service and writes `AuthorizationScopes.json` under `artifacts/validation/RealDemo/<demo-id>/Attempt...`. Each scope names the exact task, questions and 27 source versions. Startup refuses to replace a runtime with pending work. Use `--no-start` to reuse an existing compatible service and resume its workload.

After separate approval for both complete scopes, use the same demonstration ID:

```sh
.venv/bin/python -m scripts.real_demo --demo-id real-driver-v1 \
  --authorizations /absolute/path/Authorizations.json --verify-recovery
```

The authorization file maps scenario names to existing approved authorization records. Writing this file does not grant approval:

```json
{"support": "existing-approved-support-id", "equipment": "existing-approved-equipment-id"}
```

The driver checks both scopes, request limits, pricing, measured budget and expiry before retrieving the existing Keychain credential. It places the credential in an owner-bound, task-bound, expiring file on runtime memory storage (`tmpfs`, directory `0700`, file `0600`). It never places the key in command arguments or Docker environment configuration. Cleanup removes only that attempt's credential and scheduler. An optional restart preserves pending work and reinstalls the authorized credential afterward. A failed or uncertain provider request stops further paid work for that task.

Preparation, unauthorized-run denial, scoped native-clock scheduling and restart recovery passed without paid calls. Full paid execution remains unverified. The approved one-request Jev probe passed at a measured provider charge of $0.000011592. It returned `typesafe/jev-1.13-20260917` for the requested `jev-1.13` alias. Its saved response was accepted after a narrow model-name compatibility fix, without another paid call. That approval does not authorize either complete source scope. See `artifacts/validation/RealModelPreparation/ProbeAcceptance.json`.

Packaging has explicit `development`, `real` and `predictor_fixture` modes. Real mode requires actual predictors, actual Jev and complete provider billing. Fixture mode labels simulated text findings and separates fictional charges from actual spending. Both ordinary and sandbox-generated offline reports passed desktop/mobile checks. All results remain working-tree evidence; paid Jev and exact committed-candidate acceptance are separate gates.

## Local audience reports

The working tree now produces audience-scoped briefings, analysis, CSV/JSON exports and source evidence. Operators can review and correct observations; read-only audiences cannot. Corrections preserve history and refresh the report. Generated layouts execute in the restricted host sandbox and require a separate local review. Development checks still use explicitly simulated models.

After running the updated development code against an isolated database, open reports for its completed task IDs:

```sh
export BACKINTEL_APP_DATABASE_URL="$BACKINTEL_TEST_DATABASE_URL"
.venv/bin/python -m scripts.audience_demo \
  --task support-audience-v1 --task equipment-audience-v1 \
  --access-file artifacts/validation/Audiences/local-access.json
```

The task IDs must match the chosen demonstration ID; `audience-v1` is an example. Open the printed loopback login page and use the appropriate token from the new private access file. Tokens last one hour, bind a task version and audience, and never appear in URLs or logs. The access file must not already exist. Stop the viewer with Ctrl-C. The isolated development image now includes the audience workflow; the preserved Olist service remains unchanged.

Direct checks: `python -m scripts.validation.check_audiences` exercises actual HTTP authorization, report actions and generated-code review against an explicitly isolated test database. The browser companion is `scripts/validation/check_audience_ui.cjs`; it uses Playwright, a live local viewer and the private fixture emitted by the direct check. Evidence includes desktop/mobile captures, keyboard source inspection and table scrolling, saved corrections, and denied access. Full real-model packaging remains unfinished.

A separate restore check backs up the completed development database, restores it into a fresh `test_` database on the existing isolated validation PostgreSQL container, compares accepted evidence, replays completed jobs, and removes the temporary clone:

```sh
.venv/bin/python -m scripts.validation.check_capability_restore --demo-id demo-v1
```

This check currently requires the local `backintel-capability-test` PostgreSQL container on port 55436. Its backup and receipt remain under `artifacts/validation/CapabilityRestore`. To restore an isolated predictor evidence database and approved model files together, set both database variables to that source database and run:

```sh
.venv/bin/python -m scripts.validation.check_real_model_restore \
  --predictor-receipt /absolute/path/PredictorReceipt.json --restore-database \
  --predictor-image sha256:<existing-image-that-prepared-the-models>
```

Omit `--predictor-image` only when the host libraries match the prepared packages. The check uses a fresh temporary database on the validation server, restores package/checkpoint files into a temporary directory, reproduces recorded predictions and replays completed jobs. It preserves a backup and receipt, then removes both temporary restores. It does not restore the live scheduler or broker, and fixture Jev evidence cannot establish actual Jev recovery.

## Preserved Olist runtime

The local stack now runs from this canonical checkout. Runtime candidate: `741773df289866437b067c306d6fefea1b415691`. The eight historical backend worktrees have been deleted; their commits remain in `main` and the recovery bundle. The separate website remains untouched.

Health endpoint: <http://127.0.0.1:2026/health>. Reports and submission receipts live outside Git at `~/Library/Application Support/BackIntel/Evidence/PoCReports`. The installed runtime has no provider key enabled. Its recorded demo, graceful restart, and replay checks passed without new inference calls. Required total-cost acceptance remains blocked for unpriced local compute and human review.

Run a new recorded demo on the installed stack; choose an unused receipt filename:

```sh
docker exec backintel-runtime-proof-runtime-1 python -m scripts.poc demo \
  --previous-partition openrouter-olist-2017-02-v1 \
  --partition openrouter-olist-2017-03-v1 \
  --receipt /reports/my-demo.json

docker exec backintel-runtime-proof-runtime-1 python -m scripts.poc inspect \
  --receipt /reports/my-demo.json --wait
```

The original database password is preserved in macOS Keychain, service `BackIntel Local PostgreSQL`, account `aegra`. The existing provider credential is preserved under service `BackIntel OpenRouter`, account `runtime`; retrieving it for inference requires separate authorization. No repository `.env` file is needed. Before an authorized future rebuild, inject the database password without printing it and keep paid inference disabled:

```sh
export BACKINTEL_RUNTIME_DB_PASSWORD="$(security find-generic-password -s 'BackIntel Local PostgreSQL' -a aegra -w)"
export OPENROUTER_API_KEY=""
```

Cutover and cleanup receipts: `~/Library/Application Support/BackIntel/Evidence/PoCRecovery/{cutover-acceptance,cleanup-receipt}.json`. Recovery set: `~/Library/Application Support/BackIntel/Recovery/20260926T170122/runtime-cutover`. Migration 0006 changes the snapshot uniqueness key; rollback requires restoring the coordinated application/checkpoint/broker backups before starting the previous image.

## Run the preserved Olist PoC

Use the existing Python/PostgreSQL/Aegra stack. The demo defaults to replaying recorded observations and makes **no inference calls**. Missing recordings are an error; they are never replaced with fabricated Jev output.

Prerequisites: Docker Compose; approved Olist v2 files outside Git; an isolated local application database; and, for the no-spend demo, its previously recorded accepted observations. The local database snapshot under `~/Library/Application Support/BackIntel/Evidence/PoCRecovery/recorded-demo.pgdump` preserves this machine's existing facts and recordings. Keep that licensed data private and outside Git. A fresh facts-only load does not invent those recordings.

For a new, separately approved local runtime, set the following in your shell or ignored `.env`. Generate your own database password. Set the candidate SHA from a clean checkout before building.

```sh
export BACKINTEL_CANDIDATE_SHA="$(git rev-parse HEAD)"
export BACKINTEL_REPORT_DIR="$HOME/Library/Application Support/BackIntel/Evidence/PoCReports"
mkdir -p "$BACKINTEL_REPORT_DIR"
# Set BACKINTEL_RUNTIME_DB_PASSWORD through your local secret source.
docker compose -f compose.runtime.yml up --build -d
```

Do not run that command over the existing demonstration runtime until its transition is approved. Runtime/API binds only to loopback. Its checkpoint database, application facts database, and Redis broker serve different purposes.

The setup entrypoint creates the application database only when requested, applies every migration in order, verifies source fingerprints, and loads or reconciles the approved files. From a Python environment with `requirements.txt` installed and `BACKINTEL_APP_DATABASE_URL` set:

```sh
python -m scripts.poc setup --create-database \
  --data-dir "$HOME/Library/Application Support/BackIntel/Datasets/OlistV2"
```

Inside a container, provide the dataset through an explicitly approved read-only mount or run setup from a local environment that can reach the database. The database name must be `backintel_app`, or an explicitly configured test database ending in `_test`/starting with `test_`. Never point validation at the demonstration database.

To reproduce the recorded demo in a fresh isolated database, restore the retained snapshot with PostgreSQL's native `pg_restore --no-owner`, then run `python -m runtime.bootstrap` from the current candidate. That preserves original provider request IDs, source hashes, costs, and old snapshots; migration 0006 gives corrected attribution its own version.

Submit and disconnect:

```sh
python -m scripts.poc demo \
  --previous-partition openrouter-olist-2017-02-v1 \
  --partition openrouter-olist-2017-03-v1 \
  --receipt "$HOME/Library/Application Support/BackIntel/Evidence/PoC/demo-run.json"
```

Inspect the **same receipt** later; add `--wait` for a bounded terminal wait. Use a new receipt filename only for a deliberate replay.

```sh
python -m scripts.poc inspect \
  --receipt "$HOME/Library/Application Support/BackIntel/Evidence/PoC/demo-run.json" --wait
```

The result identifies HTML/JSON artifacts, hashes, source examples, candidate identity, and cost disposition. Container `/reports` paths correspond to `BACKINTEL_REPORT_DIR` on the host. `--base-url` selects an isolated validation runtime at submission; the receipt remembers it.

## What the demo proves

An accepted recorded review batch can run in the background, derive corrected versioned signals, compare two batches, and produce a review with source evidence. Replaying identical accepted inputs reuses observations and artifact content. Unknown categories and multi-seller orders do not receive category attribution.

The two five-review samples demonstrate integration. They do not establish population trends, verified complaint rates, model accuracy, seller responsibility, human time savings, or full v0.1.0 readiness. Provider charges, local compute, and human review stay separate; unknown required costs remain blocked.

## Validation

Set `BACKINTEL_TEST_DATABASE_URL` to a disposable, explicitly test-named database. Offline checks use synthetic fixtures and no paid calls:

```sh
python -m unittest discover -s tests -p test_olist_facts.py -v
python -m scripts.validation.check_runtime
node scripts/validation/run.mjs --manifest tabellio.validation.json \
  --expected-commit "$(git rev-parse HEAD)" --output artifacts/validation/local
```

Exact-commit validation requires a clean checkout. Preserve durable evidence outside the checkout. The manifest's offline pass does not substitute for the real recorded-data background run, recovery/cancellation checks, rendered review, or total-cost acceptance.
