"""Offline checks for the isolated, explicitly budgeted cycle runner."""

import importlib.util
import json
import sqlite3
import subprocess
from pathlib import Path
from types import SimpleNamespace

import pytest

from backintel.bench.improvement import ComparisonPolicy, fingerprint
from backintel.bench.native_costs import native_accounting_version
from backintel.bench.run import reference_version, scorer_version, source_version
from backintel.contracts import Scenario


def runner():
    path = Path(__file__).parents[1] / "scripts/run_improvement_cycle.py"
    spec = importlib.util.spec_from_file_location("improvement_cycle", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize("candidate_source", ["worker", "current"])
def test_snapshot_uses_old_runtime_and_current_grader_without_host_files(
    tmp_path, monkeypatch, candidate_source
):
    cycle = runner()
    repo = tmp_path / "repo"
    files = {
        "src/backintel/agent.py": "current runtime",
        "src/backintel/tools.py": "current tools",
        "src/backintel/contracts.py": "same contract",
        "src/backintel/agent_files/lead.md": "current prompt",
        "src/backintel/bench/scoring.py": "current scorer",
        "src/backintel/bench/judge.py": "current judge",
        "src/backintel/bench/judge_context.py": "current source context",
        "src/backintel/bench/run.py": "current runner",
        "src/backintel/bench/usage.py": "current usage",
        "benchmarks/answers/facts.json": "reserved data never passed to worker",
        "uv.lock": "locked dependencies",
        "pyproject.toml": "project dependencies",
        "Dockerfile.sandbox": "sandbox",
        "compose.yaml": "services",
        ".env": "host secrets",
        ".git/config": "host git configuration",
        "data/private.csv": "host data",
    }
    for name, content in files.items():
        path = repo / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)
    old = {
        "src/backintel/agent.py": "old runtime",
        "src/backintel/tools.py": "old tools",
        "src/backintel/contracts.py": "same contract",
        "src/backintel/agent_files/lead.md": "old prompt",
    }

    def fake_git(root, *args):
        assert root == repo
        if args[0] == "rev-parse":
            return "old-revision\n"
        if args[0] == "ls-tree":
            return "src/backintel/agent_files/lead.md\n"
        assert args[0] == "show"
        return old[args[1].split(":", 1)[1]]

    monkeypatch.setattr(cycle, "git", fake_git)
    output = tmp_path / "prepared"
    plan = cycle.prepare_snapshots(repo, output, "old-revision", candidate_source=candidate_source)
    baseline, candidate = Path(plan["baseline"]), Path(plan["candidate"])
    assert (baseline / "src/backintel/agent.py").read_text() == "old runtime"
    assert (baseline / "src/backintel/bench/scoring.py").read_text() == "current scorer"
    assert (candidate / "uv.lock").read_text() == "locked dependencies"
    assert scorer_version(baseline) == scorer_version(candidate) == scorer_version(repo)
    assert plan["candidate_source_version"] == source_version(candidate)
    if candidate_source == "worker":
        assert source_version(baseline) == source_version(candidate) != source_version(repo)
    else:
        assert source_version(baseline) != source_version(candidate) == source_version(repo)
        assert (candidate / "src/backintel/agent.py").read_text() == "current runtime"
    assert not any((baseline / name).exists() for name in (".git", ".env", "data"))
    (candidate / "src/backintel/agent_files/lead.md").write_text("worker proposal")
    assert (baseline / "src/backintel/agent_files/lead.md").read_text() == "old prompt"
    assert source_version(baseline) != source_version(candidate)
    with pytest.raises(FileExistsError):
        cycle.prepare_snapshots(repo, output, "old-revision")


def test_automatic_cycle_refuses_reserved_cases_and_executable_worker_edits():
    cycle = runner()
    with pytest.raises(ValueError, match="development cases"):
        cycle.prepare(SimpleNamespace(files=["src/backintel/agent_files/lead.md"], split="acceptance"))
    with pytest.raises(ValueError, match="Python proposals require semantic review"):
        cycle.prepare(SimpleNamespace(files=["src/backintel/agent.py"], split="development"))
    with pytest.raises(ValueError, match="require a demonstrated improvement"):
        cycle.prepare(SimpleNamespace(candidate_source="worker", require_improvement=False))


def test_manifest_binds_scenarios_to_exact_store_bytes_and_reference_hash(tmp_path):
    cycle = runner()
    database = tmp_path / "stores/sqlite/original.sqlite"
    database.parent.mkdir(parents=True)
    with sqlite3.connect(database) as connection:
        connection.execute("CREATE TABLE original (value INTEGER)")
        connection.execute("INSERT INTO original VALUES (7)")
    scenario = Scenario(
        id="original-01",
        dataset="original",
        question="Count the records",
        level=1,
        answer_type="number",
        expected=1,
        store="sqlite:original",
    )
    stores = {
        "sqlite:original": {
            "path": "stores/sqlite/original.sqlite",
            "sha256": cycle.sha(database),
            "size_bytes": database.stat().st_size,
        }
    }
    document = {
        "schema": 1,
        "dataset": "frozen-originals",
        "split": "development",
        "scenarios": [scenario.model_dump()],
        "stores": stores,
        "reference_hash": reference_version([scenario]),
        "data_hash": fingerprint(stores),
    }
    manifest = tmp_path / "originals.json"
    manifest.write_text(json.dumps(document))
    settings = SimpleNamespace(data_dir=tmp_path)
    loaded, cases = cycle.load_scenario_manifest(manifest, settings)
    assert cases == [scenario] and loaded["data_hash"] == document["data_hash"]
    document["scenarios"][0]["expected"] = 2
    manifest.write_text(json.dumps(document))
    with pytest.raises(ValueError, match="references differ"):
        cycle.load_scenario_manifest(manifest, settings)
    document["scenarios"][0]["expected"] = 1
    manifest.write_text(json.dumps(document))
    with sqlite3.connect(database) as connection:
        connection.execute("UPDATE original SET value = 8")
    with pytest.raises(ValueError, match="store bytes changed"):
        cycle.load_scenario_manifest(manifest, settings)


@pytest.mark.parametrize("native", [False, True])
def test_current_mode_invokes_only_fresh_baseline_candidate_and_shares_allowance(
    tmp_path, monkeypatch, native
):
    cycle = runner()
    plan = {
        "candidate_source": "current",
        "baseline": str(tmp_path / "baseline"),
        "candidate": str(tmp_path / "candidate"),
        "data_dir": str(tmp_path / "data"),
        "accounting": {"basis": "native_estimate" if native else "provider_reported"},
    }
    identity = dict(
        dataset="frozen",
        data_version="data1",
        reference_version="ref1",
        scorer_version="scorer1",
        judge_model="judge",
        judge_version="rubric1",
    )
    cycle.write_new(
        tmp_path / "policy.json",
        ComparisonPolicy(
            identity,
            ("case",),
            ("case",),
            cost_basis=plan["accounting"]["basis"],
            accounting_version=native_accounting_version() if native else None,
        ).document(),
    )
    monkeypatch.setattr(cycle, "load_plan", lambda output: plan)
    invoked = []

    def subprocess_run(command, **kwargs):
        stage = command[command.index("--stage") + 1]
        invoked.append((stage, float(command[command.index("--max-cost-usd") + 1])))
        assert kwargs["env"]["PYTHONPATH"] == str(tmp_path / stage / "src")
        records = tmp_path / f"{stage}.jsonl"
        supported = int(stage == "candidate")
        record = {
            **identity,
            "scenario_id": "case",
            "answerable": True,
            "evaluation_status": "valid",
            "scores": dict(
                correct=supported,
                abstention_correct=1,
                evidence_reproduces=1,
                fully_supported=supported,
                judge_method=1,
            ),
            "outputs": {
                "answer": {"status": "answered"},
                "metrics": {
                    "total_reported_cost_usd": None if native else 0.02,
                    "total_cost_complete": not native,
                    "total_estimated_cost_usd": 0.02 if native else None,
                    "total_estimate_complete": native,
                    "billing_mode": "native_api_estimate" if native else "api",
                    "accounting_version": native_accounting_version() if native else None,
                    "latency_s": 1,
                    "llm_calls": 2,
                },
            },
        }
        records.write_text(json.dumps(record) + "\n")
        cycle.write_new(
            tmp_path / f"{stage}-result.json",
            {
                "status": "completed",
                "records": str(records),
                "budget": {
                    "reported_spent_usd": None if native else 0.02,
                    "estimated_spent_usd": 0.02 if native else None,
                    "calls": 2,
                    "unknown_charge": native,
                    "accounting_uncertain": False,
                    "reservation_breached": False,
                },
            },
        )
        return subprocess.CompletedProcess(command, 0)

    monkeypatch.setattr(cycle.subprocess, "run", subprocess_run)
    cycle.execute(SimpleNamespace(output=tmp_path, max_cost_usd=0.1, max_calls=5, reservation_usd=0.01))
    assert invoked == [("baseline", 0.1), ("candidate", 0.08)]
    result = json.loads((tmp_path / "comparison.json").read_text())
    assert result["verdict"] == "accept_for_review"
    assert result["cycle_reported_cost_usd"] == (None if native else 0.04)
    assert result["cycle_estimated_cost_usd"] == (0.04 if native else None)
    assert result["cycle_model_calls"] == 4
    assert not (tmp_path / "worker.log").exists()


def test_campaign_accounting_rejects_mixed_or_unqualified_models_before_calls():
    cycle = runner()
    from backintel.bench.usage import NativeRunBudget

    policy = cycle.accounting_policy("openai/gpt-6-luna", "anthropic/claude-haiku-5-5")
    assert policy["version"] == native_accounting_version()
    assert isinstance(cycle.campaign_budget({"accounting": policy}, 0.1, 2, 0.01), NativeRunBudget)
    for model, judge in (
        ("openai/gpt-6-luna", "openrouter/anthropic/claude-haiku-5.5"),
        ("openai/unqualified", "anthropic/claude-haiku-5-5"),
    ):
        with pytest.raises(ValueError, match="qualified native"):
            cycle.accounting_policy(model, judge)
