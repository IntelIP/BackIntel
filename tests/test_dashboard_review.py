"""Presentation invariants, bounded revisions and real browser capture; no provider calls."""

import copy
import json
from pathlib import Path

import pytest

from backintel.presentation.dashboard import generate_dashboard
from backintel.presentation.design import CRITERIA, DesignPlan, DesignReview, validate_plan
from backintel.presentation.review import parse_response, review_dashboard
from tests.test_artifacts import report_spec as report_fixture


def plan_for(data):
    return {
        "title": "Understand the operating pattern",
        "introduction": "Compare the retained measures across periods and groups.",
        "sections": [
            {
                "title": f"What does business comparison {i + 1} show us?",
                "takeaway": "Read the comparison with its stated units.",
                "columns": 1,
                "charts": [
                    {
                        "chart": i,
                        "title": c["title"],
                        "caption": "Source: retained analysis.",
                        "encoding": "column" if c["kind"] == "line" else "original",
                        "x_label": c["x"],
                        "y_label": c.get("y", "Observations"),
                    }
                ],
            }
            for i, c in enumerate(data["charts"])
        ],
    }


def rating(score, blockers=None):
    return DesignReview(
        ratings=[
            {
                "criterion": c,
                "evidence": "Visible comparison is readable.",
                "views": ["desktop/Story"],
                "score": score,
            }
            for c in CRITERIA
        ],
        blocking_issues=blockers or [],
        revisions=[] if score >= 4 else ["Group related charts into named pages."],
    )


class Scripted:
    def __init__(self, *values):
        self.values = list(values)
        self.calls = 0
        self.inputs = []

    def with_structured_output(self, schema, **kwargs):
        return self

    def invoke(self, messages, **kwargs):
        self.inputs.append(messages)
        self.calls += 1
        value = self.values.pop(0)
        if isinstance(value, Exception):
            raise value
        return value


def captured(directory, output):
    # Explicit test double; real browser evidence has a separate integration check below.
    output.mkdir()
    (output / "desktop.png").write_bytes(b"test-image")
    return {
        "views": [{"name": "desktop/Story", "file": "desktop.png"}],
        "failures": [],
        "checks": ["scripted check"],
    }


@pytest.fixture
def delivery(tmp_path, monkeypatch):
    monkeypatch.setenv("LANGSMITH_TRACING", "false")
    target = tmp_path / "dashboard"
    generate_dashboard(report_fixture.__wrapped__(), target)
    return target


def run_loop(delivery, tmp_path, reviewer, writer, **kwargs):
    return review_dashboard(
        delivery,
        tmp_path / "review",
        brief="Explain the operating pattern.",
        reviewer=reviewer,
        reviser=writer,
        reviewer_id="anthropic/claude-haiku-5-5",
        reviser_id="chatgpt-plan/gpt-6.1-sol",
        capture=kwargs.pop("capture", captured),
        **kwargs,
    )


def test_review_revises_rendered_output_and_stops_on_pass(delivery, tmp_path):
    data = json.loads((delivery / "dashboard.json").read_text())
    reviewer, writer = Scripted(rating(2), rating(4)), Scripted(DesignPlan.model_validate(plan_for(data)))
    result = run_loop(delivery, tmp_path, reviewer, writer)
    assert result["ready"] and result["status"] == "passed"
    assert len(result["rounds"]) == 2 and writer.calls == 1 and reviewer.calls == 2
    selected = Path(result["selected"])
    assert (selected / "dashboard.json").read_bytes() == (delivery / "dashboard.json").read_bytes()
    assert not (delivery / "presentation.json").exists()
    assert any(b["type"] == "image_url" for b in reviewer.inputs[0][1].content)
    # The critic cannot see previous scores or generator rationale.
    assert '"review":' not in reviewer.inputs[1][1].content[0]["text"]


def test_two_revision_limit_retains_best_instead_of_last(delivery, tmp_path):
    plan = DesignPlan.model_validate(plan_for(json.loads((delivery / "dashboard.json").read_text())))
    reviewer, writer = Scripted(rating(3), rating(2), rating(1)), Scripted(plan, plan)
    result = run_loop(delivery, tmp_path, reviewer, writer)
    assert result["status"] == "needs_revision" and not result["ready"]
    assert result["selected"].endswith("candidate-0")
    assert reviewer.calls == 3 and writer.calls == 2


@pytest.mark.parametrize("failure", ["browser", "provider", "invented_view", "blocking_claim"])
def test_failures_cannot_be_averaged_into_acceptance(delivery, tmp_path, failure):
    review = rating(5, ["Gross sales labeled as profit"] if failure == "blocking_claim" else None)
    if failure == "invented_view":
        review.ratings[0].views = ["not-captured"]
    reviewer = Scripted(RuntimeError("provider stopped") if failure == "provider" else review)

    def browser(directory, output):
        result = captured(directory, output)
        if failure == "browser":
            result["failures"] = ["Navigation is broken"]
        return result

    result = run_loop(delivery, tmp_path, reviewer, Scripted(), max_revisions=0, capture=browser)
    assert not result["ready"] and result["status"] != "passed"
    assert (tmp_path / "review/review.json").is_file()


def test_revision_cannot_change_data_or_drop_charts(delivery, tmp_path):
    data = json.loads((delivery / "dashboard.json").read_text())
    plan = plan_for(data)
    bad = copy.deepcopy(plan)
    bad["tables"] = []
    with pytest.raises(ValueError):
        validate_plan(bad, data)
    bad = copy.deepcopy(plan)
    bad["sections"].pop()
    with pytest.raises(ValueError, match="Every retained chart"):
        validate_plan(bad, data)
    writer = Scripted(DesignPlan.model_validate(bad))
    result = run_loop(delivery, tmp_path, Scripted(rating(2)), writer)
    assert result["status"] == "review_error"
    assert result["selected"].endswith("candidate-0")
    with pytest.raises(ValueError, match="max_revisions"):
        review_dashboard(
            delivery,
            tmp_path / "bad",
            brief="question",
            reviewer=None,
            reviser=None,
            reviewer_id="a",
            reviser_id="b",
            max_revisions=3,
        )


def test_plan_final_json_recovery_is_validated(delivery):
    from langchain_core.messages import AIMessage

    data = json.loads((delivery / "dashboard.json").read_text())
    raw = AIMessage(
        content=[
            {"type": "reasoning", "encrypted_content": "ignored"},
            {"type": "text", "text": json.dumps(plan_for(data))},
        ]
    )
    parsed = parse_response({"raw": raw, "parsed": None}, DesignPlan)
    assert validate_plan(parsed.model_dump(), data)
    raw.content = "I finished the dashboard."
    with pytest.raises(ValueError):
        parse_response({"raw": raw, "parsed": None}, DesignPlan)


def test_designed_dashboard_real_browser_and_download(delivery, tmp_path):
    pytest.importorskip("playwright")
    pytest.importorskip("streamlit")
    from backintel.presentation.capture import capture_dashboard

    data = json.loads((delivery / "dashboard.json").read_text())
    presentation = plan_for(data)
    presentation["context"] = {
        "audience": "An illustrative operations planning exercise.",
        "decision": "Which period should a team investigate?",
        "coverage": "The retained report, not a live activity feed.",
        "limitation": "Historical observations do not establish causality.",
    }
    presentation["sections"][0]["charts"][0]["reading_guide"] = "Each mark compares one retained group."
    (delivery / "presentation.json").write_text(json.dumps(presentation))
    # Poisoning the generated launcher must not execute on the host.
    (delivery / "app.py").write_text("raise RuntimeError('untrusted')")
    result = capture_dashboard(delivery, tmp_path / "screenshots")
    assert not result["failures"]
    assert len(result["views"]) >= 2 * (len(data["charts"]) + 2)
    assert "mobile: workbook download and source values" in result["checks"]
    assert all((tmp_path / "screenshots" / v["file"]).stat().st_size > 1000 for v in result["views"])
    from PIL import Image

    # Regression: element screenshots were tall blank canvases clipped by Streamlit's inner scroller.
    assert all(Image.open(tmp_path / "screenshots" / v["file"]).height == 900 for v in result["views"])
