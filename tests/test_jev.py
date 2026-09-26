"""Offline LangChain/Jev workflow contract tests using synthetic review text only."""
from __future__ import annotations

import json
import os
import sys
from decimal import Decimal
import unittest
import uuid
from unittest.mock import patch
from pathlib import Path
from types import SimpleNamespace

import psycopg
from psycopg.conninfo import conninfo_to_dict

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from runtime.bootstrap import __file__ as _bootstrap_file  # noqa: E402,F401
from runtime.jev import answer_payload, build_questions, process_review_ids, record_correction, request_id, usage_counts  # noqa: E402
from runtime.signals import build_signal_snapshot, compare_signal_snapshots  # noqa: E402


class Answer:
    def __init__(self, **values): self.values = values
    def model_dump(self, mode="python"): return self.values


class Primitive:
    def __init__(self, **values): self.values = values


class FakeClassifier:
    question_types = SimpleNamespace(Noul=Primitive, Choice=Primitive, Score=Primitive)
    def __init__(self): self.calls = 0
    def invoke(self, request):
        self.calls += 1
        assert set(request) == {"state", "questions"}
        return SimpleNamespace(
            nouls={"mentions_delivery_problem": Answer(type="noul", noul=0.92)},
            choices={"primary_expressed_theme": Answer(type="choice", choice="delivery", confidence=0.8, probabilities={"delivery": 0.8, "other_or_unclear": 0.2})},
            scores={"reported_experience_severity": Answer(type="score", score=1.7, probabilities={"1": 0.3, "2": 0.7})},
            model="jev-test-fixture", request_id=f"fake-{self.calls}",
            usage=SimpleNamespace(input_tokens=120, output_tokens=24),
        )


class JevPipelineTests(unittest.IsolatedAsyncioTestCase):
    @classmethod
    def setUpClass(cls):
        cls.test_dsn = os.environ.get("BACKINTEL_TEST_DATABASE_URL")
        if not cls.test_dsn:
            raise RuntimeError("BACKINTEL_TEST_DATABASE_URL is required; refusing to use the application database")
        database = conninfo_to_dict(cls.test_dsn).get("dbname", "")
        if not (database.endswith("_test") or database.startswith("test_")):
            raise RuntimeError("Refusing destructive setup: Jev tests require a test-named database")

    async def asyncSetUp(self):
        os.environ["BACKINTEL_APP_DATABASE_URL"] = self.test_dsn
        with psycopg.connect(self.test_dsn) as conn:
            conn.execute("DROP SCHEMA IF EXISTS backintel CASCADE")
            conn.execute("CREATE SCHEMA backintel")
            conn.execute("CREATE TABLE backintel.source_batches (batch_id uuid primary key, file_sha256 char(64) not null)")
            conn.execute("CREATE TABLE backintel.source_records (batch_id uuid, source_row_number bigint, primary key(batch_id, source_row_number))")
            conn.execute("""CREATE TABLE backintel.reviews (
                review_record_id bigint primary key, message text, source_batch_id uuid,
                source_row_number bigint, order_id text)""")
            conn.execute("CREATE TABLE backintel.order_items (order_id text, seller_id text, product_id text)")
            conn.execute("CREATE TABLE backintel.products (product_id text primary key, category_name text)")
            conn.execute("INSERT INTO backintel.products VALUES ('p1','home'), ('p2','home')")
            conn.execute("INSERT INTO backintel.order_items VALUES ('o1','s1','p1'), ('o2','s1','p2')")
            conn.execute("""INSERT INTO backintel.source_batches VALUES
                ('00000000-0000-0000-0000-000000000001', repeat('a',64))""")
            conn.execute("""INSERT INTO backintel.source_records VALUES
                ('00000000-0000-0000-0000-000000000001', 17),
                ('00000000-0000-0000-0000-000000000001', 18)""")
            conn.execute("""INSERT INTO backintel.reviews VALUES
                (1, 'A entrega demorou muito.', '00000000-0000-0000-0000-000000000001', 17, 'o1'),
                (2, 'O produto chegou rápido.', '00000000-0000-0000-0000-000000000001', 18, 'o2')""")
            migration_dir = ROOT / "migrations"
            for name in ("0002_partition_results.sql", "0003_usage_events.sql", "0004_jev_observations.sql", "0005_semantic_signal_snapshots.sql", "0006_signal_definition_version.sql"):
                conn.execute((migration_dir / name).read_text(), prepare=False)

    async def test_observation_lineage_usage_and_replay_are_persisted(self):
        fake = FakeClassifier()
        kwargs = {"partition_id": "synthetic-jevtst", "review_record_ids": [1], "classifier": fake}
        first = await process_review_ids(**kwargs)
        second = await process_review_ids(**kwargs)
        observation_id = first["observations"][0]["observation_id"]
        await record_correction(observation_id=observation_id, corrected_by="fixture-reviewer",
                                corrected_answers={"mentions_delivery_problem": False},
                                rationale="Synthetic test correction")
        self.assertEqual(fake.calls, 1)
        self.assertFalse(first["observations"][0]["reused"])
        self.assertTrue(second["observations"][0]["reused"])
        self.assertEqual(first["result_sha256"], second["result_sha256"])
        with psycopg.connect(self.test_dsn) as conn:
            observations = conn.execute("""SELECT count(*), min(source_language), min(model), min(request_id)
                FROM backintel.jev_observations""").fetchone()
            usage = conn.execute("""SELECT count(*), min(stage), min(input_tokens), min(output_tokens),
                min(outcome), min(charge_status) FROM backintel.usage_events""").fetchone()
            partition = conn.execute("SELECT disposition FROM backintel.partition_results WHERE partition_id=%s", (kwargs["partition_id"],)).fetchone()
        self.assertEqual(observations, (1, "pt-BR-assumed-from-dataset", "jev-test-fixture", "fake-1"))
        self.assertEqual(usage, (1, "jev", 120, 24, "success", "unknown"))
        self.assertEqual(partition, ("accepted",))
        with psycopg.connect(self.test_dsn) as conn:
            original, correction_count = conn.execute("""SELECT o.answers, (SELECT count(*) FROM backintel.jev_observation_corrections c WHERE c.observation_id=o.observation_id)
                FROM backintel.jev_observations o WHERE o.observation_id=%s""", (uuid.UUID(observation_id),)).fetchone()
            self.assertEqual(original["mentions_delivery_problem"]["noul"], 0.92)
            self.assertEqual(correction_count, 1)
            with self.assertRaises(psycopg.errors.RaiseException):
                with conn.transaction():
                    conn.execute("UPDATE backintel.jev_observations SET answers='{}'::jsonb WHERE observation_id=%s", (uuid.UUID(observation_id),))

    async def test_missing_provider_credential_stops_before_any_call(self):
        with patch.dict(os.environ, {"OPENROUTER_API_KEY": ""}):
            with self.assertRaisesRegex(RuntimeError, "OPENROUTER_API_KEY is not configured"):
                await process_review_ids(partition_id="no-credential", review_record_ids=[1])
        with psycopg.connect(self.test_dsn) as conn:
            count = conn.execute("SELECT count(*) FROM backintel.usage_events").fetchone()[0]
        self.assertEqual(count, 0)

    async def test_openrouter_system_one_route_uses_key_and_preserves_usage_cost(self):
        import httpx2
        from langchain_typesafe import Noul
        from runtime.jev import OpenRouterJevClassifier
        seen = {}
        def responder(request):
            seen["url"] = str(request.url)
            seen["auth"] = request.headers.get("Authorization")
            payload = json.loads(request.content)
            seen["model"] = payload["model"]
            return httpx2.Response(200, json={
                "id": "gen-test-123", "provider": "TypeSafe", "model": "typesafe/jev-1.13-test",
                "answers": {"delivery": {"type": "noul", "noul": 0.75}},
                "usage": {"input_tokens": 20, "output_tokens": 5, "cost": 0.00000123},
            })
        classifier = OpenRouterJevClassifier(api_key="test-openrouter-key", transport=httpx2.MockTransport(responder))
        try:
            response = classifier.invoke({"state": "A review", "questions": {"delivery": Noul(instructions="Does it mention delivery?")}})
            self.assertEqual(response.nouls["delivery"].noul, 0.75)
            self.assertEqual(seen["url"], "https://openrouter.ai/api/v1/systemone")
            self.assertEqual(seen["auth"], "Bearer test-openrouter-key")
            self.assertEqual(seen["model"], "jev-1.13")
            self.assertEqual(classifier.last_metadata["request_id"], "gen-test-123")
            self.assertEqual(classifier.last_metadata["cost_usd"], 0.00000123)
        finally:
            await classifier.aclose()

    async def test_installed_typesafe_package_contract_is_compatible(self):
        from langchain_typesafe import Choice, Noul, Score
        from langchain_typesafe.classifier import ClassifierResponse
        from runtime.jev import load_question_set
        definition, _ = load_question_set()
        questions = build_questions(definition, SimpleNamespace(Noul=Noul, Choice=Choice, Score=Score))
        self.assertEqual(set(questions), set(definition["questions"]))
        self.assertEqual([type(questions[k]).__name__ for k in questions], ["Noul", "Noul", "Choice", "Score"])
        response = ClassifierResponse.model_validate({
            "model": "jev-test-fixture", "request_id": "req-test-1",
            "usage": {"input_tokens": 12, "output_tokens": 7},
            "answers": {
                "delivery": {"type": "noul", "noul": 0.8},
                "theme": {"type": "choice", "choice": "delivery", "probabilities": {"delivery": 0.8, "other": 0.2}, "confidence": 0.6},
                "severity": {"type": "score", "score": 1.5, "legend": {0: "none", 1: "minor", 2: "major"}, "probabilities": {0: 0.1, 1: 0.3, 2: 0.6}, "confidence": 0.5},
            },
        })
        payload = answer_payload(response)
        self.assertEqual(set(payload), {"delivery", "theme", "severity"})
        self.assertEqual(usage_counts(response), (12, 7))
        self.assertEqual(request_id(response), "req-test-1")

    async def test_new_review_batch_produces_traceable_changed_signal(self):
        class ChangingClassifier(FakeClassifier):
            def invoke(self, request):
                self.calls += 1
                value = 0.2 if "demorou" in request["state"] else 0.8
                return SimpleNamespace(
                    nouls={"mentions_delivery_problem": Answer(type="noul", noul=value),
                           "mentions_product_problem": Answer(type="noul", noul=0.1)},
                    choices={"primary_expressed_theme": Answer(type="choice", choice="delivery" if value < 0.5 else "positive_or_no_problem", confidence=0.6, probabilities={"delivery": value, "positive_or_no_problem": 1-value})},
                    scores={"reported_experience_severity": Answer(type="score", score=value*2, probabilities={"1": 0.5, "2": 0.5})},
                    model="jev-test-fixture", request_id=f"changed-{self.calls}", usage=SimpleNamespace(input_tokens=10, output_tokens=5))
        old_classifier, new_classifier = ChangingClassifier(), ChangingClassifier()
        await process_review_ids(partition_id="review-month-old", review_record_ids=[1], classifier=old_classifier)
        old_snapshot = await build_signal_snapshot("review-month-old")
        await process_review_ids(partition_id="review-month-new", review_record_ids=[2], classifier=new_classifier)
        new_snapshot = await build_signal_snapshot("review-month-new")
        result = await compare_signal_snapshots("review-month-old", "review-month-new")
        self.assertEqual(old_snapshot["snapshot_count"], 3)
        self.assertEqual(new_snapshot["snapshot_count"], 3)
        self.assertEqual(result["shared_entities_compared"], 3)
        marketplace = next(row for row in result["findings"] if row["entity_type"] == "marketplace")
        self.assertEqual(marketplace["mean_model_probability_delta_points"], 60.0)
        self.assertIn("not an observed complaint rate", marketplace["interpretation"])

    async def test_unknown_category_and_multiple_sellers_are_not_attributed(self):
        with psycopg.connect(self.test_dsn) as conn:
            conn.execute("INSERT INTO backintel.products VALUES ('unknown', NULL)")
            conn.execute("INSERT INTO backintel.order_items VALUES ('o1','s1','unknown'), ('o2','s2','p1')")
        await process_review_ids(partition_id="ambiguous", review_record_ids=[1, 2], classifier=FakeClassifier())
        snapshot = await build_signal_snapshot("ambiguous")
        scopes = {(s["entity_type"], s["entity_key"]): s["review_count"] for s in snapshot["snapshots"]}
        self.assertEqual(scopes, {("marketplace", "*"): 2, ("seller", "s1"): 1})
        self.assertEqual(snapshot["signal_version"], "review-signals-v2")
        self.assertEqual(snapshot, await build_signal_snapshot("ambiguous"))

    async def test_recorded_replay_needs_no_credential_and_never_calls_provider(self):
        fake = FakeClassifier()
        await process_review_ids(partition_id="recorded", review_record_ids=[1], classifier=fake)
        with patch.dict(os.environ, {"OPENROUTER_API_KEY": ""}):
            with patch("runtime.jev.OpenRouterJevClassifier", side_effect=AssertionError("Provider forbidden")):
                replay = await process_review_ids(partition_id="recorded", review_record_ids=[1], reuse_only=True)
                with self.assertRaisesRegex(ValueError, "Recorded observation missing"):
                    await process_review_ids(partition_id="absent-recording", review_record_ids=[2], reuse_only=True)
        self.assertEqual(replay["reused_observations"], 1)
        self.assertEqual(fake.calls, 1)
        with psycopg.connect(self.test_dsn) as conn:
            self.assertEqual(conn.execute("SELECT count(*) FROM backintel.usage_events").fetchone()[0], 1)

    async def test_provider_failure_is_recorded_as_unknown_cost(self):
        class FailingClassifier(FakeClassifier):
            def invoke(self, request):
                self.calls += 1
                raise RuntimeError("synthetic provider failure")
        with self.assertRaisesRegex(RuntimeError, "synthetic provider failure"):
            await process_review_ids(partition_id="provider-failure", review_record_ids=[1], classifier=FailingClassifier())
        with psycopg.connect(self.test_dsn) as conn:
            row = conn.execute("SELECT outcome, charge_status FROM backintel.usage_events WHERE partition_id='provider-failure'").fetchone()
            observations = conn.execute("SELECT count(*) FROM backintel.jev_observations WHERE partition_id='provider-failure'").fetchone()[0]
        self.assertEqual(row, ("error", "unknown"))
        self.assertEqual(observations, 0)

    async def test_openrouter_reported_charge_is_saved_to_usage_ledger(self):
        import httpx2
        from runtime.jev import OpenRouterJevClassifier
        def responder(request):
            return httpx2.Response(200, json={
                "id": "gen-cost-456", "provider": "TypeSafe", "model": "typesafe/jev-1.13-test",
                "answers": {
                    "mentions_delivery_problem": {"type": "noul", "noul": 0.8},
                    "mentions_product_problem": {"type": "noul", "noul": 0.1},
                    "primary_expressed_theme": {"type": "choice", "choice": "delivery", "probabilities": {"delivery": 0.8, "product_condition_or_function": 0.1, "seller_service_or_communication": 0.0, "positive_or_no_problem": 0.0, "other_or_unclear": 0.1}, "confidence": 0.5},
                    "reported_experience_severity": {"type": "score", "score": 1.8, "legend": {0: "none", 1: "minor", 2: "material"}, "probabilities": {0: 0.0, 1: 0.2, 2: 0.8}, "confidence": 0.4},
                },
                "usage": {"input_tokens": 100, "output_tokens": 10, "cost": 0.0000042},
            })
        classifier = OpenRouterJevClassifier(api_key="test-openrouter-key", transport=httpx2.MockTransport(responder))
        try:
            await process_review_ids(partition_id="openrouter-cost", review_record_ids=[1], classifier=classifier)
        finally:
            await classifier.aclose()
        with psycopg.connect(self.test_dsn) as conn:
            usage = conn.execute("""SELECT provider, model, request_id, input_tokens, output_tokens, charge_status, charge_usd
                FROM backintel.usage_events WHERE partition_id='openrouter-cost'""").fetchone()
        self.assertEqual(usage, ("openrouter", "typesafe/jev-1.13-test", "gen-cost-456", 100, 10, "measured", Decimal("0.000004200")) )

    async def test_measurement_version_cannot_be_mutated_in_place(self):
        await process_review_ids(partition_id="version-check", review_record_ids=[1], classifier=FakeClassifier())
        path = ROOT / "config" / "review_measurements.v1.json"
        original = path.read_text()
        changed = path.with_name("review_measurements.test-mutated.json")
        try:
            import json
            definition = json.loads(original)
            definition["questions"]["mentions_delivery_problem"]["instructions"] += " Changed."
            changed.write_text(json.dumps(definition))
            with self.assertRaisesRegex(ValueError, "increment its version"):
                await process_review_ids(partition_id="version-check-2", review_record_ids=[1],
                                         classifier=FakeClassifier(), definition_path=changed)
        finally:
            changed.unlink(missing_ok=True)
