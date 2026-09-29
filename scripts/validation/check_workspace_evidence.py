"""Check the required saved browser observations for the current candidate."""
import hashlib
import json
import os
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[2]
REQUIRED = {"react_review", "react_evidence", "react_prediction_labels", "react_history_outcome", "react_search_empty", "react_equipment", "react_mobile", "react_service_error", "react_conflict", "reflex_shared_review", "reflex_equipment", "reflex_evidence", "reflex_mobile", "reference_fidelity", "fonts_loaded", "no_horizontal_overflow", "loopback_services"}


def main():
    head = os.environ.get("TABELLIO_EXPECTED_COMMIT") or subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    path = ROOT / "artifacts/validation/DecisionWorkspace/BrowserChecks.json"
    report = json.loads(path.read_text())
    if report.get("candidateCommit") != head:
        raise ValueError("Browser evidence does not match the current candidate")
    if not REQUIRED <= report.get("checks", {}).keys() or any(report["checks"][name] is not True for name in REQUIRED):
        raise ValueError("A required browser check is missing or did not pass")
    for item in report["artifacts"]:
        file = ROOT / item["path"]
        file.resolve().relative_to(ROOT)
        if hashlib.sha256(file.read_bytes()).hexdigest() != item["sha256"]:
            raise ValueError("Browser artifact changed: " + item["path"])
    captures = {item["name"] for item in report["artifacts"]}
    if not {"ReactDesktop", "ReactMobile", "ReactEvidence", "ReflexDesktop", "ReflexMobile"} <= captures:
        raise ValueError("Required screenshots are missing")
    print(json.dumps({"status": "passed", "candidateCommit": head, "checks": len(REQUIRED), "captures": len(captures)}))


if __name__ == "__main__":
    main()
