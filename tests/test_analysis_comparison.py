"""Comparison integrity and stop behavior, without model-provider requests."""

import json
from pathlib import Path

import pytest

from scripts.run_analysis_comparison import run_suite, summarize_arm


def test_selected_case_keeps_frozen_suite_and_limits_subscription_calls(tmp_path, monkeypatch):
    import scripts.run_analysis_comparison as suite

    monkeypatch.setattr(suite, "build_model", lambda *args, **kwargs: object())
    seen = []

    async def run(brief, **kwargs):
        seen.append(kwargs)
        return {"status": "failed", "error": "Controlled stop before provider call."}

    monkeypatch.setattr(suite, "run_analysis", run)
    result = run_suite(tmp_path / "selected", model_ids=["chatgpt-plan/test"], case_ids=["irregular-energy"])
    assert result["case_ids"] == ["irregular-energy"]
    assert len(seen) == 1
    assert seen[0]["budget"].max_calls == 24
    assert result["arms"][0]["summary"]["case_count"] == 1
    # SQLite file bytes include engine-version metadata. Freeze the full suite for this
    # environment rather than pinning one host's file encoding across platforms.
    full = run_suite(tmp_path / "full", model_ids=["chatgpt-plan/test"])
    assert full["case_ids"] == list(suite.CASE_IDS)
    assert result["dataset_sha256"] == full["dataset_sha256"]


def test_unresolved_cases_and_unknown_costs_never_qualify_an_arm():
    records = {"a": {"status": "completed", "usage": {"cost_usd": 0.01, "cost_complete": True}}}
    scores = {"a": [{"key": "task_pass", "score": 1}]}
    result = summarize_arm(["a", "b"], records, scores, scripted=False)
    assert result["unresolved"] == ["b"]
    assert not result["eligible_for_live_review"]
    records["b"] = {"status": "completed", "usage": {"cost_usd": None, "cost_complete": False}}
    scores["b"] = [{"key": "task_pass", "score": 1}]
    result = summarize_arm(["a", "b"], records, scores, scripted=False)
    assert result["all_tasks_passed"]
    assert result["provider_cost_usd"] is None
    assert result["known_reported_cost_usd"] == 0.01
    assert not result["cost_complete"]
    assert not result["eligible_for_live_review"]
    assert not summarize_arm(["a", "b"], records, scores, scripted=True)["eligible_for_live_review"]


def test_plan_quality_review_requires_complete_tokens_without_invented_api_costs():
    records = {
        "a": {
            "status": "completed",
            "usage": {
                "billing_mode": "chatgpt_plan",
                "usage_complete": True,
                "cost_usd": None,
                "cost_complete": False,
                "cost_applicable": False,
                "input_tokens": 100,
                "output_tokens": 20,
                "llm_calls": 1,
            },
        }
    }
    scores = {"a": [{"key": "task_pass", "score": 1}]}
    result = summarize_arm(["a"], records, scores, scripted=False, billing_mode="chatgpt_plan")
    assert result["eligible_for_live_review"]
    assert result["provider_cost_usd"] is None
    assert result["known_reported_cost_usd"] is None
    assert result["billing_mode"] == "chatgpt_plan"
    assert not result["cost_applicable"]
    assert not result["cost_complete"]
    assert result["input_tokens"] == 100
    assert result["output_tokens"] == 20
    assert result["provider_calls"] == 1
    assert "no automatic model promotion" in result["scope"]
    records["a"]["usage"]["usage_complete"] = False
    assert not summarize_arm(["a"], records, scores, scripted=False, billing_mode="chatgpt_plan")[
        "eligible_for_live_review"
    ]
    records["a"]["usage"]["usage_complete"] = True
    assert not summarize_arm(["a", "b"], records, scores, scripted=False, billing_mode="chatgpt_plan")[
        "eligible_for_live_review"
    ]
    scores["a"][0]["score"] = 0
    assert not summarize_arm(["a"], records, scores, scripted=False, billing_mode="chatgpt_plan")[
        "eligible_for_live_review"
    ]


def test_plan_feedback_marks_cost_not_applicable(tmp_path):
    from scripts.analysis_cases import build_cases
    from scripts.run_analysis_comparison import grade

    case = build_cases(tmp_path / "cases")[1]
    record = {
        "status": "cannot_answer",
        "completion": {"status": "cannot_answer", "reason": "Product costs are absent."},
        "usage": {"billing_mode": "chatgpt_plan", "usage_complete": True, "cost_complete": False},
    }
    feedback = {item["key"]: item for item in grade(case, record, tmp_path)}
    assert feedback["task_pass"]["score"] == 1
    assert feedback["cost_complete"]["score"] is None
    assert feedback["usage_complete"]["score"] == 1


def test_workbook_roundoff_is_accepted_but_changed_numbers_are_rejected(tmp_path, monkeypatch):
    from openpyxl import Workbook, load_workbook

    import scripts.run_analysis_comparison as suite
    from scripts.analysis_cases import build_cases, scripted_spec

    case = build_cases(tmp_path / "fixtures")[2]
    report = scripted_spec(case)
    output = tmp_path / "run"
    bundle = output / "artifacts" / "report"
    bundle.mkdir(parents=True)
    (bundle / "report.json").write_text(json.dumps(report))
    workbook = Workbook()
    workbook.remove(workbook.active)
    for index, table in enumerate(report["tables"], 1):
        sheet = workbook.create_sheet(f"T{index}-{table['id']}"[:31])
        for row in [table["columns"], *table["rows"]]:
            sheet.append(row)
    workbook.save(bundle / "supporting.xlsx")
    workbook.close()
    # Bundle integrity has separate renderer/integration checks; this exercises the grader
    # against a real XLSX serialization and the case's independent numerical reference.
    monkeypatch.setattr(suite, "verify_bundle", lambda path: {})
    record = {"status": "completed", "completion": {"status": "completed"}, "usage": {}}
    assert suite.grade(case, record, output)[1]["score"] == 1
    workbook = load_workbook(bundle / "supporting.xlsx")
    workbook["T1-energy_by_window"]["C2"] = 999
    workbook.save(bundle / "supporting.xlsx")
    workbook.close()
    assert suite.grade(case, record, output)[1]["score"] == 0


def test_two_arms_share_budget_and_do_not_receive_private_references(tmp_path, monkeypatch):
    import scripts.run_analysis_comparison as suite

    monkeypatch.setattr(suite, "build_model", lambda *args, **kwargs: object())
    seen = []

    async def run(brief, **kwargs):
        assert "reference" not in kwargs
        assert "private-references" not in brief.model_dump_json()
        assert all("private-references" not in path for path in kwargs["store"].python_mounts())
        seen.append((kwargs["model_id"], kwargs["budget"]))
        kwargs["budget"].reserve()
        kwargs["budget"].settle(0.1)
        kwargs["output"].mkdir()
        record = {
            "status": "failed",
            "error": "Controlled infrastructure failure",
            "usage": {"cost_usd": 0.1, "cost_complete": True, "llm_calls": 1},
        }
        (kwargs["output"] / "run.json").write_text(json.dumps(record))
        return record

    monkeypatch.setattr(suite, "run_analysis", run)
    result = run_suite(
        tmp_path / "comparison",
        model_ids=["openrouter/openai/not-invoked-a", "openrouter/openai/not-invoked-b"],
        max_cost=0.5,
        reservation=0.1,
    )
    assert len(seen) == 5
    assert len({id(budget) for _, budget in seen}) == 1
    assert seen[-1][0].endswith("-b")
    assert result["budget"]["reported_spent_usd"] == 0.5
    assert len(result["arms"]) == 2
    assert all(len(arm["summary"]["unresolved"]) == 4 for arm in result["arms"])
    assert not any(arm["summary"]["eligible_for_live_review"] for arm in result["arms"])
    assert json.loads((tmp_path / "comparison" / "comparison.json").read_text())["budget"]["calls"] == 5
    assert (
        json.loads((tmp_path / "comparison" / "arm-1" / "service-availability" / "run.json").read_text())[
            "status"
        ]
        == "not_run"
    )


def test_subscription_arms_share_call_limit_without_paid_api_routing(tmp_path, monkeypatch):
    import scripts.run_analysis_comparison as suite

    model_options, seen = [], []

    def model(model_id, **kwargs):
        model_options.append((model_id, kwargs))
        return object()

    async def run(brief, **kwargs):
        assert "private-references" not in brief.model_dump_json()
        assert all("private-references" not in path for path in kwargs["store"].python_mounts())
        assert kwargs["max_model_calls"] == 24
        assert kwargs["max_tool_calls"] == 50
        assert kwargs["timeout_s"] == 900
        budget = kwargs["budget"]
        seen.append(budget)
        # Use this case's full allowance to exercise the shared campaign limit.
        for _ in range(kwargs["max_model_calls"]):
            budget.reserve()
            budget.settle({"prompt_tokens": 4, "completion_tokens": 1})
        kwargs["output"].mkdir()
        record = {
            "status": "completed",
            "usage": {
                "billing_mode": "chatgpt_plan",
                "cost_usd": None,
                "cost_complete": False,
                "cost_applicable": False,
                "usage_complete": True,
                "llm_calls": 24,
                "input_tokens": 96,
                "output_tokens": 24,
            },
        }
        (kwargs["output"] / "run.json").write_text(json.dumps(record))
        return record

    monkeypatch.setattr(suite, "build_model", model)
    monkeypatch.setattr(suite, "run_analysis", run)
    # Numerical grading is covered separately. This test exercises selection/admission/accounting.
    monkeypatch.setattr(suite, "grade", lambda *args: [{"key": "task_pass", "score": 1}])
    result = run_suite(
        tmp_path / "comparison",
        model_ids=["chatgpt-plan/not-invoked-a", "chatgpt-plan/not-invoked-b"],
    )
    assert len(seen) == 8
    assert len({id(budget) for budget in seen}) == 1
    assert seen[0].max_calls == 192
    assert not seen[0].can_admit()
    assert result["budget"]["calls"] == 192
    assert result["billing_mode"] == "chatgpt_plan"
    assert result["provider_fallbacks"] is False
    for model_id, options in model_options:
        assert model_id.startswith("chatgpt-plan/")
        assert options["first_party_only"] is False
        assert options["max_retries"] == 0
        assert options["timeout_s"] == 300
    for arm in result["arms"]:
        assert arm["summary"]["eligible_for_live_review"]
        assert arm["summary"]["provider_cost_usd"] is None
        assert arm["summary"]["known_reported_cost_usd"] is None


def test_unreported_plan_request_stops_all_remaining_cases_without_fallback(tmp_path, monkeypatch):
    import scripts.run_analysis_comparison as suite

    models, calls = [], []

    def model(model_id, **kwargs):
        models.append(model_id)
        return object()

    async def run(brief, **kwargs):
        calls.append(kwargs["model_id"])
        kwargs["budget"].reserve()
        kwargs["budget"].settle(None)
        kwargs["output"].mkdir()
        record = {
            "status": "failed",
            "error": "Controlled missing provider usage",
            "usage": {
                "billing_mode": "chatgpt_plan",
                "usage_complete": False,
                "cost_usd": None,
                "cost_complete": False,
                "llm_calls": 1,
            },
        }
        (kwargs["output"] / "run.json").write_text(json.dumps(record))
        return record

    monkeypatch.setattr(suite, "build_model", model)
    monkeypatch.setattr(suite, "run_analysis", run)
    result = run_suite(
        tmp_path / "comparison",
        model_ids=["chatgpt-plan/not-invoked-a", "chatgpt-plan/not-invoked-b"],
    )
    assert calls == ["chatgpt-plan/not-invoked-a"]
    assert all(model_id.startswith("chatgpt-plan/") for model_id in models)
    assert result["budget"]["calls"] == 1
    statuses = []
    for arm in result["arms"]:
        assert len(arm["summary"]["unresolved"]) == 4
        assert not arm["summary"]["eligible_for_live_review"]
        assert arm["summary"]["provider_cost_usd"] is None
        statuses.extend(json.loads(Path(path).read_text())["status"] for path in arm["records"].values())
    assert statuses.count("failed") == 1
    assert statuses.count("not_run") == 7


@pytest.mark.parametrize(
    "options",
    [
        {"langsmith": True},
        {"max_cost": 1},
        {"model_ids": ["openrouter/openai/not-invoked"]},
        {"model_ids": ["openrouter/openai/a"], "max_cost": 0.1, "reservation": 1},
        {"model_ids": ["chatgpt-plan/a", "openrouter/openai/b"]},
        {"model_ids": ["chatgpt-plan/a"], "max_cost": 1},
        {"model_ids": ["chatgpt-plan/a"], "reservation": 0.1},
        {"model_ids": ["chatgpt-plan/a", "chatgpt-plan/a"]},
        {"model_ids": ["chatgpt-plan/"]},
        {"model_ids": ["openai/a"]},
    ],
)
def test_invalid_execution_options_fail_before_creating_outputs(tmp_path, options):
    with pytest.raises(ValueError):
        run_suite(tmp_path / "never-created", **options)
    assert not (tmp_path / "never-created").exists()
