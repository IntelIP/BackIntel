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

## LangChain local integration trial

An external LangChain agent can call the same authenticated saved workflow through `runtime.langchain_tools.saved_workflow_tool`. BackIntel already uses LangGraph internally; this trial checks the external agent interface, not a replacement of that runtime. It binds one workflow and the application's credentials outside model-visible tool arguments. The tool returns a compact answer to the model and preserves the full API result, calculation, coverage, and evidence in the LangChain tool message's `artifact`.

Install `requirements.langchain.txt` in the selected Python environment alongside `requirements.testing.txt`. The trial pins LangChain 1.4.6, LangChain Core 1.6.11, and LangGraph 1.2.12. The caller supplies an authenticated `httpx.Client`, using HTTPS or a loopback address for local testing, with redirects disabled. Credentials belong in an approved environment or credential store.

```python
from langchain.agents import create_agent
from langchain.agents.middleware import ModelCallLimitMiddleware, ToolCallLimitMiddleware
from runtime.langchain_tools import saved_workflow_tool

# authenticated_client, workflow_version, and approved_model come from your application.
agent = create_agent(
    model=approved_model,
    tools=[saved_workflow_tool(authenticated_client, workflow_version)],
    middleware=[ModelCallLimitMiddleware(run_limit=2), ToolCallLimitMiddleware(run_limit=1)],
    system_prompt="Run the approved workflow. Report only its checked findings and evidence. Keep failures explicit.",
)
result = agent.invoke({"messages": [{"role": "user", "content": "Run the approved retail analysis."}]})
```

Only `succeeded` establishes an accepted answer. If the wait expires, the tool returns the unfinished run identity; repeating the same invocation resumes that run. Bind another permitted, complete collection with `saved_workflow_tool(client, workflow_version, input_ref=collection_run_id)`; this selection stays outside model arguments. The default uses the workflow's original collection. An older collection cannot replace a newer accepted source answer. Authentication and current source permissions remain enforced by BackIntel, including on replay. The adapter exposes no source-record changes or arbitrary queries. BackIntel's saved workflow makes no provider calls; the external application's model requests need their own authorization, spending controls, and accounting.

The runnable local trial uses **scripted model responses** inside the actual LangChain agent loop, with the real authenticated BackIntel workflow and retained historical retail records:

```sh
python scripts/validation/run_workflow_triggers.py \
  --archive /absolute/path/to/retained/runtime-result.dump \
  --output /absolute/path/to/new/trial-output \
  --langchain
```

It creates a disposable local PostgreSQL database and API server, then removes them. Inspect `summary.json`, `langchain-cases.json`, `langchain-result.json`, and `langchain-messages.json` in the output directory. The trial compares the full calculation, checks recovery after a simulated lost admission response, and exercises replay, revoked access, and an unsupported tool request. It makes zero paid calls. Its scripted choices do not establish live model reasoning quality, independent installation, or release qualification; those limits remain explicit in S-25 and S-25.01.

The October 16, 2026 local trial passed using the retained S-39 reference archive and its latest accepted collection. All 541,909 rows were processed, with zero excluded, failed, or pending. Exact net invoice-line value remained GBP 9,747,747.934; cancellation reduction remained GBP 896,812.49. Every stock-code and country group, the period, currency, and coverage matched the previously accepted calculation. A fresh agent recovered the same run after a simulated lost admission response; replay created no additional BackIntel run. Revoked source access and an unsupported tool were rejected without changing the accepted answer. The paid-request ledger was unchanged, and the disposable database and server were removed.

The [trial receipt](</Users/hudson/Library/Application Support/BackIntel/Validation/S25LangChain-20261016C/summary.json>) and [full tool result](</Users/hudson/Library/Application Support/BackIntel/Validation/S25LangChain-20261016C/langchain-result.json>) retain the evidence. Earlier attempts exposed an outdated objective archive and an older input collection; the successful trial selected the current accepted collection without changing the objective, access checks, or freshness policy. This is working-tree validation, not a release or production-capacity claim.

## Agno local integration trial

Agno developers can call the same saved workflow using `runtime.agno_tools.saved_workflow_tool`. Install `requirements.agno.txt` (Agno 3.1.4). Agno and LangChain share `runtime.workflow_client`, so the HTTP permission, response, recovery, and transport checks stay the same. The caller owns a receipt list that retains the full API answer; the model receives only its compact summary. The tool accepts no model-supplied arguments.

```python
from agno.agent import Agent
from runtime.agno_tools import saved_workflow_tool

receipts = []
agent = Agent(
    model=approved_model,
    tools=[saved_workflow_tool(authenticated_client, workflow_version,
                               receipts=receipts, input_ref=accepted_collection_id)],
    tool_call_limit=1,
    telemetry=False,
)
# Model use requires the application's own approved allowance.
response = agent.run(saved_question)
# Check receipts[-1]['status']; only succeeded is an accepted answer.
```

Run the no-spend local trial with `--framework agno` instead of `--langchain` in the command above. It uses the real Agno agent loop with two scripted responses and the actual BackIntel API. Inspect `agno-result.json`, `agno-messages.json`, `agno-cases.json`, and `summary.json` in the output directory. The scripts check the complete retained calculation, fresh-agent recovery, replay, revoked source access, and an unknown tool. Scripted decisions do not measure autonomous reasoning or production readiness.

The local Agno trial passed: all 541,909 rows, the same GBP 9,747,747.934 net invoice value and GBP 896,812.49 cancellation reduction, retained evidence, recovery, replay, and denied operations. The [completed receipt](</Users/hudson/Library/Application Support/BackIntel/Validation/S25Agno-20261016B/summary.json>) uses the retained run from the [initial full calculation](</Users/hudson/Library/Application Support/BackIntel/Validation/S25Agno-20261016A/agno-result.json>). That initial run matched the original native calculation but its final check expected different wording for an unavailable tool. The corrected rerun accepted Agno's explicit unavailable-tool error. Both runs made zero paid requests and removed their temporary database and server.

## Mastra local integration trial

JavaScript applications can use `integrations/mastra/workflow.mjs` to call the same authenticated saved workflow. This optional package is separate from the web app. Run `npm ci --prefix integrations/mastra --ignore-scripts` with Node 22.13 or newer; it pins Mastra 1.78.0 and Zod 4.6.7. The checked local Node version is retained in the trial receipt.

```javascript
import { Agent } from '@mastra/core/agent';
import { savedWorkflowTool } from './workflow.mjs';

const receipts = [];
const agent = new Agent({
  id: 'retail-analysis', name: 'Retail analysis',
  instructions: 'Use the approved workflow. Treat unfinished or failed results explicitly.',
  model: approvedModel,
  tools: { run_backintel_workflow: savedWorkflowTool({
    baseUrl, authorization, workflowVersion, inputRef: acceptedCollectionId, receipts,
  }) },
});
// Model use requires the application's own approved allowance.
const response = await agent.generate(savedQuestion, { maxSteps: 2 });
// Only a succeeded receipt represents an accepted answer.
```

The tool accepts an empty, strict input schema. Credentials and workflow selection are application configuration. It requires HTTPS or a loopback server, refuses redirects, bounds HTTP requests and waiting, and always reads the authorized result endpoint. The model receives the compact result; the application retains the complete API receipt. BackIntel owns recovery and deduplication. Errors remain in Mastra's tool-invocation messages, including denied access and unavailable tools.

Run the retained-data trial with `--framework mastra` in the command above. The Python harness supplies disposable credentials to the Node process over standard input. The real Mastra agent uses a scripted provider with two responses and no network model client. `mastra-result.json`, `mastra-messages.json`, `mastra-cases.json`, and `summary.json` retain results. Run its focused check with `npm test --prefix integrations/mastra`.

The [completed Mastra trial](</Users/hudson/Library/Application Support/BackIntel/Validation/S25Mastra-20261016A/summary.json>) passed on Node 26.3.1. It processed all 541,909 rows with zero pending, failed, or excluded rows. The complete calculation matched the native accepted answer: GBP 9,747,747.934 net invoice value and GBP 896,812.49 cancellation reduction, with every product/country group, period, currency, coverage measure, and evidence retained. Fresh-agent recovery returned the same run, replay created no duplicate, and revoked source access and unknown tools were rejected. The provider ledger stayed unchanged; the temporary server and database were removed.

| Framework | Application language | Full result retained in | Local trial |
| --- | --- | --- | --- |
| LangChain 1.4.6 / LangGraph 1.2.12 | Python | Tool-message artifact | Passed |
| Agno 3.1.4 | Python | Application receipt list | Passed |
| Mastra 1.78.0 | JavaScript | Application receipt list | Passed |

All three adapters reuse the saved analytical pipeline. These trials establish local integration behavior with scripted choices; they do not compare model reasoning, model cost, speed, independent deployment, or production scale. S-25 remains open for its broader release qualification.

## Application

Send an authenticated `POST /api/v1/workflows/{version}/runs` with `{}` for the original accepted collection, or `{"input_ref":"COLLECTION_RUN_ID"}` for another complete permitted collection. The response contains the run identity. Read its result at `GET /api/v1/runs/{id}`.

The platform offers **Run saved workflow** beside each saved version and a collection selector. The returned result includes the workflow version, input reference, complete coverage, findings, calculation evidence, limitations and measured usage. Missing dependencies, incompatible input contracts, denied access and failed meaning checks remain explicit failures.


## Specialist coordination

For a confirmed retail objective, one request lets three specialists interpret the source, select the invoice-value calculation, and check the finding against retained original records. They share one job, the permitted connection, the objective version, and a limit of six model requests. Collection, preparation, value checks, and calculation use the existing tools. Each specialist receives its own context and one permitted read tool.

The owner can inspect each contribution, its input and evidence versions, progress, rejection reason, and measured or unresolved charges. A disagreement cannot replace the accepted answer. Retrying the same request reuses retained work and provider responses; an unresolved charge requires reconciliation before another attempt. A changed objective, revoked source grant, or concurrently accepted answer prevents stale work from being published.

Use the same application database and `BACKINTEL_ACCESS_TOKEN` as the other toolkit commands:

```sh
python -m runtime.source_coordination start GOAL_ID --request-id retail-team-001 --max-spend-usd 0.50
python -m runtime.source_coordination inspect RUN_ID
```

`start` waits for the job by default; `--no-wait` only queues it. Reuse the request identity and allowance to resume. The allowance must fit within the confirmed objective's budget. Model access and spending must already be authorized; these commands do not grant either.

The application offers **Let specialists answer together**. The authenticated API accepts `POST /api/v1/goals/{id}/coordination` with `{"request_id":"retail-team-001","max_model_calls":6,"max_spend_usd":0.50}` and exposes the same progress through `GET /api/v1/runs/{id}/coordination`. Both the API and toolkit recheck the current source grant.

Three live specialists have completed the complete historical retail question with independently checked results, retained progress, and measured charges. See the [reference result](retail-reference-workflow.md#specialist-coordination) for evidence, costs, and limits. Simulated fault scenarios are labeled separately. The demonstrated scope is one local PostgreSQL retail workflow; additional business systems and production capacity remain future work.

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


## Multiple users in the local application

Objectives are private to their owner and permitted administrators. A source grant permits access to that source; it does not share another user's objective. An owner can grant `read`, `run`, or `manage` access through `PUT /api/v1/goals/{goal_id}/access/{principal_id}`. Send `permission: null` to revoke that share. A read-only user can inspect explicitly shared work and cannot start, cancel, or change it. Connected-source operations also require a separate source grant.

Ordinary owners cannot administer shared sources or other accounts. On an operator-managed local installation, `python -m scripts.analysis_demo seed --administrator --budget-usd 0` explicitly enables administration for the seeded manager while keeping model spending at zero. Omit those flags to preserve existing authority. An administrator can assign individual cumulative model-spending limits through the existing principal-grant endpoint. Individual limits sit below the existing run, domain, and shared-service limits. Reservations and unsettled charges count toward each limit.

The application shows permitted jobs, time spent waiting, shared running/waiting counts, and the signed-in user's model spending. The local dispatcher allows two active jobs; this configured limit is not a claim about sustained production capacity. Local computer costs remain unmeasured.

S-30 validation uses `scripts/validation/run_workflow_triggers.py --multi-user retail` with the retained retail archive. It imports the accepted data, interpretation, and method into four private objective contexts and then recomputes four answers. Planning artifacts are retained; the four executions do not claim new model reasoning. The check uses two owners, a read-only viewer, independent source grants and budgets, browser checks, and no paid requests. Completion requires the resulting checks and full calculation comparisons to pass; code presence alone does not establish that result.


### Observed local multi-user result

The S-30 trial completed four distinct saved-workflow executions in 280.816 seconds after admission. Each processed all 541,909 retained retail records with zero failed, pending, or excluded rows. Every answer matched the reference totals, product and country groups, currency, dates, and coverage. At most two jobs ran at once; waiting work was visible.

| Account | Completed analyses | Time waiting before execution | Model charges |
| --- | ---: | --- | ---: |
| Owner A | 2 | 1.99–2.76 seconds | US$0 |
| Owner B | 2 | 140.71–140.95 seconds | US$0 |
| Read-only viewer | No execution permission; one shared result visible | Shared run history only | US$0 |

The native API denied cross-owner reads, changes, and cancellation. Browser checks passed for both owners and the viewer at desktop and narrow widths. Separate simulated reservation checks rejected concurrent spending beyond a user's cap. The original provider ledger was unchanged; no model request was made. Local computer costs were not measured. These are observations from one local trial using retained planning and interpretation, not a sustained-capacity or fresh model-reasoning result.

Evidence is in `~/Library/Application Support/BackIntel/Validation/S30Retail-20261017H/`: `summary.json`, `multiuser-cases.json`, `multiuser-queues.json`, four full result files, and browser evidence. The 158 passing database/application regressions are retained in `S30Retail-20261017G/multiuser-checks.log`; all 25 web tests, the web build, dead-code check, and patch check also passed. The temporary database and native server were removed after the trial.

## Source documents (S-27)

A manager can attach a field guide to a connected objective from the Sources view. BackIntel retains the original bytes and source reference, extracts readable text, and provides relevant passages to field interpretation. The selected reference is the official [UCI Online Retail documentation](https://archive.ics.uci.edu/dataset/352/online+retail), which describes cancellation invoice codes and prices in sterling.

Accepted field citations name an existing retained document and passage, quote its exact extracted text, and include the linked field name. Source text is untrusted evidence: it cannot grant access, execute tools, or change approved business definitions. Unknown or conflicting meanings stay explicit. Citations show documentary support; numerical claims still require the existing full-source checks. Both the ordinary interpreter and the coordinated data specialist use this contract.

Adding or removing attachments creates a new objective version and clears confirmation. Old documents and answers remain retained. The saved workflow includes document references and validated quotations, checks their integrity before reuse, and rejects execution against a changed objective version. Final analytical and forecast results preserve the citations; the application displays them beside the answer and identifies an answer from an older objective version.

Supported inputs are UTF-8 plain text and HTML, up to 2 MB original bytes and 128,000 readable characters each. Each objective can attach four documents and retain 40 versions. The initial passage selector uses exact source field names and supplies at most 16 matching passages, each at most 1,600 characters. Unsupported files, absent text, invalid UTF-8, oversized content, and forged citations fail explicitly. PDF, scanned documents, and general semantic document search remain outside this first implementation.

The shared Python interface is `runtime.source_documents`: retain with `admit`, inspect with `read`, select passages with `context`, and validate accepted quotations with `accepted_evidence`. Attach retained IDs through `analysis_service.revise_goal(document_refs=..., expected_version=...)`. These reusable functions are current-source interfaces; they do not qualify the unavailable historical toolkit candidate.

The authenticated application routes are `POST /api/v1/goals/{id}/documents`, `GET /api/v1/goals/{id}/documents`, and `GET /api/v1/documents/{id}`. The POST takes a title, optional HTTP(S) source reference, media type, and base64-encoded original bytes. It retains the original; attach its returned ID with the goal update route. The original-download route ends in `/original` and serves bytes as an attachment with `nosniff`, never as active application HTML. URLs are provenance references only and are not fetched by these routes. Read-only collaborators can inspect explicitly shared documents but cannot change attachments.

Local verification uses `run_workflow_triggers.py --documents /absolute/path/to/retained/online-retail.html` with a retained retail archive and a separate output directory. It labels simulated interpretation and retained method responses, executes preparation/checking/calculation over the real retained records, compares the complete result, checks saved references and invalidation, and verifies browser access to quotations and original downloads. No provider is contacted in this mode. A fresh autonomous document interpretation needs its own approved model allowance.

The local S-27 trial passed on 2026-10-17. It processed all 541,909 retained retail rows and matched every total, country/product group, currency, period, and coverage measure from the accepted reference. Net invoice-line value remained GBP 9,747,747.934, including GBP -896,812.49 in cancellation value. The answer retained exact UCI quotations for `InvoiceNo` and `UnitPrice`. Original download bytes matched the retained hash, and both confirmation and workflow-version checks blocked reuse after attachments changed. Model interpretation responses were simulated; the analytical method was retained from the accepted reference. No new provider calls or charges occurred.

Fresh autonomous document interpretation passed on 2026-10-18 with one OpenRouter request costing US$0.04056129, within the approved two-request / US$0.25 cap. The model supplied exact citations for all eight source fields. Preparation, meaning checks, the full calculation, saved-workflow references, desktop/narrow browser checks, original downloads, and attachment-change guards passed. All 541,909 records and every total/group matched the retained reference. The calculation method was reused; only document interpretation was newly generated. Evidence: `~/Library/Application Support/BackIntel/Validation/S27LiveDocuments-20261018B/summary.json` and the adjacent interpretation, answer, workflow, and browser artifacts. The initial zero-budget attempt made no provider call; the disposable account then received the approved allowance. Local computing cost remains unknown.

The prepared live interpretation request is saved locally at `localdevelopmentpilot/work/S27Documents/live-interpretation-request.json`. The model-output schema requires citation fields while older saved interpretations still read with empty citation lists. The data specialist receives citation rules as system guidance, separate from untrusted document passages.

After explicit approval of the S-27 allowance, the live command below resumes the reviewed pre-calculation archive. It reuses its aggregate profile, admits one new interpretation run, permits at most two provider requests on that run, and relies on the existing cumulative run budget for the US$0.25 limit. Unknown charges stop continuation. A second request is used only to repair a measured, rejected interpretation. The calculation method is reused from the real reference workflow and its origin is retained; no new method-generation call is made. The approved live run completed using the command below with the existing Keychain credential injected into the parent process.

```sh
/private/tmp/BackIntelS20Runtime.6IvJge/bin/python scripts/validation/run_workflow_triggers.py \
  --archive '/Users/hudson/Library/Application Support/BackIntel/Validation/S27Documents-20261017B/runtime-result.dump' \
  --documents /Users/hudson/Documents/Codex/2026-10-13/localdevelopmentpilot/work/S27Documents/online-retail.html \
  --documents-resume '/Users/hudson/Library/Application Support/BackIntel/Validation/S27Documents-20261017B' \
  --output '/Users/hudson/Library/Application Support/BackIntel/Validation/S27LiveDocuments-20261018B' \
  --documents-live
```

Use the existing credential-injection mechanism only after the allowance is approved; do not put credential values in the command or repository. The focused schema, compatibility, request-limit, objective, and coordination checks passed (17 tests). The earlier completed retail evidence remains a simulated-interpretation trial until the approved live run succeeds.


## Combine retail results with demonstration targets

S-34 adds a selected local two-system path. First collect the permitted PostgreSQL source and execute a saved retail workflow. Then `runtime.cross_systems.assess(run_id, actor, {"target_ref": "s34-targets", "request_id": "comparison-001"})` reads the separately granted target service, reuses the specialist independent check against original records, and compares country categories with explicit 10% demonstration targets. The authenticated API is `POST /api/v1/runs/{id}/cross-system`; retrieve a finding through `GET /api/v1/cross-system/{id}`.

The rate is negative signed C-prefix cancellation value divided by the signed value of non-cancellation invoice lines, in GBP. Exact fractions decide whether a target is exceeded; percentages are rounded for display only. Targets must cover the entire historical source calendar period. The result preserves the collection and calculation hashes, independent source check, target snapshot and hash, publication time, and retrieval time. Source timezone remains unknown. Country labels, including Unspecified and European Community, remain recorded categories; the system does not infer geographic identities or aliases. Missing mappings, repeated identities, incompatible currency, incomplete effective periods, or an unavailable target service produce a blocked finding that cannot be delivered.

Delivery requires a separate operator-managed `deliver_findings` grant in `backintel.analysis_service_grants`; `read_targets` alone is insufficient. Both grants explicitly name the domain, principals, literal loopback HTTP service address, and expiry. The primary source grant and private-objective permission are also rechecked. These local grants do not authorize business-record changes, external messages, arbitrary URLs, or real business targets.

Use `runtime.cross_systems.deliver(finding_id, actor, "s34-local-inbox")`, or `POST /api/v1/cross-system/{id}/deliveries` with `{"destination_ref":"s34-local-inbox"}`. A stable delivery identity is committed before contact. The recipient retains the accepted finding and a receipt; BackIntel reads the receipt back and checks the result identity and content hash. If acknowledgement is lost, retry the same finding and destination. Confirmed replay returns the retained receipt without another effect. A blocked comparison stays in its attempt history; use a new request identity after correcting its source.

The selected service is `scripts/validation/cross_system_service.py`. It serves the explicitly synthetic policy in `config/reference_scenarios/retail_cancellation_targets.json` and retains local inbox deliveries in SQLite. No new model call is needed: the analysis method was previously generated and checked, and the target comparison follows the agreed contract. This does not demonstrate new autonomous method generation, arbitrary connector discovery, real Databricks access, or sustained capacity.

Run the selected full-data acceptance with `scripts/validation/run_workflow_triggers.py --cross-systems --incremental-csv /absolute/path/to/OnlineRetail/data.csv --archive /absolute/path/to/retained/runtime.dump --output /absolute/path/to/new/evidence`. The archive must contain a current accepted retail reference before attachments were detached. The trial provisions a disposable read-only PostgreSQL source and separate local target/inbox process, exercises the authenticated API, checks all country calculations with independent SQL, and tests conflicting mappings, unavailable sources, forbidden destinations, lost acknowledgement, receiver restart, and duplicate replay. Native runtime and target service are stopped afterward; source evidence, findings, receipts, and the local inbox remain in the output directory.

The approved S-34 trial passed on 2026-10-18. `S34CrossSystems-20261018C` collected all 541,909 PostgreSQL records and reproduced the accepted calculation; `S34CrossSystems-20261018D` reused that completed collection and repeated the final comparison and delivery checks with corrected observation timestamps. Independent SQL reconciled all 38 country categories. Eight exceeded the explicitly synthetic 10% target: Singapore, USA, Hong Kong, Bahrain, Czech Republic, Portugal, Spain, and Saudi Arabia. These are demonstration comparisons, not actual business-policy breaches. Lost acknowledgement, receiver restart, and retries produced exactly one retained inbox effect. Conflicting identities/mappings, missing coverage, currency mismatch, unavailable sources, and revoked permissions were rejected. There were zero new model calls or charges. Evidence is retained under `~/Library/Application Support/BackIntel/Validation/` in those two directories; all trial servers were stopped. Actual Databricks remains S-26.

## Sustained local workload (S-36)

The approved local target is 30 minutes with two private owners, at most two active jobs and six waiting jobs, and a 100-record source update every five minutes. Each owner must receive a correct answer within five minutes. The trial includes one forced worker interruption, zero paid model calls, the existing four-CPU/about-eight-GB Docker allocation, and at most four GB of additional storage. Host process use is measured separately; local hardware and electricity remain unpriced.

The shared admission boundary reserves six outstanding analysis jobs in total, including active jobs. This preserves space for interrupted jobs to return to waiting without exceeding six. Stable request replay does not consume another slot. The queue API exposes active, waiting, active_limit, waiting_limit, and outstanding_limit. Separate concurrent admission checks cover overload, visible waiting work, retry reservations, access isolation, and reuse of freed worker slots. Those checks do not establish sustained throughput.

Run the actual workload using `scripts/validation/run_workflow_triggers.py --sustained --incremental-csv /absolute/path/to/OnlineRetail/data.csv --archive /absolute/path/to/retained/runtime-result.dump --output /absolute/path/to/new/evidence`. The archive supplies a previously accepted calculation method. Two separately authorized private workflows read the real PostgreSQL source through native workers. The trial driver represents the external source sending change events and inserts six explicitly synthetic batches of 100 invoice records. These are demonstration records, not new business transactions. Each completed answer is compared with independent SQL for totals, every country, and every product group.

### Recorded local result, 2026-10-18

`S36Sustained-20261018C` passed on the local working tree. The source grew from 541,909 to 542,509 records. All twelve complete answers matched the independent calculations. One interrupted refresh succeeded on its second attempt, with no unfinished work. The source batches arrived within 1.00 seconds of their scheduled times.

| Measure | Agreed target or boundary | Observed result |
| --- | --- | --- |
| Sustained observation | At least 1,800 seconds | 1800.93 seconds |
| Complete answers | Two owners for six updates | 12 correct answers; 0.40 answers/minute at this arrival rate |
| Source change to checked answer | At most 300 seconds | 116.95–139.23 seconds |
| Queue | At most two active and six waiting; six outstanding admitted by implementation | Peak 2 active, 2 waiting; maximum sampled waiting age 1.59 seconds |
| Docker allocation | Four CPUs; 8,322,945,024 bytes memory | Unchanged; peak combined sampled container memory 1,278,570,496 bytes |
| Container CPU | Measure actual use separately from configured allocation | 460.94 observed CPU-seconds across sampled containers |
| Host processes | Measure separately | Peak sampled RSS 1,611,628,544 bytes; peak sampled CPU 131.2% (100% is one core) |
| Additional storage | At most 4,000,000,000 bytes | Peak 2,517,318,096 bytes; 2,216,769,519 bytes retained including archive |
| Provider use | Zero paid model calls | Zero calls, US$0; request ledger unchanged |

Resource samples were taken approximately every ten seconds. Combined memory and host CPU/RSS are sampled peaks. Container CPU is the database counter delta plus last observed calculation-container counters; short-lived containers or work after their last sample can be missed. Waiting age is sampled, not an exact queue-latency bound. Hardware and electricity costs are unpriced as agreed. This result establishes the declared local workload, not a larger capacity or production service target.

Evidence is retained in `/Users/hudson/Library/Application Support/BackIntel/Validation/S36Sustained-20261018C`: `sustained-report.json`, `summary.json`, logs, the database archive, and the trial-owned host database directory. Storage accounting includes 876,645,804 bytes from earlier S-36 attempts, database files, temporary calculation files, and retained evidence. The native server stopped and the trial database container was removed; unrelated Docker data was preserved. The focused database suite passed all 162 checks; syntax, dead-code, patch, and scoped Graphify checks also passed.

Two earlier attempts remain recorded as failed, incomplete trials. Attempt A exceeded freshness (486.1 seconds) and stopped after 681.4 seconds; it exposed delayed retry dispatch and an exclusive objective read lock. The runtime now fills freed worker slots promptly, admits work with a shared read lock, and pools short application queries while retaining dedicated job transactions and live permission checks. Attempt B completed six correct answers in 136.4–150.0 seconds, then failed after 995.7 seconds when shared Docker storage filled. Trial C used its own host bind mount within the approved storage allowance and completed the unchanged target.
