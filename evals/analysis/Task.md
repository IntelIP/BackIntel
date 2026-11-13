# Sandboxed analytical report and missing-cost refusal

Status: Draft, agent-reviewed implementation under the owner's instruction to execute
without a new approval pause. This is an offline integration task, not a human-calibrated
or live-model benchmark result. Date: 2026-11-11.

The broader, separately documented [four-case comparison](cases.md) now adds energy and
service-availability tasks. This original demo remains the explicit coding-error-recovery
integration; its two cases and historical results are preserved.

## Purpose and source

Exercise BackIntel's Deep Agents analysis graph, persistent SmolVM workspace, ordinary
coding-error recovery, read-only source access, report renderer, PNG inspection tool and
exported artifact verification. Prior benchmark outputs were structured answers; this task
adds an actual report/chart/workbook bundle and independent numerical reconciliation.

Governing implementation: `src/backintel/analysis.py`, `analysis_sandbox.py`, `artifacts.py`.
Runnable task: `scripts/run_analysis_demo.py`. Direct checks: `tests/test_analysis_workflow.py`.
The project's benchmark World Skill supplies the reusable rule that verifier references,
grading logic and scenario-specific expected values stay outside analyst mounts. It also
requires distinguishing harness failures from model behavior. No new World Skill truth or
human approval is implied here.

## Exact business input

Primary objective: “Produce a business report of delivered-order net revenue by category
and day, including a total metric, static and interactive charts, and supporting sheets.”

Business context: a synthetic retailer's operational sales review; all money is USD.
Audience: operations manager. Period: 2026-11-01 through 2026-11-03 inclusive.
Definition: deduplicate exact repeated line rows, include delivered orders only, sum refunded
quantity per line before subtracting it, then multiply by integer unit cents. Revenue is
not profit. The source has no product-cost or expense fields.

Second run objective: “Calculate net profit for the delivered orders in the assigned period.”
Other definitions and limitations are unchanged. A correct response identifies the missing
cost/expense inputs and does not substitute revenue for profit.

## Environment and visibility

The evaluator creates a new SQLite database with four tables: orders, lines, catalog and
refunds. It contains a cancelled order, an exact repeated line and two refund records for
one line. Only this source file is mounted, read-only. The normal source schema/query tools,
preinstalled packages and local documentation are available. Writable per-run paths and
resource limits are supplied by the sandbox, with no public network or host shell fallback.

The fixture builder, this Task, scripted client and verifier remain on the host. Expected
numbers are not mounted into the VM. Each run uses a fresh VM/workspace and
new output directory. The report run and refusal run share the unchanged immutable source.

A scripted `FakeMessagesListChatModel` supplies predetermined actions through the actual
Deep Agents graph. It discovers tables, reads relevant schemas/docs, writes a program with
an ordinary missing-column error, executes it, writes a corrected SQL-based program,
renders the report, receives a PNG through `inspect_chart`, and submits structured completion.
The refusal script inspects source availability and submits `cannot_answer`.

This verifies tool wiring and artifact behavior, not autonomous discovery, LLM reasoning,
vision judgment, unseen-domain transfer or production reliability. It uses zero provider
inference calls; the graph still executes scripted model steps.
The live entry uses the same business input with an explicit output-layout requirement:
table IDs `categories`, `daily`, `total`, with columns respectively `Category, Revenue`,
`Date, Revenue`, and `Revenue`. Values must be USD; row/table presentation order is free.
This exposes a formatting contract, not answers, SQL, scripted actions or verifier logic.

## Independent verification

The verifier reads raw SQLite records and independently calculates values with integer
arithmetic, without reusing the analyst's aggregation SQL. Expected category revenues:
Home 75 USD, Outdoor 40 USD, Essentials 20 USD. Total: 135 USD. Daily totals: 35, 50 and
50 USD. The analytical SQL and independent calculation must agree.

The complete primary pass condition requires:

- Graph status completed; bundle exists and passes inventory/checksum validation.
- Canonical tables match the independent reference, including category/period labels;
  row and table presentation order may differ.
- The requested total metric and category/day charts exist.
- CSV and XLSX cells reconcile with those canonical tables.
- A real missing-column execution error appears in the trace before the successful output.
- Actual PNG data returns through the chart-inspection tool.
- A deliberately wrong but structurally valid control fails independent numerical grading.
- The second graph run returns an explanatory missing-cost refusal.
- The source file's hash is unchanged after both runs.

PNG tool delivery is not a visual-aesthetic grade. The implementation owner separately
opens representative output to inspect rendering. The deterministic renderer supplies the
static/interactive figures from the same canonical tables; numerical reference matching
does not establish the truth of every narrative sentence or an arbitrary live question.

Correct equivalent calculations are acceptable for later live-model runs. This scripted
integration checks a chosen path, not a required tool sequence for general agents.
The wrong-result control changes table/metric totals consistently; structural consistency
alone cannot pass it. A malformed/corrupt bundle or missing evidence must fail the existing
bundle/runtime verification. Source modifications are prohibited collateral changes.

SmolVM/image startup errors, unavailable dependencies, broken graph assembly or renderer
errors are infrastructure/harness failures. Keep failed run records and repair those faults
before interpreting success as a functioning integration. They are not model failures.

## Running and evidence

Build and prepare the project's sandbox image as described in
[sandbox setup](../../docs/analysis-sandbox.md#build-and-demonstrate), then run:

```bash
uv run python -m scripts.run_analysis_demo
```

Outputs live under a fresh `data/output/analysis-demo-...` directory. `evaluation.json`
records independent checks, measured resources and explicit limits. Each run retains
`run.json` with the full graph trajectory. Delivered files are under
`report-run/artifacts/report/`, including report HTML/JSON, chart PNG/SVG/HTML, CSV tables,
supporting XLSX and manifest. Source datasets and run artifacts stay out of Git.

Ordinary unit test:

```bash
uv run pytest -q tests/test_analysis_workflow.py
```

Real SmolVM integration (opt-in, no provider calls):

```bash
BACKINTEL_SMOLVM_TESTS=1 uv run pytest -q tests/test_analysis_workflow.py
```

This task does not claim a large-data result, a live model comparison, user-facing
deployment, LangSmith score improvement, or a completed release milestone.

## Optional live LangSmith entry

This historical OpenRouter-only entry also prepares two actual model runs through
`run_analysis`, one repetition each,
serially. It is deliberately smaller than the proposed eight-scenario, sixteen-run model
comparison. That broader campaign still needs additional tasks and approved execution.
Choose an independently qualified model/endpoint and a separately authorized allowance
before using this template; placeholders are not model selection or spend approval:

```bash
doppler run -p backintel -c dev -- uv run python scripts/run_analysis_demo.py \
  --live --model "$BACKINTEL_ANALYSIS_MODEL" --reasoning medium \
  --max-cost-usd "$BACKINTEL_APPROVED_RUN_BUDGET" \
  --reservation-usd "$BACKINTEL_APPROVED_CALL_RESERVATION" \
  --langsmith --dataset backintel-analysis-artifacts-v1
```

The current transport is Responses through OpenRouter, first-party provider only, without
fallbacks or retries. The reasoning/API combination must be supported by the qualified model.
Limits are 24 model calls, 50 tool calls and 900 seconds per case; the shared admission ledger
also caps both runs at 48 model calls and the explicit dollar allowance. Unknown charges or
a per-call reservation breach stop later calls. This is application admission control, not a
hard provider billing cap. A provider-side key limit is necessary for a strict dollar ceiling.

`--langsmith` uploads the synthetic case inputs/references, actual run outputs and traces,
and deterministic feedback into LangSmith. Existing dataset contents must match the frozen
case/reference definitions; changes require a new dataset version. Without `--langsmith`,
live results stay local and tracing is disabled for those runs. Neither mode uses an LLM judge.
Both retain `run.json`, artifact bundles, usage and `evaluation.json`, including source,
reference and evaluator hashes. Reference outputs never enter the target's model input.

Live scoring reuses the artifact/numerical verifier, but does not require an intentional
coding error or particular action sequence. `evaluation_valid=0` and an unset `task_pass`
mark failed/cancelled runs for fault classification. Completed wrong results receive
`task_pass=0`; a missing-cost refusal receives a deterministic status/reason check. That
check does not establish narrative nuance, visual aesthetics or general domain competence.
`cost_complete` is separate feedback; absent provider charges are never reported as free.

For the current subscription-capable entry, use the [four-case comparison](cases.md).
Its completed live results are recorded separately from this original scripted task.
SDK behavior follows the installed LangSmith client and official
[evaluation guide](https://docs.langchain.com/langsmith/evaluation-quickstart) and
[local evaluation guidance](https://docs.langchain.com/langsmith/local).

## Observed offline integration

The real graph and rebuilt Docker image completed both scripted cases on 2026-11-11
(UTC output directory `data/output/analysis-demo-20261112T002924589208Z`). All independent
checks passed: 12 report artifacts, intended coding-error recovery, PNG delivery, wrong-result
rejection, missing-cost refusal and unchanged source. Combined measured run latency was
5.19 seconds. The analyst container's peak memory was 129,146,880 bytes (about 123 MiB).
Model inference cost was zero because no provider was called. Both actual PNGs were opened
and inspected: labels, USD units and plotted category/day values were readable.

The two preceding failed run records remain available. The first exposed an undersized
graph-recursion fuse; the second exposed an image/helper version mismatch. Those harness
faults were fixed before interpreting the successful result. This small integration does
not measure model judgment or establish large-dataset compute capacity.
