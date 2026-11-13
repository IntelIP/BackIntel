"""Native allowance estimates stay separate from invoices and fail closed."""

from copy import deepcopy
from types import SimpleNamespace
from uuid import uuid4

import pytest
from langchain_core.messages import AIMessage
from langchain_core.outputs import ChatGeneration, LLMResult

from backintel.bench.improvement import ComparisonPolicy, compare_records
from backintel.bench.native_costs import native_accounting_version, native_estimate
from backintel.bench.run import Harness
from backintel.bench.usage import BudgetExceeded, NativeRunBudget, UsageTracker
from backintel.contracts import Scenario

MODEL = "openai/gpt-6-luna"


def message():
    return SimpleNamespace(
        usage_metadata={
            "input_tokens": 100,
            "output_tokens": 20,
            "total_tokens": 120,
            "input_token_details": {"cache_read": 50},
            "output_token_details": {"reasoning": 15},
        },
        response_metadata={"model_name": "gpt-6-luna-2026-11-01", "service_tier": "default"},
    )


def finish(tracker, value=None):
    value = value or message()
    run_id = uuid4()
    tracker.on_chat_model_start({}, [], run_id=run_id)
    tracker.on_llm_end(
        LLMResult(generations=[[ChatGeneration(message=AIMessage(content="ok", **vars(value)))]]),
        run_id=run_id,
    )


def test_estimate_counts_cache_and_reasoning_once_and_never_claims_invoice():
    budget = NativeRunBudget(0.1, 3, 0.01)
    tracker = UsageTracker(budget, model_id=MODEL)
    finish(tracker)
    finish(tracker)
    assert tracker.report()["estimated_cost_usd"] == pytest.approx(0.00013)
    assert tracker.report()["estimate_complete"]
    assert tracker.report()["cost_usd"] is None
    assert not tracker.report()["cost_complete"]
    assert budget.report()["estimated_spent_usd"] == pytest.approx(0.00013)
    assert budget.report()["reported_spent_usd"] is None
    assert budget.report()["unknown_charge"]
    assert not budget.report()["accounting_uncertain"]
    assert budget.can_admit()


@pytest.mark.parametrize(
    "section,field,value",
    [
        ("usage_metadata", "input_tokens", None),
        ("usage_metadata", "input_tokens", True),
        ("usage_metadata", "output_tokens", -1),
        ("usage_metadata", "total_tokens", 121),
        ("usage_metadata", "input_token_details", {"audio": 1}),
        ("usage_metadata", "output_token_details", {"reasoning": 21}),
        ("response_metadata", "model_name", "gpt-6-luna-unqualified"),
        ("response_metadata", "model_name", "gpt-6-sol"),
        ("response_metadata", "service_tier", "priority"),
    ],
)
def test_unqualified_usage_cannot_be_estimated(section, field, value):
    response = message()
    getattr(response, section)[field] = value
    assert native_estimate(MODEL, response) is None


def test_native_accounting_stops_on_missing_usage_error_or_oversized_response():
    with pytest.raises(ValueError, match="No qualified"):
        UsageTracker(NativeRunBudget(0.1, 3, 0.01), model_id="openai/unqualified")
    for kind in ("missing", "error", "too_large"):
        budget = NativeRunBudget(0.1, 3, 0.01)
        tracker = UsageTracker(budget, model_id=MODEL)
        if kind == "error":
            run_id = uuid4()
            tracker.on_chat_model_start({}, [], run_id=run_id)
            tracker.on_llm_error(RuntimeError("HTTP request failed"), run_id=run_id)
        else:
            value = message()
            if kind == "missing":
                value.response_metadata = {}
            else:
                value.usage_metadata.update(input_tokens=1_050_000, total_tokens=1_050_020)
            finish(tracker, value)
        assert not tracker.report()["estimate_complete"]
        assert budget.report()["accounting_uncertain"]
        assert budget.report()["reserved_usd"] == 0.01
        with pytest.raises(BudgetExceeded):
            tracker.on_chat_model_start({}, [], run_id=uuid4())


def test_anthropic_requires_complete_raw_cache_counts_and_rejects_server_tool_fees():
    response = SimpleNamespace(
        usage_metadata={"input_tokens": 120, "output_tokens": 20, "total_tokens": 140},
        response_metadata={
            "model": "claude-haiku-5-5",
            "usage": {
                "input_tokens": 100,
                "output_tokens": 20,
                "cache_read_input_tokens": 10,
                "cache_creation_input_tokens": 10,
            },
        },
    )
    assert native_estimate("anthropic/claude-haiku-5-5", response) == pytest.approx(0.00017)
    for usage in (
        {"input_tokens": 120, "output_tokens": 20},
        {**response.response_metadata["usage"], "cache_creation_input_tokens": 11},
        {**response.response_metadata["usage"], "server_tool_use": {"web_search_requests": 1}},
    ):
        changed = deepcopy(response)
        changed.response_metadata["usage"] = usage
        assert native_estimate("anthropic/claude-haiku-5-5", changed) is None


def test_native_record_and_comparison_require_the_frozen_estimate_basis():
    budget = NativeRunBudget(0.1, 3, 0.01)
    analyst = UsageTracker(budget, model_id=MODEL)
    judge = UsageTracker(budget, model_id=MODEL)
    finish(analyst)
    finish(judge)
    identity = dict(
        dataset="test",
        data_version="data",
        reference_version="ref",
        scorer_version="scorer",
        judge_model=MODEL,
        judge_version="judge",
    )
    harness = Harness(SimpleNamespace(), None, None, MODEL, None, {}, judge=True, run_metadata=identity)
    scenario = Scenario(id="case", dataset="test", level=1, question="q", answer_type="number", expected=1)
    scores = {
        name: {"score": 1, "comment": "fixture"}
        for name in ("correct", "fully_supported", "abstention_correct", "evidence_reproduces")
    }
    scores["judge_method"] = {"score": 1, "comment": "fixture", "metrics": judge.report()}
    row = harness.record(scenario, {"metrics": analyst.report()}, scores)
    metrics = row["outputs"]["metrics"]
    assert metrics["total_estimated_cost_usd"] == pytest.approx(0.00013)
    assert metrics["total_estimate_complete"]
    assert metrics["total_reported_cost_usd"] is None
    assert not metrics["total_cost_complete"]
    policy = ComparisonPolicy(
        identity,
        ("case",),
        ("case",),
        require_improvement=False,
        cost_basis="native_estimate",
        accounting_version=native_accounting_version(),
        max_candidate_cost_usd=0.01,
    )
    result = compare_records([row], [row], policy)
    assert result["verdict"] == "accept_for_review"
    assert result["candidate"]["reported_cost_usd"] is None
    assert not result["candidate"]["cost_complete"]
    for key, value in (
        ("accounting_version", "different"),
        ("total_estimate_complete", False),
        ("total_estimated_cost_usd", None),
    ):
        invalid = deepcopy(row)
        invalid["outputs"]["metrics"][key] = value
        assert compare_records([row], [invalid], policy)["verdict"] == "invalid_comparison"


def test_native_message_fallback_cannot_report_complete_zero_cost():
    class MissingCallbacks:
        def stream(self, *args, **kwargs):
            yield {"messages": [AIMessage(content="untracked", **vars(message()))]}

    budget = NativeRunBudget(0.1, 3, 0.01)
    harness = Harness(
        SimpleNamespace(), None, None, MODEL, MissingCallbacks(), {}, judge=False, budget=budget
    )
    outputs = harness.answer("q")
    assert not outputs["metrics"]["estimate_complete"]
    assert not budget.can_admit()
