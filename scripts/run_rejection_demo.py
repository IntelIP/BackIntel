#!/usr/bin/env python3
"""Validate a controlled rejection demo; --execute enables one paid judge call and LangSmith.

The wrong-zero candidate is deterministic, not a model regression. A compatible measured
baseline row is reused unchanged, with its original cost reported separately from new spend.
"""

from __future__ import annotations

import argparse
import importlib.metadata
import json
from pathlib import Path

from run_improvement_cycle import load_scenario_manifest, sha, write_new

from backintel.bench import improvement
from backintel.bench.improvement import ComparisonPolicy, compare_records, fingerprint, read_records
from backintel.bench.judge import judge_version
from backintel.bench.run import Harness, git_sha, reference_version, run_langsmith, scorer_version
from backintel.bench.scoring import score_correct
from backintel.bench.usage import RunBudget
from backintel.contracts import AnalystAnswer, Evidence
from backintel.sandbox import PythonSandbox
from backintel.settings import Settings, repo_root
from backintel.stores import open_store

CASE_ID = "olist-l1-01"
CONTROL_MODEL = "controlled-fixture/wrong-zero-no-analyst-model"
CONTROL_ANSWER = AnalystAnswer(
    status="answered",
    answer_type="number",
    value=0,
    unit="orders",
    method="CONTROLLED NEGATIVE FIXTURE: deliberately return zero without counting the source data.",
    evidence=[Evidence(kind="sql", code="SELECT 0 AS deliberately_wrong_count")],
    caveats=["This deterministic negative control tests rejection; it is not an analyst-model response."],
)


class WrongZeroAgent:
    def stream(self, _inputs, **_kwargs):
        yield {"messages": [], "structured_response": CONTROL_ANSWER}


def run(args) -> int:
    # A single reservation covers the only possible model operation: the real method judge.
    budget = RunBudget(args.max_cost_usd, max_calls=1, reservation_usd=args.max_cost_usd)
    settings = Settings.from_env()
    sandbox = PythonSandbox(settings.sandbox)
    document, scenarios = load_scenario_manifest(args.scenario_manifest, settings)
    selected = [scenario for scenario in scenarios if scenario.id == CASE_ID]
    if len(selected) != 1 or selected[0].answer_type != "number" or not selected[0].answerable:
        raise ValueError("Manifest must contain the answerable numeric count control")
    scenario = selected[0]
    if score_correct(scenario, CONTROL_ANSWER)["correct"] != 0:
        raise ValueError("Wrong-zero control must be incorrect for the frozen case")
    matches = [
        row
        for row in read_records(args.baseline)
        if row.get("scenario_id") == CASE_ID and row.get("trial", 0) == 0
    ]
    if len(matches) != 1:
        raise ValueError("Provide exactly one completed baseline trial-0 count row")
    baseline = matches[0]
    identity = {
        "dataset": document["dataset"],
        "data_version": document["data_hash"],
        "reference_version": reference_version(scenarios),
        "scorer_version": scorer_version(),
        "judge_model": settings.judge_model,
        "judge_version": judge_version(),
    }
    policy = ComparisonPolicy(
        identity,
        (CASE_ID,),
        (CASE_ID,),
        require_improvement=False,
    )
    compatible = compare_records([baseline], [baseline], policy)
    if compatible["verdict"] != "accept_for_review":
        raise ValueError("Baseline is not compatible and fully passing: " + json.dumps(compatible))
    dependencies = {
        package: importlib.metadata.version(package)
        for package in ("deepagents", "langsmith", "duckdb", "polars")
    }
    if (
        baseline.get("evaluation_status") != "valid"
        or baseline.get("model") != settings.model
        # Harness metadata records its initial store, while bound() applies each explicit
        # Scenario.store. The frozen manifest/reference/scorer pins that per-case binding.
        or baseline.get("store") not in document["stores"]
        or baseline.get("question") != scenario.question
        or baseline.get("sandbox") != sandbox.label
        or baseline.get("dependencies") != dependencies
        or not baseline.get("langsmith_run_id")
        or any(baseline["scores"].get(key) != 1 for key in improvement.DETERMINISTIC)
    ):
        raise ValueError("Baseline must be a completed compatible measured model response for this case")
    if args.output.exists():
        raise ValueError("Use a fresh output directory; previous demonstrations are never overwritten")
    source_hash = sha(Path(__file__))
    pins = {
        "baseline_jsonl_sha256": sha(args.baseline),
        "baseline_record_hash": fingerprint(baseline),
        "scenario_manifest_sha256": sha(args.scenario_manifest),
        "control_source_sha256": source_hash,
        "comparison_source_sha256": sha(Path(improvement.__file__)),
    }
    manifest = {
        "source_kind": "controlled-negative-fixture",
        "scope": "Measured compatible baseline reused; deterministic wrong-zero candidate, real judge",
        "baseline_reused": True,
        "baseline_jsonl": str(args.baseline.resolve()),
        "baseline_trial": 0,
        "baseline_run_id": baseline["langsmith_run_id"],
        "baseline_harness_store": baseline["store"],
        "baseline_case_store": scenario.store,
        "baseline_original_reported_cost_usd": baseline["outputs"]["metrics"]["total_reported_cost_usd"],
        "baseline_new_cost_usd": 0,
        "identity": identity,
        "policy_hash": policy.document()["policy_hash"],
        "control_model": CONTROL_MODEL,
        "control_answer": CONTROL_ANSWER.model_dump(),
        "budget": budget.report(),
        **pins,
    }
    if not args.execute:
        print(json.dumps({"validated": manifest, "model_calls": 0, "executed": False}, indent=2))
        return 0

    args.output.mkdir(parents=True, exist_ok=False)
    write_new(args.output / "policy.json", policy.document())
    write_new(args.output / "manifest.json", manifest)
    (args.output / "control-source.py").write_bytes(Path(__file__).read_bytes())
    with (args.output / "baseline-reused.jsonl").open("x") as handle:
        handle.write(json.dumps(baseline) + "\n")

    def verify_frozen():
        current, _ = load_scenario_manifest(args.scenario_manifest, settings)
        if (
            current != document
            or sha(args.baseline) != pins["baseline_jsonl_sha256"]
            or sha(args.scenario_manifest) != pins["scenario_manifest_sha256"]
            or sha(Path(__file__)) != source_hash
            or sha(args.output / "control-source.py") != source_hash
            or sha(Path(improvement.__file__)) != pins["comparison_source_sha256"]
            or scorer_version() != identity["scorer_version"]
            or judge_version() != identity["judge_version"]
            or ComparisonPolicy.from_document(json.loads((args.output / "policy.json").read_text())) != policy
        ):
            raise ValueError("Frozen rejection-demo inputs changed")

    verify_frozen()  # All compatibility checks precede LangSmith writes and the paid judge.
    metadata = {
        **identity,
        "store": scenario.store,
        "model": CONTROL_MODEL,
        "agent": "controlled deterministic negative fixture; no analyst model",
        "source_kind": "controlled-negative-fixture",
        "candidate_source": "controlled-negative-fixture",
        "cycle_stage": "controlled-rejection",
        "source_version": f"controlled-fixture:{source_hash}",
        "method_version": f"controlled-fixture:{source_hash[:12]}",
        "control_source_sha256": source_hash,
        "git_sha": git_sha(),
        "working_tree": "control-source.py identifies candidate; scorer_version identifies evaluator",
        "sandbox": sandbox.label,
        "dependencies": dependencies,
        "trial": 0,
        "baseline_reused": True,
        "baseline_record_hash": pins["baseline_record_hash"],
        "baseline_run_id": baseline["langsmith_run_id"],
        "baseline_harness_store": baseline["store"],
        "baseline_case_store": scenario.store,
    }
    harness = Harness(
        settings,
        open_store(scenario.store, settings),
        sandbox,
        CONTROL_MODEL,
        WrongZeroAgent(),
        {case.id: case for case in scenarios},
        True,
        metadata,
        budget,
    )
    report = {"status": "failed", "source_kind": "controlled-negative-fixture"}
    try:
        experiment = run_langsmith(harness, [scenario], out_dir=args.output, max_concurrency=1)
        candidate = read_records(Path(experiment["path"]))
        verify_frozen()
        comparison = compare_records([baseline], candidate, policy)
        write_new(args.output / "comparison.json", comparison)
        rejected = (
            comparison["verdict"] == "reject"
            and any(row["metric"] == "correct" for row in comparison["regressions"])
            and any(row.get("reason") == "mandatory case failed" for row in comparison["acceptance_failures"])
            and len(candidate) == 1
            and candidate[0]["outputs"]["metrics"]["llm_calls"] == 0
            and candidate[0]["outputs"]["metrics"]["judge"]["llm_calls"] == 1
            and not budget.uncertain
            and not budget.breached
        )
        report.update(
            status="demonstrated" if rejected else "not_demonstrated",
            experiment=experiment,
            verdict=comparison["verdict"],
            baseline_reused=True,
            interpretation="Controlled rejection-path check; not evidence that an LLM regressed",
        )
        return 0 if rejected else 1
    finally:
        harness.close()
        report["new_usage"] = budget.report()
        write_new(args.output / "execution-result.json", report)
        print(json.dumps(report, indent=2))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline", type=Path, required=True, help="completed compatible pilot JSONL")
    parser.add_argument("--output", type=Path, required=True, help="fresh result directory")
    parser.add_argument("--max-cost-usd", type=float, required=True, help="explicitly approved new allowance")
    parser.add_argument(
        "--scenario-manifest",
        type=Path,
        default=repo_root() / "benchmarks/improvement/original-regression.json",
    )
    parser.add_argument("--execute", action="store_true", help="publish control to LangSmith; one paid judge")
    raise SystemExit(run(parser.parse_args()))


if __name__ == "__main__":
    main()
