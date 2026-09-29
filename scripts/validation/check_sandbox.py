"""Actually attempt prohibited operations in the local generated-code sandbox."""

from __future__ import annotations

import json
from pathlib import Path
import tempfile
import uuid

from runtime.sandbox import run_candidate
from runtime.simulation import encoded


def main() -> int:
    output = Path(__file__).resolve().parents[2] / "artifacts/validation/Sandbox"
    output.mkdir(parents=True, exist_ok=True)
    receipt = {"schema": "backintel-sandbox-check/v1", "candidate": "uncommitted-working-tree",
               "code_generation": "simulated", "sandbox_execution": "real", "checks": [], "status": "running"}
    with tempfile.TemporaryDirectory(prefix="BackIntelHostBoundary") as temporary:
        secret = Path(temporary) / "forbidden.txt"
        secret.write_text("synthetic host-only marker")
        samples = {
            "approved_input": ('import json\ns=json.load(open("/input/snapshot.json"))\nprint(json.dumps({"total":sum(s["values"])}))', "candidate"),
            "host_read": (f'print(open({str(secret)!r}).read())', "process_failed"),
            "protected_input_write": ('open("/input/snapshot.json","w").write("changed")', "process_failed"),
            "protected_source_write": ('open("/candidate/code.py","w").write("changed")', "process_failed"),
            "protected_dependency_write": ('import json\nopen(json.__file__,"w").write("changed")', "process_failed"),
            "network": ('import socket\nsocket.create_connection(("1.1.1.1",443),timeout=1)', "process_failed"),
            "cpu": ('while True: pass', "time_limit"),
            "memory": ('x=bytearray(1024*1024*1024)\nprint("{}")', "process_failed"),
            "output": ('while True: print("x"*4096)', "output_limit"),
            "temporary_storage": ('open("/tmp/large","wb").write(b"x"*(2*1024*1024))', "process_failed"),
        }
        path = output / (uuid.uuid4().hex + ".json")
        try:
            for name, (source, expected) in samples.items():
                run = run_candidate(source, {"values": [2, 3, 5]}, "backintel-capability-demo-runtime:latest")
                actual = run["status"] if run["status"] == "candidate" else run["stop_reason"]
                passed = actual == expected and run["cleanup_confirmed"]
                if name == "approved_input":
                    passed = passed and run["result"] == {"total": 10}
                receipt["checks"].append({"name": name, "passed": passed, "expected": expected, "run": run})
                path.write_bytes(encoded(receipt))
                print(json.dumps({"check": name, "passed": passed, "actual": actual}), flush=True)
                if not passed:
                    raise AssertionError("Sandbox failed " + name)
            receipt["status"] = "passed"
        except Exception as exc:
            receipt.update(status="failed", error={"type": type(exc).__name__, "message": str(exc)})
            raise
        finally:
            path.write_bytes(encoded(receipt))
            print(json.dumps({"status": receipt["status"], "receipt": str(path)}), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
