"""Native-clock scoped scheduling and tmpfs checks using source preparation only."""

import json
from pathlib import Path
import subprocess
import time
import uuid

import psycopg

from runtime.evidence import Evidence
from runtime.jobs import schedule
from runtime.simulation import encoded
from scripts.capability_demo import BASE, DEMO_DSN, ROOT
from scripts.jev.run_review_batch import request
from scripts.real_demo import RUN_LOCK, clear_credential, install_credential, restart_pending, scheduler, set_scheduler
from scripts.real_capabilities import submit


def main():
    suffix = uuid.uuid4().hex[:8]
    demo_id = "driver-clock-"+suffix
    output = ROOT/"artifacts/validation/RealDriverRuntime"/("Attempt"+suffix)
    output.mkdir(parents=True,mode=0o700)
    task_ids = [f"{name}-real-{demo_id}" for name in ("support","equipment")]
    receipt = {"status":"running","candidate":"uncommitted-working-tree","operations":"source preparation only",
               "credential":"dummy non-provider test value; no Keychain retrieval","actual_paid_provider_calls":0}
    cron_id = ignored = None
    try:
        with psycopg.connect(DEMO_DSN,autocommit=True) as connection:
            if not connection.execute("SELECT pg_try_advisory_lock(%s)",(RUN_LOCK,)).fetchone()[0]:
                raise RuntimeError("A real-run command owns the runtime; validation must wait")
            assistants = request("POST","/assistants/search",{"graph_id":"capability_platform","limit":1},base=BASE)
            schemas = request("GET",f"/assistants/{assistants[0]['assistant_id']}/schemas",base=BASE)
            assert "task_ids" in schemas["input_schema"]["properties"]
            for scenario in ("support","equipment"):
                assert submit("prepare",scenario,demo_id,"native-history")["result"]["state"] == "completed"
            before_calls = connection.execute("SELECT count(*) FROM backintel.capability_model_requests").fetchone()[0]
            install_credential("fixture-only-not-a-provider-key",task_ids,time.time()+60,output.name)
            program = """import json,os,stat
from pathlib import Path
from runtime.real_semantics import runtime_credential
p=Path('/run/backintel-credentials/openrouter.json')
r=json.loads(p.read_text())
assert stat.S_IMODE(p.stat().st_mode)==0o600
assert runtime_credential(r['task_ids'][0]) is not None
assert runtime_credential('unapproved-task') is None
print(json.dumps({'mode':'0600','task_bound':True,'tasks':len(r['task_ids'])}))
"""
            checked = subprocess.run(["docker","compose","-f","compose.capabilities.yml","exec","-T","runtime","python","-c",program],
                                     cwd=ROOT,capture_output=True,text=True,check=True,timeout=15)
            receipt["tmpfs_credential"] = json.loads(checked.stdout)
            due = float(connection.execute("SELECT extract(epoch FROM now())").fetchone()[0])-1
            for scenario,task_id in zip(("support","equipment"),task_ids):
                schedule(Evidence(connection,task_id),"event",{"operation":"real_prepare","scenario":scenario},due,"native-prepare")
            ignored = schedule(Evidence(connection,"support-real-ignored-"+suffix),"event",{"operation":"real_prepare","scenario":"support"},due,"untouched")
            connection.execute("LISTEN backintel_capability_jobs")
            cron_id = scheduler(assistants[0]["assistant_id"],task_ids,demo_id,time.time()+45)
            receipt["recovery"] = restart_pending(connection,task_ids,cron_id,"fixture-only-not-a-provider-key",time.time()+60,output)
            set_scheduler(cron_id,True)
            deadline = time.monotonic()+30
            while True:
                rows = connection.execute("SELECT task_id,state,result_sha256 FROM backintel.capability_jobs WHERE task_id=ANY(%s) AND trigger_id IS NOT NULL",(task_ids,)).fetchall()
                if len(rows)==2 and all(row[1]=="completed" for row in rows):
                    break
                if any(row[1] in ("failed","cancelled") for row in rows) or time.monotonic() >= deadline:
                    raise AssertionError("Native-clock preparation did not complete")
                next(connection.notifies(timeout=max(0,deadline-time.monotonic()),stop_after=1),None)
            set_scheduler(cron_id,False)
            assert connection.execute("SELECT state FROM backintel.capability_triggers WHERE trigger_id=%s",(ignored,)).fetchone()[0]=="pending"
            for task_id,state,sha in rows:
                assert Evidence(connection,task_id).get(sha)["body"]["source_records"]==24
            assert connection.execute("SELECT count(*) FROM backintel.capability_model_requests").fetchone()[0]==before_calls
            connection.execute("DELETE FROM backintel.capability_triggers WHERE trigger_id=%s AND state='pending'",(ignored,))
            ignored = None
            receipt.update(status="passed",scheduler="aegra_native_cron",cron_id=cron_id,completed_tasks=task_ids,unrelated_trigger_unchanged=True)
    except Exception as exc:
        receipt.update(status="failed",error={"type":type(exc).__name__,"message":str(exc)})
        raise
    finally:
        if cron_id:
            try:
                set_scheduler(cron_id,False)
            except Exception as exc:
                receipt.update(status="failed",scheduler_cleanup=type(exc).__name__)
        try:
            clear_credential(output.name)
            check = subprocess.run(["docker","compose","-f","compose.capabilities.yml","exec","-T","runtime","python","-c",
                                    "from pathlib import Path; assert not Path('/run/backintel-credentials/openrouter.json').exists()"],
                                   cwd=ROOT,capture_output=True,text=True,timeout=15)
            receipt["dummy_credential_removed"] = check.returncode==0
            if check.returncode:
                receipt["status"] = "failed"
        except Exception as exc:
            receipt.update(status="failed",credential_cleanup=type(exc).__name__)
        if ignored:
            with psycopg.connect(DEMO_DSN,autocommit=True) as connection:
                connection.execute("DELETE FROM backintel.capability_triggers WHERE trigger_id=%s AND state='pending'",(ignored,))
        path = output/"Checks.json"
        path.write_bytes(encoded(receipt))
        print(json.dumps({"status":receipt["status"],"receipt":str(path)}))
    return 0 if receipt["status"]=="passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
