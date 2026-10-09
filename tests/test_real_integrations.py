"""Provider-boundary checks use local fixtures, never paid inference or downloaded models."""
import copy
import json
import os
import sys
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
import uuid
from unittest.mock import MagicMock, patch

import psycopg
from psycopg.types.json import Jsonb

from runtime.bootstrap import initialize
from runtime.contracts import admit_source,current_sources,register_task
from runtime.evidence import Evidence
from runtime.ledger import dsn
from runtime.jobs import enqueue, execute
from runtime.real_pipeline import compare_history, interpret_source, prepare_followups, prepare_history, start_followups
from runtime.real_semantics import _verified_metadata,extract_real,questions_for,scope_for,typed_answer,usage_for
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
    def test_prediction_rechecks_approved_configuration_before_loading(self):
        from unittest.mock import Mock
        from runtime import real_models as models
        for route in ('catboost', 'tabiclv2'):
            config = {route: {'parameters': {'depth': 2}}}
            model = {'body': {'route': route, 'configuration_sha256': models.digest(config), 'parameters': {'depth': 2}, 'columns': ['value'], 'target': {'kind': 'regression'}}}
            estimator = Mock(); estimator.predict.return_value = [1]
            with self.subTest(route=route), patch.object(models, '_allow_model_use', return_value=config) as approval, patch.object(models, '_load', return_value=estimator) as load, patch.object(models, 'matrix', return_value=[[1]]), patch.object(models, 'model_root', return_value=Path('/fixture-models')):
                self.assertEqual(models.predict_real(model, {}), 1)
                load.reset_mock()
                approval.return_value = {route: {'parameters': {'depth': 3}}}
                with self.assertRaisesRegex(ValueError, 'configuration changed'):
                    models.predict_real(model, {})
                load.assert_not_called()
                approval.return_value = config
                model['body']['parameters'] = {'depth': 3}
                with self.assertRaisesRegex(ValueError, 'configuration changed'):
                    models.predict_real(model, {})
                load.assert_not_called()

    def test_prepared_package_must_match_current_training_request(self):
        from unittest.mock import Mock
        from runtime import real_models as models
        store = MagicMock()
        store.find.return_value = None
        store.put.side_effect = lambda kind,key,body,*args: {'body':body}
        estimator = Mock()
        estimator.save_model.side_effect = lambda path: Path(path).write_text('fixture model')
        training = [{'feature':{'sha256':'feature','body':{'values':{'structured:value':1}}},
                     'outcome':{'sha256':'outcome','body':{'value':1}}}]
        task = {'sha256':'task','body':{'target':{'kind':'regression'}}}
        config = {'limits':{'max_training_rows':2},'catboost':{'parameters':{}}}
        with tempfile.TemporaryDirectory() as directory, patch.object(models,'matrix',return_value=[[1]]), patch.object(models,'model_root',return_value=Path(directory)), patch.object(models,'versions',return_value={'fixture':'version'}), patch.object(models,'_allow_model_use',return_value=config), patch.dict('sys.modules',{'catboost':SimpleNamespace(CatBoostClassifier=lambda **kwargs:estimator,CatBoostRegressor=lambda **kwargs:estimator)}):
            original = models.prepare_real(store,task,training,'catboost','structured',0)['body']
            manifest = Path(directory)/original['artifact']['package']/'manifest.json'
            self.assertEqual(models.prepare_real(store,task,training,'catboost','structured',0)['body'],original)
            for name,value in {'training_matrix_sha256':'other-training','route':'tabiclv2','feature_set':'semantic','prepared_at':99,'configuration_sha256':'other-config','scales':{},'artifact':{**original['artifact'],'file':'../outside'}}.items():
                changed = copy.deepcopy(original);changed[name]=value
                manifest.write_text(json.dumps(changed))
                with self.subTest(field=name), self.assertRaisesRegex(ValueError,'package was modified'):
                    models.prepare_real(store,task,training,'catboost','structured',0)
            estimator.fit.assert_called_once()

    def test_cached_predictor_rechecks_revoked_model_approval(self):
        from unittest.mock import Mock, patch
        from runtime import real_models as models
        estimator = Mock()
        estimator.predict.return_value = [2.5]
        config = {'catboost': {'parameters': {}}}
        body = {'route':'catboost', 'columns':[], 'target':{'kind':'regression'}, 'configuration_sha256':models.digest(config), 'parameters':{}}
        with patch.object(models, '_allow_model_use', side_effect=[config, PermissionError('Fixture approval revoked')]) as approval, patch.object(models, '_load', return_value=estimator) as load, patch.object(models, 'matrix', return_value=[[]]), patch.object(models, 'model_root', return_value='/fixture-model-root'):
            models.predict_real({'body':body}, {})
            with self.assertRaisesRegex(PermissionError, 'approval revoked'):
                models.predict_real({'body':body}, {})
            self.assertEqual(approval.call_count, 2)
            load.assert_called_once()

    def test_model_cache_identity_changes_with_predictor_implementation(self):
        from runtime import real_models as models
        store = MagicMock()
        store.find.return_value = {'fixture':'existing-model'}
        training = [{'feature':{'sha256':'features','body':{'values':{'structured:value':1}}},
                     'outcome':{'sha256':'outcome'}}]
        with patch.object(models, '_allow_model_use', return_value={'limits':{'max_training_rows':2}}), \
                patch.object(models, 'versions', return_value={'fixture':'version'}), \
                patch.object(models, 'file_sha', side_effect=['implementation-a','implementation-b']):
            models.prepare_real(store, {'sha256':'task'}, training, 'catboost', 'structured', 0)
            first = store.find.call_args.args[1]
            models.prepare_real(store, {'sha256':'task'}, training, 'catboost', 'structured', 0)
            self.assertNotEqual(first, store.find.call_args.args[1])

    def test_numeric_probability_rounding_preserves_raw_reply_and_rejects_bad_weights(self):
        question = {"id": "wear", "type": "number", "prompt": "Reported wear", "rule": {"kind": "number"}}
        answer = {"legend": {str(i): str(10 * i / 9) for i in range(10)},
                  "probabilities": dict(zip(map(str, range(10)), [.05, .01, 0, .02, .23, .67, 0, 0, 0, .01]))}
        result = typed_answer(question, answer)
        self.assertAlmostEqual(sum(result["distribution"]["probabilities"]), 1)
        self.assertAlmostEqual(result["value"], sum(float(answer["legend"][k]) * p
                                                   for k, p in answer["probabilities"].items()) / .99)
        self.assertAlmostEqual(sum(answer["probabilities"].values()), .99)
        for invalid in ({"0": .2, "1": .3}, {"0": -.01, "1": 1.01},
                        {"0": float("nan"), "1": .5}):
            with self.subTest(invalid=invalid), self.assertRaises(ValueError):
                typed_answer(question, {"legend": {"0": "0", "1": "10"}, "probabilities": invalid})

    def test_numeric_question_uses_text_labels_and_preserves_numeric_score(self):
        from langchain_typesafe import Noul, Score
        question = {"id": "wear", "type": "number", "prompt": "What wear level is reported?", "rule": {"kind": "number"}}
        task = {"questions": [question], "policy": {"signal_scale": 10}}
        serialized = questions_for(task, SimpleNamespace(Noul=Noul, Score=Score))["wear"].model_dump(mode="json")
        self.assertEqual(len(serialized["criteria"]), 10)
        self.assertEqual((serialized["criteria"][0],serialized["criteria"][-1]), ("0","10"))
        self.assertTrue(all(isinstance(value,str) for value in serialized["criteria"]))
        endpoints = typed_answer(question, {"legend": {"0": "0", "9": "10"}, "probabilities": {"0": .25, "9": .75}})
        self.assertAlmostEqual(endpoints["value"], 7.5)
        response = typed_answer(question, {"legend": {"0": "1", "1": "4"}, "probabilities": {"0": .25, "1": .75}})
        self.assertAlmostEqual(response["value"], 3.25)
        self.assertEqual(response["distribution"]["values"], [1.0, 4.0])

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
    def test_revocation_before_dispatch_prevents_invocation(self):
        from runtime import real_semantics as semantics
        self.conn.execute('UPDATE backintel.capability_provider_authorizations SET approved=true WHERE authorization_id=%s',(self.authorization,))
        def revoke():
            self.conn.execute('UPDATE backintel.capability_provider_authorizations SET approved=false WHERE authorization_id=%s',(self.authorization,))
            return 0
        with patch.object(semantics.time,'perf_counter',side_effect=revoke), self.assertRaisesRegex(PermissionError,'changed before dispatch'):
            semantics.request_real(self.task,self.sources[0],self.authorization,FixtureClassifier)
        self.assertEqual(FixtureClassifier.calls,0)

    def test_authorization_row_stays_locked_through_provider_invocation(self):
        from concurrent.futures import ThreadPoolExecutor, TimeoutError
        from threading import Event
        from runtime.real_semantics import request_real
        self.conn.execute('UPDATE backintel.capability_provider_authorizations SET approved=true WHERE authorization_id=%s',(self.authorization,))
        started = Event(); futures = []; tester = self
        def revoke():
            with psycopg.connect(dsn(),autocommit=True) as connection:
                started.set()
                connection.execute('UPDATE backintel.capability_provider_authorizations SET approved=false WHERE authorization_id=%s',(self.authorization,))
        with ThreadPoolExecutor(max_workers=1) as workers:
            class LockCheckingClassifier(FixtureClassifier):
                def invoke(classifier,payload):
                    futures.append(workers.submit(revoke))
                    tester.assertTrue(started.wait(5))
                    with tester.assertRaises(TimeoutError):
                        futures[0].result(timeout=.2)
                    return super().invoke(payload)
            request_real(self.task,self.sources[0],self.authorization,LockCheckingClassifier)
            futures[0].result(timeout=5)
        self.assertFalse(self.conn.execute('SELECT approved FROM backintel.capability_provider_authorizations WHERE authorization_id=%s',(self.authorization,)).fetchone()[0])

    @classmethod
    def setUpClass(cls):
        if not os.environ.get("BACKINTEL_TEST_DATABASE_URL") or os.environ["BACKINTEL_TEST_DATABASE_URL"] != dsn() or not psycopg.conninfo.conninfo_to_dict(dsn())["dbname"].startswith("test_"):
            raise RuntimeError("Real-boundary fixtures require an explicitly isolated test database")
        initialize()

    def setUp(self):
        from runtime import jobs
        # Provider accounting fixtures share mock counters and a test connection.
        # Exercise the transaction engine; real process isolation has separate tests.
        worker = patch.object(jobs, '_run_worker', side_effect=jobs._execute_claimed)
        worker.start()
        self.addCleanup(worker.stop)
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

    def test_request_price_ceiling_is_reserved_before_dispatch(self):
        from runtime.real_semantics import request_real
        scope = {**scope_for(self.task,self.sources), 'max_request_usd': '.09'}
        self.conn.execute('UPDATE backintel.capability_provider_authorizations SET approved=true,price_ceiling_known=true,max_requests=2,max_measured_usd=.10,scope=%s,scope_sha256=%s WHERE authorization_id=%s',
                          (Jsonb(scope), digest(scope), self.authorization))
        FixtureClassifier.charge = .09
        first = request_real(self.task,self.sources[0],self.authorization,FixtureClassifier)
        self.assertEqual(first['metadata']['reserved_usd'], '0.09')
        with self.assertRaisesRegex(RuntimeError, 'cannot reserve'):
            request_real(self.task,self.sources[1],self.authorization,FixtureClassifier)
        self.assertEqual(FixtureClassifier.calls, 1)
        self.assertTrue(request_real(self.task,self.sources[0],self.authorization,FixtureClassifier)['cached'])
        self.assertEqual(FixtureClassifier.calls, 1)

    def test_cached_response_requires_current_matching_authorization(self):
        from runtime.real_semantics import request_real
        self.conn.execute('UPDATE backintel.capability_provider_authorizations SET approved=true WHERE authorization_id=%s',(self.authorization,))
        request_real(self.task,self.sources[0],self.authorization,FixtureClassifier)
        self.assertTrue(request_real(self.task,self.sources[0],self.authorization,FixtureClassifier)['cached'])
        with self.assertRaises(PermissionError):
            request_real(self.task,self.sources[0],'not-authorized',FixtureClassifier)
        self.conn.execute('UPDATE backintel.capability_provider_authorizations SET approved=false WHERE authorization_id=%s',(self.authorization,))
        with self.assertRaises(PermissionError): request_real(self.task,self.sources[0],self.authorization,FixtureClassifier)
        self.conn.execute("UPDATE backintel.capability_provider_authorizations SET approved=true,expires_at=now()-interval '1 second' WHERE authorization_id=%s",(self.authorization,))
        with self.assertRaises(PermissionError): request_real(self.task,self.sources[0],self.authorization,FixtureClassifier)
        scope = {**scope_for(self.task,self.sources),'source_sha256s':[]}
        self.conn.execute("UPDATE backintel.capability_provider_authorizations SET expires_at=now()+interval '1 hour',scope=%s,scope_sha256=%s WHERE authorization_id=%s",(Jsonb(scope),digest(scope),self.authorization))
        with self.assertRaises(PermissionError): request_real(self.task,self.sources[0],self.authorization,FixtureClassifier)
        self.assertEqual(FixtureClassifier.calls,1)

    def test_capped_request_without_known_finite_ceiling_is_not_dispatched(self):
        from runtime.real_semantics import request_real
        for priced, value in ((False, '.01'), (True, None), (True, 'NaN'), (True, '-1'), (True, '0')):
            with self.subTest(priced=priced, value=value):
                scope = {**scope_for(self.task,self.sources), 'max_request_usd': value}
                self.conn.execute('UPDATE backintel.capability_provider_authorizations SET approved=true,price_ceiling_known=%s,max_measured_usd=.10,scope=%s,scope_sha256=%s WHERE authorization_id=%s',
                                  (priced, Jsonb(scope), digest(scope), self.authorization))
                with self.assertRaisesRegex(RuntimeError, 'price ceiling'):
                    request_real(self.task,self.sources[0],self.authorization,FixtureClassifier)
        self.assertEqual(FixtureClassifier.calls, 0)

    def test_charge_above_reserved_ceiling_is_retained_but_not_accepted(self):
        from runtime.real_semantics import request_real
        scope = {**scope_for(self.task,self.sources), 'max_request_usd': '.01'}
        self.conn.execute('UPDATE backintel.capability_provider_authorizations SET approved=true,price_ceiling_known=true,max_measured_usd=.10,scope=%s,scope_sha256=%s WHERE authorization_id=%s',
                          (Jsonb(scope), digest(scope), self.authorization))
        FixtureClassifier.charge = .02
        for _ in range(2):
            with self.assertRaisesRegex(RuntimeError, 'charge'):
                request_real(self.task,self.sources[0],self.authorization,FixtureClassifier)
        self.assertEqual(FixtureClassifier.calls, 1)
        saved = self.conn.execute('SELECT state,metadata FROM backintel.capability_model_requests WHERE authorization_id=%s', (self.authorization,)).fetchone()
        self.assertEqual((saved[0],saved[1]['cost_usd']), ('completed', .02))

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

    def test_default_plan_cache_rejects_changed_history_and_events(self):
        from copy import deepcopy
        from runtime.capability_pipeline import followup_events
        store = Evidence(self.conn, 'changed-history-'+uuid.uuid4().hex[:20])
        plan = prepare_history(store, 'support')
        changed = deepcopy(history('support'))
        changed[0]['policy']['cooldown'] += 1
        with patch('runtime.real_pipeline.history', return_value=changed), self.assertRaisesRegex(ValueError, 'identity conflicts'):
            prepare_history(store, 'support')
        prepare_followups(store, plan)
        changed_events = [*followup_events('support'), (999, 'fixture', {'operation':'refresh', 'at':999})]
        with patch('runtime.capability_pipeline.followup_events', return_value=changed_events), self.assertRaisesRegex(ValueError, 'identity conflicts'):
            prepare_followups(store, plan)
        self.assertEqual(FixtureClassifier.calls, 0)

    def test_missing_credential_preserves_approved_request_slot(self):
        self.approve_fixture()
        test_dsn = dsn()
        with patch.dict(os.environ, {"BACKINTEL_APP_DATABASE_URL": test_dsn, "BACKINTEL_TEST_DATABASE_URL": test_dsn}, clear=True):
            # Preserve local database authentication; every provider credential is absent.
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

    def test_provider_rejection_is_retained_without_credential_or_automatic_retry(self):
        from runtime.real_semantics import request_real

        self.approve_fixture()
        credential = "fixture-secret-never-retain"
        classifier = FixtureClassifier("jev-1.13")
        classifier.last_response = {"error": {"code": 400, "message": "Rejected rubric: "+credential}}
        with patch("runtime.real_semantics.runtime_credential",return_value=credential), \
                patch("runtime.real_semantics._default_classifier",return_value=classifier), \
                patch.object(classifier,"invoke",side_effect=RuntimeError("provider rejected request")) as invoke:
            with self.assertRaisesRegex(RuntimeError,"provider rejected request"):
                request_real(self.task,self.sources[0],self.authorization)
            with self.assertRaisesRegex(RuntimeError,"automatic paid retry prohibited"):
                request_real(self.task,self.sources[0],self.authorization)
            self.assertEqual(invoke.call_count,1)
        state,error,response = self.conn.execute("SELECT state,error,response FROM backintel.capability_model_requests WHERE authorization_id=%s",(self.authorization,)).fetchone()
        self.assertEqual(state,"blocked")
        self.assertIsNone(response)
        captured = json.loads(error.split(": ",1)[1])
        self.assertEqual(captured["error"]["code"],400)
        self.assertIn("[REDACTED]",captured["error"]["message"])
        self.assertNotIn(credential,error)
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
        other = register_task(self.store,changed,available_at=1)
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
            constructor = MagicMock()
            thread_limit = MagicMock()
            with patch.dict(sys.modules, {"tabicl": SimpleNamespace(TabICLClassifier=constructor, TabICLRegressor=MagicMock()),
                                          "torch": SimpleNamespace(set_num_threads=thread_limit)}):
                _tabicl("classification",Path(directory)/"absent.ckpt")
                thread_limit.assert_called_once_with(2)
                self.assertFalse(constructor.call_args.kwargs["allow_auto_download"])
                self.assertEqual(constructor.call_args.kwargs["device"],"cpu")
                self.assertEqual(constructor.call_args.kwargs["n_estimators"],1)


if __name__ == "__main__":
    unittest.main()
