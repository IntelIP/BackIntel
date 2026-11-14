"""Bounded visual critique and presentation revision, independent of analysis correctness."""

from __future__ import annotations

import asyncio
import base64
import hashlib
import json
import math
import time
from pathlib import Path

from langchain_core.messages import HumanMessage, SystemMessage
from langsmith import trace

from backintel.bench.usage import PlanRunBudget, UsageTracker
from backintel.presentation.capture import capture_dashboard_async
from backintel.presentation.dashboard import LAUNCHER, workbook_bytes
from backintel.presentation.design import DesignPlan, DesignReview, validate_plan

PROMPT_PATH = Path(__file__).parents[1] / "agent_files" / "docs" / "dashboard-review.md"
DEFAULT_REVIEWER = "anthropic/claude-haiku-5-5"


def _messages(instruction: str, payload: dict, capture: dict, folder: Path):
    text = json.dumps(payload, ensure_ascii=False)
    if len(text.encode()) > 250_000:
        raise ValueError("Review context exceeds 250 KB; prepare a smaller aggregate report.")
    content = [{"type": "text", "text": text}]
    total = 0
    for view in capture["views"]:
        image = (folder / view["file"]).read_bytes()
        total += len(image)
        if total > 24_000_000:
            raise ValueError("Screenshots exceed the 24 MB review limit.")
        content.extend(
            [
                {"type": "text", "text": "Rendered view: " + view["name"]},
                {
                    "type": "image_url",
                    "image_url": {"url": "data:image/png;base64," + base64.b64encode(image).decode()},
                },
            ]
        )
    return [SystemMessage(content=instruction), HumanMessage(content=content)]


async def _call(model, schema, instruction, payload, capture, folder, usage, name):
    attachments = {
        Path(v["file"]).stem: ("image/png", (folder / v["file"]).read_bytes()) for v in capture["views"]
    }
    async with trace(
        name, inputs={"brief": payload["brief"], "checks": capture["checks"]}, attachments=attachments
    ) as run:
        method = "json_schema" if schema is DesignReview else "function_calling"
        value = await model.with_structured_output(schema, method=method, include_raw=True).ainvoke(
            _messages(instruction, payload, capture, folder), config={"callbacks": [usage]}
        )
        parsed = parse_response(value, schema)
        if schema is DesignReview:
            parsed.checked({v["name"] for v in capture["views"]})
        run.end(outputs=parsed.model_dump())
        # Standard LANGSMITH_TRACING controls upload; the application never enables it implicitly.
        from langsmith.utils import tracing_is_enabled

        if schema is DesignReview and tracing_is_enabled() is True:
            from langsmith import AsyncClient

            async with AsyncClient() as client:
                session_id = run.session_id or (await client.read_project(project_name=run.session_name)).id
                for rating in parsed.ratings:
                    await client.create_feedback(
                        run_id=run.id,
                        session_id=session_id,
                        key="dashboard_" + rating.criterion,
                        score=rating.score,
                        comment=rating.evidence,
                    )
                await client.create_feedback(
                    run_id=run.id,
                    session_id=session_id,
                    key="dashboard_accepted",
                    score=parsed.passed and not capture["failures"],
                )
    return parsed


def parse_response(value, schema):
    """Plan transport cannot force a tool call; accept schema-valid final JSON too."""
    if isinstance(value, dict) and "raw" in value:
        if value.get("parsed") is not None:
            return schema.model_validate(value["parsed"])
        raw = value["raw"]
        for call in raw.tool_calls:
            if call["name"].split(".")[-1] == schema.__name__:
                return schema.model_validate(call["args"])
        content = raw.content
        text = (
            content
            if isinstance(content, str)
            else "".join(
                block.get("text", "")
                for block in content
                if isinstance(block, dict) and block.get("type") == "text"
            )
        )
        text = text.strip()
        if text.startswith("```json\n") and text.endswith("```"):
            text = text[8:-3].strip()
        return schema.model_validate_json(text)
    return schema.model_validate(value)


def review_dashboard(directory: Path, output: Path, **kwargs) -> dict:
    """Synchronous CLI entry point; async callers await review_dashboard_async directly."""
    return asyncio.run(review_dashboard_async(directory, output, **kwargs))


async def review_dashboard_async(
    directory: Path,
    output: Path,
    *,
    brief: str,
    reviewer,
    reviser,
    reviewer_id: str,
    reviser_id: str,
    max_revisions: int = 2,
    capture=capture_dashboard_async,
    timeout_s: float = 900,
) -> dict:
    """Initial review + at most two revisions. Never overwrite the original delivery.

    Inputs are retained aggregates, never executable output. Failed capture/provider/schema
    checks cannot pass. The best assessed candidate remains available even after a failure.
    The immutable benchmark and numerical analysis are not rerun by this process.
    """
    started = time.monotonic()
    if not math.isfinite(timeout_s) or timeout_s <= 0:
        raise TimeoutError("No analysis time remains for dashboard review.")
    if type(max_revisions) is not int or not 0 <= max_revisions <= 2:
        raise ValueError("max_revisions must be 0, 1 or 2.")
    if not reviewer_id.startswith("anthropic/") or not reviser_id.startswith(("chatgpt-plan/", "openai/")):
        raise ValueError(
            "Use a native Anthropic reviewer and an OpenAI/ChatGPT writer of a different family."
        )
    if any(getattr(m, "max_retries", 0) != 0 for m in (reviewer, reviser)):
        raise ValueError("Provider retries must be disabled for the bounded design loop.")
    if not brief.strip() or len(brief) > 12000:
        raise ValueError("Supply a business brief of 1–12000 characters.")
    directory, output = Path(directory), Path(output)
    source = (directory / "dashboard.json").read_bytes()
    if len(source) > 250_000:
        raise ValueError("Review requires aggregate dashboard data smaller than 250 KB.")
    data = json.loads(source)
    if not data.get("charts"):
        raise ValueError("Visual review requires at least one chart.")
    original_plan = directory / "presentation.json"
    plan = validate_plan(json.loads(original_plan.read_text()), data) if original_plan.exists() else None
    if output.exists():
        raise ValueError("Use a new review output directory; previous reviews are preserved.")
    output.mkdir(parents=True, mode=0o700)
    reviewer_usage = UsageTracker()
    reviser_usage = UsageTracker(
        PlanRunBudget(max(1, max_revisions)) if reviser_id.startswith("chatgpt-plan/") else None
    )
    rules = PROMPT_PATH.read_text()
    record = {
        "status": "review_error",
        "ready": False,
        "max_revisions": max_revisions,
        "reviewer": reviewer_id,
        "reviser": reviser_id,
        "rounds": [],
        "selected": None,
        "score_meaning": "Automated rubric judgment, not human-calibrated design certification",
        "input_sha256": hashlib.sha256(source).hexdigest(),
        "rubric_sha256": hashlib.sha256(rules.encode()).hexdigest(),
    }
    best = None
    try:
        async with asyncio.timeout(max(0, timeout_s - (time.monotonic() - started))):
            for attempt in range(max_revisions + 1):
                if time.monotonic() - started >= timeout_s:
                    raise TimeoutError("Whole-run deadline reached during dashboard review.")
                folder = output / f"candidate-{attempt}"
                folder.mkdir()
                (folder / "dashboard.json").write_bytes(source)
                (folder / "app.py").write_text(LAUNCHER)
                if attempt:
                    prior = best
                    plan = await _call(
                        reviser,
                        DesignPlan,
                        rules + "\nROLE: Revise the presentation using the specific review feedback. "
                        "Return only a DesignPlan. Keep every chart exactly once. No numerical, table, "
                        "unit, binding or source edits. Retain useful sections; fix demonstrated weaknesses.",
                        {
                            "brief": brief,
                            "data": data,
                            "current_plan": prior["plan"],
                            "review": prior["review"].model_dump(),
                            "browser_failures": prior["capture"]["failures"],
                        },
                        prior["capture"],
                        prior["folder"] / "screenshots",
                        reviser_usage,
                        "dashboard.revise",
                    )
                    plan = validate_plan(plan.model_dump(), data)
                if plan:
                    (folder / "presentation.json").write_text(plan.model_dump_json(indent=2))
                (folder / "analysis.xlsx").write_bytes(workbook_bytes(data, plan))
                evidence = await capture(folder, folder / "screenshots")
                if not evidence["views"]:
                    raise ValueError("No rendered views were captured; visual review cannot proceed.")
                assessed = await _call(
                    reviewer,
                    DesignReview,
                    rules + "\nROLE: Independent visual reviewer. Inspect every supplied screenshot "
                    "and the interaction checks. Cite view names as evidence. Grade before seeing any "
                    "previous score. Use blocking_issues for misleading claims/labels, hidden material "
                    "limitations or unusable content. Propose concrete revisions. Do not reward verbosity.",
                    {
                        "brief": brief,
                        "verified_data": data,
                        "plan": plan.model_dump() if plan else None,
                        "browser_checks": evidence,
                    },
                    evidence,
                    folder / "screenshots",
                    reviewer_usage,
                    "dashboard.review",
                )
                passed = assessed.passed and not evidence["failures"]
                current = {
                    "folder": folder,
                    "plan": plan.model_dump() if plan else None,
                    "review": assessed,
                    "capture": evidence,
                    "quality": (-len(evidence["failures"]), *assessed.quality),
                }
                if best is None or current["quality"] > best["quality"]:
                    best = current
                record["rounds"].append(
                    {
                        "candidate": folder.name,
                        "review": assessed.model_dump(),
                        "browser": evidence,
                        "passed": passed,
                    }
                )
                record["selected"] = str(best["folder"].resolve())
                record["status"] = "needs_revision"
                if passed:
                    record.update(status="passed", ready=True, selected=str(folder.resolve()))
                    break
    except asyncio.CancelledError:
        record.update(status="cancelled", ready=False, error="Dashboard review cancelled.")
        raise
    except Exception as error:
        record.update(
            status="timed_out" if isinstance(error, TimeoutError) else "review_error",
            ready=False,
            error_type=type(error).__name__,
            error="Review stopped before acceptance. The retained candidate is provisional.",
        )
        # Local detailed errors help repair the runner; avoid retaining provider error bodies.
        if isinstance(error, (ValueError, TimeoutError)):
            record["detail"] = str(error)[:1200]
    finally:
        record["usage"] = {"reviewer": reviewer_usage.report(), "reviser": reviser_usage.report()}
        record["latency_s"] = round(time.monotonic() - started, 3)
        (output / "review.json").write_text(json.dumps(record, indent=2))
    return record
