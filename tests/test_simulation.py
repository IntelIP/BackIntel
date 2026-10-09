"""Observable cross-domain workflow checks; synthetic sources only, no dependencies or network."""
import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from runtime.simulation import digest, load_scenario, publish, render_html, simulate

ROOT = Path(__file__).resolve().parents[1]


class SimulationTests(unittest.TestCase):
    def test_distinct_domains_share_workflow_and_preserve_missingness(self):
        for name in ("support", "equipment"):
            with self.subTest(name=name):
                result = simulate(load_scenario(name))
                baseline, change, missing, recovery = result["batches"]
                self.assertEqual(baseline["summary"], {"records": 3, "known": 2, "unknown": 1, "flagged": 0, "rate": 0})
                self.assertEqual(change["summary"], {"records": 4, "known": 3, "unknown": 1, "flagged": 2, "rate": 2/3})
                self.assertEqual(change["change"], 2/3)
                self.assertIsNone(missing["summary"]["rate"])
                self.assertEqual(recovery["summary"]["rate"], 0)
                self.assertFalse(change["projection"]["validated"])
                self.assertEqual(change["projection"]["next_rate"], 1)
                for batch in result["batches"]:
                    for row in batch["observations"]:
                        self.assertEqual(row["source_sha256"], digest(row["source"]))

    def test_failure_retry_duplicate_acknowledgment_and_staleness(self):
        result = simulate(load_scenario("support"))
        self.assertEqual([e["outcome"] for e in result["timeline"]], [
            "completed", "reused", "simulated_transient_failure", "completed", "acknowledged",
            "stale", "reused", "completed", "completed"])
        self.assertEqual(result["timeline"][4]["condition"], "active")
        self.assertEqual(result["timeline"][5]["condition"], "unknown")
        self.assertEqual(result["timeline"][7]["condition"], "unknown")
        self.assertEqual(result["timeline"][8]["condition"], "cleared")
        self.assertEqual(len(result["inbox"]), 1)
        self.assertTrue(result["inbox"][0]["acknowledged"])

    def test_outputs_change_with_input_and_replay_reuses_exact_bytes(self):
        source = load_scenario("equipment")
        original = simulate(source)
        changed = copy.deepcopy(source)
        changed["source"]["data"] = changed["source"]["data"].replace("baseline,40", "baseline,90")
        altered = simulate(changed)
        self.assertNotEqual(original["input_sha256"], altered["input_sha256"])
        self.assertEqual(altered["batches"][0]["summary"]["rate"], 1/2)
        with tempfile.TemporaryDirectory() as directory:
            destination = Path(directory)
            first = publish(original, destination)
            timestamps = {p.name: p.stat().st_mtime_ns for p in destination.iterdir()}
            self.assertEqual(first, publish(simulate(source), destination))
            self.assertEqual(timestamps, {p.name: p.stat().st_mtime_ns for p in destination.iterdir()})
            Path(first["json"]["path"]).write_text("corrupted")
            with self.assertRaises(ValueError):
                publish(original, destination)

    def test_source_text_remains_inert_in_html(self):
        config = load_scenario("support")
        config["source"]["data"][0]["message"] = '<script>alert("unsafe")</script>'
        rendered = render_html(simulate(config))
        self.assertNotIn("<script>", rendered)
        self.assertIn("&lt;script&gt;", rendered)
        self.assertIn("SYNTHETIC SIMULATION", rendered)

    def test_invalid_sources_and_event_sequences_are_rejected(self):
        mutations = [
            lambda c: c["source"]["data"].append(c["source"]["data"][0]),
            lambda c: c["source"]["data"][0].pop("queue"),
            lambda c: c["events"].append({"at": -1, "action": "tick"}),
            lambda c: c["events"].append({"at": 20, "action": "send_email"}),
            lambda c: c["events"][0].update(period="absent"),
            lambda c: c["policy"].update(attention_rate=0),
            lambda c: c.update(events=c["events"][:3]),
        ]
        for mutate in mutations:
            config = load_scenario("support")
            mutate(config)
            with self.assertRaises(ValueError):
                simulate(config)
        with self.assertRaises(ValueError):
            load_scenario("../../secret")
        config = load_scenario("equipment")
        config["source"]["data"] = config["source"]["data"].replace("baseline,40", "baseline,NaN")
        with self.assertRaises(ValueError):
            simulate(config)

    def test_cli_creates_inspectable_artifacts_without_runtime_or_dataset(self):
        with tempfile.TemporaryDirectory() as directory:
            completed = subprocess.run([sys.executable, "-m", "scripts.simulate", "--output", directory],
                                       cwd=ROOT, capture_output=True, text=True, timeout=20, check=True)
            receipts = json.loads(completed.stdout)
            self.assertEqual({r["scenario"] for r in receipts}, {"support", "equipment"})
            for receipt in receipts:
                self.assertEqual(receipt["provider_calls"], 0)
                saved = json.loads(Path(receipt["artifacts"]["json"]["path"]).read_text())
                self.assertEqual(saved["mode"], "synthetic_simulation")
                self.assertEqual(len(saved["batches"]), 4)
                self.assertTrue(Path(receipt["artifacts"]["html"]["path"]).is_file())


if __name__ == "__main__":
    unittest.main()
