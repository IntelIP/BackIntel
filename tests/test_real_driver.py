"""Driver boundaries use fictional authorizations and keys; no provider calls."""

import json
import os
from pathlib import Path
import tempfile
import time
import unittest
import uuid
from unittest.mock import patch

import psycopg
from psycopg.types.json import Jsonb

from runtime.bootstrap import initialize
from runtime.evidence import Evidence
from runtime.jobs import dispatch, enqueue, schedule
from runtime.ledger import dsn
from runtime.real_pipeline import prepare_followups, prepare_history
from runtime.real_semantics import runtime_credential, scope_for
from runtime.simulation import digest
from scripts import real_demo


class RealDriverTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not os.environ.get("BACKINTEL_TEST_DATABASE_URL") or dsn() != os.environ["BACKINTEL_TEST_DATABASE_URL"] or not psycopg.conninfo.conninfo_to_dict(dsn())["dbname"].startswith("test_"):
            raise RuntimeError("Driver checks require an explicitly isolated test database")
        initialize()

    def setUp(self):
        self.connection = psycopg.connect(dsn(),autocommit=True)
        self.addCleanup(self.connection.close)
        self.proposals, self.stores, self.authorizations = {}, {}, {}
        for scenario in real_demo.SCENARIOS:
            store = Evidence(self.connection,"driver-"+scenario+"-"+uuid.uuid4().hex[:12])
            history = prepare_history(store,scenario)
            future = prepare_followups(store,history)
            task = store.get(history["body"]["task"])
            sources = [store.get(sha) for sha in history["body"]["sources"]+future["body"]["sources"]]
            self.stores[scenario] = store
            self.proposals[scenario] = {"task_id":store.task_id,"scope":scope_for(task,sources),"maximum_input_characters":100}
            authorization = "driver-fixture-"+uuid.uuid4().hex
            self.authorizations[scenario] = authorization
            scope = self.proposals[scenario]["scope"]
            self.connection.execute("""INSERT INTO backintel.capability_provider_authorizations
                (authorization_id,provider,model,max_requests,max_input_characters,price_ceiling_known,approved,scope_sha256,scope,expires_at)
                VALUES (%s,'openrouter','jev-1.13',27,5000,true,true,%s,%s,now()+interval '1 hour')""",(authorization,digest(scope),Jsonb(scope)))

    def test_both_approvals_precede_credential_and_scheduler_access(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/"Authorizations.json"
            path.write_text(json.dumps({**self.authorizations,"equipment":"not-approved"}))
            with patch.object(real_demo,"ROOT",Path(directory)), patch.object(real_demo,"DEMO_DSN",dsn()), \
                    patch.object(real_demo,"prepare",return_value=self.proposals), patch.object(real_demo.subprocess,"run") as external, \
                    patch.object(real_demo,"request") as api, patch("sys.argv",["real_demo","--demo-id","driver-check","--no-start","--authorizations",str(path)]):
                self.assertEqual(real_demo.main(),1)
                external.assert_not_called()
                api.assert_not_called()
            receipt = json.loads(next(Path(directory).glob("artifacts/validation/RealDemo/driver-check/Attempt*/Integration.json")).read_text())
            self.assertEqual(receipt["status"],"blocked")
            self.assertNotIn("credential",receipt)

    def test_preflight_enforces_bounded_known_price_approval(self):
        self.assertEqual(real_demo.preflight(self.connection,self.proposals,self.authorizations,time.time()+300)[0],54)
        self.connection.execute("UPDATE backintel.capability_provider_authorizations SET price_ceiling_known=false WHERE authorization_id=%s",(self.authorizations["support"],))
        with self.assertRaisesRegex(PermissionError,"known-price"):
            real_demo.preflight(self.connection,self.proposals,self.authorizations,time.time()+300)
        self.connection.execute("UPDATE backintel.capability_provider_authorizations SET price_ceiling_known=true,max_requests=1 WHERE authorization_id=%s",(self.authorizations["support"],))
        with self.assertRaisesRegex(PermissionError,"request"):
            real_demo.preflight(self.connection,self.proposals,self.authorizations,time.time()+300)
        self.connection.execute("UPDATE backintel.capability_provider_authorizations SET max_requests=27,max_measured_usd=.01 WHERE authorization_id=%s",(self.authorizations["support"],))
        self.connection.execute("""INSERT INTO backintel.capability_model_requests
            (request_key,task_id,source_sha256,model,request,state,authorization_id,metadata,response,finished_at)
            VALUES (%s,%s,%s,'jev-1.13',%s,'completed',%s,%s,'{"test_fixture":true}'::jsonb,now())""",
            (digest(["fixture-budget",self.stores["support"].task_id]),self.stores["support"].task_id,
             self.proposals["support"]["scope"]["source_sha256s"][0],Jsonb({"test_fixture":True}),self.authorizations["support"],
             Jsonb({"test_fixture":True,"request_id":"fixture-budget","model":"jev-1.13","cost_usd":.01})))
        with self.assertRaisesRegex(PermissionError,"fixture"):
            real_demo.preflight(self.connection,self.proposals,self.authorizations,time.time()+300)
        # Isolate the dollar-limit decision; fixture rejection above remains the real-run default.
        with patch.object(real_demo,"usage_for",return_value={"provider_fixture_requests":0}):
            with self.assertRaisesRegex(PermissionError,"budget"):
                real_demo.preflight(self.connection,self.proposals,self.authorizations,time.time()+300)

    def test_ephemeral_credential_has_task_and_time_bounds(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/"Credential.json"
            record = {"key":"fixture-only-key","task_ids":["approved-task"],"expires_at":time.time()+60}
            path.write_text(json.dumps(record))
            with patch.dict(os.environ,{"OPENROUTER_API_KEY":"","BACKINTEL_PROVIDER_CREDENTIAL_FILE":str(path)}):
                self.assertEqual(runtime_credential("approved-task"),"fixture-only-key")
                self.assertIsNone(runtime_credential("other-task"))
                path.write_text(json.dumps({**record,"expires_at":0}))
                self.assertIsNone(runtime_credential("approved-task"))
                path.write_text(json.dumps({**record,"expires_at":float("nan")}))
                with self.assertRaisesRegex(RuntimeError,"invalid"):
                    runtime_credential("approved-task")

    def test_dispatch_preserves_other_tasks_triggers_and_expired_jobs(self):
        selected,other = self.stores["support"],self.stores["equipment"]
        schedule(selected,"event",{"scenario":"support","operation":"real_prepare"},0,"selected")
        untouched = schedule(other,"event",{"scenario":"equipment","operation":"real_prepare"},0,"other")
        expired = enqueue(other,{"scenario":"equipment","operation":"real_prepare"},"expired")
        self.connection.execute("UPDATE backintel.capability_jobs SET state='running',attempts=max_attempts,lease_until=now()-interval '1 second' WHERE job_id=%s",(expired,))
        result = dispatch([selected.task_id])
        self.assertEqual([job["state"] for job in result["jobs"]],["completed"])
        self.assertEqual(self.connection.execute("SELECT state FROM backintel.capability_triggers WHERE trigger_id=%s",(untouched,)).fetchone()[0],"pending")
        self.assertEqual(self.connection.execute("SELECT state FROM backintel.capability_jobs WHERE job_id=%s",(expired,)).fetchone()[0],"running")


if __name__ == "__main__":
    unittest.main()
