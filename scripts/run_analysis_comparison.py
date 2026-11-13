"""Run the four-case specialist suite offline, or compare explicitly qualified models.

The default exercises reference scripts through the real graph and SmolVM. It measures
integration only. Live arms use either ChatGPT subscription call limits or an explicitly
budgeted OpenRouter API route, with no fallback between billing modes.
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path

from langsmith import Client, tracing_context

from backintel.analysis import _same_cells, run_analysis
from backintel.artifacts import verify_bundle
from backintel.bench.usage import RunBudget
from backintel.models import build_model
from scripts.analysis_cases import (
    CASE_IDS,
    AnalysisCase,
    build_cases,
    scripted_spec,
    verify_case_completion,
)
from scripts.run_analysis_demo import ScriptedAnalysisModel, call


def fingerprint(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def examples_for(cases: list[AnalysisCase]) -> list[dict]:
    """The target receives inputs only; reference values are evaluator-owned outputs."""
    return [
        {
            "inputs": {"case_id": case.case_id, "brief": case.brief.model_dump()},
            "outputs": {
                "source_sha256": case.source_sha256,
                "reference_sha256": case.reference_sha256,
                "expected_status": case.expected_status,
                "reference": json.loads(case.reference.read_text()),
            },
        }
        for case in cases
    ]


def reference_model(case: AnalysisCase) -> ScriptedAnalysisModel:
    """Privileged reference solution: never use these scripted actions for live trials."""
    steps = [("list_tables", {})]
    if case.expected_status == "cannot_answer":
        steps.append(
            (
                "AnalysisCompletion",
                {
                    "status": "cannot_answer",
                    "summary": "Profit needs cost and expense inputs absent from the source.",
                    "reason": "Product costs and operating expenses are unavailable.",
                    "caveats": ["Scripted integration; not a live model decision."],
                },
            )
        )
    else:
        spec = scripted_spec(case)
        steps.extend(
            [
                ("run_shell", {"command": "cat /docs/artifact-contract.md"}),
                (
                    "write_analysis_file",
                    {"path": "/workspace/report.json", "content": json.dumps(spec)},
                ),
                ("render_report", {"spec_path": "/workspace/report.json"}),
                (
                    "inspect_chart",
                    {"path": f"/artifacts/report/charts/{spec['charts'][0]['id']}.png"},
                ),
                (
                    "AnalysisCompletion",
                    {
                        "status": "completed",
                        "summary": "The reference-scripted graph rendered the requested bundle.",
                        "caveats": ["Integration evidence, not autonomous model capability."],
                    },
                ),
            ]
        )
    return ScriptedAnalysisModel(responses=[call(name, args, i) for i, (name, args) in enumerate(steps)])


def grade(case: AnalysisCase, record: dict, directory: Path) -> list[dict]:
    """Numerical/artifact checks; unresolved failures cannot qualify an arm for review."""
    if fingerprint(case.source) != case.source_sha256 or fingerprint(case.reference) != case.reference_sha256:
        return [
            {"key": "evaluation_valid", "score": 0, "comment": "Source/reference identity changed."},
            {"key": "task_pass", "score": None, "comment": "Rebuild a new frozen trial."},
        ]
    if record.get("status") in {"failed", "cancelled", "not_run"}:
        return [
            {"key": "evaluation_valid", "score": 0, "comment": "Failure needs layer classification."},
            {"key": "task_pass", "score": None, "comment": record.get("error", "Run unfinished.")},
        ]
    try:
        report = None
        if record.get("status") == "completed":
            bundle = directory / "artifacts" / "report"
            verify_bundle(bundle)
            report = json.loads((bundle / "report.json").read_text())
            from openpyxl import load_workbook

            workbook = load_workbook(bundle / "supporting.xlsx", read_only=True, data_only=True)
            try:
                for index, table in enumerate(report["tables"], 1):
                    sheet = workbook[f"T{index}-{table['id']}"[:31]]
                    # XLSX serializes finite floats to decimal text; use the same declared
                    # numeric tolerance as evidence reproduction, preserving null/text types.
                    if not _same_cells(
                        [list(row) for row in sheet.values], [table["columns"], *table["rows"]]
                    ):
                        raise ValueError("Workbook differs from the report's analytical tables.")
            finally:
                workbook.close()
        completion = record.get("completion") or {}
        if completion.get("status") != record.get("status"):
            raise ValueError("Completion and run status disagree.")
        verify_case_completion(case, completion, report)
        passed, comment = True, "Independent case reference and delivered output agree."
    except (ValueError, KeyError, OSError) as error:
        passed, comment = False, str(error)
    usage = record.get("usage", {})
    plan_billing = usage.get("billing_mode") == "chatgpt_plan"
    return [
        {"key": "evaluation_valid", "score": 1, "comment": "Completed result available for grading."},
        {"key": "task_pass", "score": int(passed), "comment": comment},
        {
            "key": "cost_complete",
            "score": None if plan_billing else int(usage.get("cost_complete", False)),
            "comment": "Subscription billing; per-request API dollar cost is not applicable."
            if plan_billing
            else "Provider-reported cost completeness, separate from task quality.",
        },
        {
            "key": "usage_complete",
            "score": int(usage.get("usage_complete", False)),
            "comment": "Reported token completeness, separate from task quality.",
        },
    ]


def summarize_arm(
    case_ids: list[str], records: dict, scores: dict, *, scripted: bool, billing_mode: str = "api"
) -> dict:
    billing_mode = "scripted" if scripted else billing_mode
    plan_billing = billing_mode == "chatgpt_plan"
    feedback = {case: {item["key"]: item["score"] for item in items} for case, items in scores.items()}
    passed = [case for case in case_ids if feedback.get(case, {}).get("task_pass") == 1]
    wrong = [case for case in case_ids if feedback.get(case, {}).get("task_pass") == 0]
    unresolved = [case for case in case_ids if feedback.get(case, {}).get("task_pass") is None]
    costs = [record.get("usage", {}).get("cost_usd") for record in records.values()]
    complete_cost = len(records) == len(case_ids) and all(
        record.get("usage", {}).get("cost_complete", False) for record in records.values()
    )
    complete_usage = len(records) == len(case_ids) and all(
        record.get("usage", {}).get("usage_complete", False) for record in records.values()
    )
    complete_accounting = complete_usage if plan_billing else complete_cost
    if scripted:
        provider_cost = known_cost = 0
        review_basis = "Scripted integration is not eligible for live quality review"
    elif plan_billing:
        provider_cost = known_cost = None
        review_basis = "Task quality and complete reported tokens under subscription billing"
    else:
        provider_cost = sum(costs) if complete_cost else None
        known_cost = sum(cost for cost in costs if cost is not None)
        review_basis = "Task quality and complete provider-reported API charges"
    return {
        "billing_mode": billing_mode,
        "case_count": len(case_ids),
        "passed": passed,
        "wrong": wrong,
        "unresolved": unresolved,
        "all_tasks_passed": len(passed) == len(case_ids),
        "eligible_for_live_review": not scripted and len(passed) == len(case_ids) and complete_accounting,
        "review_eligibility_basis": review_basis,
        "provider_cost_usd": provider_cost,
        "known_reported_cost_usd": known_cost,
        "cost_applicable": not scripted and not plan_billing,
        "cost_complete": True if scripted else False if plan_billing else complete_cost,
        "usage_complete": complete_usage,
        "input_tokens": sum(record.get("usage", {}).get("input_tokens", 0) for record in records.values()),
        "output_tokens": sum(record.get("usage", {}).get("output_tokens", 0) for record in records.values()),
        "total_latency_s": sum(record.get("latency_s", 0) for record in records.values()),
        "provider_calls": 0
        if scripted
        else sum(record.get("usage", {}).get("llm_calls", 0) for record in records.values()),
        "scope": "Scripted integration only"
        if scripted
        else "One trial per case; quality-review eligibility only, no automatic model promotion",
    }


def run_suite(
    output: Path,
    *,
    model_ids: list[str] | None = None,
    reasoning: str = "medium",
    max_cost: float | None = None,
    reservation: float | None = None,
    langsmith: bool = False,
    dataset_name: str = "backintel-analysis-four-cases-v1",
    case_ids: list[str] | None = None,
) -> dict:
    selected = list(CASE_IDS) if case_ids is None else case_ids
    if not selected or len(set(selected)) != len(selected) or set(selected) - set(CASE_IDS):
        raise ValueError("Select distinct known case IDs; at least one case is required.")
    scripted = not model_ids
    if scripted and (langsmith or max_cost is not None or reservation is not None):
        raise ValueError("LangSmith and spend options require explicit live model IDs.")
    billing_mode, budget = "scripted", None
    if model_ids:
        providers = {model_id.split("/", 1)[0] for model_id in model_ids}
        if (
            len(set(model_ids)) != len(model_ids)
            or len(providers) != 1
            or not providers.issubset({"openrouter", "chatgpt-plan"})
            or any("/" not in model_id or not model_id.split("/", 1)[1] for model_id in model_ids)
        ):
            raise ValueError("Use distinct qualified models in one billing mode: OpenRouter or chatgpt-plan.")
        if providers == {"chatgpt-plan"}:
            if max_cost is not None or reservation is not None:
                raise ValueError("ChatGPT plan comparisons use call limits, not API dollar budget options.")
            from backintel.bench.usage import PlanRunBudget

            billing_mode = "chatgpt_plan"
            budget = PlanRunBudget(max_calls=24 * len(selected) * len(model_ids))
        else:
            if max_cost is None or reservation is None:
                raise ValueError("OpenRouter comparisons require an allowance and per-call reservation.")
            billing_mode = "api"
            budget = RunBudget(max_cost, 24 * len(selected) * len(model_ids), reservation)
    if budget and not budget.can_admit():
        raise ValueError("The allowance cannot admit one reserved request.")
    output = output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    cases = build_cases(output / "fixtures")
    examples = examples_for(cases)
    by_id = {case.case_id: case for case in cases if case.case_id in selected}
    expected_inputs = {example["inputs"]["case_id"]: example["inputs"] for example in examples}
    summary = {
        "execution": "scripted integration; not a model comparison" if scripted else "live model comparison",
        "billing_mode": billing_mode,
        "reasoning": None if scripted else reasoning,
        "repetitions": 1,
        "max_model_calls_per_case": 24,
        "max_tool_calls_per_case": 50,
        "timeout_s_per_case": 900,
        "provider_fallbacks": False,
        "case_ids": list(by_id),
        "evaluator_sha256": fingerprint(Path(__file__)),
        "cases_sha256": fingerprint(Path(__file__).with_name("analysis_cases.py")),
        "dataset_sha256": hashlib.sha256(json.dumps(examples, sort_keys=True).encode()).hexdigest(),
        "arms": [],
        "limitations": [
            "Controlled small fixtures; not unseen real-domain or large-data acceptance.",
            "Deterministic task checks do not grade every narrative claim or visual aesthetic.",
            "Unresolved failures block acceptance and need classification; they are not silently excluded.",
        ],
    }

    def handlers(arm_dir, model, model_id, records, scores, arm):
        def target(inputs: dict) -> dict:
            case_id = inputs.get("case_id")
            if case_id not in by_id or inputs != expected_inputs[case_id]:
                raise ValueError("Inputs differ from the frozen case.")
            case = by_id[case_id]
            destination = arm_dir / case_id
            if budget and not budget.can_admit():
                destination.mkdir()
                record = {
                    "status": "not_run",
                    "error": "Shared budget cannot admit another call.",
                    "usage": {
                        "billing_mode": billing_mode,
                        "cost_usd": None,
                        "cost_applicable": billing_mode == "api",
                        "cost_complete": False,
                        "usage_complete": False,
                        "llm_calls": 0,
                    },
                }
                (destination / "run.json").write_text(json.dumps(record, indent=2))
            else:
                store = case.open_store()
                try:
                    record = asyncio.run(
                        run_analysis(
                            case.brief,
                            model=reference_model(case) if scripted else model,
                            model_id=model_id,
                            store=store,
                            output=destination,
                            budget=budget,
                            max_model_calls=24,
                            max_tool_calls=50,
                            timeout_s=900,
                            scripted=scripted,
                        )
                    )
                finally:
                    store.close()
            records[case_id] = record
            arm["records"][case_id] = str(destination / "run.json")
            report = destination / "artifacts" / "report" / "report.json"
            return {
                **{key: value for key, value in record.items() if key != "messages"},
                "report": json.loads(report.read_text()) if report.exists() else None,
            }

        def evaluator(inputs: dict, outputs: dict, reference_outputs: dict) -> list[dict]:
            case_id = inputs["case_id"]
            expected = next(
                example["outputs"] for example in examples if example["inputs"]["case_id"] == case_id
            )
            if reference_outputs != expected:
                raise ValueError("Reference outputs differ from the frozen case.")
            scores[case_id] = grade(by_id[case_id], outputs, arm_dir / case_id)
            return scores[case_id]

        return target, evaluator

    client, stored = None, None
    try:
        if langsmith:
            client = Client()
            if client.has_dataset(dataset_name=dataset_name):
                dataset = client.read_dataset(dataset_name=dataset_name)
            else:
                dataset = client.create_dataset(
                    dataset_name=dataset_name,
                    description=(
                        "BackIntel: retail, energy and service availability; frozen independent references."
                    ),
                )
                client.create_examples(dataset_id=dataset.id, examples=examples)
            stored = list(client.list_examples(dataset_id=dataset.id))
            actual = [{"inputs": item.inputs, "outputs": item.outputs} for item in stored]
            if sorted(actual, key=lambda x: x["inputs"]["case_id"]) != sorted(
                examples, key=lambda x: x["inputs"]["case_id"]
            ):
                raise ValueError("Existing LangSmith dataset differs. Use a new version; never overwrite it.")
            stored = [item for item in stored if item.inputs["case_id"] in by_id]
        for index, model_id in enumerate(model_ids or ["scripted-reference"]):
            arm_dir = output / f"arm-{index}"
            arm_dir.mkdir()
            records, scores = {}, {}
            arm = {"model": model_id, "billing_mode": billing_mode, "records": {}, "scores": scores}
            summary["arms"].append(arm)
            model = (
                None
                if scripted
                else build_model(
                    model_id,
                    reasoning_effort=reasoning,
                    responses_api=True,
                    first_party_only=billing_mode == "api",
                    max_retries=0,
                    timeout_s=300,
                )
            )

            target, evaluator = handlers(arm_dir, model, model_id, records, scores, arm)

            try:
                if client:
                    results = client.evaluate(
                        target,
                        data=stored,
                        evaluators=[evaluator],
                        experiment_prefix="backintel-specialist-" + model_id.rsplit("/", 1)[-1],
                        metadata={key: value for key, value in summary.items() if key != "arms"},
                        max_concurrency=1,
                        num_repetitions=1,
                        blocking=False,
                    )
                    arm["runs"] = [
                        {"case_id": row["example"].inputs["case_id"], "run_id": str(row["run"].id)}
                        for row in results
                    ]
                    arm["experiment"] = results.experiment_name
                    arm["url"] = client.read_project(project_name=results.experiment_name).url
                else:
                    with tracing_context(enabled=False):
                        for example in examples:
                            if example["inputs"]["case_id"] not in by_id:
                                continue
                            result = target(example["inputs"])
                            evaluator(example["inputs"], result, example["outputs"])
            finally:
                arm["summary"] = summarize_arm(
                    list(by_id), records, scores, scripted=scripted, billing_mode=billing_mode
                )
    finally:
        summary["budget"] = budget.report() if budget else None
        (output / "comparison.json").write_text(json.dumps(summary, indent=2, default=str))
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/output") / ("analysis-suite-" + datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ")),
    )
    parser.add_argument(
        "--model",
        action="append",
        help="Qualified openrouter/... or chatgpt-plan/... model; repeat within one billing mode.",
    )
    parser.add_argument(
        "--reasoning", choices=["none", "minimal", "low", "medium", "high", "xhigh"], default="medium"
    )
    parser.add_argument(
        "--max-cost-usd", type=float, help="OpenRouter only: shared approved dollar allowance."
    )
    parser.add_argument("--reservation-usd", type=float, help="OpenRouter only: per-call dollar reservation.")
    parser.add_argument("--langsmith", action="store_true")
    parser.add_argument("--dataset", default="backintel-analysis-four-cases-v1")
    parser.add_argument(
        "--case", action="append", choices=CASE_IDS, help="Run only selected cases; repeatable."
    )
    args = parser.parse_args()
    result = run_suite(
        args.output,
        model_ids=args.model,
        reasoning=args.reasoning,
        max_cost=args.max_cost_usd,
        reservation=args.reservation_usd,
        langsmith=args.langsmith,
        dataset_name=args.dataset,
        case_ids=args.case,
    )
    print(json.dumps(result, indent=2))
    if any(not arm["summary"]["all_tasks_passed"] for arm in result["arms"]):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
