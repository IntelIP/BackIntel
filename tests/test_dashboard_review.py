"""Presentation invariants, bounded revisions and real browser capture; no provider calls."""

import asyncio
import copy
import json
import time
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

    async def ainvoke(self, messages, **kwargs):
        self.inputs.append(messages)
        self.calls += 1
        value = self.values.pop(0)
        if isinstance(value, Exception):
            raise value
        return value


async def captured(directory, output):
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
    assert json.loads(reviewer.inputs[0][1].content[0]["text"])["verified_data"]["sources"] == data["sources"]
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

    async def browser(directory, output):
        result = await captured(directory, output)
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


def test_designed_dashboard_real_browser_and_download(delivery, tmp_path, monkeypatch):
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
    # A valid section and chart can share a title (h2 vs h3).
    presentation["sections"][0]["charts"][0]["title"] = presentation["sections"][0]["title"]
    presentation["sections"][0]["charts"][0]["reading_guide"] = "Each mark compares one retained group."
    presentation["sections"][0]["charts"].extend(presentation["sections"].pop(1)["charts"])
    presentation["sections"][0]["columns"] = 2
    (delivery / "presentation.json").write_text(json.dumps(presentation))
    # Poisoning the generated launcher must not execute on the host.
    (delivery / "app.py").write_text("raise RuntimeError('untrusted')")
    monkeypatch.chdir(tmp_path)  # No repository Streamlit configuration is available.
    result = capture_dashboard(delivery, tmp_path / "screenshots")
    assert not result["failures"]
    assert len(result["views"]) >= 2 * (len(presentation["sections"]) + 2)
    assert "mobile: workbook download and source values" in result["checks"]
    assert all((tmp_path / "screenshots" / v["file"]).stat().st_size > 1000 for v in result["views"])
    from PIL import Image

    # Regression: element screenshots were tall blank canvases clipped by Streamlit's inner scroller.
    assert all(Image.open(tmp_path / "screenshots" / v["file"]).height == 900 for v in result["views"])


@pytest.mark.parametrize("field", ["title", "section", "chart", "x_label", "y_label", "coverage"])
def test_whitespace_only_presentation_labels_are_rejected(delivery, field):
    data = json.loads((delivery / "dashboard.json").read_text())
    plan = plan_for(data)
    plan["context"] = dict(
        audience="Manager",
        decision="Investigate demand",
        coverage="Retained data",
        limitation="Historical only",
    )
    target, key = {
        "title": (plan, "title"),
        "section": (plan["sections"][0], "title"),
        "chart": (plan["sections"][0]["charts"][0], "title"),
        "x_label": (plan["sections"][0]["charts"][0], "x_label"),
        "y_label": (plan["sections"][0]["charts"][0], "y_label"),
        "coverage": (plan["context"], "coverage"),
    }[field]
    target[key] = " \t\n "
    with pytest.raises(ValueError):
        validate_plan(plan, data)


@pytest.mark.parametrize(
    "name", [" Explore ", " About the data ", " What does business comparison 2 show us? "]
)
def test_section_names_are_normalized_before_uniqueness_checks(delivery, name):
    data = json.loads((delivery / "dashboard.json").read_text())
    plan = plan_for(data)
    plan["sections"][0]["title"] = name
    with pytest.raises(ValueError, match="unique"):
        validate_plan(plan, data)


@pytest.mark.parametrize("stage", ["capture", "reviewer", "writer"])
def test_deadline_cancels_current_stage_and_prevents_more_calls(delivery, tmp_path, stage):
    stopped = []

    async def stall():
        try:
            await asyncio.sleep(60)
        finally:
            stopped.append(stage)

    class SlowModel(Scripted):
        async def ainvoke(self, messages, **kwargs):
            self.calls += 1
            await stall()
            raise AssertionError("A timed-out request must not finish normally")

    async def browser(directory, output):
        if stage == "capture":
            await stall()
        return await captured(directory, output)

    reviewer = SlowModel() if stage == "reviewer" else Scripted(rating(2))
    writer = SlowModel()
    started = time.monotonic()
    # Allow workbook/trace setup on CI before cancelling the deliberately stalled stage.
    result = run_loop(delivery, tmp_path, reviewer, writer, capture=browser, timeout_s=2)
    assert time.monotonic() - started < 5
    assert result["status"] == "timed_out" and not result["ready"]
    assert stopped == [stage]
    assert reviewer.calls == (0 if stage == "capture" else 1)
    assert writer.calls == (1 if stage == "writer" else 0)
    if stage == "writer":
        assert result["selected"].endswith("candidate-0")
    assert json.loads((tmp_path / "review/review.json").read_text())["status"] == "timed_out"


def test_cancelled_capture_closes_owned_preview_server(delivery, monkeypatch):
    pytest.importorskip("streamlit")
    from backintel.presentation import capture

    processes = []
    original = capture.subprocess.Popen

    def spawn(*args, **kwargs):
        import tomllib

        settings = tomllib.loads((Path(__file__).parents[1] / ".streamlit/config.toml").read_text())
        command = args[0]
        for section in ("theme", "client"):
            for key, value in settings[section].items():
                expected = str(value).lower() if isinstance(value, bool) else str(value)
                assert command[command.index(f"--{section}.{key}") + 1] == expected
        process = original(*args, **kwargs)
        processes.append(process)
        return process

    monkeypatch.setattr(capture.subprocess, "Popen", spawn)

    async def run():
        with pytest.raises(TimeoutError):
            async with asyncio.timeout(0.15):
                async with capture.dashboard_server(delivery):
                    await asyncio.sleep(60)

    asyncio.run(run())
    assert processes and all(p.poll() is not None for p in processes)


def test_capture_waits_for_a_later_chart_to_render():
    pytest.importorskip("playwright")
    from playwright.async_api import async_playwright

    from backintel.presentation.capture import _wait_for_charts

    async def run():
        async with async_playwright() as p:
            browser = await p.chromium.launch()
            try:
                page = await browser.new_page()
                await page.set_content(
                    '<div class="chart"><svg class="main-svg"></svg></div><div class="chart" id="later"></div>'
                )
                await page.evaluate("""setTimeout(() => {
                    document.getElementById('later').innerHTML = '<svg class="main-svg"></svg>';
                }, 500)""")
                await _wait_for_charts(page.locator(".chart"), 2)
                assert await page.locator("#later .main-svg").count() == 1
            finally:
                await browser.close()

    asyncio.run(run())


@pytest.mark.parametrize("complete", [False, True])
def test_passing_review_requires_every_desktop_and_mobile_capture(delivery, tmp_path, complete):
    review = rating(4)
    if complete:
        review.ratings[-1].views.append("mobile/Story")

    async def two_views(directory, output):
        result = await captured(directory, output)
        result["views"].append({"name": "mobile/Story", "file": "desktop.png"})
        return result

    result = run_loop(delivery, tmp_path, Scripted(review), Scripted(), capture=two_views, max_revisions=0)
    assert result["ready"] is complete
    if not complete:
        assert result["status"] == "review_error"
        assert "every supplied screenshot" in result["detail"]


def test_review_only_cli_needs_no_writer_credentials(delivery, tmp_path, monkeypatch):
    from types import SimpleNamespace

    from backintel import cli, models
    from backintel.presentation import review

    reviewer = Scripted(rating(4))
    monkeypatch.setattr(models, "build_dashboard_reviewer", lambda _: reviewer)

    def forbidden_writer(*args, **kwargs):
        pytest.fail("Review-only mode must not construct or authenticate a writer")

    monkeypatch.setattr(models, "build_model", forbidden_writer)
    monkeypatch.setattr(
        review, "review_dashboard", lambda *a, **kw: review_dashboard(*a, capture=captured, **kw)
    )
    brief = tmp_path / "brief.txt"
    brief.write_text("Explain the operating pattern.")
    cli.cmd_dashboard(
        SimpleNamespace(
            action="review",
            directory=str(delivery),
            output=str(tmp_path / "review"),
            brief=str(brief),
            reviewer_model="anthropic/claude-haiku-5-5",
            writer_model=None,
            max_revisions=0,
        ),
        SimpleNamespace(analysis_model="unused/writer"),
    )
    record = json.loads((tmp_path / "review/review.json").read_text())
    assert record["ready"] and record["reviser"] is None and reviewer.calls == 1


@pytest.mark.parametrize("failure", ["project", "feedback"])
def test_feedback_upload_failure_preserves_local_assessment(delivery, tmp_path, monkeypatch, failure):
    from contextlib import asynccontextmanager
    from types import SimpleNamespace

    import langsmith
    import langsmith.utils

    from backintel.presentation import review

    @asynccontextmanager
    async def local_trace(*args, **kwargs):
        yield SimpleNamespace(id="run", session_id=None, session_name="project", end=lambda **kw: None)

    calls = []

    class UnavailableFeedback:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            pass

        async def read_project(self, **kwargs):
            calls.append("project")
            if failure == "project":
                raise RuntimeError("private service error")
            return SimpleNamespace(id="project")

        async def create_feedback(self, **kwargs):
            calls.append("feedback")
            raise RuntimeError("private service error")

    monkeypatch.setattr(review, "trace", local_trace)
    monkeypatch.setattr(langsmith.utils, "tracing_is_enabled", lambda: True)
    monkeypatch.setattr(langsmith, "AsyncClient", UnavailableFeedback)
    result = run_loop(delivery, tmp_path, Scripted(rating(4)), None, max_revisions=0)
    assert failure in calls
    assert result["ready"] and result["status"] == "passed"
    assert result["rounds"][0]["review"]["ratings"][0]["score"] == 4
    assert result["observability_warnings"][0]["error_type"] == "RuntimeError"
    retained = (tmp_path / "review/review.json").read_text()
    assert json.loads(retained)["observability_warnings"] == result["observability_warnings"]
    assert "private service error" not in retained
