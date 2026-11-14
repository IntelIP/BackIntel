"""Structured completion must survive text-only model stops without inventing success."""

import asyncio
import json
import os
import sqlite3
from pathlib import Path
from types import SimpleNamespace

import pytest
from langchain_core.language_models.fake_chat_models import FakeMessagesListChatModel
from langchain_core.messages import AIMessage

from backintel.analysis import AnalysisBrief, build_analysis_agent, run_analysis
from backintel.artifacts import verify_bundle
from backintel.stores.sqlite import SQLiteStore


class CompletionTestModel(FakeMessagesListChatModel):
    def bind_tools(self, tools, **kwargs):
        return self


def call(name, args, index):
    return AIMessage(content="", tool_calls=[{"name": name, "args": args, "id": f"test-{index}"}])


def completion():
    return call(
        "AnalysisCompletion",
        {"status": "cannot_answer", "summary": "Missing required inputs.", "reason": "Costs are absent."},
        99,
    )


@pytest.fixture
def store(tmp_path):
    source = tmp_path / "source.sqlite"
    with sqlite3.connect(source) as connection:
        connection.execute("CREATE TABLE items(value INTEGER)")
        connection.executemany("INSERT INTO items VALUES (?)", [(1,), (2,)])
    store = SQLiteStore(source, dataset="completion-test")
    try:
        yield store
    finally:
        store.close()


def graph(store, responses, *, max_model_calls=4):
    sandbox = SimpleNamespace(env={}, resource_usage=lambda: {"profile": {}})
    return build_analysis_agent(
        CompletionTestModel(responses=responses),
        store,
        sandbox,
        {},
        {},
        max_model_calls=max_model_calls,
    )


@pytest.mark.parametrize("recover", [False, True])
def test_valid_completion_and_text_only_recovery(store, recover):
    responses = ([AIMessage(content="I cannot calculate this.")] if recover else []) + [completion()]
    result = asyncio.run(graph(store, responses).ainvoke({"messages": [("user", "Analyze the data.")]}))
    assert result["structured_response"].status == "cannot_answer"
    assert bool(result.get("completion_repair_attempted")) is recover
    if recover:
        assert any(m.type == "human" and "AnalysisCompletion" in m.content for m in result["messages"])
        assert any(m.type == "ai" and m.content == "I cannot calculate this." for m in result["messages"])


def test_repeated_text_stop_fails_without_resetting_call_limit(store):
    agent = graph(store, [AIMessage(content="Done."), AIMessage(content="Still done.")])
    with pytest.raises(ValueError, match="Missing AnalysisCompletion after one recovery prompt"):
        asyncio.run(agent.ainvoke({"messages": [("user", "Analyze the data.")]}))


def test_completion_recovery_respects_original_call_limit(store):
    from langchain.agents.middleware.model_call_limit import ModelCallLimitExceededError

    agent = graph(store, [AIMessage(content="Done."), completion()], max_model_calls=1)
    with pytest.raises(ModelCallLimitExceededError):
        asyncio.run(agent.ainvoke({"messages": [("user", "Analyze the data.")]}))


def test_virtual_skill_read_uses_instruction_backend_without_vm_execution(store):
    agent = graph(
        store,
        [
            call("read_file", {"file_path": "/skills/analysis/analysis-specialist/SKILL.md"}, 0),
            completion(),
        ],
    )
    result = asyncio.run(agent.ainvoke({"messages": [("user", "Read your skill, then check inputs.")]}))
    reads = [m for m in result["messages"] if m.type == "tool" and m.name == "read_file"]
    assert len(reads) == 1
    assert "# Analysis and visual reporting" in reads[0].content
    assert result["structured_response"].status == "cannot_answer"


@pytest.mark.skipif(os.environ.get("BACKINTEL_SMOLVM_TESTS") != "1", reason="Requires prepared SmolVM")
def test_recovered_completion_exports_verified_bundle(tmp_path, store):
    spec = {
        "title": "Completion recovery fixture",
        "summary": "The two assigned values sum to three.",
        "evidence": [
            {
                "id": "sum",
                "kind": "sql",
                "code": "SELECT SUM(value) AS Total FROM items",
                "source_ids": ["assigned"],
            }
        ],
        "tables": [
            {
                "id": "total",
                "title": "Sum",
                "columns": ["Total"],
                "rows": [[3]],
                "units": {"Total": "items"},
                "evidence_ids": ["sum"],
            }
        ],
        "metrics": [],
        "charts": [],
    }
    model = CompletionTestModel(
        responses=[
            call("write_analysis_file", {"path": "/workspace/report.json", "content": json.dumps(spec)}, 0),
            call("render_report", {"spec_path": "/workspace/report.json"}, 1),
            AIMessage(content="The report is ready."),
            call("AnalysisCompletion", {"status": "completed", "summary": "The report is ready."}, 2),
        ]
    )
    output = tmp_path / "run"
    record = asyncio.run(
        run_analysis(
            AnalysisBrief(objective="Report the sum of the assigned values."),
            model=model,
            model_id="scripted-reference",
            store=store,
            output=output,
            scripted=True,
        )
    )
    assert record["status"] == "completed", record.get("error")
    assert record["completion_recovery_attempts"] == 1
    assert record["resources"]["backend"] == "smolvm"
    bundle = output / "artifacts" / "report"
    assert verify_bundle(bundle) == record["artifacts"]
    assert json.loads((bundle / "report.json").read_text())["tables"][0]["rows"] == [[3]]
    assert record["dashboard"]["status"] == "generated"
    assert (output / "dashboard" / "app.py").is_file()


@pytest.mark.parametrize(
    "outcome",
    [
        "completed",
        "cannot_answer",
        "export_failure",
        "generation_timeout",
        "review_error",
        "review_timeout",
        "table_only",
    ],
)
def test_completion_delivers_dashboard_only_after_verified_export(tmp_path, store, monkeypatch, outcome):
    import backintel.analysis as analysis
    import backintel.artifacts as artifacts
    import backintel.presentation.dashboard as dashboard

    clock = SimpleNamespace(now=100.0)
    if outcome == "generation_timeout":
        simulated_time = SimpleNamespace(monotonic=lambda: clock.now)
        monkeypatch.setattr(analysis, "time", simulated_time)
        monkeypatch.setattr(dashboard, "time", simulated_time)

    spec = json.loads((Path(__file__).parents[1] / "examples/analysis-report.json").read_text())
    if outcome == "table_only":
        spec["charts"] = []
    verified = []
    reviewed = []

    class Sandbox:
        env = {}

        def __init__(self, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def close(self):
            pass

        def resource_usage(self):
            return {"profile": {}}

        def write_file(self, *args):
            return SimpleNamespace(exit_code=0)

        def run_python(self, *args):
            return SimpleNamespace(exit_code=0)

        def export_artifacts(self, *args):
            if outcome == "export_failure":
                raise ValueError("export failed")

    def build(model, store, sandbox, identity, rendered, **kwargs):
        rendered.update(spec=spec, spec_sha256="test", reproduction={})

        async def stream(*args, **kwargs):
            yield {
                "structured_response": {
                    "status": "cannot_answer" if outcome == "cannot_answer" else "completed",
                    "summary": "Example",
                    "reason": "Missing input",
                }
            }

        return SimpleNamespace(astream=stream)

    def verify(path):
        verified.append(path)
        if outcome == "generation_timeout":
            clock.now += 901  # Export used the original 900-second budget.
        return {"verified": True}

    monkeypatch.setattr(analysis, "AnalysisSandbox", Sandbox)
    monkeypatch.setattr(analysis, "build_analysis_agent", build)
    monkeypatch.setattr(artifacts, "verify_bundle", verify)
    import backintel.presentation.review as dashboard_review

    actual_review = dashboard_review.review_dashboard_async

    async def review(directory, output, **kwargs):
        assert verified, "Design review must follow verified numerical export"
        assert 0 < kwargs["timeout_s"] < 900
        reviewed.append(directory)
        if outcome == "review_error":
            raise ValueError("Review cannot start")
        if outcome == "review_timeout":
            raise TimeoutError("No review budget remains")
        if outcome == "table_only":
            return await actual_review(directory, output, **{**kwargs, "reviser_id": "openai/scripted-test"})
        return {"ready": False, "status": "needs_revision", "selected": str(directory)}

    monkeypatch.setattr(dashboard_review, "review_dashboard_async", review)
    output = tmp_path / "delivery"
    result = asyncio.run(
        run_analysis(
            AnalysisBrief(objective="Analyze assigned data"),
            model=CompletionTestModel(responses=[completion()]),
            model_id="scripted",
            store=store,
            output=output,
            scripted=True,
            dashboard_reviewer=None if outcome == "generation_timeout" else object(),
            dashboard_reviewer_id="anthropic/test-not-invoked",
        )
    )
    if outcome in {"completed", "review_error", "review_timeout", "table_only"}:
        assert verified
        assert result["status"] == "completed", result.get("error")
        assert (output / "dashboard/app.py").is_file()
        assert reviewed and not result["dashboard"]["ready"]
        assert result["dashboard_review"]["status"] == (
            "needs_revision"
            if outcome == "completed"
            else "timed_out"
            if outcome == "review_timeout"
            else "review_error"
        )
        if outcome != "completed":
            assert result["dashboard_review"]["selected"] is None
        if outcome == "table_only":
            assert result["dashboard_review"]["error_type"] == "ValueError"
        assert json.loads((output / "run.json").read_text())["status"] == "completed"
    elif outcome == "generation_timeout":
        assert verified and result["status"] == "failed"
        assert "deadline reached during dashboard generation" in result["error"]
        assert json.loads((output / "run.json").read_text())["status"] == "failed"
        assert not (output / "dashboard").exists()
        assert not reviewed
    else:
        assert result["status"] == ("failed" if outcome == "export_failure" else "cannot_answer")
        assert not verified
        assert not (output / "dashboard").exists()
        assert not reviewed
