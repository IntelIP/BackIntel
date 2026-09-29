"""Prepare or run both real-model scenarios through the isolated native scheduler."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import subprocess
import time
import uuid

import psycopg

from runtime.evidence import Evidence
from runtime.jobs import execute
from runtime.real_pipeline import require_approved_scope
from runtime.real_semantics import scope_for, usage_for
from runtime.simulation import encoded
from scripts.capability_demo import BASE, DEMO_DSN, ROOT, domain_snapshot, status
from scripts.jev.run_review_batch import request
from scripts.package_capabilities import package
from scripts.real_capabilities import submit

SCENARIOS = ("support","equipment")
CREDENTIAL_PATH = "/run/backintel-credentials/openrouter.json"
RUN_LOCK = 81827027


def startup(output):
    active = subprocess.run(["docker","compose","-f","compose.capabilities.yml","ps","--status","running","--quiet","runtime"],
                            cwd=ROOT,capture_output=True,text=True,check=True,timeout=15).stdout.strip()
    connection = psycopg.connect(DEMO_DSN,autocommit=True) if active else None
    try:
        if connection:
            if not connection.execute("SELECT pg_try_advisory_lock(%s)",(RUN_LOCK,)).fetchone()[0]:
                raise RuntimeError("Another real-run command owns the isolated runtime")
            pending = connection.execute("""SELECT (SELECT count(*) FROM backintel.capability_jobs WHERE state IN ('queued','running','retry'))
                + (SELECT count(*) FROM backintel.capability_triggers WHERE state='pending')""").fetchone()[0]
            if pending:
                raise RuntimeError("Development work is pending. Resume the existing runtime with --no-start; startup will not replace it.")
        environment = {**os.environ,"BACKINTEL_WITH_MODELS":"1"}
        with (output/"Startup.log").open("w") as log:
            subprocess.run(["docker","compose","-f","compose.capabilities.yml","up","--build","--detach","--wait","--wait-timeout","120"],
                           cwd=ROOT,env=environment,stdout=log,stderr=subprocess.STDOUT,check=True,timeout=600)
    finally:
        if connection:
            connection.close()


def prepare(connection,demo_id):
    proposals = {}
    for scenario in SCENARIOS:
        for stage in ("prepare","prepare_followups"):
            result = submit(stage,scenario,demo_id,"real-run-"+stage+"-v1")["result"]
            if result["state"] != "completed":
                raise RuntimeError("Source preparation did not complete: "+str(result))
        store = Evidence(connection,f"{scenario}-real-{demo_id}")
        history = store.find("real_plan","history-v1")
        followups = store.find("real_plan","followups-v1")
        task = store.get(history["body"]["task"])
        sources = [store.get(sha) for sha in history["body"]["sources"]+followups["body"]["sources"]]
        proposals[scenario] = {"task_id":store.task_id,"model":task["body"]["observation_provider"]["version"],
            "scope":scope_for(task,sources),"source_versions":len(sources),"maximum_new_requests":len(sources),
            "maximum_input_characters":max(len(r["body"]["content"]) for r in sources),
            "questions":task["body"]["questions"],
            "inputs":[{"source_sha256":r["sha256"],"content":r["body"]["content"],"available_at":r["available_at"]} for r in sources],
            "history_plan":history["sha256"],"followup_plan":followups["sha256"],
            "approval":"separate approval required; this proposal creates no authorization"}
    return proposals


def preflight(connection,proposals,authorizations,deadline):
    if set(authorizations) != set(SCENARIOS) or any(not isinstance(v,str) or not 1 <= len(v) <= 128 for v in authorizations.values()):
        raise ValueError("Authorization file must map support and equipment to existing approved authorization IDs")
    remaining = 0
    for scenario,proposal in proposals.items():
        store = Evidence(connection,proposal["task_id"])
        usage = usage_for(store)
        if usage["provider_fixture_requests"]:
            raise PermissionError("The real run cannot use fixture semantic history")
        completed = {r[0] for r in connection.execute("SELECT source_sha256 FROM backintel.capability_model_requests WHERE task_id=%s AND state='completed'",(store.task_id,))}
        missing = set(proposal["scope"]["source_sha256s"])-completed
        if not missing:
            continue
        authorization = authorizations[scenario]
        task = store.get(proposal["scope"]["task_sha256"])
        require_approved_scope(store,task,proposal["scope"],authorization)
        limit,characters,priced,expires,max_usd = connection.execute("""SELECT max_requests,max_input_characters,price_ceiling_known,expires_at,max_measured_usd
            FROM backintel.capability_provider_authorizations WHERE authorization_id=%s""",(authorization,)).fetchone()
        used,spent = connection.execute("SELECT count(*),coalesce(sum((metadata->>'cost_usd')::numeric),0) FROM backintel.capability_model_requests WHERE authorization_id=%s",(authorization,)).fetchone()
        if limit-used < len(missing) or characters < proposal["maximum_input_characters"] or (not priced and (limit != 1 or len(missing) != 1)):
            raise PermissionError("Prepared batch exceeds the approved request, character or known-price limits")
        if max_usd is not None and spent >= max_usd:
            raise PermissionError("The approved measured provider budget is exhausted")
        deadline = min(deadline,expires.timestamp())
        remaining += len(missing)
    if remaining and deadline <= time.time():
        raise PermissionError("The approved execution window expired")
    return remaining,deadline


def install_credential(credential,task_ids,deadline,owner_id):
    # The value travels over stdin into container tmpfs, never argv, logs or Docker environment configuration.
    program = """import json,os,sys,time
from pathlib import Path
path=Path('/run/backintel-credentials/openrouter.json')
assert any(row.split()[1:3]==['/run/backintel-credentials','tmpfs'] for row in Path('/proc/mounts').read_text().splitlines()), 'Credential mount must be tmpfs'
record=json.load(sys.stdin)
if path.exists():
    previous=json.loads(path.read_text())
    if previous.get('owner_id')!=record['owner_id'] and previous['expires_at']>time.time():
        raise RuntimeError('Another run owns the live runtime credential')
temporary=path.with_name(record['owner_id']+'.tmp')
with os.fdopen(os.open(temporary,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600),'w') as target:
    json.dump(record,target)
os.replace(temporary,path)
"""
    subprocess.run(["docker","compose","-f","compose.capabilities.yml","exec","-T","runtime","python","-c",program],
                   cwd=ROOT,input=json.dumps({"key":credential,"task_ids":task_ids,"expires_at":deadline,"owner_id":owner_id}),text=True,
                   stdout=subprocess.PIPE,stderr=subprocess.PIPE,check=True,timeout=15)


def clear_credential(owner_id):
    subprocess.run(["docker","compose","-f","compose.capabilities.yml","exec","-T","runtime","python","-c",
                    "import json,sys; from pathlib import Path; p=Path('/run/backintel-credentials/openrouter.json'); owner=sys.stdin.read(); p.unlink() if p.exists() and json.loads(p.read_text()).get('owner_id')==owner else None; p.with_name(owner+'.tmp').unlink(missing_ok=True)"],
                   cwd=ROOT,input=owner_id,text=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE,check=True,timeout=15)


def scheduler(assistant,task_ids,demo_id,deadline):
    purpose = "backintel-real-"+demo_id
    crons = request("POST","/runs/crons/search",{"assistant_id":assistant,"limit":100},base=BASE)
    cron = next((c for c in crons if c.get("metadata",{}).get("purpose") == purpose),None)
    end = datetime.fromtimestamp(deadline,timezone.utc).isoformat()
    if cron is None:
        cron = request("POST","/runs/crons",{"assistant_id":assistant,"schedule":"*/2 * * * * *","enabled":False,
                       "input":{"operation":"dispatch","task_ids":task_ids},"metadata":{"purpose":purpose},"end_time":end},base=BASE)
    else:
        request("PATCH",f"/runs/crons/{cron['cron_id']}",{"enabled":False,"end_time":end,
                "input":{"operation":"dispatch","task_ids":task_ids}},base=BASE)
    return cron["cron_id"]


def set_scheduler(cron_id,enabled):
    request("PATCH",f"/runs/crons/{cron_id}",{"enabled":enabled},base=BASE)


def restart_pending(connection,task_ids,cron_id,credential,deadline,output):
    set_scheduler(cron_id,False)
    connection.execute("SET lock_timeout='45s'")
    connection.execute("SELECT pg_advisory_lock(81827026)")
    try:
        pending = connection.execute("SELECT count(*) FROM backintel.capability_triggers WHERE task_id=ANY(%s) AND state='pending'",(task_ids,)).fetchone()[0]
        if not pending:
            raise ValueError("Recovery verification needs pending work; replay completed work without --verify-recovery")
        before = domain_snapshot(connection,task_ids)
        with (output/"Restart.log").open("w") as log:
            subprocess.run(["docker","compose","-f","compose.capabilities.yml","restart","runtime"],cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,check=True,timeout=60)
            subprocess.run(["docker","compose","-f","compose.capabilities.yml","up","--detach","--wait","--no-build","--no-recreate","runtime"],cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,check=True,timeout=120)
        if credential:
            install_credential(credential,task_ids,deadline,output.name)
        assert domain_snapshot(connection,task_ids) == before, "Restart changed accepted evidence or jobs"
        assert connection.execute("SELECT count(*) FROM backintel.capability_triggers WHERE task_id=ANY(%s) AND state='pending'",(task_ids,)).fetchone()[0] == pending
        receipt = {"status":"passed","pending_triggers":pending,"domain_digest":before["digest"],"restart_boundary":"between dispatch jobs; no in-flight paid request interrupted"}
        (output/"Restart.json").write_bytes(encoded(receipt))
        return receipt
    finally:
        connection.execute("SELECT pg_advisory_unlock(81827026)")


def wait_for_run(connection,demo_id,deadline):
    connection.execute("LISTEN backintel_capability_jobs")
    task_ids = [f"{name}-real-{demo_id}" for name in SCENARIOS]
    while True:
        progress = status(connection,"real-"+demo_id)
        if progress["status"] != "running":
            if progress["status"] != "passed":
                raise RuntimeError("Real workflow stopped: "+str(progress["errors"]))
            completed = {r[0] for r in connection.execute("""SELECT task_id FROM backintel.capability_jobs
                WHERE task_id=ANY(%s) AND state='completed' AND payload->>'operation'='real_event'
                  AND payload->>'action'='artifact_refresh'""",(task_ids,))}
            if completed != set(task_ids):
                raise RuntimeError("Both final report stages must complete before packaging")
            return progress
        remaining = deadline-time.time()
        if remaining <= 0:
            raise TimeoutError("Bounded real-run window ended; persisted jobs may be resumed with matching approval")
        next(connection.notifies(timeout=min(remaining,30),stop_after=1),None)


def replay(connection,task_ids):
    before = domain_snapshot(connection,task_ids)
    prior = {key:os.environ.get(key) for key in ("BACKINTEL_APP_DATABASE_URL","BACKINTEL_TEST_DATABASE_URL")}
    os.environ.update(BACKINTEL_APP_DATABASE_URL=DEMO_DSN,BACKINTEL_TEST_DATABASE_URL=DEMO_DSN)
    try:
        jobs = connection.execute("SELECT job_id FROM backintel.capability_jobs WHERE task_id=ANY(%s) ORDER BY sequence",(task_ids,)).fetchall()
        assert all(execute(row[0]).get("reused") for row in jobs)
    finally:
        for key,value in prior.items():
            if value is None:
                os.environ.pop(key,None)
            else:
                os.environ[key] = value
    assert domain_snapshot(connection,task_ids) == before
    return {"status":"passed","jobs":len(jobs),"domain_digest":before["digest"]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--demo-id",required=True)
    parser.add_argument("--prepare-only",action="store_true")
    parser.add_argument("--authorizations",type=Path,help="JSON mapping support/equipment to existing approved authorization IDs")
    parser.add_argument("--no-start",action="store_true",help="Reuse the running model-enabled isolated service")
    parser.add_argument("--verify-recovery",action="store_true")
    parser.add_argument("--timeout",type=int,default=900)
    args = parser.parse_args()
    if not re.fullmatch(r"[a-z][a-z0-9-]{0,24}",args.demo_id) or not 60 <= args.timeout <= 3600:
        parser.error("Use a bounded demo identity and 60..3600 second execution window")
    if args.prepare_only and (args.authorizations or args.verify_recovery):
        parser.error("Preparation does not use authorizations or restart an active journey")
    if not args.prepare_only and not args.authorizations:
        parser.error("Real execution requires an existing approved authorization map; use --prepare-only first")
    output = ROOT/"artifacts/validation/RealDemo"/args.demo_id/("Attempt"+uuid.uuid4().hex[:12])
    output.mkdir(parents=True,mode=0o700)
    receipt = {"schema":"backintel-real-demo/v1","status":"running","candidate":"uncommitted-working-tree",
               "demo_id":args.demo_id,"final_real_model_acceptance":"blocked","exact_commit_acceptance":"blocked"}
    cron_id = credential = None
    credential_installed = False
    try:
        if not args.no_start:
            startup(output)
        with psycopg.connect(DEMO_DSN,autocommit=True) as connection:
            if not connection.execute("SELECT pg_try_advisory_lock(%s)",(RUN_LOCK,)).fetchone()[0]:
                raise RuntimeError("Another real-run command is active; its native workflow remains running")
            proposals = prepare(connection,args.demo_id)
            (output/"AuthorizationScopes.json").write_bytes(encoded(proposals))
            receipt["authorization_scopes"] = str(output/"AuthorizationScopes.json")
            if args.prepare_only:
                receipt.update(status="passed",stage="preparation_only",paid_provider_calls=0)
                return 0
            authorizations = json.loads(args.authorizations.read_text())
            remaining,deadline = preflight(connection,proposals,authorizations,time.time()+args.timeout)
            task_ids = [proposals[name]["task_id"] for name in SCENARIOS]
            assistants = request("POST","/assistants/search",{"graph_id":"capability_platform","limit":1},base=BASE)
            if not assistants:
                raise RuntimeError("The isolated capability assistant is unavailable")
            schemas = request("GET",f"/assistants/{assistants[0]['assistant_id']}/schemas",base=BASE)
            if "task_ids" not in schemas.get("input_schema",{}).get("properties",{}):
                raise RuntimeError("The running image lacks task-scoped dispatch; update it while quiescent before real execution")
            if remaining:
                credential = subprocess.run(["security","find-generic-password","-s","BackIntel OpenRouter","-a","runtime","-w"],
                                            capture_output=True,text=True,check=True,timeout=15).stdout.rstrip("\n")
                if not credential:
                    raise RuntimeError("The existing Keychain credential is empty")
                receipt["credential"] = {"source":"existing macOS Keychain","runtime_storage":"task-scoped expiring tmpfs","expires_at":deadline,"owner_id":output.name}
                credential_installed = True
                install_credential(credential,task_ids,deadline,output.name)
            cron_id = scheduler(assistants[0]["assistant_id"],task_ids,args.demo_id,deadline)
            receipt.update(cron_id=cron_id,scheduler="bounded_task_scoped_aegra_native_cron",task_ids=task_ids)
            for scenario in SCENARIOS:
                result = submit("start",scenario,args.demo_id,"real-run-start-v1",provider_authorization_id=authorizations[scenario])["result"]
                if result["state"] != "completed":
                    raise RuntimeError("Durable start did not complete: "+str(result))
            if args.verify_recovery:
                receipt["recovery"] = restart_pending(connection,task_ids,cron_id,credential,deadline,output)
            set_scheduler(cron_id,True)
            print(json.dumps({"stage":"running","demo_id":args.demo_id,"new_requests_within_approved_scopes":remaining}),flush=True)
            receipt["workflow"] = wait_for_run(connection,args.demo_id,deadline)
            set_scheduler(cron_id,False)
            cron_id = None
            if credential_installed:
                clear_credential(output.name)
                credential_installed = False
                credential = None
                receipt["credential"]["removed"] = True
            receipt["replay"] = replay(connection,task_ids)
            packaged = package(connection,task_ids,output/"Package",mode="real")
            receipt.update(status="passed",package=str(output/"Package/Package.json"),paid_provider_calls=packaged["paid_provider_calls"],
                           provider_usd=packaged["provider_usd"],local_compute_usd=None)
    except Exception as exc:
        message = str(exc).replace(credential,"[REDACTED]") if credential else str(exc)
        receipt.update(status="blocked",error={"type":type(exc).__name__,"message":message})
    finally:
        if cron_id:
            try:
                set_scheduler(cron_id,False)
            except Exception as exc:
                receipt.update(status="blocked",scheduler_cleanup=type(exc).__name__)
        if credential_installed:
            try:
                clear_credential(output.name)
                receipt["credential"]["removed"] = True
            except Exception as exc:
                receipt.update(status="blocked",credential_cleanup=type(exc).__name__)
        credential = None
        path = output/"Integration.json"
        path.write_bytes(encoded(receipt))
        print(json.dumps({"status":receipt["status"],"receipt":str(path)}),flush=True)
    return 0 if receipt["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
