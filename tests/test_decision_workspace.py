import json
import hashlib
from copy import deepcopy
from pathlib import Path
import tempfile
from threading import Thread
import unittest
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from runtime.decision_workspace import Conflict, DecisionStore, WorkspaceServer, issue_cases, load_cases


class DecisionWorkspaceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / "reviews.sqlite3"
        self.cases, self.mode = load_cases(None)
        self.store = DecisionStore(self.path, self.cases)
        self.body = {"decision": "follow_up", "reason": "Verify the original report with its owner.", "expected_revision": 0, "expected_source_sha256": self.cases[0]["evidence"]["sha256"]}

    def tearDown(self):
        self.tmp.cleanup()

    def test_unavailable_packet_blocks_writes_and_preserves_existing_review(self):
        case_id = self.cases[0]["id"]
        saved = self.store.decide(case_id, self.body)
        packet_path = Path(self.tmp.name) / "packet.json"
        packet_path.write_text(json.dumps({"schema": "backintel-decision-workspace/v1", "cases": self.cases, "demo": {"status": "unavailable"}}))
        self.store.packet_path = packet_path
        with self.assertRaises(OSError):
            self.store.decide(case_id, {**self.body, "expected_revision": 1})
        self.assertEqual(self.store.case(case_id)["review"], saved["review"])
        packet_path.write_text("invalid json")
        with self.assertRaises(OSError):
            self.store.decide(case_id, self.body)

    def test_corrupt_packet_returns_structured_service_error(self):
        packet_path = Path(self.tmp.name) / "packet.json"
        packet_path.write_text("invalid json")
        self.store.packet_path = packet_path
        server = WorkspaceServer(self.store, self.mode, port=0)
        thread = Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            with self.assertRaises(HTTPError) as result:
                urlopen(f"http://127.0.0.1:{server.server_port}/api/workspace", timeout=5)
            self.assertEqual(result.exception.code, 503)
            self.assertIn("unavailable", json.load(result.exception)["error"])
        finally:
            server.shutdown()
            server.server_close()
            thread.join()

    def test_outcome_hidden_until_decision_and_review_survives_restart(self):
        case_id = self.cases[0]["id"]
        self.assertIsNone(self.store.case(case_id)["outcome"])
        saved = self.store.decide(case_id, self.body)
        self.assertEqual(saved["review"]["revision"], 1)
        restored = DecisionStore(self.path, self.cases).case(case_id)
        self.assertEqual(saved, restored)
        self.assertIsNotNone(restored["outcome"])

    def test_stale_decision_rejected_without_overwriting_history(self):
        case_id = self.cases[0]["id"]
        first = self.store.decide(case_id, self.body)
        with self.assertRaises(Conflict):
            self.store.decide(case_id, dict(self.body, reason="Overwrite"))
        self.assertEqual(self.store.case(case_id), first)
        updated = self.store.decide(case_id, dict(self.body, expected_revision=1, decision="no_action"))
        self.assertEqual(updated["review"]["revision"], 2)
        self.assertEqual([review["revision"] for review in updated["history"]], [2, 1])
        with self.store.connect() as connection:
            self.assertEqual(connection.execute("SELECT COUNT(*) FROM reviews").fetchone()[0], 2)

    def test_strict_decision_fields_and_nonempty_reason(self):
        for body in [dict(self.body, reason=" "), dict(self.body, reason="x"*2001), dict(self.body, expected_revision=True), dict(self.body, decision="delete"), dict(self.body, extra="x"), []]:
            with self.subTest(body=body), self.assertRaises(ValueError):
                self.store.decide(self.cases[0]["id"], body)

    def test_changed_source_does_not_inherit_review_or_reveal_outcome(self):
        case_id = self.cases[0]["id"]
        self.store.decide(case_id, self.body)
        self.cases[0]["evidence"]["sha256"] = "b" * 64
        changed = DecisionStore(self.path, self.cases)
        self.assertIsNone(changed.case(case_id)["review"])
        self.assertIsNone(changed.case(case_id)["outcome"])
        with self.assertRaises(Conflict):
            changed.decide(case_id, self.body)
        updated = changed.decide(case_id, dict(self.body, expected_source_sha256="b" * 64))
        self.assertEqual(updated["review"]["revision"], 2)

    def test_packet_refresh_waits_for_decision_commit_and_response(self):
        from concurrent.futures import ThreadPoolExecutor
        from contextlib import contextmanager
        from threading import Event
        from unittest.mock import patch
        path = Path(self.tmp.name) / 'packet.json'
        path.write_text(json.dumps({'schema': 'backintel-decision-workspace/v1', 'cases': self.cases}))
        self.store.packet_path = path
        entered, release, refresh_started, refreshed = Event(), Event(), Event(), Event()
        original_connect = self.store.connect
        @contextmanager
        def connect():
            if not entered.is_set():
                entered.set()
                if not release.wait(5):
                    raise TimeoutError('Test did not release decision')
            with original_connect() as connection:
                yield connection
        def refresh():
            refresh_started.set()
            packet = self.store.workspace(self.mode)
            refreshed.set()
            return packet
        with patch.object(self.store, 'connect', side_effect=connect), ThreadPoolExecutor(max_workers=2) as workers:
            decision = workers.submit(self.store.decide, self.cases[0]['id'], self.body)
            try:
                self.assertTrue(entered.wait(5))
                changed = deepcopy(self.cases)
                changed[0]['evidence']['sha256'] = 'b' * 64
                path.write_text(json.dumps({'schema': 'backintel-decision-workspace/v1', 'cases': changed}))
                refresh_result = workers.submit(refresh)
                self.assertTrue(refresh_started.wait(5))
                self.assertFalse(refreshed.wait(.25))
            finally:
                release.set()
            saved = decision.result(timeout=5)
            self.assertEqual(saved['review']['revision'], 1)
            self.assertEqual(saved['evidence']['sha256'], self.body['expected_source_sha256'])
            self.assertIsNone(refresh_result.result(timeout=5)['cases'][0]['review'])

    def public_source(self):
        source = Path(self.tmp.name)
        row = {"number": 1, "original": {"title": "Example", "body": "<script>alert(1)</script>"}, "created_at": "2024-01-01T00:00:00Z", "original_sha256": "a"*64, "url": "https://github.com/example/project/issues/1", "state_at_deadline": "closed", "qualifying_comments": [], "outcome_available_at": "2024-01-08T00:00:00Z"}
        cohort = json.dumps({"holdout": [row]}).encode()
        predictions = {"cohort_sha256": hashlib.sha256(cohort).hexdigest(), "probabilities": {"baseline": [0.25]}, "cases": [{"number": 1, "probabilities": {"baseline": 0.25}}]}
        (source / "cohort.json").write_bytes(cohort)
        (source / "predictions.json").write_text(json.dumps(predictions))
        return source, row, predictions

    def test_public_adapter_preserves_text_and_keeps_label_out_of_facts(self):
        source, row, _ = self.public_source()
        cases = issue_cases(source)
        self.assertEqual(cases[0]["evidence"]["text"], row["original"]["body"])
        self.assertNotIn("closed", json.dumps(cases[0]["facts"]))
        self.assertFalse(cases[0]["simulated"])
        self.assertEqual(cases[0]["prediction"]["estimates"], {"baseline": 0.25})

    def test_public_adapter_rejects_predictions_from_another_cohort(self):
        source, row, _ = self.public_source()
        row["original"]["body"] = "Changed opening report"
        (source / "cohort.json").write_text(json.dumps({"holdout": [row]}))
        with self.assertRaisesRegex(ValueError, "cohort"):
            issue_cases(source)

    def test_public_adapter_rejects_misaligned_or_invalid_scores(self):
        source, _, valid = self.public_source()
        invalid = []
        for mutation in ("identity", "count", "score", "nan", "range"):
            predictions = deepcopy(valid)
            if mutation == "identity":
                predictions["cases"][0]["number"] = 2
            elif mutation == "count":
                predictions["probabilities"]["baseline"] = []
            elif mutation == "score":
                predictions["probabilities"]["baseline"] = [0.75]
            else:
                predictions["probabilities"]["baseline"] = [float("nan") if mutation == "nan" else 1.1]
            invalid.append((mutation, predictions))
        for mutation, predictions in invalid:
            with self.subTest(mutation=mutation), self.assertRaises(ValueError):
                (source / "predictions.json").write_text(json.dumps(predictions))
                issue_cases(source)

    def test_http_contract_origin_body_conflict_and_no_outcome_leak(self):
        server = WorkspaceServer(self.store, self.mode, port=0)
        thread = Thread(target=server.serve_forever, daemon=True)
        thread.start()
        base = f"http://127.0.0.1:{server.server_port}"
        try:
            with urlopen(base + "/api/workspace") as response:
                workspace = json.load(response)
                self.assertEqual(response.headers["Cache-Control"], "no-store")
                self.assertTrue(all(case["outcome"] is None for case in workspace["cases"]))
            route = base + f"/api/cases/{self.cases[0]['id']}/decision"
            bad_origin = Request(route, data=json.dumps(self.body).encode(), method="PUT", headers={"Content-Type":"application/json", "Origin":"https://evil.example"})
            with self.assertRaises(HTTPError) as result:
                urlopen(bad_origin)
            self.assertEqual(result.exception.code, 403)
            request = Request(route, data=json.dumps(self.body).encode(), method="PUT", headers={"Content-Type":"application/json"})
            with urlopen(request) as response:
                self.assertIsNotNone(json.load(response)["outcome"])
            with self.assertRaises(HTTPError) as result:
                urlopen(request)
            self.assertEqual(result.exception.code, 409)
        finally:
            server.shutdown(); server.server_close(); thread.join()


if __name__ == "__main__":
    unittest.main()
