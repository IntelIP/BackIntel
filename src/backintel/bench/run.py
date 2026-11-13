"""Run scenarios through the analyst and score them, locally and as LangSmith experiments.

One `run_scenario` does the whole job for a question: build the answer, score it with code,
re-execute its evidence, ask the judge, and record tokens, cost and latency. The LangSmith path
wraps the same functions as `evaluate()` target and evaluators so experiments and local runs
measure the same thing. Every record is also appended to `results/raw/<experiment>.jsonl`.
"""

from __future__ import annotations

import hashlib
import importlib.metadata
import json
import subprocess
import time
import traceback
from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from langchain_core.messages import AIMessage, ToolMessage

from backintel.agent import build_agent, method_version
from backintel.bench.judge import judge_answer, judge_version
from backintel.bench.judge_context import build_judge_context, context_version
from backintel.bench.oracle import load_answers
from backintel.bench.scoring import abstention_correct, evidence_reproduces, score_correct
from backintel.bench.usage import BudgetExceeded, NativeRunBudget, RunBudget, UsageTracker
from backintel.contracts import AnalystAnswer, Scenario
from backintel.models import build_model, usage_from_message
from backintel.providers.chatgpt_plan import PlanUsageStopped
from backintel.sandbox import PythonSandbox
from backintel.settings import Settings, repo_root
from backintel.stores import open_store
from backintel.stores.base import Store

RESULTS_DIR = repo_root() / "results" / "raw"
RECURSION_LIMIT = 80


def git_sha() -> str:
    try:
        return subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True,
            text=True,
            cwd=repo_root(),
            check=True,
        ).stdout.strip()
    except Exception:
        return "unknown"


def source_version(root: Path | None = None) -> str:
    """Identify the actual working code even before the owner authorizes a commit."""
    digest = hashlib.sha256()
    root = root or repo_root()
    paths = [
        *sorted((root / "src").rglob("*.py")),
        *sorted((root / "src").rglob("*.md")),
        root / "uv.lock",
        root / "Dockerfile.sandbox",
        root / "compose.yaml",
    ]
    for path in paths:
        if path.exists():
            digest.update(str(path.relative_to(root)).encode())
            digest.update(path.read_bytes())
    return digest.hexdigest()[:16]


def working_tree() -> str:
    try:
        status = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=repo_root(),
            text=True,
            capture_output=True,
            check=True,
        ).stdout
        return "dirty; source_version identifies working code" if status.strip() else "clean"
    except (OSError, subprocess.CalledProcessError):
        return "unknown"


def scorer_version(root: Path | None = None) -> str:
    """Lock implementation, not merely rubric labels, when comparing candidate runs."""
    digest = hashlib.sha256()
    root = root or repo_root()
    for relative in (
        "bench/scoring.py",
        "bench/judge.py",
        "bench/judge_context.py",
        "bench/run.py",
        "bench/usage.py",
        "contracts.py",
    ):
        path = root / "src" / "backintel" / relative
        digest.update(relative.encode())
        digest.update(path.read_bytes())
    return digest.hexdigest()[:16]


def reference_version(scenarios: Iterable[Scenario]) -> str:
    return hashlib.sha256(
        json.dumps([s.model_dump() for s in scenarios], sort_keys=True).encode()
    ).hexdigest()[:16]


def _provider_error_envelope(error: Exception) -> bool:
    """LangChain may wrap the provider's structured HTTP error in a plain ValueError."""
    if not isinstance(error, ValueError) or not error.args or not isinstance(error.args[0], dict):
        return False
    envelope = error.args[0]
    metadata = envelope.get("metadata")
    return (
        isinstance(envelope.get("message"), str)
        and isinstance(envelope.get("code"), int)
        and 400 <= envelope["code"] <= 599
        and isinstance(metadata, dict)
        and isinstance(metadata.get("error_type"), str)
        and bool(metadata["error_type"])
    )


@dataclass
class Harness:
    settings: Settings
    store: Store
    sandbox: PythonSandbox
    model_id: str
    agent: Any
    scenarios: dict[str, Scenario]
    judge: bool = True
    run_metadata: dict = field(default_factory=dict)
    budget: RunBudget | None = None
    _extra: dict = field(default_factory=dict)  # store id -> (store, agent) for scenario-bound stores

    def bound(self, scenario: Scenario | None) -> tuple[Store, Any]:
        """The store and agent for a scenario: the run's, unless the scenario names its own store."""
        if scenario is None or not scenario.store or scenario.store == self.store.id:
            return self.store, self.agent
        if scenario.store not in self._extra:
            store = open_store(scenario.store, self.settings)
            self._extra[scenario.store] = (
                store,
                build_agent(
                    build_model(self.model_id, max_retries=0 if self.budget else 2), store, self.sandbox
                ),
            )
        return self._extra[scenario.store]

    @classmethod
    def build(
        cls,
        settings: Settings,
        *,
        dataset: str,
        store_id: str,
        model_id: str | None = None,
        judge: bool = True,
        scenarios: list[Scenario] | None = None,
        data_version: str | None = None,
        budget: RunBudget | None = None,
    ) -> Harness:
        store = open_store(store_id, settings)
        sandbox = PythonSandbox(settings.sandbox)
        model_id = model_id or settings.model
        agent = build_agent(build_model(model_id, max_retries=0 if budget else 2), store, sandbox)
        scenarios = {s.id: s for s in (load_answers(dataset) if scenarios is None else scenarios)}
        metadata = {
            "dataset": dataset,
            "store": store_id,
            "model": model_id,
            "judge_model": settings.judge_model if judge else None,
            "judge_version": judge_version() if judge else None,
            "judge_context_version": context_version() if judge else None,
            "method_version": method_version(),
            "sandbox": sandbox.label,
            "git_sha": git_sha(),
            "source_version": source_version(),
            "reference_version": reference_version(scenarios.values()),
            "working_tree": working_tree(),
            "scorer_version": scorer_version(),
            "data_version": data_version,
            "dependencies": {
                p: importlib.metadata.version(p) for p in ("deepagents", "langsmith", "duckdb", "polars")
            },
            "agent": "deepagents single lead, no subagents",
        }
        return cls(settings, store, sandbox, model_id, agent, scenarios, judge, metadata, budget)

    # ------------------------------------------------------------------ one question
    def answer(self, question: str, scenario: Scenario | None = None) -> dict:
        """Run the analyst once. Returns {"answer": dict|None, "error": str|None, "metrics": {...}}."""
        if self.budget and not self.budget.can_admit():
            return {
                "answer": None,
                "error": "BudgetExceeded: no model-call reservation available; case not attempted",
                "failure_class": "budget",
                "attempted": False,
                "metrics": {**UsageTracker().report(), "latency_s": 0.0, "tool_calls": 0, "tools": {}},
            }
        _, agent = self.bound(scenario)
        started = time.monotonic()
        metrics = {
            "llm_calls": 0,
            "tool_calls": 0,
            "input_tokens": 0,
            "output_tokens": 0,
            "cost_usd": 0.0,
            "unpriced_llm_calls": 0,
            "tools": {},
        }
        answer = error = failure_class = None
        usage = UsageTracker(self.budget, model_id=self.model_id)
        result = {}
        try:
            for state in agent.stream(
                {"messages": [{"role": "user", "content": question}]},
                config={"recursion_limit": RECURSION_LIMIT, "callbacks": [usage]},
                stream_mode="values",
            ):
                result = state
            structured = result.get("structured_response")
            if structured is None:
                error = "the agent finished without a structured answer"
                failure_class = "agent"
            else:
                answer = (
                    structured
                    if isinstance(structured, AnalystAnswer)
                    else AnalystAnswer.model_validate(structured)
                )
        except Exception as exc:  # a crashed run is a scored failure, not a skipped row
            error = f"{type(exc).__name__}: {str(exc)[:500]}"
            failure_class = (
                "budget"
                if isinstance(exc, BudgetExceeded)
                else "infrastructure"
                if isinstance(exc, (TimeoutError, ConnectionError, PlanUsageStopped))
                or type(exc).__module__.startswith(("openai", "anthropic", "httpx", "requests"))
                or _provider_error_envelope(exc)
                else "agent"
            )
            metrics["traceback"] = traceback.format_exc()[-2000:]
        for message in result.get("messages", []):
            if isinstance(message, AIMessage):
                for call in message.tool_calls or []:
                    metrics["tool_calls"] += 1
                    metrics["tools"][call["name"]] = metrics["tools"].get(call["name"], 0) + 1
            elif isinstance(message, ToolMessage) and message.status == "error":
                metrics["tool_errors"] = metrics.get("tool_errors", 0) + 1
        metrics.update(usage.report())
        # Older/custom harnesses may not propagate callbacks. Preserve known partial usage
        # without claiming that a message-history fallback observed every request.
        messages = [m for m in result.get("messages", []) if isinstance(m, AIMessage)]
        if not metrics["llm_calls"] and messages:
            reported = [usage_from_message(message) for message in messages]
            costs = [u["cost_usd"] for u in reported if u["cost_usd"] is not None]
            metrics.update(
                llm_calls=len(messages),
                input_tokens=sum(u["input_tokens"] for u in reported),
                output_tokens=sum(u["output_tokens"] for u in reported),
                cost_usd=sum(costs) if costs else None,
                unpriced_llm_calls=len(messages) - len(costs),
                usage_complete=False,
                cost_complete=False,
                scope="message-history fallback; completeness not established",
            )
        if failure_class == "infrastructure" and not metrics["llm_calls"]:
            metrics.update(usage_complete=False, cost_complete=False, cost_usd=None)
        if isinstance(self.budget, NativeRunBudget) and not metrics["usage_complete"]:
            metrics["estimate_complete"] = False
            self.budget.uncertain = True
        metrics["latency_s"] = round(time.monotonic() - started, 2)
        return {
            "answer": answer.model_dump() if answer else None,
            "error": error,
            "failure_class": failure_class,
            "attempted": True,
            "metrics": metrics,
        }

    # ------------------------------------------------------------------ scoring
    def score(self, scenario: Scenario, outputs: dict) -> dict[str, dict]:
        if outputs.get("failure_class") in {"budget", "infrastructure"}:
            comment = f"invalid evaluation ({outputs['failure_class']}): {outputs.get('error')}"
            keys = [
                "correct",
                "partial_credit",
                "evidence_reproduces",
                "abstention_correct",
                "fully_supported",
            ]
            scores = {key: {"score": None, "comment": comment} for key in keys}
            if self.judge:
                scores["judge_method"] = {
                    "score": None,
                    "comment": comment,
                    "metrics": UsageTracker().report(),
                }
            return scores
        answer = AnalystAnswer.model_validate(outputs["answer"]) if outputs.get("answer") else None
        store, _ = self.bound(scenario)
        correct = score_correct(scenario, answer)
        scores = {
            "correct": {"score": correct["correct"], "comment": correct["comment"]},
            "partial_credit": {"score": correct["partial"], "comment": correct["comment"]},
            "evidence_reproduces": evidence_reproduces(scenario, answer, store, self.sandbox),
            "abstention_correct": abstention_correct(scenario, answer),
        }
        if self.judge:
            judge_usage = UsageTracker(self.budget, model_id=self.settings.judge_model)
            judge_started = time.monotonic()
            try:
                context = build_judge_context(store, scenario.id) if answer else None
                judged = judge_answer(
                    scenario.question,
                    answer,
                    model_id=self.settings.judge_model,
                    callbacks=[judge_usage],
                    max_retries=0 if self.budget else 2,
                    context=context,
                )
                scores["judge_method"] = {
                    "score": judged["score"],
                    "comment": judged["comment"] + " " + json.dumps(judged["criteria"]),
                    "context": context,
                }
            except Exception as exc:
                scores["judge_method"] = {
                    "score": None,
                    "comment": f"judge failed: {type(exc).__name__}: {str(exc)[:200]}",
                    "failure_class": "budget" if isinstance(exc, BudgetExceeded) else "infrastructure",
                }
            scores["judge_method"]["metrics"] = {
                **judge_usage.report(),
                "latency_s": round(time.monotonic() - judge_started, 2),
            }
        supported = (
            scores["correct"]["score"] == 1.0
            and scores["abstention_correct"]["score"] == 1.0
            and scores["evidence_reproduces"]["score"] in (1.0, None)
        )
        scores["fully_supported"] = {
            "score": float(supported),
            "comment": "correct, with reproducible evidence" if supported else "see other scores",
        }
        return scores

    def run_scenario(self, scenario: Scenario) -> dict:
        outputs = self.answer(scenario.question, scenario)
        scores = self.score(scenario, outputs)
        return self.record(scenario, outputs, scores)

    def record(self, scenario: Scenario, outputs: dict, scores: dict) -> dict:
        outputs = {**outputs, "metrics": dict(outputs.get("metrics") or {})}
        judge_usage = scores.get("judge_method", {}).get("metrics")
        if not self.judge:
            judge_usage = UsageTracker(self.budget, model_id=self.model_id).report()
        if judge_usage is not None:
            outputs["metrics"]["judge"] = judge_usage
            analyst = outputs["metrics"]
            known = [c for c in (analyst.get("cost_usd"), judge_usage.get("cost_usd")) if c is not None]
            outputs["metrics"]["total_reported_cost_usd"] = sum(known) if known else None
            outputs["metrics"]["total_cost_complete"] = bool(
                analyst.get("cost_complete") and judge_usage.get("cost_complete")
            )
            if analyst.get("billing_mode") == "native_api_estimate":
                outputs["metrics"]["total_estimated_cost_usd"] = analyst.get(
                    "estimated_cost_usd", 0
                ) + judge_usage.get("estimated_cost_usd", 0)
                outputs["metrics"]["total_estimate_complete"] = bool(
                    analyst.get("estimate_complete")
                    and judge_usage.get("estimate_complete")
                    and analyst.get("accounting_version") == judge_usage.get("accounting_version")
                )
        judge_invalid = self.judge and scores.get("judge_method", {}).get("score") is None
        if judge_invalid:
            outputs["evaluation_error"] = scores.get("judge_method", {}).get(
                "comment", "required judge missing"
            )
        return {
            "scenario_id": scenario.id,
            "level": scenario.level,
            "answer_type": scenario.answer_type,
            "answerable": scenario.answerable,
            "question": scenario.question,
            **self.run_metadata,
            "recorded_at": datetime.now(UTC).isoformat(),
            "evaluation_status": (
                "invalid"
                if judge_invalid or outputs.get("failure_class") in {"budget", "infrastructure"}
                else "valid"
            ),
            "outputs": outputs,
            "judge_context": scores.get("judge_method", {}).get("context"),
            "scores": {k: v["score"] for k, v in scores.items()},
            "comments": {k: v["comment"] for k, v in scores.items()},
        }

    def close(self) -> None:
        self.store.close()
        for store, _ in self._extra.values():
            store.close()


def select(
    scenarios: Iterable[Scenario],
    *,
    levels: set[int] | None,
    ids: set[str] | None,
    limit: int | None,
) -> list[Scenario]:
    chosen = [s for s in scenarios if (levels is None or s.level in levels) and (ids is None or s.id in ids)]
    return chosen[:limit] if limit else chosen


def write_records(path: Path, records: list[dict]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a") as handle:
        for record in records:
            handle.write(json.dumps(record, default=str) + "\n")
    return path


def experiment_name(harness: Harness, levels: set[int] | None) -> str:
    model = harness.model_id.split("/")[-1]
    level_tag = "L" + "".join(str(level) for level in sorted(levels)) if levels else "Lall"
    stamp = datetime.now(UTC).strftime("%Y%m%d-%H%M%S")
    return f"{harness.run_metadata['dataset']}-{harness.store.kind}-{model}-{level_tag}-{stamp}-{uuid4().hex}"


# ---------------------------------------------------------------------- local run
def run_local(
    harness: Harness,
    scenarios: list[Scenario],
    *,
    out_dir: Path = RESULTS_DIR,
    name: str | None = None,
) -> Path:
    name = name or experiment_name(harness, {s.level for s in scenarios})
    path = out_dir / f"{name}.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x"):
        pass  # Reserve this experiment before any model calls; never append another run.
    for index, scenario in enumerate(scenarios, 1):
        record = harness.run_scenario(scenario)
        write_records(path, [record])
        scores = record["scores"]
        print(
            f"[{index}/{len(scenarios)}] {scenario.id} correct={scores['correct']} "
            f"evidence={scores['evidence_reproduces']} "
            f"judge={scores.get('judge_method')} {record['outputs']['metrics']['latency_s']}s "
            f"cost={record['outputs']['metrics']['cost_usd']} {record['comments']['correct'][:90]}",
            flush=True,
        )
    return path


# ---------------------------------------------------------------------- LangSmith
def dataset_name(dataset: str) -> str:
    return f"backintel-v2/{dataset}"


def sync_dataset(dataset: str, *, client=None, scenarios: list[Scenario] | None = None) -> dict:
    """Create or update the LangSmith dataset so that it mirrors benchmarks/answers/<dataset>.json."""
    from langsmith import Client

    client = client or Client()
    scenarios = load_answers(dataset) if scenarios is None else scenarios
    name = dataset_name(dataset)
    if client.has_dataset(dataset_name=name):
        ds = client.read_dataset(dataset_name=name)
    else:
        ds = client.create_dataset(
            dataset_name=name,
            description=f"BackIntel v2 benchmark scenarios for {dataset}; "
            "versioned independent reference calculations.",
        )
    existing = {
        ex.metadata.get("scenario_id"): ex for ex in client.list_examples(dataset_id=ds.id) if ex.metadata
    }
    created = updated = unchanged = 0
    to_create = []
    for scenario in scenarios:
        inputs = {
            "question": scenario.question,
            "scenario_id": scenario.id,
            "dataset": dataset,
            "level": scenario.level,
            "answer_type": scenario.answer_type,
        }
        outputs = {
            "expected": scenario.expected,
            "tolerance": scenario.tolerance.model_dump(exclude_none=True),
            "unit": scenario.unit,
            "answerable": scenario.answerable,
        }
        metadata = {
            "scenario_id": scenario.id,
            "level": scenario.level,
            "answer_type": scenario.answer_type,
            "answerable": scenario.answerable,
            "tags": scenario.tags,
        }
        example = existing.get(scenario.id)
        if example is None:
            to_create.append({"inputs": inputs, "outputs": outputs, "metadata": metadata})
            created += 1
        elif example.inputs != inputs or json.loads(json.dumps(example.outputs, default=str)) != json.loads(
            json.dumps(outputs, default=str)
        ):
            client.update_example(example.id, inputs=inputs, outputs=outputs, metadata=metadata)
            updated += 1
        else:
            unchanged += 1
    if to_create:
        client.create_examples(dataset_id=ds.id, examples=to_create)
    return {
        "dataset": name,
        "id": str(ds.id),
        "created": created,
        "updated": updated,
        "unchanged": unchanged,
    }


def run_langsmith(
    harness: Harness,
    scenarios: list[Scenario],
    *,
    out_dir: Path = RESULTS_DIR,
    max_concurrency: int = 2,
) -> dict:
    from langsmith import Client

    client = Client()
    dataset = harness.run_metadata["dataset"]
    sync_dataset(dataset, client=client, scenarios=list(harness.scenarios.values()))
    wanted = {s.id for s in scenarios}
    examples = [
        ex
        for ex in client.list_examples(dataset_name=dataset_name(dataset))
        if ex.metadata and ex.metadata.get("scenario_id") in wanted
    ]
    name = experiment_name(harness, {s.level for s in scenarios})

    def target(inputs: dict) -> dict:
        return harness.answer(inputs["question"], harness.scenarios[inputs["scenario_id"]])

    evaluation_usage = {}

    def make_evaluator(key: str):
        def evaluator(inputs: dict, outputs: dict, reference_outputs: dict) -> dict:
            scenario = harness.scenarios[inputs["scenario_id"]]
            scored = harness.score(scenario, outputs) if key == "__all__" else None
            evaluation_usage[scenario.id] = scored
            return [
                {
                    "key": k,
                    "score": v["score"],
                    "comment": v["comment"],
                    "evaluator_info": {"usage": v["metrics"]} if "metrics" in v else {},
                }
                for k, v in scored.items()
            ]

        evaluator.__name__ = "backintel_scores"
        return evaluator

    results = client.evaluate(
        target,
        data=examples,
        evaluators=[make_evaluator("__all__")],
        experiment_prefix=name,
        metadata=harness.run_metadata,
        max_concurrency=max_concurrency,
        blocking=False,
        description="BackIntel v2 analyst benchmark: deterministic correctness, evidence re-execution, "
        "abstention, and an LLM method judge.",
    )
    records = []
    path = out_dir / f"{results.experiment_name}.jsonl"
    for row in results:
        example, run = row["example"], row["run"]
        scenario = harness.scenarios[example.inputs["scenario_id"]]
        outputs = run.outputs or {
            "answer": None,
            "error": str(run.error)[:500] if run.error else "no outputs",
            "metrics": {},
        }
        scores = {
            r.key: {"score": r.score, "comment": r.comment} for r in row["evaluation_results"]["results"]
        }
        for key, score in evaluation_usage.get(scenario.id, {}).items():
            if "metrics" in score and key in scores:
                scores[key]["metrics"] = score["metrics"]
        record = harness.record(scenario, outputs, scores)
        record["langsmith_run_id"] = str(run.id)
        records.append(record)
        write_records(path, [record])
        print(
            f"[{len(records)}/{len(scenarios)}] {scenario.id}: "
            f"correct={record['scores'].get('correct')} "
            f"evidence={record['scores'].get('evidence_reproduces')}",
            flush=True,
        )
    project = client.read_project(project_name=results.experiment_name)
    return {
        "experiment": results.experiment_name,
        "records": len(records),
        "path": str(path),
        "project_url": project.url,
    }


def rescore(experiment: str, settings: Settings, *, out_dir: Path = RESULTS_DIR, judge: bool = True) -> Path:
    """Re-score an experiment's stored outputs without re-running the agent (new scorer or judge)."""
    path = out_dir / f"{experiment}.jsonl"
    records = [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
    first = records[0]
    harness = Harness.build(
        settings, dataset=first["dataset"], store_id=first["store"], model_id=first["model"], judge=judge
    )
    try:
        rescored = []
        for record in records:
            scenario = harness.scenarios[record["scenario_id"]]
            scores = harness.score(scenario, record["outputs"])
            updated = {
                **record,
                "scores": {**record["scores"], **{k: v["score"] for k, v in scores.items()}},
                "comments": {**record["comments"], **{k: v["comment"] for k, v in scores.items()}},
                "rescored_at": datetime.now(UTC).isoformat(),
                "scorer_source_version": source_version(),
            }
            if record.get("langsmith_run_id"):
                from langsmith import Client

                client = Client()
                existing = {f.key: f for f in client.list_feedback(run_ids=[record["langsmith_run_id"]])}
                for key, result in scores.items():
                    if key in existing:
                        client.update_feedback(
                            existing[key].id, score=result["score"], comment=result["comment"]
                        )
                    else:
                        client.create_feedback(
                            record["langsmith_run_id"], key, score=result["score"], comment=result["comment"]
                        )
            rescored.append(updated)
    finally:
        harness.close()
    path.write_text("".join(json.dumps(r, default=str) + "\n" for r in rescored))
    return path
