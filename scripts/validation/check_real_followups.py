"""Actual local predictors with deterministic provider fixtures; never final Jev acceptance."""

from __future__ import annotations

import json
import os
from pathlib import Path
from types import SimpleNamespace
import uuid
from unittest.mock import patch

import psycopg
from psycopg.types.json import Jsonb

from runtime.bootstrap import initialize
from runtime.contracts import current_sources
from runtime.evidence import Evidence
from runtime.jobs import enqueue, execute, release_due, runnable
from runtime.ledger import dsn
from runtime.prediction import registry
from runtime.real_semantics import extract_real, scope_for
from runtime.simulation import digest, encoded


class ProviderFixture:
    calls = 0

    def __init__(self,model):
        self.model = model

    def invoke(self,payload):
        type(self).calls += 1
        request_id = "fixture-"+uuid.uuid4().hex
        content = payload["state"]
        if content in ("Login failed","Service working"):
            nouls = {key:{"noul":.95 if content == "Login failed" else .05} for key in payload["questions"]}
            scores = {}
        else:
            value = float(content)
            low = int(value)
            high = min(10,low+1)
            scores = {key:{"score":value,"legend":{str(low):low,str(high):high},
                          "probabilities":{str(low):1-(value-low),str(high):value-low} if high != low else {str(low):1.}}
                      for key in payload["questions"]}
            nouls = {}
        self.last_metadata = {"request_id":request_id,"model":self.model,"cost_usd":.001,"test_fixture":True}
        self.last_response = {"test_fixture":True,"nouls":nouls,"scores":scores}
        return SimpleNamespace(nouls=nouls,choices={},scores=scores,request_id=request_id,
                               model=self.model,usage=SimpleNamespace(input_tokens=10,output_tokens=3))

    async def aclose(self):
        pass


def fixture_extract(*args,**kwargs):
    kwargs["classifier_factory"] = ProviderFixture
    return extract_real(*args,**kwargs)


def main():
    if not os.environ.get("BACKINTEL_TEST_DATABASE_URL") or dsn() != os.environ["BACKINTEL_TEST_DATABASE_URL"] or not psycopg.conninfo.conninfo_to_dict(dsn())["dbname"].startswith("test_"):
        raise PermissionError("Provider-fixture journey requires an explicitly isolated test database")
    initialize()
    output = Path(__file__).resolve().parents[2]/"artifacts/validation/RealFollowups"/("Attempt"+uuid.uuid4().hex[:12])
    output.mkdir(parents=True)
    receipt = {"schema":"backintel-real-followup-fixture/v1","status":"running","candidate":"uncommitted-working-tree",
               "provider":"deterministic local fixture; reported charges are fictional","predictors":"actual local CatBoost and TabICLv2",
               "clock":"due timestamps and retry delays advanced in the isolated test database",
               "actual_paid_provider_calls":0,"actual_provider_usd":0,"local_compute_usd":None,"checks":[]}
    try:
        with psycopg.connect(dsn(),autocommit=True) as connection, patch("runtime.real_pipeline.extract_real",side_effect=fixture_extract), patch("runtime.real_semantics._default_classifier",side_effect=AssertionError("Paid provider forbidden in this check")):
            for scenario in ("support","equipment"):
                store = Evidence(connection,"followup-fixture-"+scenario+"-"+uuid.uuid4().hex[:12])
                def run(operation,identity,**fields):
                    job = enqueue(store,{"scenario":scenario,"operation":operation,**fields},identity)
                    result = execute(job)
                    if result["state"] != "completed":
                        raise AssertionError(result)
                    return store.get(result["result"])
                history = run("real_prepare","prepare")
                followups = run("real_prepare_followups","prepare-followups")
                assert len(current_sources(store,71,history["body"]["task"])) == 24
                sources = [store.get(sha) for sha in history["body"]["sources"]+followups["body"]["sources"]]
                scope = scope_for(store.get(history["body"]["task"]),sources)
                authorization = "fixture-followups-"+uuid.uuid4().hex
                connection.execute("""INSERT INTO backintel.capability_provider_authorizations
                    (authorization_id,provider,model,max_requests,max_input_characters,price_ceiling_known,approved,scope_sha256,scope,expires_at)
                    VALUES (%s,'openrouter','jev-1.13',27,5000,true,true,%s,%s,now()+interval '1 hour')""",(authorization,digest(scope),Jsonb(scope)))
                scheduled = run("real_start","start",provider_authorization_id=authorization)
                assert len(scheduled["body"]["triggers"]) == 26
                while True:
                    connection.execute("""UPDATE backintel.capability_triggers SET due_at=to_timestamp(ordinal.position)
                        FROM (SELECT trigger_id,row_number() OVER (ORDER BY due_at,trigger_id) AS position
                              FROM backintel.capability_triggers WHERE task_id=%s AND state='pending') ordinal
                        WHERE backintel.capability_triggers.trigger_id=ordinal.trigger_id""",(store.task_id,))
                    release_due(connection)
                    pending = connection.execute("SELECT count(*) FROM backintel.capability_jobs WHERE task_id=%s AND state IN ('queued','retry','running')",(store.task_id,)).fetchone()[0]
                    if not pending:
                        break
                    connection.execute("UPDATE backintel.capability_jobs SET due_at=now() WHERE task_id=%s AND state='retry'",(store.task_id,))
                    ready = [j for j in runnable(connection) if connection.execute("SELECT task_id FROM backintel.capability_jobs WHERE job_id=%s",(j,)).fetchone()[0] == store.task_id]
                    if not ready:
                        raise AssertionError("Fixture journey has pending work but no runnable job")
                    assert pending <= 20
                    for job in ready:
                        result = execute(job)
                        if result["state"] not in ("completed","retry"):
                            raise AssertionError(result)
                failed = connection.execute("SELECT job_id,error FROM backintel.capability_jobs WHERE task_id=%s AND state!='completed'",(store.task_id,)).fetchall()
                assert not failed, failed
                assert connection.execute("SELECT count(*) FROM backintel.capability_triggers WHERE task_id=%s AND state='pending'",(store.task_id,)).fetchone()[0] == 0
                initial = store.get(store.find("real_stage_result","history-v1")["body"]["result"])
                assert initial["body"]["mode"] == "synthetic_sources_real_predictors_fixture_semantics"
                assert {(m["body"]["route"],m["body"]["feature_set"]) for m in store.list("model") if m["body"].get("implementation_mode") == "real"} == {(r,f) for r in ("catboost","tabiclv2") for f in ("structured","semantic")}
                assert len(store.list("task")) == 1
                assert store.list("invalidation") and store.list("analysis") and store.list("artifact")
                active = store.get(registry(store,94)["active"])
                assert active["body"]["implementation_mode"] in ("real","native_baseline")
                updated = store.get(store.find("model_update","bounded-update")["body"]["model"])
                assert updated["body"]["implementation_mode"] in ("real","native_baseline")
                assert updated["body"]["training_count"] <= 64
                assert updated["body"]["training_count"] == 24  # Corrected future source must not train on its superseded features.
                before = [r[0] for r in connection.execute("SELECT sha256 FROM backintel.capability_evidence WHERE task_id=%s ORDER BY sha256",(store.task_id,))]
                calls_before = ProviderFixture.calls
                jobs = connection.execute("SELECT job_id FROM backintel.capability_jobs WHERE task_id=%s ORDER BY sequence",(store.task_id,)).fetchall()
                assert len(jobs) == 45
                assert all(execute(j[0])["reused"] for j in jobs)
                assert ProviderFixture.calls == calls_before
                assert [r[0] for r in connection.execute("SELECT sha256 FROM backintel.capability_evidence WHERE task_id=%s ORDER BY sha256",(store.task_id,))] == before
                requests = connection.execute("SELECT count(*) FROM backintel.capability_model_requests WHERE task_id=%s",(store.task_id,)).fetchone()[0]
                assert requests == 27
                receipt["checks"].append({"scenario":scenario,"task_id":store.task_id,"completed_jobs":len(jobs),
                    "provider_fixture_requests":requests,"initial_result":initial["sha256"],"active_model":active["sha256"],
                    "models":len(store.list("model")),"replay_unchanged":True,"correction_invalidations":len(store.list("invalidation")),
                    "update_training_rows":updated["body"]["training_count"]})
                print(json.dumps(receipt["checks"][-1]),flush=True)
        receipt["status"] = "passed"
    except Exception as exc:
        receipt.update(status="failed",error={"type":type(exc).__name__,"message":str(exc)})
        raise
    finally:
        path = output/"Followups.json"
        path.write_bytes(encoded(receipt))
        print(json.dumps({"status":receipt["status"],"receipt":str(path)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
