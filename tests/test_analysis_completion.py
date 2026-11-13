"""Structured completion must survive text-only model stops without inventing success."""

import asyncio
import json
import os
import sqlite3
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
