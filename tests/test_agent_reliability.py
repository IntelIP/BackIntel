"""Offline checks for defects observed in real benchmark traces.

The demo trace 01a1c80b-ffe6-7039-963b-fe7cb4fb4032 repeated the same successful empty
schema query 15 times. Other recorded failures cited a broken second Python check or
repeated one report metric. Fixtures below vary the business question and data.
"""

import asyncio
import json
import sqlite3

import pytest
from langchain_core.language_models.fake_chat_models import FakeMessagesListChatModel
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langgraph.errors import GraphRecursionError
from pydantic import Field, ValidationError

from backintel.agent import build_agent
from backintel.answer_validation import answer_schema, repeated_successful_read, validate_answer_evidence
from backintel.contracts import AnalystAnswer
from backintel.stores.multi import MultiStore
from backintel.stores.sqlite import SQLiteStore
from tests.trusted_python import TrustedFixturePython


@pytest.fixture
def store(tmp_path):
    path = tmp_path / "custom-location.sqlite"
    with sqlite3.connect(path) as conn:
        conn.execute("CREATE TABLE sales (amount REAL)")
        conn.executemany("INSERT INTO sales VALUES (?)", [(7.5,), (2.5,)])
    connected = SQLiteStore(path, dataset="custom")
    yield connected
    connected.close()


def response(**kwargs):
    return {
        "status": "answered",
        "answer_type": "number",
        "value": 10.0,
        "method": "Sum observed amounts.",
        "evidence": [{"kind": "sql", "code": "SELECT SUM(amount) FROM sales"}],
        **kwargs,
    }


def tool_call(name, args, number):
    return AIMessage(content="", tool_calls=[{"name": name, "args": args, "id": f"call-{number}"}])


def read_history(count=3, *, name="run_sql", args=None, payload=None, status="success"):
    history = [HumanMessage(content="Compute the requested metric.")]
    args = args or {"sql": "SELECT SUM(amount) FROM sales"}
    payload = payload or {"columns": ["total"], "rows": [[10.0]], "elapsed_ms": 1}
    for index in range(count):
        history.extend(
            [
                tool_call(name, args, index),
                ToolMessage(content=json.dumps(payload), tool_call_id=f"call-{index}", status=status),
            ]
        )
    return history


def test_repeat_guard_requires_same_successful_work_and_result():
    assert repeated_successful_read(read_history())
    assert not repeated_successful_read(read_history(2))  # independent sanity checking remains possible
    assert not repeated_successful_read(read_history(status="error"))
    assert not repeated_successful_read(read_history(name="run_python", payload={"exit_code": 1}))
    changed_args = read_history()
    changed_args[-2].tool_calls[0]["args"] = {"sql": "SELECT COUNT(*) FROM sales"}
    assert not repeated_successful_read(changed_args)
    changed_result = read_history()
    changed_result[-1].content = json.dumps({"columns": ["total"], "rows": [[20]], "elapsed_ms": 1})
    assert not repeated_successful_read(changed_result)
    new_turn = [*read_history(), HumanMessage(content="Now count the rows.")]
    assert not repeated_successful_read(new_turn)


class ScriptedModel(FakeMessagesListChatModel):
    """Exercise the installed agent graph without a network or a paid model call."""

    model_name: str = "backintel-offline-test"
    bindings: list[list[str]] = Field(default_factory=list)

    def bind_tools(self, tools, **kwargs):
        self.bindings.append([tool.name if hasattr(tool, "name") else tool["name"] for tool in tools])
        return self


def test_read_only_analyst_exposes_no_mutating_filesystem_or_host_shell(store):
    model = ScriptedModel(responses=[tool_call("VerifiedAnalystAnswer", response(), 0)])
    graph = build_agent(model, store, TrustedFixturePython())
    graph.invoke({"messages": [HumanMessage(content="Total sales?")]})
    exposed = set(model.bindings[0])
    assert {"list_tables", "describe_table", "run_sql", "run_python", "read_file"} <= exposed
    assert not exposed & {"delete", "execute", "write_file", "edit_file", "task"}


@pytest.mark.parametrize("decline", [False, True])
def test_real_agent_finalizes_repeat_loop_without_deciding_answerability(store, decline):
    query = "SELECT SUM(amount) FROM sales"
    final = (
        {
            "status": "cannot_answer",
            "method": "Inspected available sales fields.",
            "reason": "The requested expense amounts are not present.",
        }
        if decline
        else response()
    )
    model = ScriptedModel(
        responses=[
            *(tool_call("run_sql", {"sql": query}, i) for i in range(3)),
            tool_call("VerifiedAnalystAnswer", final, 3),
        ]
    )
    graph = build_agent(model, store, TrustedFixturePython())
    result = graph.invoke({"messages": [HumanMessage(content="Analyze the available records.")]})
    assert result["structured_response"].status == ("cannot_answer" if decline else "answered")
    assert "run_sql" in model.bindings[0]
    assert model.bindings[-1] == ["VerifiedAnalystAnswer"]


def test_native_structured_output_retries_failed_evidence(store):
    bad = response(evidence=[{"kind": "sql", "code": "SELECT missing FROM sales"}])
    model = ScriptedModel(
        responses=[
            tool_call("VerifiedAnalystAnswer", bad, 0),
            tool_call("VerifiedAnalystAnswer", response(), 1),
        ]
    )
    graph = build_agent(model, store, TrustedFixturePython())
    result = graph.invoke({"messages": [HumanMessage(content="Total sales?")]})
    assert result["structured_response"].value == 10
    assert any(isinstance(m, ToolMessage) and "query failed" in m.content for m in result["messages"])
    assert len(model.bindings) == 2


def test_numeric_unit_conversion_is_repaired_through_real_finalization(store):
    # Different local data/amounts from the live benchmark; no evaluator truth is used.
    bad = response(value=0.1, unit="EUR", method="Convert minor to major units.")
    repaired = response(
        value=0.1,
        unit="EUR",
        evidence=[{"kind": "sql", "code": "SELECT SUM(amount) / 100.0 FROM sales"}],
    )
    model = ScriptedModel(
        responses=[
            tool_call("VerifiedAnalystAnswer", bad, 0),
            tool_call("VerifiedAnalystAnswer", repaired, 1),
        ]
    )
    result = build_agent(model, store, TrustedFixturePython()).invoke(
        {"messages": [HumanMessage(content="Report the total in major currency units.")]}
    )
    assert result["structured_response"].value == 0.1
    assert len(model.bindings) == 2
    assert any(isinstance(m, ToolMessage) and "unit conversion" in m.content for m in result["messages"])


@pytest.mark.parametrize(
    "kind,code", [("sql", "SELECT SUM(amount) * 100 FROM sales"), ("python", "print(1000)")]
)
def test_numeric_output_must_match_the_answer_not_only_execute(store, kind, code):
    with pytest.raises(ValidationError, match="reported numeric value"):
        answer_schema(store, TrustedFixturePython()).model_validate(
            response(evidence=[{"kind": kind, "code": code}])
        )


def test_numeric_claim_in_note_or_program_source_is_not_executed_output(store):
    with pytest.raises(ValidationError, match="reported numeric value"):
        answer_schema(store, TrustedFixturePython()).model_validate(
            response(evidence=[{"kind": "python", "code": "total = 10\nprint('finished')", "note": "10"}])
        )


@pytest.mark.parametrize(
    "kind,code,value",
    [
        ("sql", "SELECT SUM(amount) / 3 FROM sales", 3.33),
        ("python", "print('1e1')", 10),
        ("python", "print('10,000.00')", 10000),
    ],
)
def test_numeric_output_accepts_display_rounding_and_numeric_notation(store, kind, code, value):
    answer_schema(store, TrustedFixturePython()).model_validate(
        response(value=value, evidence=[{"kind": kind, "code": code}])
    )


def test_failed_finalization_remains_an_execution_failure(store):
    model = ScriptedModel(
        responses=[
            tool_call("VerifiedAnalystAnswer", {"status": "cannot_answer", "method": "", "reason": ""}, 0),
        ]
    )
    graph = build_agent(model, store, TrustedFixturePython())
    with pytest.raises(GraphRecursionError):
        graph.invoke({"messages": [HumanMessage(content="Total sales?")]}, {"recursion_limit": 8})


def test_async_agent_uses_same_repeat_guard(store):
    model = ScriptedModel(
        responses=[
            *(tool_call("run_sql", {"sql": "SELECT SUM(amount) FROM sales"}, i) for i in range(3)),
            tool_call("VerifiedAnalystAnswer", response(), 3),
        ]
    )
    graph = build_agent(model, store, TrustedFixturePython())
    result = asyncio.run(graph.ainvoke({"messages": [HumanMessage(content="Total sales?")]}))
    assert result["structured_response"].value == 10
    assert model.bindings[-1] == ["VerifiedAnalystAnswer"]


def test_duplicate_report_ids_rejected_before_finalization_but_history_remains_parseable(store):
    duplicate = response(
        answer_type="report",
        value=None,
        rows=[
            {"metric": "total", "value": 10, "unit": "USD"},
            {"metric": " TOTAL ", "value": 10, "unit": "USD"},
        ],
    )
    assert AnalystAnswer.model_validate(duplicate).rows  # historical failures remain gradable
    with pytest.raises(ValidationError, match="identifiers must be unique"):
        answer_schema(store, TrustedFixturePython()).model_validate(duplicate)


def test_every_evidence_item_runs_and_broken_second_program_is_rejected(store):
    executed = []

    class RecordingSandbox(TrustedFixturePython):
        def run(self, code, **kwargs):
            executed.append(code)
            return super().run(code, **kwargs)

    answer = AnalystAnswer.model_validate(
        response(
            evidence=[
                {"kind": "python", "code": "print(10)"},
                {
                    "kind": "python",
                    "code": "import os, sqlite3\nsqlite3.connect(os.environ['BACKINTEL_STORE_NOTE'])",
                },
                {"kind": "python", "code": "print('check completed')"},
            ]
        )
    )
    with pytest.raises(ValueError, match="Evidence 2: program failed"):
        validate_answer_evidence(answer, store, RecordingSandbox())
    assert len(executed) == 3


def test_python_uses_actual_bound_store_path(store):
    program = (
        "import os, sqlite3\n"
        "con=sqlite3.connect('file:'+os.environ['BACKINTEL_SQLITE_PATH']+'?mode=ro',uri=True)\n"
        "print(con.execute('SELECT SUM(amount) FROM sales').fetchone()[0])"
    )
    answer_schema(store, TrustedFixturePython()).model_validate(
        response(evidence=[{"kind": "python", "code": program}])
    )


def test_multistore_evidence_requires_consistent_store_binding(store, tmp_path):
    path = tmp_path / "catalog.sqlite"
    with sqlite3.connect(path) as conn:
        conn.execute("CREATE TABLE catalog (name TEXT)")
    catalog = SQLiteStore(path, dataset="catalog")
    multi = MultiStore([store, catalog])
    schema = answer_schema(multi, TrustedFixturePython())
    schema.model_validate(
        response(
            evidence=[
                {
                    "kind": "sql",
                    "code": "SELECT SUM(amount) FROM sales",
                    "store": store.id,
                }
            ]
        )
    )
    with pytest.raises(ValidationError, match="disagrees"):
        schema.model_validate(
            response(
                evidence=[
                    {
                        "kind": "sql",
                        "code": f"-- store: {catalog.id}\nSELECT 10",
                        "store": store.id,
                    }
                ]
            )
        )
    catalog.close()


@pytest.mark.parametrize(
    "changes,problem",
    [
        ({"evidence": []}, "must cite"),
        ({"value": float("nan")}, "finite"),
        ({"text": "10"}, "only the value field"),
        ({"status": "cannot_answer", "value": None, "reason": ""}, "required information"),
        ({"status": "cannot_answer", "reason": "Costs absent"}, "unsupported result"),
    ],
)
def test_runtime_contract_does_not_accept_malformed_or_contradictory_answers(store, changes, problem):
    with pytest.raises(ValidationError, match=problem):
        answer_schema(store, TrustedFixturePython()).model_validate(response(**changes))
