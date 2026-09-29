"""Provider-boundary checks use local fixtures, never paid inference or downloaded models."""
import copy
import json
import os
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
import uuid
from unittest.mock import patch

import psycopg
from psycopg.types.json import Jsonb

from runtime.bootstrap import initialize
from runtime.contracts import admit_source,current_sources,register_task
from runtime.evidence import Evidence
from runtime.ledger import dsn
from runtime.jobs import enqueue, execute
from runtime.real_pipeline import compare_history, interpret_source, prepare_followups, prepare_history, start_followups
from runtime.real_semantics import _verified_metadata,extract_real,scope_for,typed_answer,usage_for
from runtime.real_models import _allow_model_use,_tabicl,checkpoint,prepare_real
from runtime.simulation import digest
from runtime.synthetic import history


class FixtureAnswer:
    def __init__(self,value):
        self.value = value
    def model_dump(self,mode="json"):
        return self.value


class FixtureClassifier:
    calls = 0
    charge = .001
    fail = False
    def __init__(self,model):
        self.model = model
        self.last_metadata = {}
        self.last_response = {}
    def invoke(self,request):
        type(self).calls += 1
        if self.fail:
            raise TimeoutError("injected response uncertainty")
        self.last_metadata = {"request_id":"fixture-request","model":self.model,"cost_usd":self.charge}
        answer = {"type":"noul","noul":.25}
        self.last_response = {"fixture":True,"answer":answer}
        return SimpleNamespace(nouls={"risk":FixtureAnswer(answer)},choices={},scores={},
                               request_id="fixture-request",model=self.model,usage=SimpleNamespace(input_tokens=10,output_tokens=3))
    async def aclose(self):
        pass


class ProviderIdentityTests(unittest.TestCase):
    def test_checked_alias_revision_keeps_identity_and_billing_guards(self):
        metadata = {"request_id": "recorded-probe", "model": "typesafe/jev-1.13-20260917", "cost_usd": .000011592}
        _verified_metadata(metadata, "jev-1.13")
        for changed in ({"model": "typesafe/jev-1.14-20260917"},
                        {"model": "typesafe/jev-1.13-20261001"},
                        {"request_id": None}, {"cost_usd": None}):
            with self.subTest(changed=changed), self.assertRaises(RuntimeError):
                _verified_metadata({**metadata, **changed}, "jev-1.13")
        with self.assertRaises(RuntimeError):
            _verified_metadata(metadata, "jev-1.12")


class RealBoundaryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not os.environ.get("BACKINTEL_TEST_DATABASE_URL") or os.environ["BACKINTEL_TEST_DATABASE_URL"] != dsn() or not psycopg.conninfo.conninfo_to_dict(dsn())["dbname"].startswith("test_"):
            raise RuntimeError("Real-boundary fixtures require an explicitly isolated test database")
        initialize()

    def setUp(self):
        self.conn = psycopg.connect(dsn(),autocommit=True)
        self.addCleanup(self.conn.close)
        task,rows,_ = history("support")
        task["id"] = "real-test-"+uuid.uuid4().hex[:20]
        task["observation_provider"] = {"name":"openrouter-jev","version":"jev-1.13","implementation_mode":"real"}
        self.store = Evidence(self.conn,task["id"])
        self.task = register_task(self.store,task)
        admit_source(self.store,self.task,{"format":"json","data":rows[:2]},3)
        self.sources = current_sources(self.store,3,self.task["sha256"])
        scope = scope_for(self.task,self.sources)
        self.authorization = "fixture-"+uuid.uuid4().hex
        self.conn.execute("""INSERT INTO backintel.capability_provider_authorizations
            (authorization_id,provider,model,max_requests,max_input_characters,price_ceiling_known,approved,scope_sha256,scope,expires_at)
            VALUES (%s,'openrouter','jev-1.13',1,5000,false,false,%s,%s,now()+interval '1 hour')""",
            (self.authorization,digest(scope),Jsonb(scope)))
        FixtureClassifier.calls,FixtureClassifier.charge,FixtureClassifier.fail = 0,.001,False

    def approve_fixture(self):
        self.conn.execute("UPDATE backintel.capability_provider_authorizations SET approved=true WHERE authorization_id=%s",(self.authorization,))

    def test_semantic_training_requires_actual_findings_for_each_question(self):
        feature = {"feature": {"sha256": "fixture-feature"}}
        config = {"limits": {"max_training_rows": 64}}
        for observations in ([], [{"kind": "observation", "body": {
                "question_id": "risk", "provider": {"implementation_mode": "simulated"},
                "request_id": "fixture"}}]):
            with self.subTest(observations=observations), patch("runtime.real_models._allow_model_use", return_value=config), patch.object(self.store, "lineage", return_value=observations):
                with self.assertRaisesRegex(ValueError, "actual Jev"):
                    prepare_real(self.store, self.task, [feature], "catboost", "semantic", 10)

    def test_preparation_commits_sources_and_replays_without_provider_calls(self):
        store = Evidence(self.conn, "stage-"+uuid.uuid4().hex[:20])
        job = enqueue(store, {"operation":"real_prepare", "scenario":"support"}, "prepare")
        result = execute(job)
        self.assertEqual(result["state"], "completed")
        plan = store.get(result["result"])
        self.assertEqual(plan["body"]["source_records"], 24)
        self.assertEqual(len(plan["body"]["outcomes"]), 24)
        with psycopg.connect(dsn()) as other:
            self.assertEqual(Evidence(other,store.task_id).get(plan["body"]["sources"][0])["kind"], "source")
        self.assertTrue(execute(job)["reused"])
        with self.assertRaises(PermissionError):
            interpret_source(store, plan, plan["body"]["sources"][0], "not-approved", FixtureClassifier)
        self.assertEqual(FixtureClassifier.calls, 0)
        self.assertEqual(usage_for(store)["provider_calls"], 0)

    def test_missing_credential_preserves_approved_request_slot(self):
        self.approve_fixture()
        with patch.dict(os.environ, {}, clear=True):
            # Preserve database addressing without allowing any credential into this check.
            os.environ["BACKINTEL_APP_DATABASE_URL"] = self.conn.info.dsn
            os.environ["BACKINTEL_TEST_DATABASE_URL"] = self.conn.info.dsn
            with self.assertRaisesRegex(RuntimeError, "ephemeral credential"):
                extract_real(self.store,self.task,self.sources[0],3,authorization_id=self.authorization)
        self.assertEqual(usage_for(self.store)["provider_calls"], 0)
        self.assertEqual(len(self.extract()), 1)

    def test_future_source_preparation_preserves_cutoffs_and_requires_separate_approval(self):
        store = Evidence(self.conn,"followup-"+uuid.uuid4().hex[:20])
        history_plan = prepare_history(store,"support")
        plan = prepare_followups(store,history_plan)
        self.assertEqual(prepare_followups(store,history_plan),plan)
        self.assertEqual(len(plan["body"]["sources"]),3)
        self.assertEqual(len(plan["body"]["events"]),16)
        task_sha = history_plan["body"]["task"]
        self.assertEqual(len(current_sources(store,71,task_sha)),24)
        self.assertEqual(len(current_sources(store,72,task_sha)),25)
        revised = [r for r in current_sources(store,75,task_sha) if r["body"]["id"] == "support-024"]
        self.assertEqual([r["body"]["revision"] for r in revised],[2])
        with self.assertRaisesRegex(ValueError,"comparison"):
            start_followups(store,plan,self.authorization)
        store.put("real_stage_result","history-v1",{"result":history_plan["sha256"],"test_fixture":True},71,[history_plan["sha256"]])
        with self.assertRaises(PermissionError):
            start_followups(store,plan,self.authorization)
        self.approve_fixture()
        with self.assertRaisesRegex(PermissionError,"scope"):
            start_followups(store,plan,self.authorization)
        self.assertEqual(self.conn.execute("SELECT count(*) FROM backintel.capability_triggers WHERE task_id=%s",(store.task_id,)).fetchone()[0],0)
        self.assertEqual(FixtureClassifier.calls,0)

    def test_incomplete_and_simulated_history_cannot_enter_real_comparison(self):
        store = Evidence(self.conn, "stage-"+uuid.uuid4().hex[:20])
        plan = prepare_history(store,"support")
        with self.assertRaisesRegex(PermissionError, "actual Jev"):
            compare_history(store,plan)
        source = store.get(plan["body"]["sources"][0])
        store.put("observation", "simulated-finding", {
            "source":source["sha256"], "task":plan["body"]["task"], "question_id":"risk",
            "provider":{"implementation_mode":"simulated"}, "request_id":"fixture"}, source["available_at"])
        with self.assertRaisesRegex(ValueError, "simulated"):
            compare_history(store,plan)

    def test_job_attempts_record_fixture_charge_once_and_preserve_unknowns(self):
        self.approve_fixture()
        def handler(store,payload):
            return self.extract()[0]
        first = enqueue(self.store,{"operation":"provider-fixture"},"fixture-charge")
        self.assertEqual(execute(first,handler)["state"],"completed")
        usage = self.store.find("job_attempt_result",first+":1")["body"]
        self.assertEqual((usage["provider_calls"],usage["provider_usd"]),(1,.001))
        replay = enqueue(self.store,{"operation":"provider-fixture"},"fixture-cached")
        self.assertEqual(execute(replay,handler)["state"],"completed")
        cached = self.store.find("job_attempt_result",replay+":1")["body"]
        self.assertEqual((cached["provider_calls"],cached["provider_usd"]),(0,0))
        self.assertEqual(FixtureClassifier.calls,1)

        locked = enqueue(self.store,{"operation":"provider-fixture"},"fixture-lock-failure")
        with patch.object(Evidence,"lock",side_effect=TimeoutError("fixture task lock timeout")):
            self.assertEqual(execute(locked,handler)["state"],"retry")
        before_handler = self.store.find("job_attempt_result",locked+":1")["body"]
        self.assertEqual((before_handler["provider_calls"],before_handler["provider_usd"]),(0,0))
        self.assertEqual(FixtureClassifier.calls,1)

        self.setUp()
        self.approve_fixture()
        FixtureClassifier.fail = True
        failed = enqueue(self.store,{"operation":"provider-fixture"},"fixture-uncertain")
        self.assertEqual(execute(failed,handler)["state"],"retry")
        uncertain = self.store.find("job_attempt_result",failed+":1")["body"]
        self.assertIsNone(uncertain["provider_calls"])
        self.assertIsNone(uncertain["provider_usd"])
        self.assertEqual(uncertain["provider_requests_admitted"],1)

    def extract(self,index=0):
        return extract_real(self.store,self.task,self.sources[index],3,authorization_id=self.authorization,classifier_factory=FixtureClassifier)

    def test_approval_gate_exact_scope_cache_and_one_request_cap(self):
        with self.assertRaises(PermissionError):
            self.extract()
        self.assertEqual(FixtureClassifier.calls,0)
        self.approve_fixture()
        observations = self.extract()
        self.assertEqual(FixtureClassifier.calls,1)
        self.assertEqual(self.extract(),observations)
        self.assertEqual(FixtureClassifier.calls,1)
        self.assertEqual(observations[0]["body"]["request_id"],"fixture-request")
        with self.assertRaisesRegex(RuntimeError,"budget exhausted"):
            self.extract(1)
        self.assertEqual(FixtureClassifier.calls,1)

    def test_unknown_outcome_and_unknown_charge_never_trigger_paid_retry(self):
        self.approve_fixture()
        FixtureClassifier.fail = True
        with self.assertRaises(TimeoutError):
            self.extract()
        FixtureClassifier.fail = False
        with self.assertRaisesRegex(RuntimeError,"automatic paid retry prohibited"):
            self.extract()
        self.assertEqual(FixtureClassifier.calls,1)
        # A distinct fixture authorization proves that a returned but unpriced response is retained.
        self.setUp()
        self.approve_fixture()
        FixtureClassifier.charge = None
        with self.assertRaisesRegex(RuntimeError,"charge unavailable"):
            self.extract()
        with self.assertRaisesRegex(RuntimeError,"charge unavailable"):
            self.extract()
        self.assertEqual(FixtureClassifier.calls,1)
        state,response = self.conn.execute("SELECT state,response FROM backintel.capability_model_requests WHERE authorization_id=%s",(self.authorization,)).fetchone()
        self.assertEqual(state,"completed")
        self.assertTrue(response["raw_response"]["fixture"])
        self.assertEqual(self.store.list("observation"),[])

    def test_response_survives_domain_rollback_and_scope_change_is_denied(self):
        self.approve_fixture()
        with self.assertRaisesRegex(ValueError,"domain rollback"):
            with self.conn.transaction():
                self.extract()
                raise ValueError("domain rollback")
        self.assertEqual(self.store.list("observation"),[])
        self.assertEqual(len(self.extract()),1)
        self.assertEqual(FixtureClassifier.calls,1)
        changed = copy.deepcopy(self.task["body"])
        changed["questions"][0]["prompt"] = "A different question"
        other = register_task(self.store,changed)
        with self.assertRaises(PermissionError):
            extract_real(self.store,other,self.sources[1],3,authorization_id=self.authorization,classifier_factory=FixtureClassifier)
        self.assertEqual(FixtureClassifier.calls,1)

    def test_actual_answer_translation_and_download_denial(self):
        question = {"type":"number"}
        translated = typed_answer(question,{"score":7.,"legend":{"0":0,"1":10},"probabilities":{"0":.3,"1":.7}})
        self.assertEqual(translated["value"],7.)
        self.assertEqual(translated["distribution"],{"values":[0,10],"probabilities":[.3,.7]})
        with tempfile.TemporaryDirectory() as directory,patch.dict(os.environ,{"BACKINTEL_MODEL_DIR":directory}):
            with self.assertRaises(PermissionError):
                _allow_model_use("catboost")
            with self.assertRaisesRegex(RuntimeError,"not been downloaded"):
                checkpoint("classification")
            with patch("tabicl.TabICLClassifier") as constructor:
                _tabicl("classification",Path(directory)/"absent.ckpt")
                self.assertFalse(constructor.call_args.kwargs["allow_auto_download"])
                self.assertEqual(constructor.call_args.kwargs["device"],"cpu")
                self.assertEqual(constructor.call_args.kwargs["n_estimators"],1)


if __name__ == "__main__":
    unittest.main()
