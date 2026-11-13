#!/usr/bin/env python3
"""Prepare isolated baseline/candidate snapshots; execute only with an approved budget.

No model call is made by the default prepare operation. The worker's only input is the
sanitized brief and explicit source text; it never receives a checkout or a filesystem tool.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

RUNTIME_FILES = ("src/backintel/agent.py", "src/backintel/tools.py", "src/backintel/contracts.py")
MODEL_ROUTING = "first_party_only"


def accounting_policy(model: str, judge_model: str) -> dict:
    """Freeze one accounting basis for every model role, before any calls."""
    from backintel.bench.native_costs import NATIVE_POLICY, NATIVE_RATES, native_accounting_version

    if all(m.startswith("openrouter/") for m in (model, judge_model)):
        return {"basis": "provider_reported", "version": None}
    if all(m in NATIVE_RATES for m in (model, judge_model)):
        return {"basis": "native_estimate", "version": native_accounting_version(), "policy": NATIVE_POLICY}
    raise ValueError("Campaign requires qualified native models or OpenRouter models in every role")


def campaign_budget(plan, limit_usd, max_calls, reservation_usd):
    from backintel.bench.usage import NativeRunBudget, RunBudget

    basis = plan.get("accounting", {}).get("basis", "provider_reported")
    if basis not in {"provider_reported", "native_estimate"}:
        raise ValueError("Unknown campaign accounting basis")
    cls = NativeRunBudget if basis == "native_estimate" else RunBudget
    return cls(limit_usd, max_calls, reservation_usd)


def configure_stage_routing(policy: str) -> None:
    """Pin models inside this isolated stage process, leaving application defaults alone."""
    from backintel.bench import improvement, judge, run
    from backintel.models import build_model

    if policy != MODEL_ROUTING:
        raise ValueError("Prepared model routing must be first_party_only")

    def routed_model(model_id: str, **kwargs):
        if model_id.startswith("openrouter/"):
            kwargs["first_party_only"] = True
        return build_model(model_id, **kwargs)

    # Every model role in the stage uses the same routing, including per-store analyst
    # reconstruction. The standalone CLI starts a new process for each stage.
    run.build_model = routed_model
    judge.build_model = routed_model
    improvement.build_model = routed_model


def write_new(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x") as handle:
        handle.write(json.dumps(value, indent=2, default=str) + "\n")


def sha(path: Path) -> str:
    with path.open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


def git(repo: Path, *args: str) -> str:
    return subprocess.run(["git", *args], cwd=repo, check=True, capture_output=True, text=True).stdout


def prepare_snapshots(repo: Path, output: Path, revision: str, *, candidate_source: str = "worker") -> dict:
    """Current evaluator on both sides; candidate is current code or baseline for worker edits."""
    from backintel.bench.run import scorer_version, source_version

    output.mkdir(parents=True, exist_ok=False)
    baseline = output / "baseline"
    baseline.mkdir()
    shutil.copytree(repo / "src", baseline / "src", ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    shutil.copytree(repo / "benchmarks", baseline / "benchmarks")
    for name in ("uv.lock", "pyproject.toml", "Dockerfile.sandbox", "compose.yaml"):
        shutil.copy2(repo / name, baseline / name)
    candidate = output / "candidate"
    if candidate_source == "current":
        shutil.copytree(baseline, candidate)
    resolved = git(repo, "rev-parse", "--verify", f"{revision}^{{commit}}").strip()
    old_skills = git(repo, "ls-tree", "-r", "--name-only", resolved, "src/backintel/agent_files").splitlines()
    shutil.rmtree(baseline / "src/backintel/agent_files")
    overlaid = {}
    for name in [*RUNTIME_FILES, *old_skills]:
        content = git(repo, "show", f"{resolved}:{name}")
        path = baseline / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)
        overlaid[name] = {
            "baseline": sha(path),
            "current": sha(repo / name) if (repo / name).exists() else None,
        }
    # Contracts also participate in scoring. A changed contract needs an explicit evaluator
    # adaptation, not a silent apples-to-oranges comparison.
    if scorer_version(baseline) != scorer_version(repo):
        raise ValueError("Baseline runtime contract differs from current frozen evaluator; adapt explicitly")
    if candidate_source == "worker":
        shutil.copytree(baseline, candidate)
    return {
        "baseline_revision": resolved,
        "baseline": str(baseline),
        "candidate": str(candidate),
        "baseline_source_version": source_version(baseline),
        "candidate_source_version": source_version(candidate),
        "current_source_version": source_version(repo),
        "scorer_version": scorer_version(baseline),
        "runtime_overlay": overlaid,
    }


def load_scenario_manifest(path: Path, settings) -> tuple[dict, list]:
    """Validate frozen explicit scenarios and their exact local SQLite store bytes."""
    from backintel.bench.improvement import fingerprint
    from backintel.bench.run import reference_version
    from backintel.contracts import Scenario

    document = json.loads(path.read_text())
    scenarios = [Scenario.model_validate(value) for value in document["scenarios"]]
    if (
        document.get("schema") != 1
        or not document.get("dataset")
        or document.get("split") not in {"development", "acceptance"}
        or not scenarios
        or len({s.id for s in scenarios}) != len(scenarios)
    ):
        raise ValueError("Scenario manifest needs a dataset, split and unique nonempty scenarios")
    if {s.store for s in scenarios} != set(document["stores"]):
        raise ValueError("Every scenario must bind exactly one fingerprinted store")
    for store_id, expected in document["stores"].items():
        kind, _, name = store_id.partition(":")
        if kind != "sqlite" or not name or Path(name).name != name or "\\" in name:
            raise ValueError("Explicit comparison manifests support local SQLite stores only")
        relative = Path("stores") / "sqlite" / f"{name}.sqlite"
        if expected["path"] != relative.as_posix():
            raise ValueError(f"Fingerprint path does not match bound store {store_id}")
        physical = settings.data_dir / relative
        if physical.stat().st_size != expected["size_bytes"] or sha(physical) != expected["sha256"]:
            raise ValueError(f"Frozen store bytes changed: {store_id}")
    if document["reference_hash"] != reference_version(scenarios):
        raise ValueError("Scenario references differ from their manifest hash")
    if document["data_hash"] != fingerprint(document["stores"]):
        raise ValueError("Store fingerprints differ from their manifest hash")
    return document, scenarios


def prepare(args) -> None:
    from backintel.bench.acceptance import build_acceptance, verify_acceptance_data
    from backintel.bench.improvement import ComparisonPolicy, fingerprint, validate_runtime_paths
    from backintel.bench.judge import judge_version
    from backintel.bench.run import reference_version
    from backintel.settings import Settings, repo_root

    candidate_source = getattr(args, "candidate_source", "worker")
    require_improvement = getattr(args, "require_improvement", True)
    if candidate_source == "worker":
        if not require_improvement:
            raise ValueError("Worker cycles require a demonstrated improvement")
        validate_runtime_paths(args.files)
        if args.split != "development":
            raise ValueError(
                "Improvement cycles use development cases; reserved acceptance follows candidate freeze"
            )
        if any(not p.startswith("src/backintel/agent_files/") or not p.endswith(".md") for p in args.files):
            raise ValueError(
                "Automatic cycles edit prompt/skill Markdown only; Python proposals require semantic review"
            )
        if not args.brief:
            raise ValueError("Preparation requires an operator-written --brief with no reserved answers")
        if getattr(args, "scenario_manifest", None):
            raise ValueError("Explicit scenario manifests are for frozen current-runtime comparisons")
    settings = Settings.from_env()
    accounting = accounting_policy(settings.model, settings.judge_model)
    scenario_manifest = getattr(args, "scenario_manifest", None)
    if scenario_manifest:
        document, scenarios = load_scenario_manifest(scenario_manifest, settings)
        if document["split"] != args.split:
            raise ValueError("Scenario manifest and requested split differ")
        dataset, data_hash = document["dataset"], document["data_hash"]
    else:
        suite = build_acceptance(settings, split=args.split)
        if not verify_acceptance_data(suite, settings):
            raise ValueError("Acceptance data differs from its manifest")
        dataset, data_hash, scenarios = suite.dataset, suite.data_hash, suite.scenarios
    wanted = set(args.ids.split(",")) if args.ids else {s.id for s in scenarios}
    if not wanted or not wanted <= {s.id for s in scenarios} or args.trials < 1:
        raise ValueError("Select existing cases and a positive trial count")
    paths = prepare_snapshots(
        repo_root(), args.output.resolve(), args.base_ref, candidate_source=candidate_source
    )
    worker_files, brief_hash = [], None
    if candidate_source == "worker":
        worker_files = args.files
        for name in worker_files:
            if not (Path(paths["candidate"]) / name).is_file():
                raise ValueError(f"Allowed worker file does not exist: {name}")
        brief = args.brief.read_text()
        (args.output / "failure-brief.txt").write_text(brief)
        brief_hash = hashlib.sha256(brief.encode()).hexdigest()
    if scenario_manifest:
        shutil.copy2(scenario_manifest, args.output / "scenarios.json")
    identity = dict(
        dataset=dataset,
        data_version=data_hash,
        reference_version=reference_version(scenarios),
        scorer_version=paths["scorer_version"],
        judge_model=settings.judge_model,
        judge_version=judge_version(),
    )
    policy = ComparisonPolicy(
        identity,
        tuple(sorted(wanted)),
        tuple(sorted(wanted)),
        trials=args.trials,
        require_improvement=require_improvement,
        cost_basis=accounting["basis"],
        accounting_version=accounting["version"],
    )
    write_new(args.output / "policy.json", policy.document())
    manifest = {
        "schema": 2,
        **paths,
        "candidate_source": candidate_source,
        "identity": identity,
        "split": args.split,
        "case_ids": sorted(wanted),
        "trials": args.trials,
        "model": settings.model,
        "judge_model": settings.judge_model,
        "model_routing": MODEL_ROUTING,
        "accounting": accounting,
        "data_dir": str(settings.data_dir),
        "worker_files": worker_files,
        "brief_hash": brief_hash,
        "scenario_manifest_hash": sha(args.output / "scenarios.json") if scenario_manifest else None,
        "policy_hash": policy.document()["policy_hash"],
        "runner_hash": sha(Path(__file__)),
        "gate_hash": sha(repo_root() / "src/backintel/bench/improvement.py"),
        "scope": (
            "fresh baseline -> frozen current runtime -> fixed comparison"
            if candidate_source == "current"
            else "fresh baseline -> coding-model proposal -> fresh candidate -> fixed comparison"
        ),
    }
    write_new(args.output / "manifest.json", {"manifest": manifest, "manifest_hash": fingerprint(manifest)})
    print(json.dumps({"prepared": str(args.output), "case_count": len(wanted), "model_calls": 0}, indent=2))


def load_plan(output: Path) -> dict:
    from backintel.bench import improvement
    from backintel.bench.improvement import ComparisonPolicy, fingerprint

    document = json.loads((output / "manifest.json").read_text())
    plan = document["manifest"]
    if fingerprint(plan) != document["manifest_hash"] or sha(Path(__file__)) != plan["runner_hash"]:
        raise ValueError("Prepared manifest or runner changed")
    if sha(Path(improvement.__file__)) != plan["gate_hash"]:
        raise ValueError("Frozen comparison implementation changed")
    if plan.get("accounting") != accounting_policy(plan["model"], plan["judge_model"]):
        raise ValueError("Frozen accounting policy changed")
    candidate_source = plan.get("candidate_source", "worker")
    if candidate_source not in {"worker", "current"}:
        raise ValueError("Unknown candidate source")
    if candidate_source == "worker" and (
        plan["split"] != "development"
        or plan.get("scenario_manifest_hash")
        or any(
            not p.startswith("src/backintel/agent_files/") or not p.endswith(".md")
            for p in plan["worker_files"]
        )
    ):
        raise ValueError("Automatic worker scope must be development cases and Markdown prompts/skills")
    policy_doc = json.loads((output / "policy.json").read_text())
    ComparisonPolicy.from_document(policy_doc)
    if policy_doc["policy_hash"] != plan["policy_hash"]:
        raise ValueError("Prepared comparison policy changed")
    if candidate_source == "worker" and sha(output / "failure-brief.txt") != plan["brief_hash"]:
        raise ValueError("Prepared worker brief changed")
    if (
        plan.get("scenario_manifest_hash")
        and sha(output / "scenarios.json") != plan["scenario_manifest_hash"]
    ):
        raise ValueError("Prepared scenario manifest changed")
    return plan


def stage(args) -> None:
    """Child process imports the selected snapshot through PYTHONPATH; no install is run."""
    from backintel.bench.acceptance import build_acceptance, verify_acceptance_data
    from backintel.bench.improvement import apply_candidate, propose_candidate, read_records
    from backintel.bench.run import Harness, reference_version, run_langsmith, scorer_version, source_version
    from backintel.settings import Settings, repo_root

    plan = load_plan(args.output)
    configure_stage_routing(plan.get("model_routing"))
    candidate_source = plan.get("candidate_source", "worker")
    if args.stage == "worker" and candidate_source != "worker":
        raise ValueError("Frozen current-runtime comparisons have no tuning worker")
    settings = Settings.from_env()
    if settings.model != plan["model"] or settings.judge_model != plan["judge_model"]:
        raise ValueError("Approved model selection differs from prepared plan")
    if scorer_version() != plan["identity"]["scorer_version"]:
        raise ValueError("Frozen evaluator changed")
    expected_root = Path(plan["baseline" if args.stage == "baseline" else "candidate"])
    if repo_root().resolve() != expected_root.resolve():
        raise ValueError("Stage did not import its isolated snapshot")
    if args.stage in {"baseline", "worker"} and source_version() != plan["baseline_source_version"]:
        raise ValueError("Runtime changed before its prepared stage")
    if args.stage == "candidate":
        if candidate_source == "current":
            if source_version() != plan["candidate_source_version"]:
                raise ValueError("Candidate differs from the frozen current runtime")
        else:
            worker = json.loads((args.output / "worker-result.json").read_text())
            if worker["status"] != "proposed" or source_version() != worker["source_version"]:
                raise ValueError("Candidate differs from the actual worker proposal")
    budget = campaign_budget(plan, args.max_cost_usd, args.max_calls, args.reservation_usd)
    stage_dir = args.output / args.stage / "cycle-results"
    stage_dir.mkdir(parents=True, exist_ok=False)
    if args.stage == "worker":
        files = {name: (repo_root() / name).read_text() for name in plan["worker_files"]}
        result = propose_candidate(
            files, (args.output / "failure-brief.txt").read_text(), model_id=settings.model, budget=budget
        )
        write_new(stage_dir / "proposal.json", result)
        if result["status"] == "proposed":
            apply_candidate(result, repo_root())
        report = {
            "stage": args.stage,
            "status": result["status"],
            "budget": budget.report(),
            "source_version": source_version(),
            "proposal": str(stage_dir / "proposal.json"),
        }
    else:
        explicit = plan.get("scenario_manifest_hash")
        if explicit:
            document, all_scenarios = load_scenario_manifest(args.output / "scenarios.json", settings)
            dataset, data_hash = document["dataset"], document["data_hash"]
        else:
            suite = build_acceptance(settings, split=plan["split"])
            dataset, data_hash, all_scenarios = suite.dataset, suite.data_hash, suite.scenarios
        if (
            data_hash != plan["identity"]["data_version"]
            or reference_version(all_scenarios) != plan["identity"]["reference_version"]
            or dataset != plan["identity"]["dataset"]
        ):
            raise ValueError("Prepared cases/data changed")
        scenarios = [s for s in all_scenarios if s.id in plan["case_ids"]]

        def verify_data():
            if explicit:
                load_scenario_manifest(args.output / "scenarios.json", settings)
            elif not verify_acceptance_data(suite, settings):
                raise ValueError("Evaluation data changed")

        harness = Harness.build(
            settings,
            dataset=dataset,
            store_id=scenarios[0].store,
            scenarios=all_scenarios,
            data_version=data_hash,
            budget=budget,
        )
        reports, records = [], []
        try:
            for trial in range(plan["trials"]):
                verify_data()
                harness.run_metadata.update(
                    trial=trial,
                    cycle_stage=args.stage,
                    working_tree="isolated snapshot; source_version identifies effective code",
                    git_sha=plan["baseline_revision"],
                    baseline_runtime_revision=plan["baseline_revision"],
                    candidate_source=candidate_source,
                    model_routing=plan["model_routing"],
                    cost_basis=plan["accounting"]["basis"],
                    accounting_version=plan["accounting"]["version"],
                )
                report = run_langsmith(harness, scenarios, out_dir=stage_dir, max_concurrency=1)
                reports.append(report)
                records += read_records(Path(report["path"]))
                verify_data()
                if (
                    candidate_source == "current"
                    and args.stage == "candidate"
                    and source_version() != plan["candidate_source_version"]
                ):
                    raise ValueError("Frozen current runtime changed during evaluation")
                if not budget.can_admit():
                    break
        finally:
            harness.close()
        with (stage_dir / "records.jsonl").open("x") as handle:
            for record in records:
                handle.write(json.dumps(record, default=str) + "\n")
        complete_field = (
            "total_estimate_complete"
            if plan["accounting"]["basis"] == "native_estimate"
            else "total_cost_complete"
        )
        valid = len(records) == len(scenarios) * plan["trials"] and all(
            r.get("evaluation_status") == "valid" and r["outputs"]["metrics"].get(complete_field)
            for r in records
        )
        report = {
            "stage": args.stage,
            "status": "completed" if valid else "invalid",
            "experiments": reports,
            "records": str(stage_dir / "records.jsonl"),
            "budget": budget.report(),
        }
    write_new(args.output / f"{args.stage}-result.json", report)
    print(json.dumps(report, indent=2))


def execute(args) -> None:
    from backintel.bench.improvement import ComparisonPolicy, compare_records, read_records

    if args.max_cost_usd is None:
        raise ValueError("--execute requires an explicitly approved --max-cost-usd")
    plan = load_plan(args.output)
    campaign_budget(plan, args.max_cost_usd, args.max_calls, args.reservation_usd)
    native = plan.get("accounting", {}).get("basis") == "native_estimate"
    write_new(
        args.output / "execution-start.json",
        {
            "limit_usd": args.max_cost_usd,
            "max_calls": args.max_calls,
            "reservation_usd": args.reservation_usd,
            "accounting": plan.get("accounting", {"basis": "provider_reported"}),
            "note": "operator-invoked paid run; reserved/unknown charges halt continuation",
        },
    )
    spent, calls = 0.0, 0
    stages = (
        ("baseline", "candidate")
        if plan.get("candidate_source") == "current"
        else ("baseline", "worker", "candidate")
    )
    for name in stages:
        remaining = args.max_cost_usd - spent
        if remaining < args.reservation_usd or calls >= args.max_calls:
            raise RuntimeError("Overall approved allowance cannot admit the next stage")
        snapshot = Path(plan["baseline" if name == "baseline" else "candidate"])
        env = dict(os.environ)
        env["PYTHONPATH"] = str(snapshot / "src")
        env["BACKINTEL_DATA_DIR"] = plan["data_dir"]
        command = [
            sys.executable,
            str(Path(__file__).resolve()),
            "--output",
            str(args.output),
            "--stage",
            name,
            "--max-cost-usd",
            str(remaining),
            "--max-calls",
            str(args.max_calls - calls),
            "--reservation-usd",
            str(args.reservation_usd),
        ]
        with (args.output / f"{name}.log").open("x") as log:
            completed = subprocess.run(command, cwd=snapshot, env=env, stdout=log, stderr=subprocess.STDOUT)
        if completed.returncode:
            raise RuntimeError(f"{name} stage failed; inspect its retained log before further spending")
        report = json.loads((args.output / f"{name}-result.json").read_text())
        budget = report["budget"]
        spent += budget["estimated_spent_usd" if native else "reported_spent_usd"]
        calls += budget["calls"]
        write_new(
            args.output / f"allowance-after-{name}.json",
            {
                "reported_spent_usd": None if native else spent,
                "estimated_spent_usd": spent if native else None,
                "calls": calls,
                "remaining_usd": args.max_cost_usd - spent,
                "stage_budget": budget,
            },
        )
        if (
            report["status"] not in {"completed", "proposed"}
            or budget["accounting_uncertain" if native else "unknown_charge"]
            or budget["reservation_breached"]
        ):
            raise RuntimeError(f"{name} is incomplete or accounting uncertain; no subsequent stage will run")
    result = compare_records(
        read_records(Path(json.loads((args.output / "baseline-result.json").read_text())["records"])),
        read_records(Path(json.loads((args.output / "candidate-result.json").read_text())["records"])),
        ComparisonPolicy.from_document(json.loads((args.output / "policy.json").read_text())),
    )
    result["cycle_reported_cost_usd"] = None if native else spent
    result["cycle_estimated_cost_usd"] = spent if native else None
    result["cycle_model_calls"] = calls
    write_new(args.output / "comparison.json", result)
    print(json.dumps(result, indent=2))
    if result["verdict"] != "accept_for_review":
        raise SystemExit(1)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--prepare-only", action="store_true", help="default: local preparation only")
    parser.add_argument(
        "--execute", action="store_true", help="run an already prepared plan; paid model calls"
    )
    parser.add_argument("--base-ref", default="cb963fd")
    parser.add_argument("--candidate-source", choices=("worker", "current"), default="worker")
    parser.add_argument("--split", choices=("development", "acceptance"), default="development")
    parser.add_argument("--scenario-manifest", type=Path, help="frozen explicit cases; current runtime only")
    parser.add_argument("--ids")
    parser.add_argument("--trials", type=int, default=1)
    parser.add_argument("--require-improvement", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--brief", type=Path)
    parser.add_argument("--files", nargs="+", default=["src/backintel/agent_files/lead.md"])
    parser.add_argument("--max-cost-usd", type=float)
    parser.add_argument("--max-calls", type=int, default=500)
    parser.add_argument("--reservation-usd", type=float, default=0.05)
    parser.add_argument("--stage", choices=("baseline", "worker", "candidate"), help=argparse.SUPPRESS)
    args = parser.parse_args()
    args.output = args.output.resolve()
    if args.prepare_only and (args.execute or args.stage):
        parser.error("--prepare-only cannot execute a stage")
    if args.stage:
        if args.max_cost_usd is None:
            parser.error("A stage requires an explicit budget")
        stage(args)
    elif args.execute:
        execute(args)
    else:
        prepare(args)


if __name__ == "__main__":
    main()
