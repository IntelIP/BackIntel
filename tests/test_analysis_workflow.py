"""Independent analytical oracle checks; real graph/SmolVM run is explicitly opt-in."""

import asyncio
import copy
import os
import sqlite3

import pytest

from scripts.run_analysis_demo import (
    ANALYSIS_QUERIES,
    create_source,
    independent_reference,
    run_demo,
    run_live,
    verify_reference,
)


def test_independent_reference_catches_duplicate_refund_join_and_wrong_total(tmp_path):
    source = tmp_path / "source.sqlite"
    create_source(source)
    expected = independent_reference(source)
    assert expected["total"]["rows"] == [[135.0]]
    assert expected["categories"]["rows"] == [["Home", 75.0], ["Outdoor", 40.0], ["Essentials", 20.0]]
    with sqlite3.connect(source) as connection:
        tables = []
        for name, query in ANALYSIS_QUERIES.items():
            cursor = connection.execute(query)
            tables.append(
                {
                    "id": name,
                    "columns": [c[0] for c in cursor.description],
                    "rows": [list(row) for row in cursor.fetchall()],
                }
            )
    verify_reference({"tables": tables}, source)
    reordered = copy.deepcopy(tables)
    reordered.reverse()
    for table in reordered:
        table["rows"].reverse()
    verify_reference({"tables": reordered}, source)
    wrong = copy.deepcopy(tables)
    wrong[0]["rows"][0][1] += 1
    with pytest.raises(ValueError, match="independent"):
        verify_reference({"tables": wrong}, source)


def test_failed_report_revision_cannot_publish_previous_success(tmp_path):
    from types import SimpleNamespace

    from backintel.analysis import build_analysis_tools
    from backintel.stores.sqlite import SQLiteStore

    source = tmp_path / "source.sqlite"
    create_source(source)
    retained = {"spec": {"title": "old successful report"}}
    sandbox = SimpleNamespace(env={}, read_file=lambda _: "not valid JSON")
    store = SQLiteStore(source, dataset="revision-check")
    try:
        tool = next(
            t for t in build_analysis_tools(store, sandbox, {}, retained) if t.name == "render_report"
        )
        result = tool.invoke({"spec_path": "/workspace/spec.json"})
        assert "Expecting value" in result
        assert retained == {}
    finally:
        store.close()


def test_live_entry_keeps_references_outside_target_and_failed_runs_ungraded(tmp_path, monkeypatch):
    import backintel.models
    import scripts.run_analysis_demo as demo

    captured = []
    monkeypatch.setattr(backintel.models, "build_model", lambda *args, **kwargs: object())

    async def failed_run(analysis_brief, **kwargs):
        captured.append((analysis_brief.model_dump(), kwargs))
        return {"status": "failed", "error": "SmolVM unavailable", "usage": {"cost_complete": False}}

    monkeypatch.setattr(demo, "run_analysis", failed_run)
    result = run_live(
        tmp_path / "live",
        model_id="openrouter/openai/test-model-not-invoked",
        reasoning="medium",
        max_cost=1,
        reservation=0.1,
    )
    assert len(captured) == 2
    assert captured[0][1]["budget"] is captured[1][1]["budget"]
    assert captured[0][1]["budget"].max_calls == 48
    assert all("135" not in str(analysis_brief) for analysis_brief, _ in captured)
    assert all("scripted" not in kwargs for _, kwargs in captured)
    assert all(scores[1]["score"] is None for scores in result["scores"].values())
    assert result["budget"]["calls"] == 0


@pytest.mark.parametrize("limit,reservation", [(float("nan"), 0.1), (1, float("inf")), (0.1, 1)])
def test_live_entry_rejects_invalid_allowance_before_building_a_provider(
    tmp_path, monkeypatch, limit, reservation
):
    import backintel.models

    def forbidden(*args, **kwargs):
        raise AssertionError("Provider construction must not precede budget validation")

    monkeypatch.setattr(backintel.models, "build_model", forbidden)
    with pytest.raises(ValueError):
        run_live(
            tmp_path / "live",
            model_id="openrouter/openai/test-model-not-invoked",
            reasoning="medium",
            max_cost=limit,
            reservation=reservation,
        )


@pytest.mark.skipif(
    os.environ.get("BACKINTEL_SMOLVM_TESTS") != "1",
    reason="Set BACKINTEL_SMOLVM_TESTS=1 for the real SmolVM/Deep Agents integration.",
)
def test_full_scripted_graph_creates_verified_artifacts_and_refuses_missing_cost(tmp_path):
    result = asyncio.run(run_demo(tmp_path / "demo"))
    assert result["provider_calls"] == 0
    assert result["model_cost_usd"] == 0
    assert result["checks"]["independent_numbers"]
    assert result["checks"]["csv_workbook_consistency"]
    assert result["checks"]["failed_program_then_recovery"]
    assert result["checks"]["wrong_result_control_rejected"]
    assert result["checks"]["missing_cost_refusal"]
    assert result["checks"]["source_unchanged"]
