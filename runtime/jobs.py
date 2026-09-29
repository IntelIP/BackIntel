"""Durable bounded jobs. Aegra's native cron scheduler is the only timer owner."""
from __future__ import annotations

import time

import psycopg
from psycopg.types.json import Jsonb

from runtime.evidence import Evidence
from runtime.ledger import dsn
from runtime.real_semantics import usage_for
from runtime.simulation import digest, encoded


def schedule(store, kind: str, payload: dict, due_at: float, request_id: str,
             repeat_seconds: int | None = None, occurrences=1) -> str:
    if kind not in ("event","schedule","deadline","staleness","on_demand") or len(encoded(payload)) > 100_000:
        raise ValueError("Invalid or oversized trigger")
    if type(occurrences) is not int or not 1 <= occurrences <= 100 or (occurrences > 1 and (type(repeat_seconds) is not int or repeat_seconds < 1)):
        raise ValueError("Recurring trigger requires a bounded interval/count")
    trigger_id = digest([store.task_id,request_id])
    with store.connection.transaction():
        store.lock()
        existing = store.connection.execute("SELECT kind,payload,repeat_seconds FROM backintel.capability_triggers WHERE trigger_id=%s",(trigger_id,)).fetchone()
        if existing:
            if existing != (kind,payload,repeat_seconds):
                raise ValueError("Conflicting trigger identity")
            return trigger_id
        pending = store.connection.execute("SELECT count(*) FROM backintel.capability_triggers WHERE task_id=%s AND state='pending'",(store.task_id,)).fetchone()[0]
        if pending >= 100:
            raise ValueError("Trigger backpressure limit reached")
        store.connection.execute("""INSERT INTO backintel.capability_triggers
            (trigger_id,task_id,kind,payload,due_at,repeat_seconds,remaining) VALUES (%s,%s,%s,%s,to_timestamp(%s),%s,%s)""",
            (trigger_id,store.task_id,kind,Jsonb(payload),due_at,repeat_seconds,occurrences))
    return trigger_id


def enqueue(store, payload: dict, request_id: str, trigger_id=None) -> str:
    if len(encoded(payload)) > 100_000:
        raise ValueError("Job payload budget exceeded")
    key, fingerprint = digest([store.task_id,request_id]), digest(payload)
    with store.connection.transaction():
        store.lock()
        existing = store.connection.execute("SELECT input_sha256 FROM backintel.capability_jobs WHERE job_id=%s",(key,)).fetchone()
        if existing:
            if existing[0] != fingerprint:
                raise ValueError("Job identity reused with conflicting input")
            return key
        pending = store.connection.execute("SELECT count(*) FROM backintel.capability_jobs WHERE task_id=%s AND state IN ('queued','running','retry')",(store.task_id,)).fetchone()[0]
        if pending >= 20:
            raise ValueError("Job backpressure limit reached")
        store.connection.execute("""INSERT INTO backintel.capability_jobs(job_id,task_id,trigger_id,payload,input_sha256)
            VALUES (%s,%s,%s,%s,%s)""",(key,store.task_id,trigger_id,Jsonb(payload),fingerprint))
    return key


def release_due(connection, task_ids=None) -> list[str]:
    jobs = []
    with connection.transaction():
        # The native scheduler can overlap dispatch runs; only one releases each occurrence.
        due = connection.execute("""SELECT trigger_id,task_id,payload,occurrence,remaining,repeat_seconds
            FROM backintel.capability_triggers WHERE state='pending' AND due_at<=now()
            AND (%s::text[] IS NULL OR task_id=ANY(%s::text[]))
            ORDER BY due_at,trigger_id FOR UPDATE SKIP LOCKED LIMIT 20""",(task_ids,task_ids)).fetchall()
        for trigger, task_id, payload, occurrence, remaining, interval in due:
            store = Evidence(connection,task_id)
            store.lock()
            pending = connection.execute("""SELECT count(*) FROM backintel.capability_jobs
                WHERE task_id=%s AND state IN ('queued','running','retry')""",(task_id,)).fetchone()[0]
            if pending >= 20:
                continue
            if occurrence and "at" in payload:
                payload = {**payload,"at":payload["at"]+occurrence*(interval or 0)}
            jobs.append(enqueue(store,payload,f"{trigger}:{occurrence}",trigger))
            connection.execute("""UPDATE backintel.capability_triggers SET remaining=remaining-1,occurrence=occurrence+1,
                state=CASE WHEN remaining=1 THEN 'fired' ELSE 'pending' END,
                due_at=CASE WHEN remaining>1 THEN due_at+make_interval(secs=>%s) ELSE due_at END
                WHERE trigger_id=%s""",(interval or 0,trigger))
    return jobs


def cancel(connection, job_id: str) -> str:
    with connection.transaction():
        row = connection.execute("""UPDATE backintel.capability_jobs SET cancel_requested=true,
            state=CASE WHEN state IN ('queued','retry') THEN 'cancelled' ELSE state END,updated_at=now()
            WHERE job_id=%s AND state NOT IN ('completed','failed','cancelled') RETURNING state""",(job_id,)).fetchone()
        return row[0] if row else "unchanged"


def claim(connection, job_id: str) -> dict | None:
    with connection.transaction():
        row = connection.execute("""UPDATE backintel.capability_jobs SET state='running',attempts=attempts+1,
            lease_until=now()+interval '30 seconds',updated_at=now()
            WHERE job_id=%s AND cancel_requested=false AND attempts<max_attempts AND due_at<=now()
            AND (state IN ('queued','retry') OR (state='running' AND lease_until<now()))
            RETURNING task_id,payload,attempts,max_attempts""",(job_id,)).fetchone()
        if row:
            Evidence(connection,row[0]).put("job_attempt_start",f"{job_id}:{row[2]}",
                {"job_id":job_id,"attempt":row[2],"status":"running"},int(time.time()))
        return dict(zip(("task_id","payload","attempt","max_attempts"),row)) if row else None


def resume_failed(connection, job_id: str, reason: str) -> None:
    if not reason.strip():
        raise ValueError("Repair reason required")
    with connection.transaction():
        row = connection.execute("""UPDATE backintel.capability_jobs SET state='retry',max_attempts=attempts+1,
            due_at=now(),updated_at=now() WHERE job_id=%s AND state='failed' AND attempts<5
            RETURNING task_id,attempts""",(job_id,)).fetchone()
        if row is None:
            raise ValueError("Only failed jobs below the repair limit may resume")
        Evidence(connection,row[0]).put("job_repair",f"{job_id}:{row[1]}",
            {"job_id":job_id,"after_attempt":row[1],"reason":reason},int(time.time()))


class JobCancelled(Exception):
    pass


def execute(job_id: str, handler=None) -> dict:
    if handler is None:
        from runtime.capability_pipeline import handle
        handler = handle
    with psycopg.connect(dsn(),autocommit=True) as connection:
        connection.execute("SET statement_timeout='30s'")
        job = claim(connection,job_id)
        if job is None:
            row = connection.execute("SELECT state,result_sha256 FROM backintel.capability_jobs WHERE job_id=%s",(job_id,)).fetchone()
            if row is None:
                raise ValueError("Unknown job")
            return {"job_id":job_id,"state":row[0],"result":row[1],"reused":True}
        started = time.perf_counter()
        previous_requests = None
        try:
            with connection.transaction():
                store = Evidence(connection,job["task_id"])
                store.lock()
                previous_requests = [r[0] for r in connection.execute(
                    "SELECT request_key FROM backintel.capability_model_requests WHERE task_id=%s", (job["task_id"],)).fetchall()]
                if job["payload"].get("fail_once") and job["attempt"] == 1:
                    raise TimeoutError("Injected synthetic transient failure")
                result = handler(store,job["payload"])
                wall_ms = (time.perf_counter()-started)*1000
                if wall_ms > 25000:
                    raise TimeoutError("Job wall-time budget exceeded")
                current = connection.execute("SELECT cancel_requested,attempts FROM backintel.capability_jobs WHERE job_id=%s FOR UPDATE",(job_id,)).fetchone()
                if current[0] or current[1] != job["attempt"]:
                    raise JobCancelled("Cancelled or lease ownership changed before acceptance")
                connection.execute("""UPDATE backintel.capability_jobs SET state='completed',result_sha256=%s,
                    lease_until=NULL,error=NULL,wall_ms=%s,updated_at=now() WHERE job_id=%s""",(result["sha256"],wall_ms,job_id))
                store.put("job_attempt_result",f"{job_id}:{job['attempt']}",
                    {"job_id":job_id,"attempt":job["attempt"],"status":"completed","wall_ms":wall_ms,
                     **usage_for(store, excluding=previous_requests)},int(time.time()),[result["sha256"]])
                connection.execute("SELECT pg_notify('backintel_capability_jobs',%s)",(job_id,))
            return {"job_id":job_id,"state":"completed","result":result["sha256"],"reused":False}
        except Exception as error:
            state = "cancelled" if isinstance(error,JobCancelled) else "retry" if job["attempt"] < job["max_attempts"] else "failed"
            with connection.transaction():
                usage = usage_for(Evidence(connection,job["task_id"]), excluding=previous_requests, strict=False) if previous_requests is not None else {
                    "provider_calls":0,"provider_usd":0,"local_compute_usd":None,"provider_fixture_requests":0,
                    "provider_requests_admitted":0,"provider_request_keys":[]}
                connection.execute("""UPDATE backintel.capability_jobs SET state=%s,error=%s,lease_until=NULL,
                    due_at=now()+interval '1 second',wall_ms=%s,updated_at=now() WHERE job_id=%s AND attempts=%s""",
                    (state,str(error)[:2000],(time.perf_counter()-started)*1000,job_id,job["attempt"]))
                Evidence(connection,job["task_id"]).put("job_attempt_result",f"{job_id}:{job['attempt']}",
                    {"job_id":job_id,"attempt":job["attempt"],"status":state,"error":str(error)[:2000],
                     **usage,
                     "wall_ms":(time.perf_counter()-started)*1000},int(time.time()))
                connection.execute("SELECT pg_notify('backintel_capability_jobs',%s)",(job_id,))
            return {"job_id":job_id,"state":state,"error":str(error)}


def runnable(connection, task_ids=None) -> list[str]:
    return [r[0] for r in connection.execute("""SELECT j.job_id FROM backintel.capability_jobs j
        WHERE j.due_at<=now() AND (j.state IN ('queued','retry') OR (j.state='running' AND j.lease_until<now()))
        AND (%s::text[] IS NULL OR j.task_id=ANY(%s::text[]))
        AND NOT EXISTS (SELECT 1 FROM backintel.capability_jobs earlier WHERE earlier.task_id=j.task_id
            AND earlier.sequence<j.sequence AND earlier.state IN ('queued','running','retry','failed'))
        ORDER BY j.sequence LIMIT 4""",(task_ids,task_ids)).fetchall()]


def dispatch(task_ids=None) -> dict:
    with psycopg.connect(dsn(),autocommit=True) as connection:
        if not connection.execute("SELECT pg_try_advisory_lock(81827026)").fetchone()[0]:
            return {"status":"dispatcher_already_running","jobs":[]}
        release_due(connection,task_ids)
        # A killed last attempt becomes failed, not permanently running.
        connection.execute("""UPDATE backintel.capability_jobs SET state=CASE WHEN cancel_requested THEN 'cancelled' ELSE 'failed' END,
            error='Worker lease expired at attempt limit',lease_until=NULL,updated_at=now()
            WHERE state='running' AND lease_until<now() AND (attempts>=max_attempts OR cancel_requested)
            AND (%s::text[] IS NULL OR task_id=ANY(%s::text[]))""",(task_ids,task_ids))
        results = [execute(job_id) for job_id in runnable(connection,task_ids)]
        return {"status":"completed","jobs":results}
