"""Controlled context and prompt-wiring checks, not live judge calibration."""

import hashlib
import json
import sqlite3
from types import SimpleNamespace

import pytest

from backintel.bench import judge
from backintel.bench.judge_context import build_judge_context, context_version
from backintel.bench.run import Harness
from backintel.contracts import AnalystAnswer, Evidence, Scenario
from backintel.stores.sqlite import SQLiteStore


def test_context_qualifies_actual_development_snapshot_builder(tmp_path):
    from backintel.bench.acceptance import build_acceptance
    from backintel.settings import Settings

    settings = Settings.from_env({"BACKINTEL_DATA_DIR": str(tmp_path / "data")})
    manifests = tmp_path / "manifests"
    suite = build_acceptance(settings, split="development", output=manifests)
    manifest = json.loads(suite.manifest_path.read_text())
    checked = []
    for scenario in suite.scenarios:
        if "temporal" not in scenario.tags:
            continue
        dataset = scenario.store.split(":", 1)[1]
        store = SQLiteStore(settings.stores_dir / "sqlite" / f"{dataset}.sqlite", dataset=dataset)
        try:
            context = build_judge_context(store, scenario.id, manifest_root=manifests)
        finally:
            store.close()
        if "cutoff_exclusive" not in manifest["planted_changes"].get(scenario.id, {}):
            assert context["snapshot"]["status"] == "unknown"
            continue
        assert context["snapshot"]["status"] == "verified"
        assert all(item["column"] != "estimated_at" for item in context["snapshot"]["observations"])
        checked.append(scenario.id)
    assert len(checked) == 6


def snapshot(tmp_path, *, future=False, duplicate=False):
    path = tmp_path / "source.sqlite"
    with sqlite3.connect(path) as con:
        con.execute(
            "CREATE TABLE orders (order_id TEXT, order_purchase_timestamp TEXT, "
            "order_delivered_customer_date TEXT, order_estimated_delivery_date TEXT)"
        )
        row = ("one", "2017-09-01", "2017-10-02" if future else "2017-09-03", "2017-10-05")
        con.executemany("INSERT INTO orders VALUES (?,?,?,?)", [row] * (2 if duplicate else 1))
    return SQLiteStore(path, dataset="olist_asof_2017-09")


@pytest.mark.parametrize("future", [False, True])
def test_actual_snapshot_observations_qualify_declared_cutoff(tmp_path, future):
    store = snapshot(tmp_path, future=future)
    try:
        context = build_judge_context(store, "case", manifest_root=tmp_path / "manifests")
    finally:
        store.close()
    assert context["snapshot"]["status"] == ("not_verified" if future else "verified")
    assert context["snapshot"]["cutoff_exclusive"] == "2017-10-01T00:00:00"
    delivery = context["snapshot"]["observations"][1]
    assert delivery["at_or_after_cutoff"] == int(future)
    assert all(c["column"] != "order_estimated_delivery_date" for c in context["snapshot"]["observations"])
    assert context["version"] == context_version()
    assert len(context["payload_sha256"]) == 64


def test_grain_is_observed_without_inventing_required_joins(tmp_path):
    store = snapshot(tmp_path, duplicate=True)
    try:
        context = build_judge_context(store, "case")
    finally:
        store.close()
    assert context["tables"][0]["row_count"] == 2
    assert context["tables"][0]["key_counts"]["order_id"] == {"non_null": 2, "distinct": 1}
    assert "require a join" in context["limits"]
    assert "sample" not in json.dumps(context)


def test_acceptance_manifest_only_contributes_hash_validated_cutoff(tmp_path):
    store = snapshot(tmp_path)
    store.id = "sqlite:owned-fixture"
    source_hash = hashlib.sha256(store.path.read_bytes()).hexdigest()
    manifest = {
        "worlds": {"case": {"store": store.id, "file_sha256": source_hash}},
        "planted_changes": {"case": {"cutoff_exclusive": "2017-10-01", "raw_future_observations": "SECRET"}},
        "scenarios": [{"expected": "SECRET"}],
        "reference_checks": [{"sql": "SECRET"}],
    }
    path = tmp_path / "development.json"
    path.write_text(json.dumps(manifest))
    try:
        context = build_judge_context(store, "case", manifest_root=tmp_path)
        assert context["snapshot"]["status"] == "verified"
        assert "SECRET" not in json.dumps(context)
        manifest["worlds"]["case"]["file_sha256"] = "wrong"
        path.write_text(json.dumps(manifest))
        with pytest.raises(ValueError, match="does not match"):
            build_judge_context(store, "case", manifest_root=tmp_path)
    finally:
        store.close()


@pytest.mark.parametrize(
    "code",
    [
        "SELECT COUNT(*) FROM orders",
        "SELECT SUM(1) FROM orders",
    ],
)
def test_method_judge_sees_context_and_accepts_alternative_shapes_as_instructions(
    tmp_path, monkeypatch, code
):
    store = snapshot(tmp_path)
    try:
        context = build_judge_context(store, "case")
    finally:
        store.close()
    prompts = []

    class CapturedJudge:
        def with_structured_output(self, schema):
            return self

        def invoke(self, prompt, config):
            prompts.append(prompt)
            return {
                key: {
                    "reason": "Controlled placeholder, not a live judgment",
                    **({"verdict": "none_established"} if key == "caveats_material" else {"rating": 2}),
                }
                for key in judge.RUBRIC
            }

    monkeypatch.setattr(judge, "build_model", lambda *args, **kwargs: CapturedJudge())
    answer = AnalystAnswer(
        status="answered",
        answer_type="number",
        value=1,
        method="Count orders in the bound snapshot.",
        evidence=[Evidence(kind="sql", code=code)],
    )
    judge.judge_answer("Count snapshot orders", answer, model_id="not-invoked", context=context)
    prompt = prompts[0]
    assert code in prompt
    assert '"status": "verified"' in prompt
    assert "does not require a redundant cutoff" in prompt
    assert "Accept mathematically equivalent" in prompt
    assert "Do not invent missing tables, join requirements" in prompt
    assert "2017-10-01T00:00:00" in prompt


def test_harness_passes_evaluator_context_and_records_it_without_changing_numeric_score(
    tmp_path, monkeypatch
):
    from backintel.bench import run

    store = snapshot(tmp_path)
    seen = []
    assessments = {"caveats_material": {"reason": "Controlled category", "verdict": "none_established"}}

    def capture(*args, **kwargs):
        seen.append(kwargs["context"])
        return {"score": 0.5, "comment": "Mock judge only", "criteria": {}, "assessments": assessments}

    monkeypatch.setattr(run, "judge_answer", capture)
    scenario = Scenario(
        id="case", dataset="test", level=6, question="Count snapshot orders", answer_type="number", expected=1
    )
    answer = AnalystAnswer(
        status="answered",
        answer_type="number",
        value=1,
        method="Count orders",
        evidence=[Evidence(kind="sql", code="SELECT COUNT(*) FROM orders")],
    )
    outputs = {"answer": answer.model_dump(), "metrics": {}}
    harness = Harness(SimpleNamespace(judge_model="not-invoked"), store, None, "analyst", None, {})
    try:
        scores = harness.score(scenario, outputs)
        record = harness.record(scenario, outputs, scores)
    finally:
        store.close()
    assert scores["correct"]["score"] == scores["evidence_reproduces"]["score"] == 1
    assert record["judge_context"] == seen[0]
    assert record["judge_assessments"] == assessments
    assert record["scores"]["judge_method"] == 0.5
