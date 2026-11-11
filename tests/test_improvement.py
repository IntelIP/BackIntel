import copy
from types import SimpleNamespace
from uuid import uuid4

import pytest
from langchain_core.messages import AIMessage
from langchain_core.outputs import ChatGeneration, LLMResult

from backintel.bench.improvement import (
    CandidatePatch,
    ComparisonPolicy,
    apply_candidate,
    compare_records,
    propose_candidate,
)
from backintel.bench.run import Harness
from backintel.bench.usage import BudgetExceeded, RunBudget, UsageTracker

IDENTITY = dict(
    dataset="acceptance",
    data_version="data1",
    reference_version="ref1",
    scorer_version="grader1",
    judge_model="judge",
    judge_version="rubric1",
)


def record(case, passed, **overrides):
    scores = dict.fromkeys(
        ("correct", "abstention_correct", "evidence_reproduces", "fully_supported"), int(passed)
    )
    scores["judge_method"] = 0.875
    return {
        **IDENTITY,
        "scenario_id": case,
        "answerable": True,
        "source_version": "src1",
        "scores": scores,
        "outputs": {
            "answer": {"status": "answered"},
            "error": None,
            "metrics": {
                "total_reported_cost_usd": 0.01,
                "total_cost_complete": True,
                "latency_s": 5,
                "llm_calls": 1,
            },
        },
        **overrides,
    }


def policy(**kwargs):
    return ComparisonPolicy(IDENTITY, ("fix", "healthy"), ("fix", "healthy"), **kwargs)


def test_candidate_must_improve_and_preserve_successful_cases():
    baseline = [record("fix", False), record("healthy", True)]
    candidate = [record("fix", True), record("healthy", True)]
    result = compare_records(baseline, candidate, policy())
    assert result["verdict"] == "accept_for_review"
    assert result["improvements"] == [{"case": "fix", "trial": 0}]
    candidate[1]["scores"]["evidence_reproduces"] = 0
    candidate[1]["scores"]["fully_supported"] = 0
    result = compare_records(baseline, candidate, policy())
    assert result["verdict"] == "reject"
    assert result["regressions"][0]["metric"] == "evidence_reproduces"


def test_comparison_cannot_hide_cases_or_change_grader_or_unknown_spend():
    baseline = [record("fix", False), record("healthy", True)]
    for candidate in (
        [record("fix", True)],
        [record("fix", True, scorer_version="changed"), record("healthy", True)],
        [record("fix", True), record("fix", True), record("healthy", True)],
    ):
        assert compare_records(baseline, candidate, policy())["verdict"] == "invalid_comparison"
    candidate = [record("fix", True), record("healthy", True)]
    candidate[0]["outputs"]["metrics"]["total_cost_complete"] = False
    assert compare_records(baseline, candidate, policy())["verdict"] == "invalid_comparison"
    candidate[0]["outputs"]["metrics"]["total_cost_complete"] = True
    candidate[0]["outputs"]["metrics"]["total_reported_cost_usd"] = "unknown"
    assert compare_records(baseline, candidate, policy())["verdict"] == "invalid_comparison"
    candidate[0]["outputs"]["metrics"]["total_reported_cost_usd"] = 0.01
    assert compare_records(baseline, candidate, policy(max_candidate_cost_usd=0.015))["verdict"] == "reject"


def test_locked_policy_detects_modification_and_repeated_trials_require_coverage():
    document = policy().document()
    assert ComparisonPolicy.from_document(document).case_ids == ("fix", "healthy")
    document["policy"]["require_improvement"] = False
    with pytest.raises(ValueError, match="modified"):
        ComparisonPolicy.from_document(document)
    rows = [record("fix", True), record("healthy", True)]
    assert compare_records(rows, rows, policy(trials=2))["verdict"] == "invalid_comparison"


def finish(tracker, cost=0.005, run_id=None):
    run_id = run_id or uuid4()
    tracker.on_chat_model_start({}, [], run_id=run_id)
    message = AIMessage(content="done", response_metadata={"token_usage": {"cost": cost}})
    tracker.on_llm_end(
        LLMResult(
            generations=[[ChatGeneration(message=message)]],
            llm_output={"token_usage": {"cost": cost, "prompt_tokens": 100, "completion_tokens": 10}},
        ),
        run_id=run_id,
    )
    return run_id


def test_usage_deduplicates_metadata_and_counts_completed_calls_before_graph_failure():
    tracker = UsageTracker()
    run_id = finish(tracker)
    tracker.on_llm_end(LLMResult(generations=[], llm_output={"token_usage": {"cost": 100}}), run_id=run_id)
    assert tracker.report()["cost_usd"] == 0.005
    assert tracker.report()["input_tokens"] == 100

    class FailingGraph:
        def stream(self, inputs, config, stream_mode):
            finish(config["callbacks"][0])
            yield {"messages": [AIMessage(content="working")]}
            raise RuntimeError("execution limit")

    harness = Harness(SimpleNamespace(), None, None, "model", FailingGraph(), {}, judge=False)
    result = harness.answer("q")
    assert "execution limit" in result["error"]
    assert result["metrics"]["cost_usd"] == 0.005
    assert result["metrics"]["cost_complete"] is True  # Known LLM usage despite a graph failure.


def test_budget_admission_unknown_usage_and_reservation_breach_stop_new_calls():
    budget = RunBudget(limit_usd=0.03, reservation_usd=0.01, max_calls=2)
    tracker = UsageTracker(budget)
    finish(tracker)
    finish(tracker)
    with pytest.raises(BudgetExceeded):
        tracker.on_chat_model_start({}, [], run_id=uuid4())
    assert budget.spent_usd == 0.01
    for cost in (None, 0.02):
        budget = RunBudget(limit_usd=0.1, reservation_usd=0.01, max_calls=10)
        tracker = UsageTracker(budget)
        if cost is None:
            run_id = uuid4()
            tracker.on_chat_model_start({}, [], run_id=run_id)
            tracker.on_llm_error(RuntimeError("unknown billed usage"), run_id=run_id)
            assert tracker.report()["cost_complete"] is False
        else:
            finish(tracker, cost)
        with pytest.raises(BudgetExceeded):
            tracker.on_chat_model_start({}, [], run_id=uuid4())


def test_worker_has_only_explicit_files_and_proposal_requires_checked_application(monkeypatch, tmp_path):
    from backintel.bench import improvement

    name = "src/backintel/agent_files/lead.md"
    seen = {}

    class Worker:
        def with_structured_output(self, schema):
            assert schema is CandidatePatch
            return self

        def invoke(self, prompt, config):
            seen["prompt"] = prompt
            finish(config["callbacks"][0])
            return CandidatePatch(
                explanation="General stopping rule", replacements=[dict(path=name, content="after")]
            )

    monkeypatch.setattr(improvement, "build_model", lambda model_id, max_retries: Worker())
    proposal = propose_candidate(
        {name: "before"}, "Repeated schema queries", model_id="approved", budget=RunBudget(0.1, 2, 0.01)
    )
    assert proposal["status"] == "proposed"
    assert "Repeated schema queries" in seen["prompt"][1]["content"]
    assert seen["prompt"][0]["role"] == "system"
    assert proposal["usage"]["cost_usd"] == 0.005
    path = tmp_path / name
    path.parent.mkdir(parents=True)
    path.write_text("before")
    assert apply_candidate(proposal, tmp_path) == [name]
    assert path.read_text() == "after"
    with pytest.raises(ValueError, match="base changed"):
        apply_candidate(proposal, tmp_path)
    malicious = copy.deepcopy(proposal)
    malicious["patch"]["replacements"][0]["path"] = "src/backintel/bench/scoring.py"
    with pytest.raises(ValueError, match="outside"):
        apply_candidate(malicious, tmp_path)
    with pytest.raises(ValueError, match="outside"):
        propose_candidate(
            {"benchmarks/answers/olist.json": "secret"},
            "q",
            model_id="approved",
            budget=RunBudget(0.1, 2, 0.01),
        )


def test_budget_exhaustion_marks_unattempted_cases_invalid_without_invoking_agent():
    from backintel.contracts import Scenario

    class NeverCalled:
        def stream(self, *args, **kwargs):
            raise AssertionError("Unfunded target must not execute")

    budget = RunBudget(0.02, 1, 0.01)
    finish(UsageTracker(budget))
    assert not budget.can_admit()
    harness = Harness(SimpleNamespace(), None, None, "model", NeverCalled(), {}, judge=True, budget=budget)
    scenario = Scenario(
        id="fix", dataset="acceptance", level=1, question="q", answer_type="number", expected=1
    )
    outputs = harness.answer("q", scenario)
    assert outputs["failure_class"] == "budget" and outputs["attempted"] is False
    scores = harness.score(scenario, outputs)
    assert all(v["score"] is None for v in scores.values())
    row = harness.record(scenario, outputs, scores)
    assert row["evaluation_status"] == "invalid"
    candidate = [{**record("fix", True), "outputs": outputs}, record("healthy", True)]
    result = compare_records([record("fix", False), record("healthy", True)], candidate, policy())
    assert result["verdict"] == "invalid_comparison"


def test_provider_failure_is_infrastructure_and_does_not_run_judge():
    from backintel.contracts import Scenario

    class BrokenProvider:
        def stream(self, *args, **kwargs):
            raise ConnectionError("provider unavailable")

    harness = Harness(SimpleNamespace(), None, None, "model", BrokenProvider(), {}, judge=True)
    outputs = harness.answer("q")
    assert outputs["failure_class"] == "infrastructure"
    scenario = Scenario(
        id="fix", dataset="acceptance", level=1, question="q", answer_type="number", expected=1
    )
    scores = harness.score(scenario, outputs)
    assert scores["fully_supported"]["score"] is None
    assert scores["judge_method"]["metrics"]["llm_calls"] == 0


@pytest.mark.parametrize(
    "envelope",
    [
        {
            "message": "This request would exceed your available credits given your current in-flight requests.",
            "code": 402,
            "metadata": {"error_type": "payment_required"},
        },
        {
            "message": "You have no credits remaining. Add credits to continue using the API at https://platform.openai.com/settings/organization/billing/.",
            "code": 502,
            "metadata": {"error_type": "provider_unavailable"},
        },
    ],
)
def test_wrapped_provider_error_is_invalid_and_never_judged(monkeypatch, envelope):
    from backintel.bench import run
    from backintel.contracts import Scenario

    error = ValueError(envelope)

    class RejectedProvider:
        def stream(self, inputs, config, stream_mode):
            tracker = config["callbacks"][0]
            run_id = uuid4()
            tracker.on_chat_model_start({}, [], run_id=run_id)
            tracker.on_llm_error(error, run_id=run_id)
            raise error

    def forbidden_judge(*args, **kwargs):
        raise AssertionError("Provider credit failures must not be graded")

    monkeypatch.setattr(run, "judge_answer", forbidden_judge)
    budget = RunBudget(0.01, 3, 0.005)
    harness = Harness(
        SimpleNamespace(), None, None, "model", RejectedProvider(), {}, judge=True, budget=budget
    )
    scenario = Scenario(id="case", dataset="test", level=1, question="q", answer_type="number", expected=1)
    outputs = harness.answer("q")
    assert outputs["failure_class"] == "infrastructure"
    assert outputs["metrics"]["unpriced_llm_calls"] == 1
    assert outputs["metrics"]["cost_complete"] is False
    assert not budget.can_admit()
    scores = harness.score(scenario, outputs)
    assert all(value["score"] is None for value in scores.values())
    assert scores["judge_method"]["metrics"]["llm_calls"] == 0
    row = harness.record(scenario, outputs, scores)
    assert row["evaluation_status"] == "invalid"
    assert row["outputs"]["metrics"]["total_cost_complete"] is False


@pytest.mark.parametrize("error", [ValueError("Invalid answer shape"), ValueError({"code": 402})])
def test_ordinary_value_errors_remain_agent_failures(error):
    class BrokenAgent:
        def stream(self, *args, **kwargs):
            raise error

    harness = Harness(SimpleNamespace(), None, None, "model", BrokenAgent(), {}, judge=False)
    assert harness.answer("q")["failure_class"] == "agent"


def test_budget_callback_aborts_actual_model_pipeline_before_provider_request(monkeypatch):
    from unittest.mock import Mock

    from langsmith import tracing_context

    from backintel.models import build_model

    model = build_model(
        "openrouter/openai/gpt-6-luna", env={"OPENROUTER_API_KEY": "test-placeholder"}, max_retries=0
    )
    provider_call = Mock(side_effect=AssertionError("Provider must not receive an unfunded request"))
    monkeypatch.setattr(model.client, "create", provider_call)
    budget = RunBudget(0.02, 1, 0.01)
    finish(UsageTracker(budget))
    with tracing_context(enabled=False), pytest.raises(BudgetExceeded):
        model.invoke("This request must not be sent", config={"callbacks": [UsageTracker(budget)]})
    provider_call.assert_not_called()
    assert budget.calls == 1


def test_required_judge_budget_failure_invalidates_otherwise_correct_answer(monkeypatch):
    from backintel.bench import run
    from backintel.contracts import AnalystAnswer, Scenario

    def unfunded_judge(*args, **kwargs):
        raise BudgetExceeded("No judge reservation remains")

    monkeypatch.setattr(run, "judge_answer", unfunded_judge)
    scenario = Scenario(
        id="fix",
        dataset="acceptance",
        level=3,
        question="q",
        answer_type="number",
        expected=None,
        answerable=False,
    )
    answer = AnalystAnswer(status="cannot_answer", method="Inspected schema", reason="Missing costs")
    harness = Harness(SimpleNamespace(judge_model="judge"), None, None, "model", None, {}, judge=True)
    outputs = {"answer": answer.model_dump(), "error": None, "metrics": UsageTracker().report()}
    scores = harness.score(scenario, outputs)
    row = harness.record(scenario, outputs, scores)
    assert row["scores"]["correct"] == 1
    assert row["scores"]["judge_method"] is None
    assert row["evaluation_status"] == "invalid"
    assert "No judge reservation" in row["outputs"]["evaluation_error"]
    assert row["outputs"]["metrics"]["total_cost_complete"] is True  # No request was sent.

    candidate = [record("fix", True), record("healthy", True)]
    candidate[0]["scores"]["judge_method"] = None
    result = compare_records([record("fix", False), record("healthy", True)], candidate, policy())
    assert result["verdict"] == "invalid_comparison"
    assert any("required judge" in reason for reason in result["invalid_reasons"])
