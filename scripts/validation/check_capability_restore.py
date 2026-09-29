"""Restore a development database into a new isolated DB and replay completed work."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import uuid

import psycopg
from psycopg import sql

from runtime.artifacts import get_artifact
from runtime.evidence import Evidence
from runtime.jobs import execute
from runtime.simulation import encoded
from scripts.capability_demo import DEMO_DSN, ROOT, domain_snapshot, status


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--demo-id", required=True)
    args = parser.parse_args()
    task_ids = [f"{name}-{args.demo_id}" for name in ("support", "equipment")]
    output = ROOT / "artifacts/validation/CapabilityRestore" / ("Attempt" + uuid.uuid4().hex[:12])
    output.mkdir(parents=True, mode=0o700)
    receipt = {"schema": "backintel-capability-restore/v1", "status": "running", "tasks": task_ids,
               "candidate": "uncommitted-working-tree", "models": "simulated", "paid_provider_calls": 0,
               "local_compute_usd": None, "limits": ["Real model package and checkpoint recovery is not established by this fixture check."]}
    target = "test_restore_" + uuid.uuid4().hex[:12]
    clone_dsn = f"postgresql://capability_test@127.0.0.1:55436/{target}"
    created = False
    try:
        with psycopg.connect(DEMO_DSN, autocommit=True) as source:
            if status(source, args.demo_id)["status"] != "passed":
                raise RuntimeError("Only a completed, quiescent demonstration can be restored")
            before = domain_snapshot(source, task_ids)
        backup = output / "DevelopmentDatabase.dump"
        with backup.open("wb") as destination, (output / "Backup.log").open("w") as log:
            subprocess.run(["docker", "compose", "-f", "compose.capabilities.yml", "exec", "-T", "postgres",
                            "pg_dump", "-U", "capability_demo", "-d", "test_backintel_demo", "--format=custom", "--no-owner", "--no-privileges"],
                           cwd=ROOT, stdout=destination, stderr=log, check=True, timeout=60)
        receipt["backup"] = {"file": str(backup), "bytes": backup.stat().st_size, "sha256": hashlib.sha256(backup.read_bytes()).hexdigest()}
        with psycopg.connect("postgresql://capability_test@127.0.0.1:55436/postgres", autocommit=True) as admin:
            admin.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(target)))
            created = True
        with backup.open("rb") as data, (output / "Restore.log").open("w") as log:
            subprocess.run(["docker", "exec", "-i", "backintel-capability-test", "pg_restore", "-U", "capability_test",
                            "-d", target, "--no-owner", "--no-privileges", "--exit-on-error"], stdin=data, stdout=log,
                           stderr=subprocess.STDOUT, check=True, timeout=60)
        with psycopg.connect(clone_dsn, autocommit=True) as clone:
            restored = domain_snapshot(clone, task_ids)
            if before["digest"] != restored["digest"]:
                raise AssertionError("Restored records or job state differ from accepted source state")
            receipt["evidence_records"] = len(restored["evidence"])
            receipt["source_sha256"], receipt["restored_sha256"] = before["digest"], restored["digest"]
            receipt["audience_rows"] = []
            for task_id in task_ids:
                store = Evidence(clone, task_id)
                for audience in ("operator", "manager", "analyst"):
                    artifact = get_artifact(store, audience)
                    receipt["audience_rows"].append({"task_id": task_id, "audience": audience, "artifact": artifact["sha256"], "rows": len(artifact["body"]["rows"])})
            # Execute only already-completed domain jobs; no scheduler or provider runs in the clone.
            prior = {name: os.environ.get(name) for name in ("BACKINTEL_APP_DATABASE_URL", "BACKINTEL_TEST_DATABASE_URL")}
            try:
                os.environ.update(BACKINTEL_APP_DATABASE_URL=clone_dsn, BACKINTEL_TEST_DATABASE_URL=clone_dsn)
                replay = [execute(row[0]) for row in restored["jobs"]]
            finally:
                for name, value in prior.items():
                    if value is None:
                        os.environ.pop(name, None)
                    else:
                        os.environ[name] = value
            if not all(r.get("reused") and r["state"] == "completed" for r in replay):
                raise AssertionError("Restored completed work was not safely reused")
            after = domain_snapshot(clone, task_ids)
            if after["digest"] != restored["digest"]:
                raise AssertionError("Restored replay changed accepted evidence or delivery history")
            receipt.update(status="passed", replayed_jobs=len(replay), after_replay_sha256=after["digest"])
    except Exception as exc:
        receipt.update(status="failed", error={"type": type(exc).__name__, "message": str(exc)})
        raise
    finally:
        if created:
            with psycopg.connect("postgresql://capability_test@127.0.0.1:55436/postgres", autocommit=True) as admin:
                admin.execute(sql.SQL("DROP DATABASE {} WITH (FORCE)").format(sql.Identifier(target)))
            receipt["temporary_database_removed"] = True
        (output / "Restore.json").write_bytes(encoded(receipt))
        print(json.dumps({"status": receipt["status"], "receipt": str(output / "Restore.json")}))


if __name__ == "__main__":
    main()
