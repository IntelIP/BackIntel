# Default analysis specialist

The owner selected **GPT-6.1 Sol through the ChatGPT subscription**, with **medium reasoning**,
after a controlled four-case comparison on the previous Docker runtime. Sol passed four cases;
Luna passed two. This is a
specialist configuration decision, not a production release or a general model ranking.

`backintel analyze` resolves its model in this order:

1. Explicit `--model` argument.
2. `BACKINTEL_ANALYSIS_MODEL` environment setting.
3. Built-in `chatgpt-plan/gpt-6.1-sol` default.

Use `--reasoning` to override medium. The specialist uses SmolVM isolation, read-only
source access and explicit model/tool/time limits. Subscription errors stop work; there is
no paid API fallback. Token usage is reported without inventing a per-request dollar charge.

```bash
docker build -f Dockerfile.sandbox -t backintel-sandbox:py312 .
uv run python -m scripts.prepare_smolvm
uv run backintel chatgpt login
uv run backintel chatgpt models
uv run backintel analyze --store sqlite:olist --brief brief.json --output data/output/my-report
```

The brief is a JSON object with a required `objective`; it can include `business_context`,
`audience`, `metric_definitions`, `time_window`, `known_limitations` and `required_outputs`.
Use a new output directory for each run. The result contains a run record and, on success,
verified HTML reports, charts, CSV tables and an XLSX workbook. Model inference uses the
subscription; Python and rendering use local SmolVM resources. Native source SQL queries
use the assigned store. The qualified host is macOS ARM64; see [sandbox setup](sandbox-environment.md).

An explicit OpenRouter override requires both `--max-cost-usd` and `--reservation-usd`.
These dollar flags are rejected for subscription runs. Comparison experiments require
explicit model IDs; changing this application default does not change a frozen benchmark.
