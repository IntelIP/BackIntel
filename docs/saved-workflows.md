# Saved workflows

A saved workflow keeps the accepted preparation rules, field meanings, calculation method, checks, limits and source references. It can process another complete collection from the same permitted objective and schema. Changed objectives or incompatible inputs require a newly checked workflow version.

The toolkit and platform call the same durable workflow job. Its first invocation prepares every input row, checks it against the originals, and computes the answer with the saved method. No model request is needed. Repeating the same version and input reuses its run. An interrupted attempt retains completed pages and stages; submit the same invocation to resume it. Failed work preserves the previous useful answer.

## Toolkit

Use the existing approved application database and access credential through `BACKINTEL_APP_DATABASE_URL` and `BACKINTEL_ACCESS_TOKEN`. Supply credentials through the approved environment or credential store; do not place secret values in arguments or saved packages.

```sh
python -m runtime.source_workflows inspect WORKFLOW_VERSION
python -m runtime.source_workflows run WORKFLOW_VERSION
python -m runtime.source_workflows run WORKFLOW_VERSION --input-ref COLLECTION_RUN_ID
```

Add `--no-wait` to queue the run and return its identity. Otherwise the command dispatches work and returns the result. A failed or incomplete result has a nonzero exit status.

Python callers use the same entry point:

```python
from runtime.source_workflows import invoke
from runtime.analysis_service import dispatch
from runtime.analysis_store import run

queued = invoke(workflow_version, authorized_actor, input_ref=collection_run_id)
dispatch(queued['id'])
result = run(queued['id'])
```

`authorized_actor` is an existing authenticated application principal. The current source grant and objective version are checked again at admission, execution and publication.

## Application

Send an authenticated `POST /api/v1/workflows/{version}/runs` with `{}` for the original accepted collection, or `{"input_ref":"COLLECTION_RUN_ID"}` for another complete permitted collection. The response contains the run identity. Read its result at `GET /api/v1/runs/{id}`.

The platform offers **Run saved workflow** beside each saved version and a collection selector. The returned result includes the workflow version, input reference, complete coverage, findings, calculation evidence, limitations and measured usage. Missing dependencies, incompatible input contracts, denied access and failed meaning checks remain explicit failures.


## Checked updates and repair limits

An update keeps the last accepted answer until its new source records pass the saved preparation rules, independent value and completeness checks, and any applicable method-performance check. Missing required fields or row identities, unreconciled records, and worse measured forecast error require review. Automatic preparation must preserve source values and declared business meanings.

Each attempted update records the source observation time, reused definitions and completed steps, recomputed steps, and any decision needed. Successful updates to changed inputs save a new immutable checked workflow version. Replaying an older successful invocation does not restore its answer over a newer accepted one.

The saved forecast method is measured on the latest four complete weeks and compared with its accepted final-test average weekly absolute error. It is not searched, tuned, or promoted during a refresh. Unchanged observations and predictions make no new performance claim. These retrospective comparisons do not establish future forecast accuracy.

Read the same update state from the toolkit or application:

```sh
python -m runtime.source_workflows status WORKFLOW_VERSION
```

```python
from runtime.source_workflows import update_status
state = update_status(goal_id, authorized_actor)
```

The authenticated application endpoint is `GET /api/v1/goals/{id}/update-status`. The application shows the last accepted answer and source time beside the latest attempt, failed checks, and required decision.

## Refresh from the connected source

Choose a saved workflow and **Refresh from source** in the application. The toolkit uses the same request:

```sh
python -m runtime.source_workflows refresh WORKFLOW_VERSION --request-id retail-refresh-001
```

Reuse the request identity to resume the same collection and answer. Use a new identity to observe a later source state. `--no-wait` queues the request durably. The authenticated application endpoint is `POST /api/v1/workflows/{version}/refresh` with `{"request_id":"retail-refresh-001"}`. Python callers use `runtime.source_workflows.refresh(version, actor, request_id)` and the existing dispatcher.

PostgreSQL supplies primary keys and row fingerprints inside one consistent read snapshot. BackIntel fetches changed values and reconstructs complete current inputs from verified originals. It scans every current key and fingerprint; this is not a database change-feed subscription. A first read or incompatible source layout requires a disclosed full reread. Saved preparation, independent value checks, and analysis still cover the complete current dataset. The update report records reused definitions, recomputed stages, fetched values, scanned fingerprints, additions, corrections, deletions, exclusions, failures, and pending records.

Deleted records leave current totals. Original values and deletion records remain retained. Read the bounded history with `GET /api/v1/runs/{collection_run_id}/source-changes?offset=0&limit=100` or `runtime.source_collection.change_history(collection_run_id, actor)`. Entries link original and current retained input identities; the existing authenticated original-input endpoint returns their unchanged payloads. Current source permission is required for both history and originals.

Collection and saved analysis use the existing durable jobs. After collection succeeds, the dispatcher admits its linked workflow and recovers this admission after an interruption. A successful collection receipt alone does not mean an answer was accepted. Inspect the shared update status for the accepted answer and source time. Failed collection or review-required analysis preserves the previous answer. If source content changes while an interrupted collection is resumed, start a new request so snapshots are not mixed. Local acceptance does not establish production throughput or sustained freshness.

## Events and bounded schedules

The owner can configure automatic starts beside a saved workflow in the application. Choose the permitted event source, an optional first run time, the displayed timezone, an expiration and a maximum number of accepted starts. Scheduled starts use Aegra's existing native timer and the same saved-workflow admission contract as a manual invocation. A busy worker may start later than the due time; it cannot admit the scheduled occurrence before that time.

`POST /api/v1/workflows/{version}/triggers` accepts `event_source`, `timezone` (an IANA name), optional `run_at`, required `expires_at`, `max_runs` (1–100), and `max_spend_usd` (currently only zero). Times must include an explicit UTC offset. An optional `interval_seconds` of at least 60 provides bounded repetition; missed intervals coalesce into one invocation instead of replaying a backlog. The existing worker credential and `BACKINTEL_AEGRA_URL` connect the native timer. Failed timer setup leaves the trigger paused with a recorded error.

Send an owner-authenticated `POST /api/v1/triggers/{id}/events` containing `event_id` and `source`. An optional `input_ref` selects a complete permitted collection. Duplicate identities return the existing accepted run without consuming another start. Reusing an identity with different inputs is denied. Distinct events and schedule occurrences consume the configured start allowance even when the unchanged workflow inputs reuse an existing result.

`GET /api/v1/triggers/{id}` and `GET /api/v1/goals/{id}/triggers` expose owner-scoped configuration, actual run status, accepted starts, and denied or skipped attempts. The application displays the same history. Use `PATCH /api/v1/triggers/{id}` with `state` set to `paused`, `active`, or `removed`. Pause and removal stop new admissions before native timer cleanup. Removal retains history; failed cleanup remains visible and can be retried. Expired or exhausted authority cannot be resumed.

Source access and objective limits are checked again when work is admitted and executed. Pausing a trigger does not cancel already accepted work. Set `refresh_source: true` to collect current source changes before each admitted start; the application selects this option by default for new triggers. This option cannot be combined with a retained `input_ref`. Existing triggers without this option keep their retained-input behavior. Both paths use deterministic saved steps without model requests. Aegra remains the only timer owner.

## Forecast method studies

S-32 adds a bounded method study for the checked retail source. A manager selects a completed connected-source answer and explicitly sets a positive spending allowance. The default allowance is zero. The study generates two Python methods in one model request, sends only earlier weekly aggregates, and runs the code through the existing isolated runner.

The agreed target is four complete weeks of total net invoice value in GBP across all countries, including signed cancellations. Partial boundary weeks remain in source reconciliation and are excluded from forecasting. The simple comparison repeats the latest four complete weeks. Candidates fit on earlier history and compete on four validation weeks using mean absolute weekly error; the simple comparison wins ties. Selection is saved before the final four weeks are scored. A second study on the same bound evaluation data is refused. A retry resumes the original study without another model request.

The toolkit entry point is `runtime.source_methods.invoke(source_run_id, policy, actor)`. The application uses `POST /api/v1/runs/{source_run_id}/method-studies` with the same policy. The policy includes `question` and `max_spend_usd` (at most 0.50); the existing per-request, objective, domain, and suite limits also apply. A larger allowance does not override those limits.

Save a completed selection with `runtime.source_workflows.save(study_run_id, actor)` or the app's **Save selected forecast workflow** action. Inspect, export, and invoke it through the existing workflow functions, CLI, and application routes. The package retains the policy, method, comparison, source references, and dependency hashes. Invocations reuse the frozen method without new inference. Forecasts appear separately from the existing business answer.

Every forecast remains evaluation only and unpromoted. Human predictor approval is a separate decision. One final period does not establish future reliability; point forecasts have no calibrated prediction intervals. Generated methods can lose to the simple comparison. Simulated proposals are labelled as such and do not establish live method generation. Measured inference charges and completed-stage wall time are reported; local computing cost remains unavailable.
