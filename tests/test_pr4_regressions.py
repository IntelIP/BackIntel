"""Regression cases for the PR #4 review, with no provider calls."""

import json
from types import SimpleNamespace

import pytest

from backintel.bench import commands, run, scorecard
from backintel.contracts import Scenario
from backintel.providers.chatgpt_plan import PlanUsageStopped
from backintel.sandbox import PythonSandbox
from backintel.settings import Settings


def scenario():
    return Scenario(id="one", dataset="fixture", level=1, question="Count?", answer_type="number", expected=1)


def test_invalid_records_do_not_inflate_capability_or_coverage():
    def record(experiment, valid, score):
        return dict(
            experiment=experiment,
            dataset="fixture",
            store="sqlite:fixture",
            model="test",
            level=1,
            recorded_at="2026-11-12",
            evaluation_status="valid" if valid else "invalid",
            outputs={"metrics": {"cost_usd": 0.01}},
            scores={"correct": score},
        )

    rows = scorecard.aggregate(
        [record("partial", True, 1)]
        + [record("partial", False, 0)] * 9
        + [record("complete", True, 0)] * 2
        + [record("outage", False, None)]
    )
    partial = next(r for r in rows if r["experiment"] == "partial")
    assert partial["n"] == 1 and partial["invalid"] == 9 and partial["attempted"] == 10
    assert partial["correct"] == 1 and partial["total_cost_usd"] == 0.1
    assert scorecard.coverage(rows)[0]["experiment"] == "complete"
    assert scorecard.coverage([next(r for r in rows if r["experiment"] == "outage")]) == []


@pytest.mark.parametrize("store_id", ["multi:postgres:orders+sqlite:catalog", "sqlite:replay-custom"])
def test_ask_does_not_load_benchmark_answers(monkeypatch, capsys, store_id):
    from backintel.cli import main

    closed = []
    store = SimpleNamespace(id=store_id, close=lambda: closed.append(True))
    monkeypatch.setattr(run, "open_store", lambda *a: store)
    monkeypatch.setattr(run, "build_model", lambda *a, **k: None)
    monkeypatch.setattr(run, "build_agent", lambda *a: None)
    monkeypatch.setattr(run, "load_answers", lambda *a: pytest.fail("ask must not read evaluator references"))
    monkeypatch.setattr(run.Harness, "answer", lambda self, q: {"question": q, "store": self.store.id})
    main(["ask", "--store", store_id, "Total sales?"])
    assert json.loads(capsys.readouterr().out)["store"] == store_id
    assert closed == [True]


@pytest.mark.parametrize("code", ["quota_unavailable", "http_503", "transport_error"])
def test_subscription_outages_are_invalid_evaluations(code):
    class FailingAgent:
        def stream(self, *args, **kwargs):
            raise PlanUsageStopped(code, "controlled provider failure")

    harness = run.Harness(Settings.from_env({}), None, None, "chatgpt-plan/test", FailingAgent(), {}, False)
    record = harness.run_scenario(scenario())
    assert record["evaluation_status"] == "invalid"
    assert record["outputs"]["failure_class"] == "infrastructure"
    assert record["scores"]["correct"] is None


@pytest.mark.parametrize("remote", [False, True])
@pytest.mark.parametrize("mode", ["complete", "budget-between-trials", "invalid", "missing", "duplicate"])
def test_acceptance_reports_complete_coverage_or_fails(monkeypatch, tmp_path, capsys, remote, mode):
    from backintel.bench import acceptance

    cases = [scenario(), scenario().model_copy(update={"id": "two"})]
    suite = SimpleNamespace(dataset="fixture", scenarios=cases, data_hash="hash")
    monkeypatch.setattr(acceptance, "build_acceptance", lambda *a, **k: suite)
    monkeypatch.setattr(acceptance, "verify_acceptance_data", lambda *a: True)
    calls, closed = [], []
    budget = SimpleNamespace(
        can_admit=lambda: mode != "budget-between-trials" or not calls, report=lambda: {}
    )
    monkeypatch.setattr(commands, "_budget", lambda a: budget)
    harness = SimpleNamespace(run_metadata={}, close=lambda: closed.append(True))
    monkeypatch.setattr(run.Harness, "build", lambda *a, **k: harness)

    def trial(*args, **kwargs):
        calls.append(True)
        records = [{"scenario_id": c.id, "evaluation_status": "valid"} for c in cases]
        if mode == "invalid":
            records[-1]["evaluation_status"] = "invalid"
        elif mode == "missing":
            records.pop()
        elif mode == "duplicate":
            records.append(records[0])
        path = tmp_path / f"trial-{len(calls)}.jsonl"
        path.write_text("\n".join(json.dumps(r) for r in records))
        return {"path": str(path)} if remote else path

    monkeypatch.setattr(run, "run_langsmith" if remote else "run_local", trial)
    args = SimpleNamespace(
        action="run", max_cost_usd=1, trials=2, split="development", ids=None, no_langsmith=not remote
    )
    if mode == "complete":
        commands.cmd_acceptance(args, Settings.from_env({}))
    else:
        with pytest.raises(SystemExit) as error:
            commands.cmd_acceptance(args, Settings.from_env({}))
        assert error.value.code == 1
    report = json.loads(capsys.readouterr().out)
    assert report["status"] == ("complete" if mode == "complete" else "incomplete")
    assert report["expected_records"] == 4
    assert closed == [True]


def test_local_experiments_are_unique_and_explicit_names_cannot_append(tmp_path):
    s = scenario()
    record = {
        "scores": {"correct": 1, "evidence_reproduces": 1},
        "outputs": {"metrics": {"latency_s": 0, "cost_usd": 0}},
        "comments": {"correct": "ok"},
    }
    harness = SimpleNamespace(
        model_id="test",
        store=SimpleNamespace(kind="sqlite"),
        run_metadata={"dataset": "fixture"},
        run_scenario=lambda s: record,
    )
    first = run.run_local(harness, [s], out_dir=tmp_path)
    second = run.run_local(harness, [s], out_dir=tmp_path)
    assert first != second
    before = first.read_bytes()
    with pytest.raises(FileExistsError):
        run.run_local(harness, [s], out_dir=tmp_path, name=first.stem)
    assert first.read_bytes() == before


def test_host_python_backend_is_rejected_before_code_execution(tmp_path):
    marker = tmp_path / "must-not-exist"
    with pytest.raises(ValueError, match="Docker"):
        PythonSandbox("subprocess").run(f"open({str(marker)!r}, 'w').write('escaped')", env={}, mounts={})
    assert not marker.exists()
