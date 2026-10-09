"""Portable playback must preserve shared reviews without exposing other files."""
import json
from pathlib import Path
import tempfile
import threading
import unittest
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from runtime.decision_workspace import DecisionStore, simulated_cases
from scripts.package_business_demo import backup_reviews, server, sha, verify


class RecordedPackageTests(unittest.TestCase):
    def test_playback_review_scope_integrity_and_loopback_boundary(self):
        with tempfile.TemporaryDirectory(prefix="BackIntelPackageChecks") as directory:
            root = Path(directory) / "Package"
            root.mkdir()
            (root / "Frontend").mkdir()
            (root / "Frontend/index.html").write_text("Recorded package")
            (root / "Records").mkdir()
            cases = simulated_cases()
            packet = {"schema": "backintel-decision-workspace/v1", "source_mode": "synthetic-business-demonstration",
                      "cases": cases, "demo": {"status": "completed", "demo_id": "business-v4"}}
            (root / "Records/Workspace.json").write_text(json.dumps(packet))
            original = Path(directory) / "PreparedReviews.sqlite3"
            DecisionStore(original, cases)
            backup_reviews(original, root / "Records/ReviewsSeed.sqlite3")
            files = [{"path": str(p.relative_to(root)), "sha256": sha(p)} for p in root.rglob("*") if p.is_file()]
            (root / "Manifest.json").write_text(json.dumps({"demo_id": "business-v4", "files": files}))
            api = server(root, 0)
            worker = threading.Thread(target=api.serve_forever, daemon=True)
            worker.start()
            base = f"http://127.0.0.1:{api.server_port}"
            seed = sha(root / "Records/ReviewsSeed.sqlite3")
            try:
                with urlopen(base + "/") as response:
                    self.assertEqual(response.read(), b"Recorded package")
                with urlopen(base + "/api/workspace") as response:
                    case = json.load(response)["cases"][0]
                body = {"decision": "follow_up", "reason": "Synthetic demo review", "expected_revision": 0,
                        "expected_context_sha256": case["context_sha256"]}
                request = Request(base + f"/api/cases/{case['id']}/decision", data=json.dumps(body).encode(), method="PUT",
                                  headers={"Content-Type": "application/json", "Origin": base})
                with urlopen(request) as response:
                    self.assertEqual(json.load(response)["review"]["revision"], 1)
                self.assertEqual(seed, sha(root / "Records/ReviewsSeed.sqlite3"))
                for path in ("/%2e%2e/Manifest.json", "/Records/ReviewsSeed.sqlite3"):
                    with self.assertRaises(HTTPError) as denied:
                        urlopen(base + path)
                    self.assertEqual(denied.exception.code, 404)
                with self.assertRaises(HTTPError) as denied:
                    urlopen(Request(base + "/api/workspace", headers={"Origin": "https://example.com"}))
                self.assertEqual(denied.exception.code, 403)
                verify(root)
                (root / "Frontend/index.html").write_text("Changed")
                with self.assertRaisesRegex(ValueError, "missing or changed"):
                    verify(root)
            finally:
                api.shutdown()
                api.server_close()
                worker.join(timeout=5)


if __name__ == "__main__":
    unittest.main()
