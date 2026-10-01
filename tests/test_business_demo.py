"""Check the demo's business claims without provider or model execution."""

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import Mock, patch

from runtime.business_demo import capacity_value, snapshot
from scripts.support_demo import prepare_frontends


class BusinessDemoTests(unittest.TestCase):
    def test_native_rehearsal_is_scoped_and_cannot_complete_the_live_workflow(self):
        from copy import deepcopy
        from runtime.business_demo import attach_workflow_rehearsal

        scopes = ["support-real-rehearsal", "equipment-real-rehearsal"]
        report = {"schema": "backintel-workflow-rehearsal/v1", "demo_id": "business-v1",
                  "source_directory": "/recorded/rehearsal",
                  "submission": {"demo_id": "real-rehearsal", "mode": "synthetic_sources_simulated_models",
                                 "scheduler": "aegra_native_cron"},
                  "integration": {"status": "passed", "model_execution": "simulated_development_only",
                                  "final_real_model_acceptance": "blocked", "errors": [], "pending_triggers": 0,
                                  "jobs": [{"scenario": scope, "state": "completed", "count": 14} for scope in scopes],
                                  "counts": [{"scenario": scope, "kind": "prediction", "count": 22} for scope in scopes],
                                  "replay": {"status": "passed", "before_sha256": "same", "after_sha256": "same",
                                             "evidence_records": 737, "responses": [{"demo_id": "real-rehearsal"}]}}}
        packet = {"demo": {"status": "prepared", "comparisons": [], "stages": [{"id": "refresh", "count": 0}]}}
        before = deepcopy(packet)
        attach_workflow_rehearsal(packet, report, "business-v1")
        self.assertEqual({key: packet["demo"][key] for key in before["demo"]}, before["demo"])
        self.assertEqual(packet["demo"]["workflow_rehearsal"]["scenarios"][0]["completed_jobs"], 14)
        for mutate in (lambda value: value.update(demo_id="another-demo"),
                       lambda value: value["integration"].update(model_execution="actual_models"),
                       lambda value: value["integration"].update(pending_triggers=1),
                       lambda value: value["integration"]["jobs"][0].update(scenario="another-task")):
            invalid = deepcopy(report)
            mutate(invalid)
            with self.assertRaises(ValueError):
                attach_workflow_rehearsal(before, invalid, "business-v1")

    def test_local_results_cannot_complete_the_workflow_or_mix_data_and_fixture_models(self):
        from copy import deepcopy
        from runtime.business_demo import attach_local_predictions, dataset
        from runtime.simulation import digest

        data, _ = dataset("support")
        report = {"schema": "backintel-local-prediction-rehearsal/v1", "demo_id": "business-v1",
                  "dataset_sha256": digest(data), "source_mode": "synthetic", "status": "completed",
                  "feature_set": "structured", "provider_calls": 0, "train_count": 18, "holdout_count": 6,
                  "selected_route": "catboost", "methods": [
                      {"route": route, "feature_set": "structured", "execution": execution, "metrics": {"brier": .2}}
                      for route, execution in (("baseline", "computed_baseline"), ("catboost", "actual_local_model"), ("tabiclv2", "actual_local_model"))]}
        packet = {"demo": {"status": "prepared", "comparisons": [], "stages": [{"id": "prediction", "count": 0}]}}
        attach_local_predictions(packet, report, "business-v1")
        self.assertEqual(packet["demo"]["status"], "prepared")
        self.assertEqual(packet["demo"]["stages"][0]["count"], 0)
        self.assertIn("separate actual local model rehearsal", packet["demo"]["comparison_basis"])
        foreign = {**report, "dataset_sha256": "different-data"}
        with self.assertRaises(ValueError):
            attach_local_predictions(packet, foreign, "business-v1")
        fixture = deepcopy(report)
        fixture["methods"][1]["execution"] = "simulated"
        with self.assertRaises(ValueError):
            attach_local_predictions(packet, fixture, "business-v1")

    def test_recording_frontend_setup_is_repeatable_and_keeps_reviews(self):
        with TemporaryDirectory(prefix="BackIntelRecording") as temporary:
            output = Path(temporary)
            reviews = output / "Reviews.sqlite3"
            reviews.write_bytes(b"existing review records")
            owned = prepare_frontends(output)
            first_css = (owned / "assets/workspace.css").read_text()
            prepare_frontends(output)
            self.assertEqual(first_css, (owned / "assets/workspace.css").read_text())
            self.assertEqual(reviews.read_bytes(), b"existing review records")
            self.assertFalse((owned / ".web").exists())
            self.assertIn('frontend_port=3002', (owned / "rxconfig.py").read_text())

    def packet(self, requests=(), stages=0, jobs=(), triggers=(), sources=()):
        store = Mock(task_id="support-test")
        store.find.side_effect = lambda kind, identity: {"body": {"task": "task", "at": 10}} if identity == "history-v1" else {"body": {"arrival_plans": ["arrival-1", "arrival-2", "arrival-3"]}} if identity == "followups-v1" else None
        store.get.return_value = {"sha256": "task", "body": {"measures": [{"id": "load", "unit": "tickets"}]}}
        store.list.side_effect = lambda kind, *args: [{"available_at": 10 + index} for index in range(stages)] if kind == "real_stage_result" else []
        with patch("runtime.contracts.current_sources", return_value=sources):
            self.last_packet = snapshot(store, jobs, requests, triggers)
            return self.last_packet["demo"]

    def test_packet_exposes_admitted_measurements_with_original_text(self):
        source = {"sha256": "a" * 64, "identity": "test-report", "available_at": 10,
                  "body": {"id": "test-report", "entity": "Access", "content": "Synthetic login failure", "measures": {"load": 70}}}
        self.packet(sources=[source])
        case = self.last_packet["cases"][0]
        self.assertIn({"label": "Recorded load", "value": "70 tickets"}, case["facts"])
        self.assertIn({"label": "Received (simulation)", "value": "00:10 UTC"}, case["facts"])
        self.assertIn("Synthetic login failure", case["evidence"]["text"])
        self.assertEqual(case["prediction"]["estimates"], {})

    def test_capacity_is_an_assumption_and_can_be_negative(self):
        assumptions = {"cases_per_week": 600, "manual_minutes_per_case": 8, "assisted_minutes_per_case": 3, "labour_usd_per_hour": 40}
        value = capacity_value(assumptions)
        self.assertEqual((value["capacity_hours_per_week"], value["capacity_value_usd_per_week"]), (50, 2000))
        self.assertTrue(all(value[key] is None for key in ("cash_savings_usd", "revenue_gain_usd", "compute_usd", "net_benefit_usd")))
        slower = capacity_value({**assumptions, "assisted_minutes_per_case": 10})
        self.assertEqual(slower["capacity_value_usd_per_week"], -800)
        for invalid in (True, -1, float("nan"), float("inf")):
            with self.subTest(invalid=invalid), self.assertRaises(ValueError):
                capacity_value({**assumptions, "labour_usd_per_hour": invalid})

    def test_retained_partial_attempt_keeps_unknown_total_and_unfinished_stages(self):
        from runtime.business_demo import attach_live_attempt

        report = {"schema": "backintel-live-jev-attempt/v1", "status": "blocked",
                  "receipt_path": "/reports/business-test/AttemptRecorded/Integration.json",
                  "request_attempts": 2, "unknown_request_cost_count": 1,
                  "total_provider_charge_usd": None}
        demo = self.packet([{"state": "completed", "metadata": {"cost_usd": .000013608}}], jobs=[{"state": "queued"}])
        self.assertEqual(demo["status"], "running")
        attach_live_attempt(self.last_packet, report, "business-test")
        self.assertEqual(demo["value"]["provider_usd"], .000013608)
        self.assertIsNone(demo["live_attempt"]["total_provider_charge_usd"])
        self.assertEqual(demo["status"], "blocked")
        self.assertTrue(all(stage["count"] == 0 for stage in demo["stages"]))
        self.assertIn("stopped after 2 request attempts", demo["error"])
        self.assertIn("total live attempt charge is unknown", demo["value"]["explanation"])
        with self.assertRaises(ValueError):
            attach_live_attempt(self.last_packet, report, "different-demo")
        with self.assertRaises(ValueError):
            attach_live_attempt(self.last_packet, {**report, "total_provider_charge_usd": 0}, "business-test")

    def test_fixture_charges_are_excluded_and_pending_requests_are_not_answers(self):
        fixture = {"state": "completed", "metadata": {"test_fixture": True, "cost_usd": 999}}
        simulated = self.packet([fixture])
        self.assertEqual(simulated["jev_mode"], "simulated Jev answers")
        self.assertEqual(simulated["value"]["provider_usd"], 0)
        self.assertEqual(simulated["actual_provider_calls"], 0)
        pending = self.packet([fixture, {"state": "pending", "metadata": {}}])
        self.assertEqual(pending["jev_mode"], "simulated Jev answers")
        self.assertIsNone(pending["value"]["provider_usd"])
        self.assertIsNone(pending["actual_provider_calls"])
        self.assertIsNone(pending["value"]["net_benefit_usd"])
        mixed = self.packet([fixture, {"state": "completed", "metadata": {"cost_usd": 0.25}}])
        self.assertEqual(mixed["jev_mode"], "mixed actual and simulated Jev answers")
        self.assertEqual(mixed["value"]["provider_usd"], 0.25)
        unknown = self.packet([{"state": "completed", "metadata": {}}])
        self.assertIsNone(unknown["value"]["provider_usd"])

    def test_completion_requires_followup_stages_and_no_pending_triggers(self):
        self.assertEqual(self.packet()["status"], "prepared")
        self.assertEqual(self.packet(stages=1)["status"], "awaiting follow-up execution")
        self.assertEqual(self.packet(stages=4)["status"], "completed")
        self.assertEqual(self.packet(stages=4, triggers=[{"state": "pending"}])["status"], "running")
        self.assertEqual(self.packet(stages=4, jobs=[{"state": "failed"}])["status"], "blocked")


if __name__ == "__main__":
    unittest.main()
