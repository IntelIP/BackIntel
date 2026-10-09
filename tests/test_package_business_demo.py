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
    def test_trusted_checkout_rejects_package_code_before_it_can_execute(self):
        import zipfile
        from unittest.mock import patch
        from scripts.package_business_demo import verify_trusted_package
        with tempfile.TemporaryDirectory() as directory:
            checkout = Path(directory)
            package = checkout / 'BackIntelDemo'
            (package / 'Records').mkdir(parents=True)
            (package / 'scripts').mkdir()
            script = package / 'scripts/__init__.py'
            script.write_text('')
            (package / 'Records/Workspace.json').write_text(json.dumps({'demo':{'status':'completed','demo_id':'business-v4'}}))
            files = [{'path':str(p.relative_to(package)), 'sha256':sha(p)} for p in package.rglob('*') if p.is_file()]
            manifest = package / 'Manifest.json'
            manifest.write_text(json.dumps({'demo_id':'business-v4','files':files}))
            distribution = checkout / 'docs/demo/Packages'
            distribution.mkdir(parents=True)
            archive = distribution / 'demo.zip'
            with zipfile.ZipFile(archive,'w') as zipped:
                for file in package.rglob('*'):
                    if file.is_file(): zipped.write(file,str(file.relative_to(checkout)))
            (distribution / 'PackageReceipt.json').write_text(json.dumps({'archive':archive.name,'archive_sha256':sha(archive)}))
            marker = checkout / 'executed'
            with patch('scripts.package_business_demo.ROOT',checkout):
                verify_trusted_package(package)
                script.write_text('from pathlib import Path\nPath('+repr(str(marker))+').touch()\n')
                with self.assertRaises(ValueError): verify_trusted_package(package)
                self.assertFalse(marker.exists())
                forged = json.loads(manifest.read_text())
                next(f for f in forged['files'] if f['path']=='scripts/__init__.py')['sha256'] = sha(script)
                manifest.write_text(json.dumps(forged))
                with self.assertRaisesRegex(ValueError,'trusted archive'): verify_trusted_package(package)
                self.assertFalse(marker.exists())

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
            state = root / '.demo-state'
            outside = Path(directory) / 'OutsideState'
            outside.mkdir()
            state.symlink_to(outside, target_is_directory=True)
            with self.assertRaisesRegex(ValueError, 'without links'): server(root, 0)
            self.assertEqual(list(outside.iterdir()), [])
            state.unlink()
            state.mkdir()
            for name in ('Reviews.sqlite3', 'Reviews.sqlite3-wal', 'Reviews.sqlite3-shm', 'Reviews.sqlite3-journal'):
                linked = state / name
                target = outside / name
                linked.symlink_to(target)
                with self.assertRaisesRegex(ValueError, 'without links'): server(root, 0)
                self.assertFalse(target.exists())
                linked.unlink()
            linked = state / 'Reviews.sqlite3'
            original_hash = sha(original)
            linked.symlink_to(original)
            with self.assertRaisesRegex(ValueError, 'without links'): server(root, 0)
            self.assertEqual(sha(original), original_hash)
            linked.unlink()
            import os
            os.link(original, linked)
            with self.assertRaisesRegex(ValueError, 'linked external file'): server(root, 0)
            self.assertEqual(sha(original), original_hash)
            linked.unlink()
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
