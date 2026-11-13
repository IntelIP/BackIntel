"""Exercise the specialist graph with an offline script or an explicit live model.

By default this is an offline integration demonstration, not a live model evaluation. Its fixture
builder, scripted actions and independent verifier are evaluator-side and never mounted
into the analyst VM. Only the SQLite source file is mounted read-only. The optional
live mode uses the same two cases and requires an explicit model and finite budget.
"""

from __future__ import annotations

import argparse
import asyncio
import copy
import csv
import hashlib
import json
import sqlite3
from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path

from langchain_core.language_models.fake_chat_models import FakeMessagesListChatModel
from langchain_core.messages import AIMessage
from pydantic import Field

from backintel.analysis import AnalysisBrief, run_analysis
from backintel.artifacts import validate_report, verify_bundle
from backintel.stores.sqlite import SQLiteStore


class ScriptedAnalysisModel(FakeMessagesListChatModel):
    """A fixed sequence of tool calls; no inference, credentials or provider requests."""

    model_name: str = "backintel-scripted-analysis-demo"
    bindings: list[list[str]] = Field(default_factory=list)

    def bind_tools(self, tools, **kwargs):
        self.bindings.append([t.name if hasattr(t, "name") else t["name"] for t in tools])
        return self


def call(name: str, args: dict, index: int) -> AIMessage:
    return AIMessage(content="", tool_calls=[{"name": name, "args": args, "id": f"demo-{index}"}])


def create_source(path: Path) -> None:
    """Small synthetic business dataset, deliberately unlike a clean SUM fixture."""
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        raise ValueError("Create a new fixture; do not overwrite an existing database.")
    with sqlite3.connect(path) as connection:
        connection.executescript("""
            CREATE TABLE orders(order_id INTEGER PRIMARY KEY, ordered_on TEXT, status TEXT);
            CREATE TABLE lines(line_id INTEGER, order_id INTEGER, sku TEXT,
                               quantity INTEGER, unit_cents INTEGER);
            CREATE TABLE catalog(sku TEXT PRIMARY KEY, category TEXT);
            CREATE TABLE refunds(refund_id INTEGER PRIMARY KEY, line_id INTEGER, quantity INTEGER);
        """)
        connection.executemany(
            "INSERT INTO orders VALUES (?,?,?)",
            [
                (1, "2026-11-01", "delivered"),
                (2, "2026-11-02", "delivered"),
                (3, "2026-11-02", "cancelled"),
                (4, "2026-11-03", "delivered"),
            ],
        )
        connection.executemany(
            "INSERT INTO catalog VALUES (?,?)",
            [
                ("a", "Essentials"),
                ("b", "Home"),
                ("c", "Outdoor"),
            ],
        )
        connection.executemany(
            "INSERT INTO lines VALUES (?,?,?,?,?)",
            [
                (1, 1, "a", 2, 1000),
                (2, 1, "b", 1, 2500),
                (2, 1, "b", 1, 2500),
                (3, 2, "a", 3, 1000),
                (4, 2, "c", 1, 4000),
                (5, 3, "c", 8, 4000),
                (6, 4, "b", 2, 2500),
            ],
        )
        connection.executemany(
            "INSERT INTO refunds VALUES (?,?,?)",
            [
                (1, 1, 1),
                (2, 3, 1),
                (3, 3, 1),
            ],
        )


def brief(*, profit: bool = False) -> AnalysisBrief:
    return AnalysisBrief(
        objective=(
            "Calculate net profit for the delivered orders in the assigned period."
            if profit
            else "Produce a business report of delivered-order net revenue by category and day, "
            "including a total metric, static and interactive charts, and supporting sheets."
        ),
        business_context="A synthetic retailer wants an operational sales review. All money is USD.",
        audience="Operations manager",
        metric_definitions={
            "net_revenue": "Deduplicate exact repeated line rows; include delivered orders only; "
            "subtract the summed refunded quantity for each line before multiplying by unit price. "
            "Prices are integer cents. Revenue is not profit.",
        },
        time_window="2026-11-01 through 2026-11-03 inclusive",
        known_limitations=["Synthetic fixture, not customer data. No product-cost or expense fields."],
        required_outputs=["report", "static charts", "interactive charts", "CSV", "XLSX"],
    )


_NET = """
WITH unique_lines AS (SELECT DISTINCT line_id, order_id, sku, quantity, unit_cents FROM lines),
refund_totals AS (SELECT line_id, SUM(quantity) AS refunded FROM refunds GROUP BY line_id),
net AS (
  SELECT o.ordered_on, c.category,
         (l.quantity - COALESCE(r.refunded, 0)) * l.unit_cents AS net_cents
  FROM unique_lines l JOIN orders o ON o.order_id = l.order_id
  JOIN catalog c ON c.sku = l.sku
  LEFT JOIN refund_totals r ON r.line_id = l.line_id
  WHERE o.status = 'delivered' AND o.ordered_on BETWEEN '2026-11-01' AND '2026-11-03'
)
""".strip()

ANALYSIS_QUERIES = {
    "categories": _NET + "\nSELECT category AS Category, SUM(net_cents)/100.0 AS Revenue "
    "FROM net GROUP BY category ORDER BY Revenue DESC, Category",
    "daily": _NET + "\nSELECT ordered_on AS Date, SUM(net_cents)/100.0 AS Revenue "
    "FROM net GROUP BY ordered_on ORDER BY Date",
    "total": _NET + "\nSELECT SUM(net_cents)/100.0 AS Revenue FROM net",
}


def analysis_program() -> str:
    """The model's scripted calculation uses SQL, with no expected answers embedded."""
    return f"""import json, os, sqlite3
from pathlib import Path
connection = sqlite3.connect("file:" + os.environ["BACKINTEL_SQLITE_PATH"] + "?mode=ro", uri=True)
queries = {ANALYSIS_QUERIES!r}
tables = []
for table_id, query in queries.items():
    result = connection.execute(query)
    tables.append({{"id": table_id, "title": table_id.title() + " net revenue",
                   "columns": [c[0] for c in result.description],
                   "rows": [list(row) for row in result.fetchall()],
                   "units": {{"Revenue": "USD"}}, "evidence_ids": [table_id + "-sql"]}})
connection.close()
by_id = {{t["id"]: t for t in tables}}
assert abs(sum(row[1] for row in by_id["categories"]["rows"]) - by_id["total"]["rows"][0][0]) < 1e-9
assert abs(sum(row[1] for row in by_id["daily"]["rows"]) - by_id["total"]["rows"][0][0]) < 1e-9
report = {{
    "title": "Delivered sales after refunds",
    "summary": "A consistent view of delivered-order revenue across categories and days. "
               "Cancelled orders and exact duplicate lines are excluded; split refunds are combined.",
    "findings": ["The category chart identifies the largest revenue contribution after refunds.",
                 "Daily values reconcile to the total for the same delivered-order population."],
    "caveats": ["Synthetic three-day demonstration; no production reliability claim.",
                "No cost data is supplied, so revenue cannot establish profit or margin.",
                "The chart-inspection tool is exercised by a scripted client, not a vision model."],
    "tables": tables,
    "metrics": [{{"id": "net-revenue", "label": "Net revenue", "table": "total", "row": 0,
                 "column": "Revenue", "definition": "Delivered line revenue less refunded units, "
                 "after exact-row deduplication, 1–3 November 2026."}}],
    "charts": [{{"id": "category-revenue", "title": "Net revenue by category", "kind": "bar",
                "table": "categories", "x": "Category", "y": "Revenue"}},
               {{"id": "daily-revenue", "title": "Net revenue by day", "kind": "line",
                "table": "daily", "x": "Date", "y": "Revenue"}}],
    "evidence": [{{"id": name + "-sql", "kind": "sql", "code": query,
                  "source_ids": ["assigned"]}} for name, query in queries.items()]
}}
Path("/workspace/report-spec.json").write_text(json.dumps(report))
print(json.dumps({{"tables": tables, "spec_path": "/workspace/report-spec.json"}}))
"""


def scripted_model(*, profit: bool = False) -> ScriptedAnalysisModel:
    steps = [
        ("list_tables", {}),
        ("describe_table", {"table": "lines"}),
    ]
    if profit:
        steps.append(
            (
                "AnalysisCompletion",
                {
                    "status": "cannot_answer",
                    "summary": "Profit cannot be calculated from sales alone.",
                    "reason": "Product costs and operating expenses are absent. Revenue is not profit.",
                    "caveats": ["No proxy profit calculation was substituted."],
                },
            )
        )
    else:
        steps.extend(
            [
                ("describe_table", {"table": "orders"}),
                ("describe_table", {"table": "catalog"}),
                ("describe_table", {"table": "refunds"}),
                ("run_shell", {"command": "cat /docs/artifact-contract.md"}),
                (
                    "write_analysis_file",
                    {
                        "path": "/workspace/analysis.py",
                        "content": "import os, sqlite3\n"
                        "c=sqlite3.connect('file:'+os.environ['BACKINTEL_SQLITE_PATH']+'?mode=ro',uri=True)\n"
                        "print(c.execute('SELECT amount FROM lines').fetchall())\n",
                    },
                ),
                ("run_shell", {"command": "python /workspace/analysis.py"}),
                ("write_analysis_file", {"path": "/workspace/analysis.py", "content": analysis_program()}),
                ("run_shell", {"command": "python /workspace/analysis.py"}),
                ("render_report", {"spec_path": "/workspace/report-spec.json"}),
                ("inspect_chart", {"path": "/artifacts/report/charts/category-revenue.png"}),
                (
                    "AnalysisCompletion",
                    {
                        "status": "completed",
                        "summary": "The scripted run generated a reconciled report, charts and workbook.",
                        "caveats": ["Integration demonstration, not a measured live-model success."],
                    },
                ),
            ]
        )
    return ScriptedAnalysisModel(responses=[call(name, args, i) for i, (name, args) in enumerate(steps)])


def independent_reference(path: Path) -> dict:
    """Independent row-wise integer arithmetic; does not reuse the analyst's SQL."""
    with sqlite3.connect(f"file:{path}?mode=ro", uri=True) as connection:
        orders = {row[0]: row[1:] for row in connection.execute("SELECT * FROM orders")}
        categories = dict(connection.execute("SELECT * FROM catalog"))
        refunds = defaultdict(int)
        for _, line_id, quantity in connection.execute("SELECT * FROM refunds"):
            refunds[line_id] += quantity
        lines = set(connection.execute("SELECT * FROM lines"))
    by_category, by_day = defaultdict(int), defaultdict(int)
    for line_id, order_id, sku, quantity, unit_cents in lines:
        day, status = orders[order_id]
        if status != "delivered" or not "2026-11-01" <= day <= "2026-11-03":
            continue
        cents = (quantity - refunds[line_id]) * unit_cents
        by_category[categories[sku]] += cents
        by_day[day] += cents
    return {
        "categories": {
            "columns": ["Category", "Revenue"],
            "rows": [
                [key, value / 100]
                for key, value in sorted(by_category.items(), key=lambda item: (-item[1], item[0]))
            ],
        },
        "daily": {
            "columns": ["Date", "Revenue"],
            "rows": [[key, value / 100] for key, value in sorted(by_day.items())],
        },
        "total": {"columns": ["Revenue"], "rows": [[sum(by_category.values()) / 100]]},
    }


def verify_reference(report: dict, source: Path) -> None:
    expected = independent_reference(source)
    actual = {t["id"]: {"columns": t["columns"], "rows": t["rows"]} for t in report["tables"]}
    # Row/table presentation order is not a business-correctness requirement.
    if actual.keys() != expected.keys() or any(
        actual[name]["columns"] != table["columns"] or sorted(actual[name]["rows"]) != sorted(table["rows"])
        for name, table in expected.items()
    ):
        raise ValueError("Report values differ from the independent raw-source reference.")


def verify_outputs(directory: Path, source: Path, *, scripted_trace: bool = True) -> dict:
    """Check actual files and trace; this does not grade visual aesthetics or model reasoning."""
    from openpyxl import load_workbook

    record = json.loads((directory / "run.json").read_text())
    if record["status"] != "completed":
        raise ValueError(f"Specialist did not complete: {record.get('error', record['status'])}")
    bundle = directory / "artifacts" / "report"
    manifest = verify_bundle(bundle)
    report = json.loads((bundle / "report.json").read_text())
    verify_reference(report, source)
    if not any(
        metric["table"] == "total" and metric["column"] == "Revenue" and metric["row"] == 0
        for metric in report["metrics"]
    ):
        raise ValueError("The requested total-revenue metric is missing.")
    if not {"categories", "daily"}.issubset({chart["table"] for chart in report["charts"]}):
        raise ValueError("The requested category and daily charts are missing.")
    workbook = load_workbook(bundle / "supporting.xlsx", read_only=True, data_only=True)
    try:
        for index, table in enumerate(report["tables"], 1):
            with (bundle / "tables" / f"{table['id']}.csv").open(newline="") as handle:
                csv_rows = list(csv.reader(handle))
            expected_csv = [[str(v) for v in row] for row in [table["columns"], *table["rows"]]]
            if csv_rows != expected_csv:
                raise ValueError("CSV disagrees with the canonical analytical table.")
            sheet = workbook[f"T{index}-{table['id']}"[:31]]
            if [list(row) for row in sheet.values] != [table["columns"], *table["rows"]]:
                raise ValueError("Workbook disagrees with the canonical analytical table.")
    finally:
        workbook.close()
    messages = record["messages"]
    failed_program = any(
        m.get("type") == "tool"
        and m.get("name") == "run_shell"
        and "no such column: amount" in str(m.get("content"))
        for m in messages
    )
    chart_returned = any(
        m.get("type") == "tool"
        and m.get("name") == "inspect_chart"
        and "data:image/png;base64," in str(m.get("content"))
        for m in messages
    )
    if scripted_trace and (not failed_program or not chart_returned):
        raise ValueError("The full trace did not exercise error recovery and image delivery.")
    if scripted_trace:
        for message in messages:
            if message.get("type") != "tool":
                continue
            content = message.get("content", "")
            if isinstance(content, str) and content.startswith("Error invoking tool"):
                raise ValueError("The scripted integration contains an unintended tool-schema error.")
            if message.get("name") in {"run_shell", "run_python", "write_analysis_file", "render_report"}:
                result = json.loads(content)
                if result.get("exit_code") != 0 and "no such column: amount" not in result.get("stderr", ""):
                    raise ValueError("The scripted integration contains an unintended command error.")
    wrong = copy.deepcopy(report)
    for table in wrong["tables"]:
        if table["id"] in {"categories", "daily"}:
            table["rows"][0][1] += 1
        else:
            table["rows"][0][0] += 1
    wrong_tables = {table["id"]: table for table in wrong["tables"]}
    for metric in wrong["metrics"]:
        table = wrong_tables[metric["table"]]
        metric["value"] = table["rows"][metric["row"]][table["columns"].index(metric["column"])]
    validate_report(wrong)  # A consistent shape must not be enough to pass factual grading.
    try:
        verify_reference(wrong, source)
    except ValueError:
        negative_rejected = True
    else:
        raise AssertionError("Independent verifier accepted the deliberately wrong control.")
    return {
        "independent_numbers": True,
        "csv_workbook_consistency": True,
        "failed_program_then_recovery": failed_program,
        "png_returned_through_tool": chart_returned,
        "wrong_result_control_rejected": negative_rejected,
        "artifact_count": len(manifest["artifacts"]),
        "report": str(bundle / "report.html"),
    }


async def run_demo(output: Path, *, profile: str = "analysis") -> dict:
    output = output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    source = output / "sources" / "sales.sqlite"
    create_source(source)
    before = hashlib.sha256(source.read_bytes()).hexdigest()
    store = SQLiteStore(source, dataset="analysis-demo")
    try:
        success = await run_analysis(
            brief(),
            model=scripted_model(),
            model_id="scripted/offline",
            store=store,
            output=output / "report-run",
            profile=profile,
            max_model_calls=20,
            max_tool_calls=30,
            scripted=True,
        )
        if success["status"] != "completed":
            raise RuntimeError(f"Report run failed: {success.get('error', success['status'])}")
        checks = verify_outputs(output / "report-run", source)
        refusal = await run_analysis(
            brief(profit=True),
            model=scripted_model(profit=True),
            model_id="scripted/offline",
            store=store,
            output=output / "missing-cost-run",
            profile=profile,
            max_model_calls=5,
            max_tool_calls=5,
            scripted=True,
        )
        if refusal["status"] != "cannot_answer" or "cost" not in refusal["completion"]["reason"]:
            raise ValueError("Missing-cost scenario did not produce the expected explanatory refusal.")
        if hashlib.sha256(source.read_bytes()).hexdigest() != before:
            raise ValueError("The read-only source changed during execution.")
        summary = {
            "execution": "scripted integration; not a model evaluation",
            "provider_calls": 0,
            "model_cost_usd": 0,
            "checks": {**checks, "missing_cost_refusal": True, "source_unchanged": True},
            "resources": success["resources"],
            "latency_s": success["latency_s"] + refusal["latency_s"],
            "limits": [
                "Scripted decisions do not establish LLM competence.",
                "Image delivery was exercised; visual aesthetics require separate inspection.",
                "The fixture is small and synthetic, not a large-data benchmark.",
            ],
        }
        (output / "evaluation.json").write_text(json.dumps(summary, indent=2))
        return summary
    finally:
        store.close()


def evaluation_examples(source: Path) -> list[dict]:
    """Only inputs reach the analyst; outputs are evaluator-owned reference material."""
    report_brief = brief().model_dump()
    report_brief["required_outputs"].append(
        "Machine-readable tables: categories with columns Category, Revenue; daily with columns "
        "Date, Revenue; total with column Revenue and one row. Revenue values are USD. "
        "Use those table IDs and column names; presentation order is your choice."
    )
    source_hash = hashlib.sha256(source.read_bytes()).hexdigest()
    return [
        {
            "inputs": {"case_id": "report", "brief": report_brief},
            "outputs": {
                "status": "completed",
                "source_sha256": source_hash,
                "tables": independent_reference(source),
            },
        },
        {
            "inputs": {"case_id": "missing-cost", "brief": brief(profit=True).model_dump()},
            "outputs": {"status": "cannot_answer", "source_sha256": source_hash},
        },
    ]


def grade_case(case_id: str, record: dict, directory: Path, source: Path, reference: dict) -> list[dict]:
    """Deterministic task feedback; failed runs require triage before a model-quality claim."""
    if hashlib.sha256(source.read_bytes()).hexdigest() != reference["source_sha256"]:
        return [{"key": "evaluation_valid", "score": 0, "comment": "Assigned source changed."}]
    if record.get("status") in {"failed", "cancelled"}:
        return [
            {"key": "evaluation_valid", "score": 0, "comment": "Run requires failure classification."},
            {"key": "task_pass", "score": None, "comment": record.get("error", "Run did not finish.")},
        ]
    if case_id == "report":
        if independent_reference(source) != reference["tables"]:
            raise ValueError("Frozen reference does not match the assigned source.")
        try:
            verify_outputs(directory, source, scripted_trace=False)
            passed, comment = True, "Independent numerical reference and exported bundle agree."
        except (ValueError, KeyError, OSError) as error:
            passed, comment = False, str(error)
    else:
        reason = record.get("completion", {}).get("reason", "").lower()
        passed = record.get("status") == "cannot_answer" and any(
            term in reason for term in ("cost", "expense")
        )
        comment = "Deterministic missing-cost refusal check; narrative nuance is not graded."
    return [
        {"key": "evaluation_valid", "score": 1, "comment": "Run available for deterministic grading."},
        {"key": "task_pass", "score": int(passed), "comment": comment},
        {
            "key": "cost_complete",
            "score": int(record.get("usage", {}).get("cost_complete", False)),
            "comment": "Missing provider costs are unknown, never zero.",
        },
    ]


def run_live(
    output: Path,
    *,
    model_id: str,
    reasoning: str,
    max_cost: float,
    reservation: float,
    profile: str = "analysis",
    langsmith: bool = False,
    dataset_name: str = "backintel-analysis-artifacts-v1",
) -> dict:
    """Two real runs, one repetition, serial, with shared admission and no provider retries."""
    from langsmith import Client, tracing_context

    from backintel.bench.usage import RunBudget
    from backintel.models import build_model

    if not model_id.startswith("openrouter/"):
        raise ValueError("This live entry requires OpenRouter provider-reported cost accounting.")
    budget = RunBudget(limit_usd=max_cost, max_calls=48, reservation_usd=reservation)
    if not budget.can_admit():
        raise ValueError("The declared budget cannot admit even one reserved call.")
    model = build_model(
        model_id,
        reasoning_effort=reasoning,
        responses_api=True,
        first_party_only=True,
        max_retries=0,
        timeout_s=300,
    )
    output = output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    source = output / "sources" / "sales.sqlite"
    create_source(source)
    examples = evaluation_examples(source)
    by_id = {example["inputs"]["case_id"]: example for example in examples}
    scores, records = {}, {}

    def target(inputs: dict) -> dict:
        case_id = inputs["case_id"]
        if case_id not in by_id or inputs != by_id[case_id]["inputs"]:
            raise ValueError("Dataset inputs differ from this frozen two-case task.")
        store = SQLiteStore(source, dataset="analysis-live-eval")
        try:
            record = asyncio.run(
                run_analysis(
                    AnalysisBrief.model_validate(inputs["brief"]),
                    model=model,
                    model_id=model_id,
                    store=store,
                    output=output / (case_id + "-run"),
                    profile=profile,
                    budget=budget,
                    max_model_calls=24,
                    max_tool_calls=50,
                    timeout_s=900,
                )
            )
        finally:
            store.close()
        records[case_id] = record
        report_path = output / (case_id + "-run") / "artifacts" / "report" / "report.json"
        return {
            **{key: value for key, value in record.items() if key != "messages"},
            "report": json.loads(report_path.read_text()) if report_path.exists() else None,
            "output_dir": str(output / (case_id + "-run")),
        }

    def evaluator(inputs: dict, outputs: dict, reference_outputs: dict) -> list[dict]:
        case_id = inputs["case_id"]
        scores[case_id] = grade_case(case_id, outputs, output / (case_id + "-run"), source, reference_outputs)
        return scores[case_id]

    summary = {
        "execution": "live model evaluation",
        "model": model_id,
        "reasoning": reasoning,
        "api": "responses",
        "routing": "first party only; no fallbacks",
        "cases": 2,
        "repetitions": 1,
        "max_model_calls_per_case": 24,
        "max_tool_calls_per_case": 50,
        "timeout_s_per_case": 900,
        "source_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
        "reference_sha256": hashlib.sha256(
            json.dumps([example["outputs"] for example in examples], sort_keys=True).encode()
        ).hexdigest(),
        "evaluator_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "scope": "Initial two-case smoke evaluation, not the planned expanded model comparison.",
    }
    try:
        if langsmith:
            client = Client()
            if client.has_dataset(dataset_name=dataset_name):
                dataset = client.read_dataset(dataset_name=dataset_name)
            else:
                dataset = client.create_dataset(
                    dataset_name=dataset_name,
                    description="BackIntel analysis v1: joined/refunded/duplicate sales and missing costs.",
                )
                client.create_examples(dataset_id=dataset.id, examples=examples)
            stored = list(client.list_examples(dataset_id=dataset.id))
            frozen = [{"inputs": ex.inputs, "outputs": ex.outputs} for ex in stored]
            if sorted(frozen, key=lambda ex: ex["inputs"]["case_id"]) != sorted(
                examples, key=lambda ex: ex["inputs"]["case_id"]
            ):
                raise ValueError(
                    "Existing LangSmith dataset differs; create a new version, do not overwrite."
                )
            results = client.evaluate(
                target,
                data=stored,
                evaluators=[evaluator],
                experiment_prefix="backintel-analysis-" + model_id.rsplit("/", 1)[-1],
                metadata=summary,
                max_concurrency=1,
                num_repetitions=1,
                blocking=False,
                description="Actual specialist graph; independent code grading; no LLM judge.",
            )
            summary["langsmith_runs"] = [
                {"case_id": row["example"].inputs["case_id"], "run_id": str(row["run"].id)} for row in results
            ]
            summary["experiment"] = results.experiment_name
            summary["project_url"] = client.read_project(project_name=results.experiment_name).url
        else:
            with tracing_context(enabled=False):
                for example in examples:
                    result = target(example["inputs"])
                    evaluator(example["inputs"], result, example["outputs"])
    finally:
        summary["budget"] = budget.report()
        summary["scores"] = scores
        summary["usage"] = {case: record["usage"] for case, record in records.items()}
        (output / "evaluation.json").write_text(json.dumps(summary, indent=2, default=str))
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/output") / ("analysis-demo-" + datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ")),
    )
    parser.add_argument("--profile", choices=["analysis", "large"], default="analysis")
    parser.add_argument("--live", action="store_true", help="run an explicitly qualified live model")
    parser.add_argument("--model", help="qualified model/endpoint; no default or policy approval implied")
    parser.add_argument(
        "--reasoning", choices=["none", "minimal", "low", "medium", "high", "xhigh"], default="medium"
    )
    parser.add_argument(
        "--max-cost-usd", type=float, help="shared approved admission allowance for both cases"
    )
    parser.add_argument(
        "--reservation-usd", type=float, help="approved per-call reservation, not a billing cap"
    )
    parser.add_argument("--langsmith", action="store_true", help="upload live dataset, traces and experiment")
    parser.add_argument("--dataset", default="backintel-analysis-artifacts-v1")
    args = parser.parse_args()
    if args.live:
        if not args.model or args.max_cost_usd is None or args.reservation_usd is None:
            parser.error("--live requires --model, --max-cost-usd and --reservation-usd")
        result = run_live(
            args.output,
            model_id=args.model,
            reasoning=args.reasoning,
            max_cost=args.max_cost_usd,
            reservation=args.reservation_usd,
            profile=args.profile,
            langsmith=args.langsmith,
            dataset_name=args.dataset,
        )
    else:
        if args.langsmith or args.model or args.max_cost_usd is not None or args.reservation_usd is not None:
            parser.error("Model, budget and LangSmith options require --live")
        result = asyncio.run(run_demo(args.output, profile=args.profile))
    print(json.dumps(result, indent=2, default=str))


if __name__ == "__main__":
    main()
