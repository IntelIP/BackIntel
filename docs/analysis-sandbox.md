# Sandboxed analysis and report delivery

The opt-in analysis specialist accepts one structured business brief, investigates assigned
read-only data, writes and revises programs in SmolVM, and produces a persistent report,
static/interactive charts, CSVs and an Excel workbook. It uses the existing Deep Agents SDK.
The specialist defaults to **GPT-6.1 Sol through the ChatGPT subscription**, with medium
reasoning, by owner decision after the controlled live comparison. The model can be
overridden with `BACKINTEL_ANALYSIS_MODEL` or the higher-priority `--model` option.
The original `backintel ask` benchmark analyst remains separate; no automatic delegation,
production scheduling or model fine-tuning is introduced.

## Build and demonstrate

```bash
docker build -f Dockerfile.sandbox -t backintel-sandbox:py312 .
uv run python -m scripts.prepare_smolvm                            # export and pin for SmolVM
uv run python -m scripts.run_analysis_demo
```

The demonstration uses a scripted model through the actual graph, tools and SmolVM sandbox.
It checks independent fixture calculations and artifact delivery without provider calls.
It is integration evidence, not a live model capability score. The script prints its output
directory; open `report-run/artifacts/report/report.html` and `supporting.xlsx` there.
Every attempted run retains its record. See [the task specification](../evals/analysis/Task.md).

## Run an authorized live brief

Create a JSON brief such as:

```json
{
  "objective": "Explain delivered-order revenue by category and over time, with supporting sheets.",
  "business_context": "An operations manager needs a descriptive review of the assigned source.",
  "audience": "Operations manager",
  "metric_definitions": {
    "revenue": "Use the documented source currency and the specified cancellation/refund conventions."
  },
  "time_window": "The period documented in the assigned source",
  "known_limitations": ["Revenue is not profit; no cost data has been supplied."],
  "required_outputs": ["report", "charts", "workbook"]
}
```

The default subscription route is shown below. To explicitly use a qualified OpenRouter
model, supply its full model ID and an applicable dollar allowance. This alternative template
does not approve a model or spending limit:

```bash
doppler run -p backintel -c dev -- uv run backintel analyze \
  --store sqlite:olist --brief /absolute/path/brief.json \
  --model "$BACKINTEL_OPENROUTER_MODEL" --responses-api --reasoning medium \
  --profile analysis --timeout 900 --max-model-calls 24 --max-tool-calls 50 \
  --max-cost-usd "$BACKINTEL_APPROVED_RUN_BUDGET" \
  --reservation-usd "$BACKINTEL_APPROVED_CALL_RESERVATION" \
  --output data/output/my-new-analysis
```

Use the API/reasoning combination supported by the selected model. Responses and first-party
OpenRouter routing have offline request-shape tests; a live smoke test must still establish
actual response parsing, multi-turn behavior and usage reporting. The OpenRouter path
requires provider-reported costs. Unknown charges stop further call admission. Application
reservations are not a hard provider billing cap; use a provider-side key limit when required.
Retries are disabled for this path. A new output directory is mandatory, preserving old runs.

`BACKINTEL_SANDBOX=subprocess` is rejected by this command. There is no host fallback.
Model credentials remain in the host process; only assigned source access enters SmolVM.

### Use the ChatGPT subscription

The `chatgpt-plan/<native-model>` route uses the operator's authenticated ChatGPT plan for
model inference. It does not give the SmolVM analysis sandbox remote CPUs or memory: Python,
SQL, charts and sheets still run with the local resource profile described below. Complete
the account login through the documented CLI; credentials do not enter the analysis VM:

```bash
uv run backintel chatgpt login
uv run backintel chatgpt models
```

The account was verified to offer the default `chatgpt-plan/gpt-6.1-sol`. For one business
brief, omitting `--model` and `--reasoning` uses that model with medium reasoning:

```bash
uv run backintel analyze \
  --store sqlite:olist --brief /absolute/path/brief.json \
  --profile analysis --timeout 900 --max-model-calls 24 --max-tool-calls 50 \
  --output data/output/my-new-plan-analysis
```

Do not add `--max-cost-usd` or `--reservation-usd` to plan runs. The plan path uses a finite
call allowance, the same tool/time limits and reported tokens. Per-request API dollar cost
is not applicable; records use `null`, not an invented zero inference cost. Subscription
fees and account quotas still apply. Missing usage or a failed request stops further
campaign admission. There is no fallback to OpenRouter or another paid API route.

An explicit `--model` overrides `BACKINTEL_ANALYSIS_MODEL`, which overrides the built-in
Sol default. `--reasoning` can override medium. Overrides must use a qualified model that is
available through the selected billing route. Model comparison scripts still require explicit
live model IDs so changing an application default cannot silently change a frozen benchmark.

See [model research](analysis-model-selection.md) for the comparison plan, primary sources,
reasoning configuration and the completed controlled comparison. A model's vendor name or
benchmark reputation is not automatic lineage qualification or proof of this capability.

The expanded controlled suite is runnable without inference:

```bash
uv run python -m scripts.run_analysis_comparison
```

It uses reference-scripted decisions through the real graph for four cases: messy retail
sales, missing costs, irregular energy observations and weighted service availability.
It verifies the environment and independent graders. To compare qualified live models,
repeat `--model` with explicit model IDs from **one billing mode**. OpenRouter comparisons
require `--max-cost-usd` and `--reservation-usd`; the dollar allowance is shared across arms.
Subscription comparisons reject those dollar options and use shared call admission instead:

```bash
uv run python -m scripts.run_analysis_comparison \
  --model "chatgpt-plan/$BACKINTEL_CHATGPT_NATIVE_MODEL_A" \
  --model "chatgpt-plan/$BACKINTEL_CHATGPT_NATIVE_MODEL_B" \
  --reasoning medium --output data/output/my-new-plan-comparison
```

Each model receives the same four frozen cases once, with at most 24 model calls, 50 tool
calls and 900 seconds per case. Two arms therefore share a maximum of 192 model calls;
requests remain subject to the account's own limits. Mixed plan/API arms are rejected before
creating outputs. Add `--langsmith` with the existing LangSmith credentials to create separate
experiments on the same frozen dataset; it does not change the inference billing route.

Unknown API charges prevent an API arm from qualifying for review. Plan arms instead require
complete reported token usage. Both modes require every case to pass, preserve unfinished
cases and unclassified failures, and label eligibility as **quality review only**. Neither
mode automatically promotes or changes the runtime model.
See [case definitions and limitations](../evals/analysis/cases.md).

## Runtime contract

The orchestrator calls `run_analysis(AnalysisBrief(...), model=..., store=..., output=...,
budget=...)` or uses the CLI. It owns source selection, business context and limits.
The specialist receives the brief, source access note, versioned prompt/skills and tools:

- Existing `list_tables`, `describe_table`, and `run_sql`/`run_query` source tools.
- `run_shell` and `run_python` inside its SmolVM workload.
- `write_analysis_file` and `read_analysis_file` for its workspace.
- `render_report(spec_path)` for the bounded report contract.
- `inspect_chart(path)` to return an actual PNG to the model for visual review.
- Read-only filesystem helpers for packaged skills and documentation.

The specialist reads `analysis-specialist`, `analysis-method`, relevant store skills and
`/docs/artifact-contract.md`. The prompt is [analysis.md](../src/backintel/agent_files/analysis.md).
These files never contain hidden expected results. Business data and documentation remain
untrusted content; they cannot expand permissions. The model can revise its programs and
artifacts, but not its governing instructions, dependencies, provider, grading truth or
production code.

Both model calls and all tool calls have explicit limits. SmolVM supplies the memory/CPU
boundary; trusted guest setup enforces process limits and bounded writable filesystems.
Cancellation deletes the VM. Its native workload lifetime also stops it if the host process dies.
This is per-run execution, not durable job recovery or a 24/7 scheduler.

## Compute and sources

The ordinary profile limits execution to 2 GiB and two CPUs. The larger profile allows 4 GiB and
three CPUs; both are configurable through `ResourceProfile`. Actual host capacity is checked
before admission. Run large jobs serially on this development host rather than assuming
that multiple maximum-size workers fit. The operating system still arbitrates other workloads.

Workspace, artifact and temporary-storage limits are separate. Read-only local source mounts
do not count against writable tmpfs limits. Use lazy/streaming processing or query pushdown;
an installed dataframe library is not permission to load all source data into memory.

The VM has no outbound networking. Assigned database endpoints remain in the existing
Docker infrastructure; each is exposed through a separate host Unix socket forwarding
only to its validated localhost TCP binding. The guest uses a loopback listener for the
original store hostname and port. No other host or database endpoint is exposed. Source
roles independently enforce read-only access. The host revalidates the assigned container
and port before each command and connection. Closing the VM removes its sockets and
forwards; existing source containers and networks are preserved. Model credentials, host
home, Docker socket, unrelated data and evaluator references are never mounted.

Local source files receive a content fingerprint. Remote sources are labelled live
observations; the run does not claim an immutable database snapshot or isolation from
external writers. See [environment and provenance](sandbox-environment.md) for the image,
dependency lock, actual capacity and measured sandbox checks.

## Artifact correctness and delivery

The agent writes a JSON report specification in `/workspace`, then calls `render_report`.
The host supplies the run/source identity. Each table must reproduce from one of its exact
citations: a read-only native query or Python printing one JSON object with `columns` and
`rows`. All citations must execute successfully. Python stdout is bounded; aggregate before
reporting. Tables that require larger outputs should use native queries within the declared
report bounds or be split into meaningful analytical tables.

This checks reproducibility, not business truth. A program that implements the wrong
definition can reproduce an incorrect answer. Independent benchmark references test that
separate question; narrative support and visual judgment also remain distinct.

The deterministic renderer binds metrics and charts to the same table cells used in CSV and
XLSX. It produces bar, line, scatter, histogram and heatmap outputs with units, readable
labels, table alternatives, self-contained interactive HTML and safe spreadsheet text.

The agent previews `/artifacts/report` and can revise the specification. After it finishes,
its VM stops. A separate clean VM, without sources or credentials, renders
the host-retained specification again. Only that renderer's output is exported. This avoids
trusting an agent-written manifest or arbitrary HTML from its shell workspace. No generated
artifact needs a CDN, remote font or external service.

The output contains `run.json` and `artifacts/report/manifest.json`, `report.html`, `report.json`,
`supporting.xlsx`, tables and charts. File paths, inventory, byte limits and checksums are
validated. Run records contain the actual source/method/image identity, limits, resource use,
provider-reported tokens, applicable API costs or subscription billing, failure state and
available trajectory, including unsuccessful runs.
These files can contain source data and business context; store them under the user's normal
access/retention rules. They are excluded from Git.

See [measured implementation results](results-analysis-sandbox.md) for the current local
demo, image identity and verification limits.

## Evaluation and release

Use the normal tests plus the explicitly enabled SmolVM suite described in
[sandbox-environment.md](sandbox-environment.md). The demonstration exercises the real graph
with scripted responses; it cannot choose a winning model. Live comparisons use the same
sources, brief, runtime and verifier, preserve all attempts, and report applicable API
charges or subscription token usage without treating either as a quality score.

INT-450 tracks the legacy tool surface; INT-452/453 track the output channel/renderers.
INT-454 remains the live agent bundle and release gate, with the existing reliability
dependency. Business-report pack acceptance (INT-455–457), durable scheduling and deployment
remain separate roadmap work. Do not infer a v0.0.4 release from an image build or scripted demo.
