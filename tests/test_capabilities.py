"""Direct capability checks against an explicitly isolated PostgreSQL database."""
import copy
import csv
import io
import json
import os
import unittest
import uuid
import time
from concurrent.futures import ThreadPoolExecutor

import psycopg

from runtime.bootstrap import initialize
from runtime.contracts import admit_source, current_sources, register_task, validate_task
from runtime.evidence import Evidence
from runtime.ledger import dsn
from runtime.observations import correct_observation, effective_observation, extract
from runtime.synthetic import history
from runtime.attention import attend
from runtime.jobs import cancel, claim, enqueue, execute, release_due, resume_failed, runnable, schedule
from runtime.prediction import (cases, chronological_split, compare, evaluate, features, invalidate_predictions,
                                metrics, outcome, prepare, registry, score, transition, update_plan)


class CapabilityTests(unittest.TestCase):
    def test_task_revision_does_not_reuse_previous_attention_episode(self):
        from runtime.attention import latest_episode
        store, task, _, _ = self.scenario()
        reason = store.put('event','version-boundary',{'event':'fixture'},0)
        previous = attend(store,task,'same-entity',reason,0,1)
        body = copy.deepcopy(task['body'])
        body['policy']['cooldown'] += 1
        with self.assertRaisesRegex(ValueError, 'strictly later'):
            register_task(store,body)
        revised = register_task(store,body,available_at=1)
        self.assertEqual(max(store.list('task'), key=lambda record: record['available_at'])['sha256'], revised['sha256'])
        self.assertEqual(register_task(store,body)['sha256'], revised['sha256'])
        self.assertIsNone(latest_episode(store,'same-entity',revised['sha256']))
        current = attend(store,revised,'same-entity',reason,1,action='staleness')
        self.assertIsNone(current['body']['last_observed_at'])
        self.assertIsNone(current['body']['episode_id'])
        self.assertEqual(current['body']['sequence'],1)
        self.assertNotIn(previous['sha256'],current['parents'])

    @classmethod
    def setUpClass(cls):
        if not os.environ.get("BACKINTEL_TEST_DATABASE_URL"):
            raise RuntimeError("Capability checks require an isolated test database")
        if os.environ.get("BACKINTEL_APP_DATABASE_URL") != os.environ["BACKINTEL_TEST_DATABASE_URL"]:
            raise RuntimeError("App and test URLs must identify the same isolated database")
        if not psycopg.conninfo.conninfo_to_dict(dsn())["dbname"].startswith("test_"):
            raise RuntimeError("Refusing capability checks outside test_ database")
        initialize()

    def setUp(self):
        self.conn = psycopg.connect(dsn(), autocommit=True)
        self.addCleanup(self.conn.close)

    def scenario(self, name="support"):
        task, rows, labels = history(name)
        task["id"] = "test-" + uuid.uuid4().hex
        store = Evidence(self.conn, task["id"])
        return store, register_task(store, task), rows, labels

    def test_portable_admission_revisions_quarantine_and_immutable_lineage(self):
        for name in ("support", "equipment"):
            store, task, rows, _ = self.scenario(name)
            source = {"format": "json", "data": [rows[0]]}
            receipt = admit_source(store, task, source, 0)
            self.assertEqual(receipt, admit_source(store, task, source, 0))
            original = current_sources(store, 0)[0]
            duplicate = admit_source(store, task, source, 1)
            self.assertEqual(duplicate["body"]["dispositions"][0]["status"], "duplicate")
            corrected = dict(rows[0], revision=2, arrived_at=2)
            corrected[task["body"]["measures"][0]["field"]] = 99
            result = admit_source(store, task, {"format":"json", "data":[corrected]}, 2)
            self.assertEqual(result["body"]["dispositions"][0]["revision_kind"], "correction")
            self.assertEqual(current_sources(store, 1), [original])
            self.assertEqual(current_sources(store, 2)[0]["body"]["revision"], 2)
            self.assertIn(original["sha256"], {r["sha256"] for r in store.lineage(result["sha256"])})
            conflict = dict(corrected)
            conflict[task["body"]["measures"][0]["field"]] = 0
            malformed = {"missing": "fields"}
            rejected = admit_source(store, task, {"format":"json", "data":[conflict, malformed]}, 3)
            self.assertEqual([d["status"] for d in rejected["body"]["dispositions"]], ["quarantined"] * 2)
            with self.assertRaises(psycopg.errors.RaiseException):
                self.conn.execute("UPDATE backintel.capability_evidence SET body='{}' WHERE sha256=%s", (original["sha256"],))
            self.assertEqual(store.get(original["sha256"]), original)

    def test_csv_text_late_revision_and_schema_failures(self):
        store, task, rows, _ = self.scenario()
        csv_buffer = io.StringIO()
        writer = csv.DictWriter(csv_buffer, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerow(dict(rows[0], revision=3))
        receipt = admit_source(store, task, {"format":"csv", "data":csv_buffer.getvalue()}, 1)
        self.assertEqual(receipt["body"]["dispositions"][0]["status"], "accepted")
        late = dict(rows[0], revision=2)
        receipt = admit_source(store, task, {"format":"text", "data":json.dumps(late)}, 2)
        self.assertEqual(receipt["body"]["dispositions"][0]["revision_kind"], "late_revision")
        self.assertEqual(current_sources(store, 3)[0]["body"]["revision"], 3)
        receipt = admit_source(store, task, {"format":"text", "data":"invalid json"}, 3)
        self.assertEqual(receipt["body"]["dispositions"][0]["status"], "quarantined")
        invalid = copy.deepcopy(task["body"])
        invalid["target"]["horizon"] = 0
        with self.assertRaises(ValueError):
            validate_task(invalid)

    def test_typed_extraction_retry_cache_correction_and_scope(self):
        store, task, rows, _ = self.scenario()
        admit_source(store, task, {"format":"json", "data":[rows[0]]}, 0)
        source = current_sources(store, 0)[0]
        calls = []
        def provider(question, content):
            calls.append(content)
            if len(calls) == 1:
                raise TimeoutError("injected transient failure")
            return {"status":"known", "value":False, "distribution":{"false":.9, "true":.1}, "reason":"simulated"}
        observation = extract(store, task, source, 0, provider)[0]
        self.assertEqual(len(calls), 2)
        self.assertEqual(extract(store, task, source, 5, provider), [observation])
        self.assertEqual(len(calls), 2)
        response = {"status":"known", "value":True, "distribution":{"false":0., "true":1.}, "reason":"reviewed synthetic text"}
        with self.assertRaises(PermissionError):
            correct_observation(store, observation["sha256"], response, "manager", "review", 1)
        correction = correct_observation(store, observation["sha256"], response, "operator", "review", 1)
        self.assertEqual(effective_observation(store, observation["sha256"], 0), observation)
        self.assertEqual(effective_observation(store, observation["sha256"], 1), correction)
        self.assertEqual(correct_observation(store, observation["sha256"], response, "operator", "review", 2), correction)
        with self.assertRaises(ValueError):
            correct_observation(store, observation["sha256"], response, "operator", "stale review", 2)
        self.assertFalse(store.get(observation["sha256"])["body"]["response"]["value"])
        self.assertEqual(len(store.list("extraction_attempt")), 2)

    def test_unknown_abstention_invalid_distribution_and_budget(self):
        store, task, rows, _ = self.scenario()
        task_body = copy.deepcopy(task["body"])
        task_body["policy"]["max_provider_calls"] = 3
        task = register_task(store, task_body, available_at=1)
        rows[0]["message"], rows[1]["message"] = None, "[abstain] uncertain"
        admit_source(store, task, {"format":"json", "data":rows[:4]}, 9)
        sources = current_sources(store, 9)
        self.assertEqual(extract(store, task, sources[0], 9)[0]["body"]["response"]["status"], "unknown")
        self.assertEqual(extract(store, task, sources[1], 9)[0]["body"]["response"]["status"], "abstained")
        def invalid(question, content):
            return {"status":"known", "value":True, "distribution":{"true":.1,"false":.9}, "reason":"wrong"}
        response = extract(store, task, sources[2], 9, invalid)[0]["body"]["response"]
        self.assertEqual(response["reason"], "provider_budget_exhausted")
        self.assertIsNone(response["value"])
        self.assertEqual(extract(store, task, sources[3], 9)[0]["body"]["response"]["reason"], "provider_budget_exhausted")
        self.assertEqual(len(store.list("extraction_attempt")), 3)

    def prepared_history(self, name="support"):
        store, task, rows, labels = self.scenario(name)
        snapshots = []
        for row, label in zip(rows, labels):
            at = row["occurred_at"]
            admit_source(store,task,{"format":"json","data":[row]},at)
            source = next(r for r in current_sources(store,at) if r["body"]["id"] == label["source_id"])
            extract(store,task,source,at)
            snapshots.extend(r for r in features(store,task,at) if r["body"]["source_id"] == label["source_id"])
            outcome(store,task,label)
        return store, task, rows, labels, snapshots

    def test_point_in_time_features_outcomes_and_chronological_isolation(self):
        store, task, rows, labels, snapshots = self.prepared_history()
        self.assertEqual(len(cases(store,task,snapshots[:1],1)),0)
        train, holdout, at = chronological_split(task["body"],cases(store,task,snapshots,71))
        self.assertTrue(all(r["outcome"]["available_at"] <= at for r in train))
        self.assertTrue(all(r["feature"]["body"]["cutoff"] >= at for r in holdout))
        with self.assertRaises(ValueError):
            prepare(store,task,train + holdout,"catboost","semantic",at)
        wrong = copy.deepcopy(train)
        wrong[0]["outcome"] = wrong[1]["outcome"]
        with self.assertRaises(ValueError):
            prepare(store,task,wrong,"catboost","semantic",at)
        old = snapshots[0]
        correction = dict(rows[0],revision=2,arrived_at=72,volume=999,message="Login failed")
        admit_source(store,task,{"format":"json","data":[correction]},72)
        self.assertEqual(features(store,task,0),[old])
        source = next(r for r in current_sources(store,72) if r["body"]["id"] == labels[0]["source_id"])
        extract(store,task,source,72)
        self.assertEqual(features(store,task,0),[old])
        with self.assertRaises(ValueError):
            outcome(store,task,dict(labels[0],available_at=1))

    def test_actual_metrics_and_five_comparable_routes(self):
        classification = metrics("classification",[0,1],[.25,.75])
        self.assertEqual(classification["accuracy"],1)
        self.assertEqual(classification["brier"],.0625)
        self.assertEqual(classification["roc_auc"],1)
        self.assertEqual(classification["ece"],.25)
        regression = metrics("regression",[1,3],[2,2])
        self.assertEqual((regression["mae"],regression["rmse"],regression["r2"]),(1,1,0))
        for name in ("support","equipment"):
            store, task, _, _, snapshots = self.prepared_history(name)
            comparison = compare(store,task,snapshots,71)
            self.assertEqual(comparison,compare(store,task,snapshots,72))
            evaluations = [store.get(sha) for sha in comparison["body"]["evaluations"]]
            models = [store.get(sha) for sha in comparison["body"]["models"]]
            self.assertEqual(len(evaluations),5)
            self.assertEqual({m["body"]["preparation"] for m in models},{"empirical_mean","training_style","context_style"})
            self.assertEqual([m["body"]["implementation_mode"] for m in models],["native_baseline"]+["simulated"]*4)
            self.assertTrue(all(e["body"]["cases"] == comparison["body"]["holdout_cases"] for e in evaluations))
            metric = comparison["body"]["primary_metric"]
            selected = next(e for e in evaluations if e["body"]["model"] == comparison["body"]["selected"])
            self.assertLessEqual(selected["body"]["metrics"][metric],evaluations[0]["body"]["metrics"][metric])
            self.assertTrue(all(e["body"]["provider_calls"] == 0 for e in evaluations))

    def test_lifecycle_scoring_fallback_shadow_rollback_and_controlled_corrections(self):
        store, task, rows, labels, snapshots = self.prepared_history()
        comparison = compare(store,task,snapshots,71)
        baseline, candidate = comparison["body"]["models"][:2]
        with self.assertRaises(ValueError):
            transition(store,task,candidate,"activate",71,"not-approved")
        transition(store,task,baseline,"approve",71,"approve-baseline")
        transition(store,task,baseline,"activate",71,"activate-baseline")
        transition(store,task,candidate,"approve",71,"approve-candidate")
        transition(store,task,candidate,"activate",71,"activate-candidate")
        self.assertEqual(registry(store)["states"][baseline],"retired")
        transition(store,task,baseline,"rollback",71,"rollback-baseline")
        self.assertEqual(registry(store)["active"],baseline)
        self.assertEqual(registry(store,70)["active"],None)
        new_row = history("support",25)[1][-1]
        admit_source(store,task,{"format":"json","data":[new_row]},72)
        source = current_sources(store,72)[-1]
        observation = extract(store,task,source,72)[0]
        fresh = next(r for r in features(store,task,72) if r["body"]["source_id"] == new_row["ticket"])
        accepted = score(store,task,fresh,72)
        self.assertEqual(score(store,task,fresh,73),accepted)
        self.assertEqual(score(store,task,fresh,72,shadow=candidate)["body"]["mode"],"shadow")
        with self.assertRaises(ValueError):
            score(store,task,fresh,74)
        changed_response = {"status":"known","value":True,"distribution":{"true":1.,"false":0.},"reason":"synthetic review"}
        corrected = correct_observation(store,observation["sha256"],changed_response,"operator","review",73)
        revised = next(r for r in features(store,task,73) if r["body"]["source_id"] == new_row["ticket"])
        self.assertNotEqual(revised["sha256"],fresh["sha256"])
        self.assertEqual(len(invalidate_predictions(store,source["sha256"],corrected,73)),2)
        self.assertNotEqual(score(store,task,revised,73)["sha256"],accepted["sha256"])
        plan = update_plan(store,store.get(baseline),[revised],corrected,73)
        self.assertNotIn("model_preparation",plan["body"]["actions"])
        self.assertFalse(plan["body"]["notify"])
        planned = update_plan(store,store.get(baseline),[revised],corrected,73,prepare_requested=True)
        self.assertIn("model_preparation",planned["body"]["actions"])
        with self.assertRaises(ValueError):
            update_plan(store,store.get(candidate),[revised],corrected,73,prepare_requested=True)
        self.assertEqual(store.get(accepted["sha256"]),accepted)
        # Explicit compatible baseline fallback works before any model activation.
        second, task2, _, _, snapshots2 = self.prepared_history()
        compared = compare(second,task2,snapshots2,71)
        future = features(second,task2,72)[0]
        fallback = score(second,task2,future,72,fallback=compared["body"]["models"][0])
        self.assertEqual(fallback["body"]["mode"],"fallback")

    def test_failed_evaluation_blocks_activation_and_contract_mismatch(self):
        store, task, _, _, snapshots = self.prepared_history()
        compared = compare(store,task,snapshots,71)
        candidate = store.get(compared["body"]["models"][1])
        store.put("evaluation","failed-contract",{"model":candidate["sha256"],"status":"blocked"},72,[candidate["sha256"]])
        with self.assertRaises(ValueError):
            transition(store,task,candidate["sha256"],"approve",72,"reject-blocked")
        changed = copy.deepcopy(task["body"])
        changed["target"]["horizon"] = 3
        new_task = register_task(store,changed,72)
        with self.assertRaises(ValueError):
            transition(store,new_task,compared["body"]["models"][0],"approve",72,"reject-incompatible")

    def test_durable_jobs_retry_concurrent_replay_cancel_conflict_and_expired_lease(self):
        store, task, _, _ = self.scenario()
        def handler(ledger,payload):
            return ledger.put("test_result",payload["identity"],payload,10,[task["sha256"]])
        payload = {"identity":"replay"}
        key = enqueue(store,payload,"replay")
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(lambda _:execute(key,handler),range(2)))
        self.assertTrue(any(r["state"] == "completed" for r in results))
        self.assertEqual(len(store.list("test_result")),1)
        self.assertTrue(execute(key,handler)["reused"])
        with self.assertRaises(ValueError):
            enqueue(store,{"identity":"conflict"},"replay")
        retry = enqueue(store,{"identity":"retry","fail_once":True},"retry")
        self.assertEqual(execute(retry,handler)["state"],"retry")
        self.conn.execute("UPDATE backintel.capability_jobs SET due_at=now()-interval '1 second' WHERE job_id=%s",(retry,))
        self.assertEqual(execute(retry,handler)["state"],"completed")
        cancelled = enqueue(store,{"identity":"cancelled"},"cancelled")
        self.assertEqual(cancel(self.conn,cancelled),"cancelled")
        self.assertEqual(execute(cancelled,handler)["state"],"cancelled")
        interrupted = enqueue(store,{"identity":"interrupted"},"interrupted")
        self.assertIsNotNone(claim(self.conn,interrupted))
        self.conn.execute("UPDATE backintel.capability_jobs SET lease_until=now()-interval '1 second' WHERE job_id=%s",(interrupted,))
        self.assertEqual(execute(interrupted,handler)["state"],"completed")
        self.assertEqual(self.conn.execute("SELECT attempts FROM backintel.capability_jobs WHERE job_id=%s",(interrupted,)).fetchone()[0],2)

    @staticmethod
    def blocking_native_handler():
        def handler(store, payload):
            import ctypes
            import json
            import os
            from pathlib import Path
            import subprocess
            import sys
            child = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(90)'])
            store.put('unfinished_native_result', 'fixture', {}, 10)
            Path(payload['marker']).write_text(json.dumps([os.getpid(), child.pid]))
            # PyDLL deliberately holds the GIL: a Python timer thread cannot
            # interrupt this call. The external supervisor must stop it.
            ctypes.PyDLL(None).sleep(90)
            raise AssertionError('Native call outlived its enforced deadline')
        return handler

    def assert_processes_stopped(self, pids):
        import subprocess
        deadline = time.monotonic()+5
        while time.monotonic() < deadline:
            states = [subprocess.run(['ps', '-o', 'stat=', '-p', str(pid)], capture_output=True, text=True).stdout.strip() for pid in pids]
            if all(not state or state.startswith('Z') for state in states):
                return
            time.sleep(0.05)
        self.fail('Owned native job processes are still running: '+str(pids))

    def test_cancellation_interrupts_native_calls_and_descendants(self):
        import tempfile
        from pathlib import Path
        store, _, _, _ = self.scenario()
        with tempfile.TemporaryDirectory() as directory:
            marker = Path(directory)/'started.json'
            key = enqueue(store, {'marker':str(marker)}, 'native-cancel')
            with ThreadPoolExecutor(max_workers=1) as pool:
                running = pool.submit(execute,key,self.blocking_native_handler(),max_wall_seconds=1800)
                deadline = time.monotonic()+10
                while not marker.exists() and not running.done() and time.monotonic()<deadline:
                    time.sleep(.05)
                self.assertTrue(marker.exists(),'Native worker did not start')
                cancel(self.conn,key)
                result = running.result(timeout=5)
            self.assertEqual(result['state'],'cancelled')
            self.assert_processes_stopped(json.loads(marker.read_text()))
        self.assertEqual(store.list('unfinished_native_result'),[])

    def test_timeout_interrupts_native_calls_and_children_from_a_thread(self):
        import tempfile
        from pathlib import Path
        store, _, _, _ = self.scenario()
        with tempfile.TemporaryDirectory() as directory:
            marker = Path(directory)/'started.json'
            key = enqueue(store, {'marker': str(marker)}, 'native-timeout')
            self.conn.execute('UPDATE backintel.capability_jobs SET max_attempts=1 WHERE job_id=%s', (key,))
            started = time.monotonic()
            with ThreadPoolExecutor(max_workers=1) as pool:
                result = pool.submit(execute, key, self.blocking_native_handler(), max_wall_seconds=25).result(timeout=35)
            self.assertEqual(result['state'], 'failed')
            self.assertIn('wall-time', result['error'])
            self.assertLess(time.monotonic()-started, 35)
            self.assert_processes_stopped(json.loads(marker.read_text()))
        self.assertEqual(store.list('unfinished_native_result'), [])
        self.assertEqual(store.list('job_attempt_result')[0]['body']['status'], 'failed')

    def test_dispatcher_death_stops_native_work_and_allows_retry(self):
        import cloudpickle
        from pathlib import Path
        import subprocess
        import sys
        import tempfile
        store, _, _, _ = self.scenario()
        with tempfile.TemporaryDirectory() as directory:
            marker = Path(directory)/'started.json'
            key = enqueue(store, {'marker': str(marker)}, 'dispatcher-death')
            payload = Path(directory)/'caller.pickle'
            payload.write_bytes(cloudpickle.dumps((key, self.blocking_native_handler())))
            code = 'import cloudpickle,sys; from runtime.jobs import execute; execute(*cloudpickle.load(open(sys.argv[1], "rb")))'
            with subprocess.Popen([sys.executable, '-c', code, str(payload)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL) as caller:
                try:
                    deadline = time.monotonic()+10
                    while not marker.exists() and caller.poll() is None and time.monotonic()<deadline:
                        time.sleep(0.05)
                    self.assertTrue(marker.exists(), 'Native worker did not start')
                finally:
                    caller.kill()
                    caller.wait(timeout=5)
            self.assert_processes_stopped(json.loads(marker.read_text()))
        self.assertEqual(store.list('unfinished_native_result'), [])
        self.conn.execute("UPDATE backintel.capability_jobs SET lease_until=now()-interval '1 second' WHERE job_id=%s", (key,))
        result = execute(key, lambda ledger, payload: ledger.put('recovered_native_result', 'fixture', {}, 10))
        self.assertEqual(result['state'], 'completed')
        self.assertEqual(self.conn.execute('SELECT attempts FROM backintel.capability_jobs WHERE job_id=%s', (key,)).fetchone()[0], 2)

    def test_interrupted_reply_does_not_overwrite_a_committed_result(self):
        from runtime.jobs import _failed_attempt
        store, _, _, _ = self.scenario()
        key = enqueue(store, {}, 'lost-reply')
        accepted = execute(key, lambda ledger, payload: ledger.put('accepted_native_result', 'fixture', {}, 10))
        attempts = store.list('job_attempt_result')
        late = _failed_attempt(self.conn, key, {'attempt': 1}, TimeoutError('Lost reply'), None, None, time.perf_counter())
        self.assertEqual(late['state'], 'completed')
        self.assertEqual(late['result'], accepted['result'])
        self.assertEqual(store.list('job_attempt_result'), attempts)

    def test_persistent_due_triggers_repeat_and_backpressure(self):
        store, task, _, _ = self.scenario()
        trigger = schedule(store,"schedule",{"identity":"scheduled"},time.time()-5,"timer",repeat_seconds=1,occurrences=2)
        with psycopg.connect(dsn(),autocommit=True) as reconnected:
            first = release_due(reconnected)
            second = release_due(reconnected)
            self.assertNotEqual(first,second)
            self.assertEqual(reconnected.execute("SELECT state,occurrence FROM backintel.capability_triggers WHERE trigger_id=%s",(trigger,)).fetchone(),("fired",2))
        self.assertEqual(schedule(store,"schedule",{"identity":"scheduled"},time.time(),"timer",repeat_seconds=1,occurrences=2), trigger)
        with self.assertRaisesRegex(ValueError, "Conflicting trigger identity"):
            schedule(store,"schedule",{"identity":"scheduled"},time.time(),"timer",repeat_seconds=1,occurrences=3)
        for key in first+second:
            execute(key,lambda ledger,payload:ledger.put("test_result","scheduled",payload,0))
        for i in range(20):
            enqueue(store,{"n":i},f"backpressure-{i}")
        with self.assertRaisesRegex(ValueError,"backpressure"):
            enqueue(store,{"n":21},"over-budget")
        self.conn.execute("UPDATE backintel.capability_jobs SET state='cancelled' WHERE task_id=%s AND state='queued'",(store.task_id,))

    def test_forecast_drives_attention_without_turning_unknown_into_false(self):
        from runtime.capability_pipeline import analyze
        store, task, rows, _ = self.scenario()
        admit_source(store, task, {"format": "json", "data": [rows[0]]}, 0)
        source = current_sources(store, 0)[0]
        observation = extract(store, task, source, 0)[0]
        feature = features(store, task, 0)[0]
        # Explicit high-forecast fixture isolates the decision policy, not model quality.
        forecast = store.put("prediction", "high-forecast-fixture", {"feature": feature["sha256"], "value": .9, "implementation_mode": "simulated"}, 0, [feature["sha256"]])
        event = store.put("event", "forecast-check", {"operation": "fixture"}, 0, [task["sha256"]])
        analysis = analyze(store, task, [feature], [forecast], event, 0)
        self.assertEqual(analysis["body"]["rows"][0]["semantic_risk"], 0)
        self.assertEqual(analysis["body"]["rows"][0]["attention_value"], .9)
        episode = attend(store, task, feature["body"]["entity"], analysis, 0, .9)
        self.assertEqual(episode["body"]["condition"], "active")
        self.assertIn(forecast["sha256"], {r["sha256"] for r in store.lineage(episode["sha256"])})
        correct_observation(store, observation["sha256"], {"status": "unknown", "value": None, "distribution": None, "reason": "needs review"}, "operator", "fixture", 1)
        missing = features(store, task, 1)[0]
        forecast = store.put("prediction", "unknown-high-forecast-fixture", {"feature": missing["sha256"], "value": .9, "implementation_mode": "simulated"}, 1, [missing["sha256"]])
        analysis = analyze(store, task, [missing], [forecast], event, 1)
        self.assertIsNone(analysis["body"]["rows"][0]["attention_value"])
        self.assertEqual(attend(store, task, missing["body"]["entity"], analysis, 1, None)["body"]["condition"], "unknown")
        with self.assertRaisesRegex(ValueError, "matching prediction"):
            analyze(store, task, [feature], [forecast], event, 1)

    def test_direct_claim_cannot_bypass_earlier_work(self):
        store, task, _, _ = self.scenario()
        first = enqueue(store, {'fixture':'first'}, 'direct-first')
        second = enqueue(store, {'fixture':'second'}, 'direct-second')
        self.assertIsNone(claim(self.conn, second))
        self.assertIsNotNone(claim(self.conn, first))
        self.assertIsNone(claim(self.conn, second))
        self.conn.execute("UPDATE backintel.capability_jobs SET state='failed' WHERE job_id=%s", (first,))
        self.assertIsNone(claim(self.conn, second))
        self.conn.execute("UPDATE backintel.capability_jobs SET state='cancelled' WHERE job_id=%s", (first,))
        self.assertIsNotNone(claim(self.conn, second))

    def test_dispatch_preserves_order_across_retry_and_restart(self):
        store, task, _, _ = self.scenario()
        with self.conn.transaction():
            first = enqueue(store,{"identity":"first"},"first")
            second = enqueue(store,{"identity":"second"},"second")
        self.assertNotIn(second,runnable(self.conn))
        self.conn.execute("UPDATE backintel.capability_jobs SET state='retry',due_at=now()+interval '1 hour' WHERE job_id=%s",(first,))
        with psycopg.connect(dsn(),autocommit=True) as restarted:
            self.assertNotIn(second,runnable(restarted))
            cancel(restarted,first)
        # Other task queues can precede this one, but no task may bypass its own earlier retry.
        self.conn.execute("UPDATE backintel.capability_jobs SET state='cancelled' WHERE job_id=%s",(second,))

    def test_jsonb_negative_zero_and_failed_job_repair_preserve_evidence(self):
        store, task, _, _ = self.scenario()
        metric = store.put("test_metric","negative-zero",{"loss":-0.0},0)
        self.assertEqual(store.get(metric["sha256"])["body"],{"loss":0.0})
        key = enqueue(store,{"identity":"repaired"},"repaired")
        def failed(ledger,payload):
            raise ValueError("injected failed implementation")
        execute(key,failed)
        self.conn.execute("UPDATE backintel.capability_jobs SET due_at=now() WHERE job_id=%s",(key,))
        self.assertEqual(execute(key,failed)["state"],"failed")
        resume_failed(self.conn,key,"Fixed deterministic implementation failure")
        self.assertEqual(execute(key,lambda ledger,payload:metric)["state"],"completed")
        self.assertEqual([r["body"]["status"] for r in store.list("job_attempt_result")],["retry","failed","completed"])

    def test_attention_hysteresis_acknowledgment_staleness_deadlines_and_local_delivery(self):
        store, task, _, _ = self.scenario()
        def event(at):
            return store.put("test_event",str(at),{"at":at},at,[task["sha256"]])
        opened = attend(store,task,"Accounts",event(0),0,.8)
        self.assertEqual(opened,attend(store,task,"Accounts",event(0),0,.8))
        self.assertEqual(len(store.list("delivery")),1)
        held = attend(store,task,"Accounts",event(1),1,.45)
        self.assertEqual(held["body"]["condition"],"active")
        overdue = attend(store,task,"Accounts",event(4),4,action="deadline")
        self.assertEqual(len(store.list("delivery")),2)
        attend(store,task,"Accounts",event(8),8,action="deadline")
        self.assertEqual(len(store.list("delivery")),2)
        acknowledged = attend(store,task,"Accounts",event(9),9,action="acknowledge")
        self.assertEqual(acknowledged["body"]["condition"],"active")
        stale = attend(store,task,"Accounts",event(10),10,action="staleness")
        self.assertEqual(stale["body"]["condition"],"unknown")
        resolved = attend(store,task,"Accounts",event(11),11,action="resolve")
        self.assertEqual(resolved["body"]["condition"],"unknown")
        cleared = attend(store,task,"Accounts",event(12),12,.1)
        self.assertEqual(cleared["body"]["condition"],"cleared")
        self.assertEqual({r["body"]["channel"] for r in store.list("delivery")},{"local_inbox"})


if __name__ == "__main__":
    unittest.main()
