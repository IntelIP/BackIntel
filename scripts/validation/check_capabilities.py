"""Persist direct working-tree capability-check results; exact-commit acceptance is separate."""
import hashlib
import io
import json
import subprocess
import time
import unittest
from pathlib import Path


def main() -> int:
    root = Path(__file__).resolve().parents[2]
    output = root / "artifacts" / "validation" / "CapabilityPackages"
    output.mkdir(parents=True, exist_ok=True)
    suite = unittest.TestSuite()
    for pattern in ("test_capabilities.py", "test_simulation.py", "test_real_integrations.py", "test_jev.py"):
        suite.addTests(unittest.defaultTestLoader.discover(str(root / "tests"),pattern=pattern))
    started, log = time.perf_counter(), io.StringIO()
    result = unittest.TextTestRunner(stream=log,verbosity=2).run(suite)
    log_path = output / "checks.log"
    log_path.write_text(log.getvalue())
    paths = [root / "runtime" / name for name in ("contracts.py","evidence.py","observations.py","prediction.py","synthetic.py","jobs.py","attention.py","capability_pipeline.py","capability_graph.py","real_models.py","real_semantics.py","jev.py","artifacts.py","audience_server.py","generated_artifacts.py","sandbox.py")]
    paths += [root / "config" / "simulation" / f"{name}.json" for name in ("support","equipment")]
    paths += [root / "tests" / "test_capabilities.py",root/"tests"/"test_real_integrations.py",root/"config"/"real_models.json",
              root/"scripts"/"real_model_probe.py",root/"requirements.models.txt",root/"migrations"/"0009_model_requests.sql",
              root / "migrations" / "0007_capability_evidence.sql",root / "migrations" / "0008_capability_background.sql", Path(__file__),log_path]
    evidence = {"schema":"backintel-capability-checks/v1", "status":"passed" if result.wasSuccessful() else "failed",
                "base_commit":subprocess.check_output(["git","rev-parse","HEAD"],cwd=root,text=True).strip(),
                "candidate":"working-tree", "exact_commit_acceptance":"blocked",
                "real_model_acceptance":"blocked", "provider_checks":"local fixtures only; no actual Jev or predictor run certified",
                "tests":result.testsRun, "failures":len(result.failures), "errors":len(result.errors), "skipped":len(result.skipped),
                "duration_ms":(time.perf_counter()-started)*1000,
                "cost":{"provider_calls":0,"provider_usd":0,"local_compute_usd":None},
                "artifacts":[{"path":str(p.relative_to(root)),"sha256":hashlib.sha256(p.read_bytes()).hexdigest(),"bytes":p.stat().st_size} for p in paths]}
    (output / "checks.json").write_text(json.dumps(evidence,indent=2)+"\n")
    print(json.dumps({k:evidence[k] for k in ("status","tests","failures","errors","exact_commit_acceptance")},indent=2))
    if not result.wasSuccessful():
        print(log.getvalue())
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    raise SystemExit(main())
