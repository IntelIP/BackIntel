"""Start the isolated capability development journey; real-model completion remains separate."""
from __future__ import annotations

import argparse
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import re
import subprocess
import time
import uuid

import psycopg

from scripts.jev.run_review_batch import request
from runtime.simulation import digest, encoded

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "artifacts" / "validation" / "CapabilityDemo"
BASE = "http://127.0.0.1:2027"
DEMO_DSN = "postgresql://capability_demo@127.0.0.1:55437/test_backintel_demo"


def status(connection, demo_id="development-v1") -> dict:
    task_ids = [f"{name}-{demo_id}" for name in ("support","equipment")]
    jobs = connection.execute("""SELECT task_id,state,count(*) FROM backintel.capability_jobs
        WHERE task_id=ANY(%s) GROUP BY task_id,state ORDER BY task_id,state""",(task_ids,)).fetchall()
    pending = connection.execute("SELECT count(*) FROM backintel.capability_triggers WHERE state='pending' AND task_id=ANY(%s)",(task_ids,)).fetchone()[0]
    errors = connection.execute("""SELECT task_id,payload->>'operation',error FROM backintel.capability_jobs
        WHERE state='failed' AND task_id=ANY(%s)""",(task_ids,)).fetchall()
    running = sum(count for _,state,count in jobs if state in ("queued","running","retry"))
    counts = connection.execute("""SELECT task_id,kind,count(*) FROM backintel.capability_evidence
        WHERE task_id=ANY(%s) AND kind IN ('prediction','comparison','delivery','model_update','artifact','artifact_candidate')
        GROUP BY task_id,kind ORDER BY task_id,kind""",(task_ids,)).fetchall()
    modes = {r[0] for r in connection.execute("""SELECT DISTINCT body->>'implementation_mode'
        FROM backintel.capability_evidence WHERE task_id=ANY(%s) AND kind='model'""",(task_ids,))}
    return {"status":"failed" if errors else "passed" if jobs and not pending and not running else "running",
            "jobs":[{"scenario":task,"state":state,"count":count} for task,state,count in jobs],
            "pending_triggers":pending,"errors":errors,
            "counts":[{"scenario":task,"kind":kind,"count":count} for task,kind,count in counts],
            "model_execution":"real_local_predictors" if "real" in modes else "simulated_development_only",
            "final_real_model_acceptance":"blocked"}


def wait_for_completion(timeout=120, demo_id="development-v1") -> dict:
    with psycopg.connect(DEMO_DSN,autocommit=True) as connection:
        connection.execute("LISTEN backintel_capability_jobs")
        deadline = time.monotonic()+timeout
        while True:
            result = status(connection,demo_id)
            if result["status"] != "running":
                return result
            remaining = deadline-time.monotonic()
            if remaining <= 0:
                return {**result,"status":"blocked","reason":"Bounded background completion timeout"}
            # Database notifications wait for actual work completion; no polling/sleep loop.
            next(connection.notifies(timeout=remaining,stop_after=1),None)


def domain_snapshot(connection, task_ids):
    evidence = [row[0] for row in connection.execute("SELECT sha256 FROM backintel.capability_evidence WHERE task_id=ANY(%s) ORDER BY sha256", (task_ids,)).fetchall()]
    jobs = connection.execute("SELECT job_id,state,attempts,result_sha256 FROM backintel.capability_jobs WHERE task_id=ANY(%s) ORDER BY sequence", (task_ids,)).fetchall()
    return {"evidence": evidence, "jobs": jobs, "digest": digest([evidence, jobs])}


def restart_with_pending_work(task_ids, output):
    with psycopg.connect(DEMO_DSN, autocommit=True) as connection:
        connection.execute("LISTEN backintel_capability_jobs")
        deadline = time.monotonic() + 45
        while True:
            completed = connection.execute("SELECT count(*) FROM backintel.capability_jobs WHERE task_id=ANY(%s) AND payload->>'operation'='bootstrap' AND state='completed'", (task_ids,)).fetchone()[0]
            if completed == len(task_ids):
                break
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise TimeoutError("Bootstrap did not finish before the bounded restart check")
            next(connection.notifies(timeout=remaining, stop_after=1), None)
        pending = connection.execute("SELECT count(*) FROM backintel.capability_triggers WHERE task_id=ANY(%s) AND state='pending'", (task_ids,)).fetchone()[0]
        if not pending:
            raise ValueError("Restart proof requires a fresh demonstration with pending work")
        before = domain_snapshot(connection, task_ids)
    (output / "RestartBefore.json").write_bytes(encoded(before))
    with (output / "Restart.log").open("w") as log:
        subprocess.run(["docker", "compose", "-f", "compose.capabilities.yml", "restart", "runtime"], cwd=ROOT,
                       stdout=log, stderr=subprocess.STDOUT, check=True, timeout=60)
        subprocess.run(["docker", "compose", "-f", "compose.capabilities.yml", "up", "--detach", "--wait", "--no-build", "--no-recreate", "runtime"], cwd=ROOT,
                       stdout=log, stderr=subprocess.STDOUT, check=True, timeout=90)
    return {"status": "restarted", "pending_triggers_before": pending, "evidence_before": len(before["evidence"]),
            "before_sha256": before["digest"], "records": before["evidence"]}


def verify_replay(connection, assistant, runs, demo_id):
    task_ids = [f"{name}-{demo_id}" for name in ("support", "equipment")]
    before = domain_snapshot(connection, task_ids)
    outputs = []
    for run in runs:
        response = request("POST", f"/threads/{run['thread_id']}/runs/wait", {
            "assistant_id": assistant, "input": {"operation": "bootstrap", "scenario": run["scenario"],
                                                  "demo_id": demo_id, "request_id": "capability-bootstrap-v1"}}, base=BASE)
        outputs.append(response)
    after = domain_snapshot(connection, task_ids)
    if before["digest"] != after["digest"]:
        raise AssertionError("Replay changed accepted evidence, job attempts, or delivery history")
    return {"status": "passed", "before_sha256": before["digest"], "after_sha256": after["digest"],
            "evidence_records": len(after["evidence"]), "responses": outputs}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--development",action="store_true",help="Explicitly permit simulated model fixtures")
    parser.add_argument("--no-start",action="store_true",help="Use the already-running isolated service")
    parser.add_argument("--wait",action="store_true",help="Wait for persisted due work using database notifications")
    parser.add_argument("--status",action="store_true",help="Inspect without submitting work")
    parser.add_argument("--verify-recovery",action="store_true",help="Restart only the isolated runtime with pending work, then verify replay")
    parser.add_argument("--serve",action="store_true",help="After completion and packaging, serve scoped local reports until Ctrl-C")
    parser.add_argument("--demo-id",default="development-v1",help="Persistent demonstration identity; reuse resumes the same work")
    args = parser.parse_args()
    if not re.fullmatch(r"[a-z][a-z0-9-]{0,24}", args.demo_id):
        parser.error("Invalid demonstration identity")
    if not args.development and not args.status:
        parser.error("Real Jev/CatBoost/TabICLv2 integration is unfinished. --development runs fixtures and cannot satisfy final acceptance.")
    OUTPUT.mkdir(parents=True,exist_ok=True)
    if args.status:
        with psycopg.connect(DEMO_DSN,autocommit=True) as connection:
            result = status(connection,args.demo_id)
        print(json.dumps(result,indent=2))
        return 1 if result["status"] == "failed" else 0
    output = OUTPUT / args.demo_id / ("Attempt" + uuid.uuid4().hex[:12])
    output.mkdir(parents=True, exist_ok=True)
    output.chmod(0o700)
    if not args.no_start:
        with (output / "Startup.log").open("w") as log:
            subprocess.run(["docker","compose","-f","compose.capabilities.yml","up","--build","--detach","--wait","--wait-timeout","120"],
                           cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,check=True,timeout=150)
    assistants = request("POST","/assistants/search",{"graph_id":"capability_platform","limit":1},base=BASE)
    if not assistants:
        raise RuntimeError("Isolated service lacks capability_platform")
    assistant = assistants[0]["assistant_id"]
    receipts = []
    for name in ("support","equipment"):
        thread = request("POST","/threads",{},base=BASE)
        run = request("POST",f"/threads/{thread['thread_id']}/runs",{
            "assistant_id":assistant,"input":{"operation":"bootstrap","scenario":name,"demo_id":args.demo_id,"request_id":"capability-bootstrap-v1"}},base=BASE)
        receipts.append({"scenario":name,"thread_id":thread["thread_id"],"run_id":run["run_id"]})
    crons = request("POST","/runs/crons/search",{"assistant_id":assistant,"limit":100},base=BASE)
    cron = next((c for c in crons if c.get("metadata",{}).get("purpose") == "bounded-capability-demo"),None)
    end = (datetime.now(timezone.utc)+timedelta(seconds=120)).isoformat()
    if cron is None:
        cron = request("POST","/runs/crons",{"assistant_id":assistant,"schedule":"*/2 * * * * *", "enabled":False,
                       "input":{"operation":"dispatch"},"metadata":{"purpose":"bounded-capability-demo"},"end_time":end},base=BASE)
    cron = request("PATCH",f"/runs/crons/{cron['cron_id']}",{"enabled":True,"end_time":end},base=BASE)
    receipt = {"base_url":BASE,"runs":receipts,"scheduler":"aegra_native_cron","cron_id":cron["cron_id"],"end_time":end,
               "mode":"synthetic_sources_simulated_models","real_model_acceptance":"blocked","demo_id":args.demo_id}
    (output / "Submission.json").write_bytes(encoded(receipt))
    print(json.dumps(receipt,indent=2),flush=True)
    if args.wait or args.verify_recovery or args.serve:
        result = {"status": "running", "candidate": "uncommitted-working-tree", "final_real_model_acceptance": "blocked"}
        task_ids = [f"{name}-{args.demo_id}" for name in ("support", "equipment")]
        try:
            recovery = restart_with_pending_work(task_ids, output) if args.verify_recovery else None
            result.update(wait_for_completion(demo_id=args.demo_id))
            if result["status"] != "passed":
                raise RuntimeError("Background stream did not complete; inspect retained job errors")
            with psycopg.connect(DEMO_DSN, autocommit=True) as connection:
                if recovery:
                    after = domain_snapshot(connection, task_ids)
                    if not set(recovery.pop("records")).issubset(after["evidence"]):
                        raise AssertionError("Restart lost accepted evidence")
                    recovery.update(status="passed", evidence_after=len(after["evidence"]), after_sha256=after["digest"])
                    result["restart"] = recovery
                result["replay"] = verify_replay(connection, assistant, receipts, args.demo_id)
                from scripts.package_capabilities import package
                packaged = package(connection, task_ids, output / "Package")
                result["package"] = {"status": packaged["status"], "path": str(output / "Package/Package.json"), "files": len(packaged["files"])}
        except Exception as exc:
            result.update(status="failed", error={"type": type(exc).__name__, "message": str(exc)})
            raise
        finally:
            (output / "Integration.json").write_bytes(encoded(result))
            request("PATCH",f"/runs/crons/{cron['cron_id']}",{"enabled":False},base=BASE)
            print(json.dumps({"status": result["status"], "receipt": str(output / "Integration.json")}, indent=2), flush=True)
        if args.serve:
            from runtime.audience_server import AudienceServer
            grants = json.loads((output / "Package/AudienceAccess.json").read_text())["grants"]
            server = AudienceServer(DEMO_DSN, grants)
            print(f"Local reports: {server.origin}/login\nPrivate tokens: {output / 'Package/AudienceAccess.json'}", flush=True)
            try:
                server.serve_forever()
            finally:
                server.server_close()
        return 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
