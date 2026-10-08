"""Database concurrency and failure recovery; all provider replies are fixtures."""
import hashlib
import os
import threading
import unittest
import uuid
from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal
from unittest.mock import patch

from psycopg.conninfo import conninfo_to_dict
from psycopg.types.json import Jsonb

from runtime import analysis_store as db, analysis_service as service
from runtime.analysis_data import CONFIG, digest


@unittest.skipUnless(os.getenv('BACKINTEL_ANALYSIS_CHECK_DB'), 'Requires isolated analysis-check database')
class CampaignChecks(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        uri = os.environ['BACKINTEL_ANALYSIS_CHECK_DB']
        name = conninfo_to_dict(uri)['dbname']
        if not (name.startswith('backintel_') and name.endswith('_test')):
            raise RuntimeError('Campaign fixtures require a disposable backintel_*_test database')
        os.environ['BACKINTEL_APP_DATABASE_URL'] = uri
        os.environ['BACKINTEL_TEST_DATABASE_URL'] = uri
        from runtime.bootstrap import initialize
        initialize()
        db.catalog()
        for role in ('manager', 'analyst', 'viewer'):
            identity = 'campaign-' + role
            db.write('INSERT INTO backintel.analysis_principals(id,token_hash,role,domains) VALUES(%s,%s,%s,%s) ON CONFLICT DO NOTHING',
                     (identity, hashlib.sha256(identity.encode()).hexdigest(), role, ['commerce', 'support']))
        cls.actor = {'id': 'campaign-manager'}

    def setUp(self):
        from runtime import jobs
        # Inject failures inside the acceptance transaction. Real process
        # termination is covered independently in test_capabilities.
        worker = patch.object(jobs, '_run_worker', side_effect=jobs._execute_claimed)
        worker.start()
        self.addCleanup(worker.stop)
        # The class guard above permits cleanup only in the disposable fixture DB.
        db.write('DELETE FROM backintel.analysis_requests')
        db.write("UPDATE backintel.capability_jobs SET state='cancelled' WHERE state IN ('queued','retry') AND task_id LIKE 'analysis-job-%'")
        self.rows = [{'id': str(uuid.uuid4()), 'entity': 'fixture', 'features': {'age': 40},
                      'target': 1, 'groups': {'department': 'A'}, 'text': 'fixture', 'split': 'train'}]
        self.snapshot = digest(self.rows)
        db.save_snapshot('commerce', self.snapshot, {'files': [], 'rows': 1, 'mode': 'fixture'}, self.rows)
        self.goal = service.create_goal(self.actor, 'commerce', 'What is the observed recommendation rate?')['id']
        service.revise_goal(self.goal, self.actor, confirmed=True)
        self.run = service.submit(self.goal, self.actor)

    def settled(self, identity, amount, run=None):
        r = run or self.run
        db.write('INSERT INTO backintel.analysis_requests(id,run_id,domain,reserved,charge,status,response) VALUES(%s,%s,%s,%s,%s,%s,%s)',
                 (identity, r['id'], db.goal(r['goal_id'])['domain'], amount, amount, 'complete', Jsonb({'mode': 'fixture', 'id': identity})))

    def test_over_reservation_charge_blocks_reconciliation_and_future_calls(self):
        from runtime.analysis_agent import record_charge, reconcile_charge
        db.reserve(self.run['id'], 'over-reservation', Decimal('.01'))
        with self.assertRaisesRegex(RuntimeError, 'exceeds approved reservation'):
            record_charge('over-reservation', Decimal('.02'))
        recorded = db.query('SELECT status,charge FROM backintel.analysis_requests WHERE id=%s', ('over-reservation',), one=True)
        self.assertEqual(recorded, {'status':'uncertain','charge':Decimal('.02')})
        with self.assertRaisesRegex(RuntimeError, 'exceeds approved reservation'):
            reconcile_charge('over-reservation', self.actor)
        with self.assertRaisesRegex(RuntimeError, 'unresolved provider charge'):
            db.reserve(self.run['id'], 'next-request', Decimal('.01'))

    def test_charge_within_reservation_completes(self):
        from runtime.analysis_agent import record_charge
        db.reserve(self.run['id'], 'within-reservation', Decimal('.02'))
        record_charge('within-reservation', Decimal('.01'))
        self.assertEqual(db.query('SELECT status FROM backintel.analysis_requests WHERE id=%s', ('within-reservation',), one=True)['status'], 'complete')

    def test_resubmission_respects_five_attempt_boundary(self):
        for attempts in (3, 4):
            db.write("UPDATE backintel.capability_jobs SET state='failed',attempts=%s,max_attempts=%s WHERE job_id=%s", (attempts, attempts, self.run['job_id']))
            db.write("UPDATE backintel.analysis_runs SET status='partial' WHERE id=%s", (self.run['id'],))
            self.assertEqual(service.submit(self.goal, self.actor)['status'], 'queued')
            self.assertEqual(db.query('SELECT max_attempts FROM backintel.capability_jobs WHERE job_id=%s', (self.run['job_id'],), one=True)['max_attempts'], 5)
        db.write("UPDATE backintel.capability_jobs SET state='failed',attempts=5 WHERE job_id=%s", (self.run['job_id'],))
        db.write("UPDATE backintel.analysis_runs SET status='partial' WHERE id=%s", (self.run['id'],))
        with self.assertRaisesRegex(RuntimeError, 'five-attempt limit'):
            service.submit(self.goal, self.actor)
        self.assertEqual(db.run(self.run['id'])['status'], 'partial')

    def test_admission_reloads_goal_after_concurrent_edit(self):
        stale = db.goal(self.goal)
        service.revise_goal(self.goal, self.actor, question='Revised fixture question')
        with db.connect() as c, c.transaction(), self.assertRaisesRegex(ValueError, 'Confirm.*goal'):
            service._admit_run(c, stale, self.actor)
        service.revise_goal(self.goal, self.actor, confirmed=True)
        with db.connect() as c, c.transaction():
            identity = service._admit_run(c, stale, self.actor)
        current = db.run(identity)
        self.assertEqual(current['goal_version'], db.goal(self.goal)['version'])
        self.assertEqual(current['body']['question'], 'Revised fixture question')

    def test_cancellation_before_sent_transition_prevents_provider_post(self):
        from unittest.mock import MagicMock
        from runtime import analysis_agent as agent
        from runtime.jobs import cancel
        client = MagicMock()
        client.__enter__.return_value = client
        client.get.return_value.json.return_value = {'data':[{'id':CONFIG['analyst']['model'],'pricing':{'prompt':'0','completion':'0'}}]}
        query = db.query
        def cancel_before_dispatch(sql, *args, **kwargs):
            if sql.startswith("UPDATE backintel.analysis_requests SET status='sent'"):
                with db.connect() as connection:
                    cancel(connection, self.run['job_id'])
            return query(sql, *args, **kwargs)
        with patch.object(agent, 'credential', return_value='fixture'), patch.object(agent.httpx, 'Client', return_value=client), \
                patch.object(db, 'query', side_effect=cancel_before_dispatch), self.assertRaisesRegex(RuntimeError, 'reservation changed'):
            agent.request(self.run['id'], 0, [])
        client.post.assert_not_called()

    def test_revoked_confirmation_stops_dispatch_and_publication(self):
        from unittest.mock import MagicMock
        from runtime import analysis_agent as agent
        service.revise_goal(self.goal, self.actor, confirmed=False)
        with self.assertRaisesRegex(PermissionError, 'unconfirmed'):
            db.check_run(self.run['id'])
        service.revise_goal(self.goal, self.actor, confirmed=True)
        client = MagicMock()
        client.__enter__.return_value = client
        client.get.return_value.json.return_value = {'data':[{'id':CONFIG['analyst']['model'],'pricing':{'prompt':'0','completion':'0'}}]}
        query = db.query
        def revoke_before_dispatch(sql, *args, **kwargs):
            if sql.startswith("UPDATE backintel.analysis_requests SET status='sent'"):
                service.revise_goal(self.goal, self.actor, confirmed=False)
            return query(sql, *args, **kwargs)
        with patch.object(agent, 'credential', return_value='fixture'), patch.object(agent.httpx, 'Client', return_value=client), patch.object(db, 'query', side_effect=revoke_before_dispatch), self.assertRaisesRegex(RuntimeError, 'reservation changed'):
            agent.request(self.run['id'], 0, [])
        client.post.assert_not_called()
        service.revise_goal(self.goal, self.actor, confirmed=True)
        def revoke_during_analysis(identity):
            service.revise_goal(self.goal, self.actor, confirmed=False)
            return {'summary':'fixture'}
        with patch.object(agent, 'analyze', side_effect=revoke_during_analysis):
            service.execute(self.run['job_id'], service.handle)
        self.assertEqual(db.run(self.run['id'])['status'], 'cancelled')
        self.assertIsNone(db.goal(self.goal)['last_success'])

    def test_import_publication_and_followups_share_job_acceptance(self):
        from runtime.jobs import cancel
        db.write("UPDATE backintel.analysis_sources SET body=body || %s WHERE id='commerce'", (Jsonb({'terms_acknowledged':True}),))
        for boundary in ('cancel_during_adaptation', 'interrupt_before_commit', 'success'):
            with self.subTest(boundary=boundary):
                run = service.submit_import('commerce', self.actor)
                snapshot = digest([self.snapshot, boundary])
                def adapt(domain, paths):
                    if boundary == 'cancel_during_adaptation':
                        with db.connect() as c:
                            cancel(c, run['job_id'])
                    return snapshot, {'files':[], 'mode':'fixture'}, self.rows
                def handler(store, payload):
                    result = service.handle(store, payload)
                    if boundary == 'interrupt_before_commit':
                        raise KeyboardInterrupt('Fixture interruption before acceptance')
                    return result
                with patch.object(service, 'source_files', return_value=[]), patch.object(service, 'adapt', side_effect=adapt):
                    if boundary == 'interrupt_before_commit':
                        with self.assertRaises(KeyboardInterrupt):
                            service.execute(run['job_id'], handler)
                        db.write("UPDATE backintel.analysis_runs SET status='partial' WHERE id=%s", (run['id'],))
                    else:
                        service.execute(run['job_id'], handler)
                if boundary == 'success':
                    self.assertEqual(db.source('commerce')['latest_snapshot'], snapshot)
                    admitted = db.query('SELECT snapshot_id FROM backintel.analysis_runs WHERE goal_id=%s AND snapshot_id=%s', (self.goal, snapshot))
                    self.assertEqual(len(admitted), 1)
                    self.assertEqual(db.run(run['id'])['status'], 'succeeded')
                else:
                    self.assertEqual(db.source('commerce')['latest_snapshot'], self.snapshot)
                    self.assertFalse(db.query('SELECT id FROM backintel.analysis_snapshots WHERE id=%s', (snapshot,)))
                    self.assertFalse(db.query('SELECT id FROM backintel.analysis_runs WHERE snapshot_id=%s', (snapshot,)))

    def test_failed_queued_import_preserves_refresh_error(self):
        db.write("UPDATE backintel.analysis_sources SET body=body || %s WHERE id='commerce'", (Jsonb({'terms_acknowledged':True}),))
        run = service.submit_import('commerce', self.actor)
        with patch.object(service, 'source_files', return_value=[]), patch.object(service, 'adapt', side_effect=OSError('Fixture source unavailable')):
            service.execute(run['job_id'], service.handle)
        source = db.source('commerce')
        self.assertEqual(source['latest_snapshot'], self.snapshot)
        self.assertIn('Fixture source unavailable', source['body']['last_refresh_error'])
        self.assertGreater(source['body']['last_checked_at'], 0)
        self.assertEqual(db.run(run['id'])['status'], 'partial')

    def test_empty_corrections_preserve_snapshot_and_explicit_null_removes_target(self):
        from runtime.analysis_api import correction, CorrectionInput
        service.revise_goal(self.goal, self.actor, paused=True)
        for change in ({}, {'features':{'age':40}}, {'target':1}):
            with self.subTest(change=change), self.assertRaisesRegex(ValueError, 'change at least one value'):
                correction('commerce', CorrectionInput(record_id=self.rows[0]['id'], explanation='Fixture no change', **change), self.actor)
            self.assertEqual(db.source('commerce')['latest_snapshot'], self.snapshot)
        correction('commerce', CorrectionInput(record_id=self.rows[0]['id'], target=None, explanation='Fixture remove mistaken label'), self.actor)
        self.assertIsNone(db.records(db.source('commerce')['latest_snapshot'])[0]['target'])

    def test_source_terms_changes_share_the_import_lock(self):
        from runtime.analysis_api import terms, TermsInput
        started = threading.Event()
        def revoke():
            started.set()
            return terms('commerce', TermsInput(acknowledged=False), self.actor)
        with ThreadPoolExecutor(max_workers=1) as workers, db.connect() as c:
            with c.transaction():
                c.execute('SELECT pg_advisory_xact_lock(hashtextextended(%s,0))', ('analysis-source:commerce',))
                revoked = workers.submit(revoke)
                self.assertTrue(started.wait(5))
                with self.assertRaises(TimeoutError):
                    revoked.result(timeout=.25)
            self.assertFalse(revoked.result(timeout=5)['body']['terms_acknowledged'])

    def test_import_serializes_with_manager_correction(self):
        from runtime.analysis_api import correction, CorrectionInput
        service.revise_goal(self.goal, self.actor, paused=True)
        db.write("UPDATE backintel.analysis_sources SET body=body || %s WHERE id='commerce'", (Jsonb({'terms_acknowledged':True}),))
        adapting, release, correction_read = threading.Event(), threading.Event(), threading.Event()
        snapshot = digest([self.snapshot, 'import'])
        original_records = db.records
        def adapt(domain, paths):
            adapting.set()
            if not release.wait(5):
                raise TimeoutError('Fixture adaptation was not released')
            return snapshot, {'files':[], 'mode':'fixture'}, self.rows
        def records(identity, **kwargs):
            correction_read.set()
            return original_records(identity, **kwargs)
        with patch.object(service, 'source_files', return_value=[]), patch.object(service, 'adapt', side_effect=adapt), patch.object(db, 'records', side_effect=records), ThreadPoolExecutor(max_workers=2) as workers:
            imported = workers.submit(service.import_source, 'commerce', self.actor)
            try:
                self.assertTrue(adapting.wait(5))
                corrected = workers.submit(correction, 'commerce', CorrectionInput(record_id=self.rows[0]['id'], features={'age':41}, explanation='Fixture correction'), self.actor)
                self.assertFalse(correction_read.wait(.25))
            finally:
                release.set()
            imported.result(timeout=5)
            corrected.result(timeout=5)
        self.assertEqual(db.records(db.source('commerce')['latest_snapshot'])[0]['features']['age'], 41)

    def test_corrections_preserve_feature_types_including_missing_values(self):
        from runtime.analysis_api import correction, CorrectionInput
        service.revise_goal(self.goal, self.actor, paused=True)
        rows = [dict(self.rows[0], features={'age':40, 'department':'A'}),
                dict(self.rows[0], id='missing', features={'age':None, 'department':None})]
        snapshot = digest(rows)
        db.save_snapshot('commerce', snapshot, {'files':[], 'mode':'fixture'}, rows)
        for features in ({'age':'forty'}, {'department':42}):
            with self.subTest(features=features), self.assertRaisesRegex(ValueError, 'established type'):
                correction('commerce', CorrectionInput(record_id='missing', features=features, explanation='Fixture invalid type'), self.actor)
            self.assertEqual(db.source('commerce')['latest_snapshot'], snapshot)
        correction('commerce', CorrectionInput(record_id='missing', features={'age':41, 'department':'B'}, explanation='Fixture valid types'), self.actor)
        correction('commerce', CorrectionInput(record_id='missing', features={'age':None}, explanation='Fixture missing value'), self.actor)
        saved = next(r for r in db.records(db.source('commerce')['latest_snapshot']) if r['id']=='missing')
        self.assertEqual(saved['features'], {'age':None, 'department':'B'})

    def test_success_publication_recovers_atomically(self):
        result = {'summary': 'explicit fixture', 'tables': [], 'mode': 'fixture'}
        with patch('runtime.analysis_agent.analyze', return_value=result):
            service.execute(self.run['job_id'], service.handle)
            previous = self.run['id']
            for boundary in ('during_publication', 'before_job_commit'):
                with self.subTest(boundary=boundary):
                    snapshot = digest([self.snapshot, boundary])
                    db.save_snapshot('commerce', snapshot, {'files': [], 'mode': 'fixture'}, self.rows)
                    run = service.submit(self.goal, self.actor)
                    def interrupted(store, payload):
                        if boundary == 'during_publication':
                            with patch.object(service, 'threshold_crossed', side_effect=KeyboardInterrupt):
                                return service.handle(store, payload)
                        service.handle(store, payload)
                        raise KeyboardInterrupt
                    with self.assertRaises(KeyboardInterrupt):
                        service.execute(run['job_id'], interrupted)
                    self.assertEqual(db.goal(self.goal)['last_success'], previous)
                    self.assertNotEqual(db.run(run['id'])['status'], 'succeeded')
                    self.assertEqual(db.query("SELECT count(*) AS n FROM backintel.analysis_events WHERE run_id=%s AND kind='completed'", (run['id'],), one=True)['n'], 0)
                    service.dispatch()
                    self.assertEqual(db.goal(self.goal)['last_success'], run['id'])
                    self.assertEqual(db.run(run['id'])['status'], 'succeeded')
                    job = db.query('SELECT state,result_sha256 FROM backintel.capability_jobs WHERE job_id=%s', (run['job_id'],), one=True)
                    self.assertEqual(job['state'], 'completed')
                    self.assertTrue(job['result_sha256'])
                    self.assertEqual(db.query("SELECT count(*) AS n FROM backintel.analysis_events WHERE run_id=%s AND kind='completed'", (run['id'],), one=True)['n'], 1)
                    previous = run['id']

    def test_refresh_retries_unchanged_snapshot_without_blocking_other_goals(self):
        revoked = 'revoked-' + uuid.uuid4().hex
        db.write('INSERT INTO backintel.analysis_principals(id,token_hash,role,domains) VALUES(%s,%s,%s,%s)',
                 (revoked, hashlib.sha256(revoked.encode()).hexdigest(), 'manager', ['commerce']))
        blocked = service.create_goal({'id': revoked}, 'commerce', 'Revoked owner fixture')['id']
        service.revise_goal(blocked, {'id': revoked}, confirmed=True)
        db.write('UPDATE backintel.analysis_principals SET enabled=false WHERE id=%s', (revoked,))
        snapshot = digest([self.snapshot, 'arrival'])
        db.save_snapshot('commerce', snapshot, {'files': [], 'mode': 'fixture'}, self.rows)
        original_submit = service.submit
        def transient(identity, actor, **kwargs):
            if identity == self.goal:
                raise RuntimeError('Temporary scheduling failure')
            return original_submit(identity, actor, **kwargs)
        with patch.object(service, 'submit', side_effect=transient):
            first = service.schedule_snapshot('commerce', {'changed': True, 'snapshot': snapshot})
        self.assertEqual(next(item for item in first if item['goal_id'] == self.goal)['status'], 'blocked')
        healthy = service.create_goal(self.actor, 'commerce', 'Healthy owner fixture')['id']
        service.revise_goal(healthy, self.actor, confirmed=True)
        for _ in range(2):
            outcomes = service.schedule_snapshot('commerce', {'changed': False, 'snapshot': snapshot})
            self.assertEqual(next(item for item in outcomes if item['goal_id'] == blocked)['status'], 'blocked')
            for goal in (self.goal, healthy):
                self.assertEqual(next(item for item in outcomes if item['goal_id'] == goal)['status'], 'queued')
                self.assertEqual(db.query('SELECT count(*) AS n FROM backintel.analysis_runs WHERE goal_id=%s AND snapshot_id=%s', (goal, snapshot), one=True)['n'], 1)

    def test_invalid_cost_and_request_ceiling(self):
        for amount in (-.01, 'NaN', 'Infinity', True):
            with self.subTest(amount=amount), self.assertRaises(ValueError):
                db.reserve(self.run['id'], 'invalid', amount)
        with self.assertRaisesRegex(RuntimeError, 'request reservation'):
            db.reserve(self.run['id'], 'too-expensive', .250001)
        self.assertEqual(db.query('SELECT count(*) AS n FROM backintel.analysis_requests', one=True)['n'], 0)

    def test_concurrent_admission_keeps_one_request_in_flight(self):
        barrier = threading.Barrier(2)
        def admit(number):
            barrier.wait(timeout=10)
            try:
                db.reserve(self.run['id'], 'race-' + str(number), .20)
                return 'admitted'
            except RuntimeError:
                return 'blocked'
        with ThreadPoolExecutor(max_workers=2) as workers:
            results = list(workers.map(admit, range(2)))
        self.assertCountEqual(results, ['admitted', 'blocked'])
        self.assertEqual(db.usage(self.run['id'])['reserved_usd'], .20)

    def test_concurrent_admission_near_campaign_cap(self):
        support_snapshot = digest(['support', self.rows])
        db.save_snapshot('support', support_snapshot, {'files': [], 'rows': 1, 'mode': 'fixture'}, self.rows)
        support_goal = service.create_goal(self.actor, 'support', 'Historical support fixture')['id']
        service.revise_goal(support_goal, self.actor, confirmed=True)
        for i in range(39):
            other = service.submit(self.goal if i < 19 else support_goal, self.actor, question='Historical fixture ' + str(i))
            self.settled('history-' + str(i), Decimal('.25'), other)
        # Exactly $0.25 remains; two $0.20 requests may not both enter.
        self.test_concurrent_admission_keeps_one_request_in_flight()
        total = db.query('SELECT sum(COALESCE(charge,reserved)) AS n FROM backintel.analysis_requests', one=True)['n']
        self.assertEqual(total, Decimal('9.95'))
        self.assertLessEqual(total, Decimal(str(CONFIG['budget']['suite_usd'])))

    def test_campaign_run_and_goal_limits(self):
        service.revise_goal(self.goal, self.actor, budget_usd=.10)
        service.revise_goal(self.goal, self.actor, confirmed=True)
        run = service.submit(self.goal, self.actor)
        with self.assertRaisesRegex(RuntimeError, 'run inference budget'):
            db.reserve(run['id'], 'goal-cap', .11)
        service.revise_goal(self.goal, self.actor, budget_usd=1)
        service.revise_goal(self.goal, self.actor, confirmed=True)
        self.run = service.submit(self.goal, self.actor)
        for i in range(6):
            self.settled('six-' + str(i), Decimal('.01'))
        with self.assertRaisesRegex(RuntimeError, 'Investigation provider call'):
            db.reserve(self.run['id'], 'seventh', .01)
        db.write('DELETE FROM backintel.analysis_requests')
        for i in range(200):
            other = service.submit(self.goal, self.actor, question='Attempt fixture ' + str(i))
            self.settled('attempt-' + str(i), Decimal('0'), other)
        with self.assertRaisesRegex(RuntimeError, 'Campaign provider attempt'):
            db.reserve(self.run['id'], 'attempt-201', .01)

    def test_settlement_replay_and_uncertain_charge(self):
        db.reserve(self.run['id'], 'settled', .20)
        response = {'mode': 'fixture', 'id': 'original-provider-identity'}
        db.write("UPDATE backintel.analysis_requests SET status='complete',charge=.03,response=%s WHERE id='settled'", (Jsonb(response),))
        self.assertEqual(db.reserve(self.run['id'], 'settled', .20), response)
        self.assertEqual(db.usage(self.run['id'])['provider_usd'], .03)
        self.assertEqual(db.usage(self.run['id'])['reserved_usd'], 0)
        db.reserve(self.run['id'], 'ambiguous', .20)
        db.write("UPDATE backintel.analysis_requests SET status='uncertain' WHERE id='ambiguous'")
        other = service.submit(self.goal, self.actor, question='Follow-up fixture')
        with self.assertRaisesRegex(RuntimeError, 'unresolved provider charge'):
            db.reserve(other['id'], 'unsafe-retry', .01)
        db.write("UPDATE backintel.analysis_runs SET status='partial' WHERE id=%s", (self.run['id'],))
        with self.assertRaisesRegex(RuntimeError, 'Reconcile uncertain'):
            service.submit(self.goal, self.actor)

    def test_duplicate_submissions_cancel_and_orphan_recovery(self):
        with ThreadPoolExecutor(max_workers=3) as workers:
            duplicates = list(workers.map(lambda _: service.submit(self.goal, self.actor), range(3)))
        self.assertEqual({r['job_id'] for r in duplicates}, {self.run['job_id']})
        # A real dispatcher owns the advisory lock and reclaims an orphaned job.
        db.write("UPDATE backintel.capability_jobs SET state='running',attempts=1,lease_until=now()+interval '1 hour' WHERE job_id=%s", (self.run['job_id'],))
        with patch('runtime.analysis_agent.analyze', return_value={'summary': 'explicit fixture', 'tables': [], 'mode': 'fixture'}):
            service.dispatch()
        self.assertEqual(db.run(self.run['id'])['status'], 'succeeded')
        self.assertEqual(db.query('SELECT attempts FROM backintel.capability_jobs WHERE job_id=%s', (self.run['job_id'],), one=True)['attempts'], 2)
        other = service.submit(self.goal, self.actor, question='Cancelled fixture')
        from runtime.jobs import cancel
        with db.connect() as connection:
            cancel(connection, other['job_id'])
        with self.assertRaises(InterruptedError):
            db.check_run(other['id'])

    def test_cancelled_run_resubmits_same_job_without_reviving_active_attempt(self):
        from runtime.analysis_api import cancel_run
        cancel_run(self.run['id'], self.actor)
        resumed = service.submit(self.goal, self.actor)
        self.assertEqual(resumed['id'], self.run['id'])
        self.assertEqual(resumed['status'], 'queued')
        job = db.query('SELECT state,cancel_requested FROM backintel.capability_jobs WHERE job_id=%s', (resumed['job_id'],), one=True)
        self.assertEqual(job, {'state': 'queued', 'cancel_requested': False})
        db.write("UPDATE backintel.capability_jobs SET state='running',cancel_requested=true WHERE job_id=%s", (resumed['job_id'],))
        db.write("UPDATE backintel.analysis_runs SET status='cancelled' WHERE id=%s", (resumed['id'],))
        self.assertEqual(service.submit(self.goal, self.actor)['status'], 'cancelled')
        self.assertTrue(db.query('SELECT cancel_requested FROM backintel.capability_jobs WHERE job_id=%s', (resumed['job_id'],), one=True)['cancel_requested'])
        service.dispatch()
        self.assertEqual(db.query('SELECT state FROM backintel.capability_jobs WHERE job_id=%s', (resumed['job_id'],), one=True)['state'], 'cancelled')
        self.assertEqual(service.submit(self.goal, self.actor)['status'], 'queued')

    def test_cancelled_run_requires_charge_reconciliation_before_resuming(self):
        from runtime.analysis_api import cancel_run
        cancel_run(self.run['id'], self.actor)
        db.write('INSERT INTO backintel.analysis_requests(id,run_id,domain,reserved,status) VALUES(%s,%s,%s,%s,%s)',
                 (str(uuid.uuid4()), self.run['id'], 'commerce', Decimal('0.01'), 'uncertain'))
        with self.assertRaisesRegex(RuntimeError, 'Reconcile uncertain charges'):
            service.submit(self.goal, self.actor)
        self.assertEqual(db.run(self.run['id'])['status'], 'cancelled')

    def test_exhausted_orphan_stops_application_progress_and_emits_completion(self):
        db.write("UPDATE backintel.capability_jobs SET state='running',attempts=max_attempts,lease_until=now()+interval '1 hour' WHERE job_id=%s", (self.run['job_id'],))
        db.write("UPDATE backintel.analysis_runs SET status='running' WHERE id=%s", (self.run['id'],))
        service.dispatch()
        self.assertEqual(db.run(self.run['id'])['status'], 'partial')
        events = db.query("SELECT body FROM backintel.analysis_events WHERE run_id=%s AND kind='completed'", (self.run['id'],))
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]['body']['status'], 'partial')
        service.dispatch()
        self.assertEqual(len(db.query("SELECT body FROM backintel.analysis_events WHERE run_id=%s AND kind='completed'", (self.run['id'],))), 1)

    def test_explicit_resubmission_recovers_exhausted_job(self):
        db.write("UPDATE backintel.capability_jobs SET state='failed',attempts=max_attempts WHERE job_id=%s", (self.run['job_id'],))
        db.write("UPDATE backintel.analysis_runs SET status='partial' WHERE id=%s", (self.run['id'],))
        previous = db.query('SELECT attempts FROM backintel.capability_jobs WHERE job_id=%s', (self.run['job_id'],), one=True)['attempts']
        resumed = service.submit(self.goal, self.actor)
        self.assertEqual((resumed['id'], resumed['job_id'], resumed['status']), (self.run['id'], self.run['job_id'], 'queued'))
        with patch('runtime.analysis_agent.analyze', return_value={'summary': 'explicit fixture', 'tables': [], 'mode': 'fixture'}):
            service.dispatch()
        self.assertEqual(db.run(self.run['id'])['status'], 'succeeded')
        self.assertEqual(db.query('SELECT attempts FROM backintel.capability_jobs WHERE job_id=%s', (self.run['job_id'],), one=True)['attempts'], previous + 1)

    def test_resumed_run_uses_current_authorized_submitter(self):
        db.write("UPDATE backintel.capability_jobs SET state='cancelled' WHERE job_id=%s", (self.run['job_id'],))
        db.write("UPDATE backintel.analysis_runs SET status='cancelled' WHERE id=%s", (self.run['id'],))
        db.write('UPDATE backintel.analysis_principals SET enabled=false WHERE id=%s', (self.actor['id'],))
        self.addCleanup(db.write, 'UPDATE backintel.analysis_principals SET enabled=true WHERE id=%s', (self.actor['id'],))
        resumed = service.submit(self.goal, {'id': 'campaign-analyst'})
        self.assertEqual(resumed['owner'], 'campaign-analyst')
        db.check_run(resumed['id'])
        with patch('runtime.analysis_agent.analyze', return_value={'summary': 'authorized retry fixture', 'tables': []}):
            service.dispatch()
        self.assertEqual(db.run(resumed['id'])['status'], 'succeeded')

    def test_viewer_model_response_contains_only_aggregate_summary(self):
        from fastapi.testclient import TestClient
        from runtime.analysis_api import app
        private = 'private-record-identifier'
        method = {'route': 'catboost', 'features': 'facts', 'metrics': {'accuracy': .8}, 'predictions': {private: .9}}
        manifest = {'methods': [method], 'splits': {'test': [private]}, 'artifacts': [{'file': private}]}
        db.write('INSERT INTO backintel.analysis_models(id,goal_id,snapshot_id,body) VALUES(%s,%s,%s,%s)',
                 (digest([self.goal, 'viewer']), self.goal, self.snapshot, Jsonb(manifest)))
        client = TestClient(app)
        route = '/api/v1/goals/' + self.goal + '/models'
        viewer = client.get(route, headers={'Authorization': 'Bearer campaign-viewer'})
        self.assertEqual(viewer.status_code, 200, viewer.text)
        self.assertNotIn(private, viewer.text)
        self.assertEqual(viewer.json()[0]['body'], {'methods': [{k:method[k] for k in ('route','features','metrics')}]})
        manager = client.get(route, headers={'Authorization': 'Bearer campaign-manager'})
        self.assertEqual(manager.json()[0]['body'], manifest)
        db.write('UPDATE backintel.analysis_runs SET result=%s WHERE id=%s', (Jsonb({'comparison': manifest}), self.run['id']))
        for route in ('/api/v1/runs?goal_id='+self.goal, '/api/v1/runs/'+self.run['id']):
            response = client.get(route, headers={'Authorization': 'Bearer campaign-viewer'})
            self.assertEqual(response.status_code, 200, response.text)
            self.assertNotIn(private, response.text)
        evidence = db.evidence(self.run['id'], 'model_comparison', 'viewer-model', manifest)
        self.assertEqual(client.get('/api/v1/evidence/'+evidence, headers={'Authorization': 'Bearer campaign-viewer'}).status_code, 403)
        self.assertEqual(client.get('/api/v1/evidence/'+evidence, headers={'Authorization': 'Bearer campaign-manager'}).status_code, 200)

    def test_correction_during_comparison_rejects_late_candidate(self):
        import json
        from types import SimpleNamespace
        from runtime.analysis_api import correction, CorrectionInput
        training = service.submit(self.goal, self.actor, operation='training')
        manifest = {'id': 'stale-comparison', 'artifacts': [{'file': 'catboost-facts.joblib'}],
                    'splits': {'train': [self.rows[0]['id']]}}
        def compare(*args, **kwargs):
            with patch.object(service, 'schedule_snapshot', return_value=[]):
                correction('commerce', CorrectionInput(record_id=self.rows[0]['id'], features={'age': 41}, explanation='fixture correction'), self.actor)
            return SimpleNamespace(returncode=0, stdout=json.dumps(manifest))
        with patch.object(service.subprocess, 'run', side_effect=compare):
            with self.assertRaisesRegex(ValueError, 'Source changed during model comparison'):
                service.model_job(training['id'])
        self.assertIsNone(db.query('SELECT id FROM backintel.analysis_models WHERE goal_id=%s', (self.goal,), one=True))

    def test_corrections_update_domain_group_aliases(self):
        from runtime.analysis_api import correction, CorrectionInput
        from runtime.analysis_agent import aggregate
        db.write('UPDATE backintel.analysis_principals SET domains=%s WHERE id=%s', (['commerce', 'support', 'churn', 'credit'], self.actor['id']))
        self.addCleanup(db.write, 'UPDATE backintel.analysis_principals SET domains=%s WHERE id=%s', (['commerce', 'support'], self.actor['id']))
        for domain, features, groups, changes, expected in (
            ('churn', {'Contract': 'Month-to-month', 'InternetService': 'DSL'},
             {'contract': 'Month-to-month', 'internet_service': 'DSL'},
             {'Contract': 'Two year', 'InternetService': 'Fiber optic'},
             {'contract': 'Two year', 'internet_service': 'Fiber optic'}),
            ('credit', {'NAME_INCOME_TYPE': 'Working', 'NAME_CONTRACT_TYPE': 'Cash loans'},
             {'income_type': 'Working', 'contract_type': 'Cash loans'},
             {'NAME_INCOME_TYPE': 'Pensioner', 'NAME_CONTRACT_TYPE': 'Revolving loans'},
             {'income_type': 'Pensioner', 'contract_type': 'Revolving loans'}),
        ):
            with self.subTest(domain=domain):
                rows = [{**self.rows[0], 'features': features, 'groups': groups}]
                db.save_snapshot(domain, digest(rows), {'files': [], 'rows': 1}, rows)
                with patch.object(service, 'schedule_snapshot', return_value=[]):
                    correction(domain, CorrectionInput(record_id=rows[0]['id'], features=changes, explanation='fixture correction'), self.actor)
                updated = db.records(db.source(domain)['latest_snapshot'])
                self.assertEqual(updated[0]['groups'], expected)
                for group, label in expected.items():
                    self.assertEqual(aggregate(updated, group)[0]['group'], label)

    def test_terminal_worker_timeout_preserves_uncertain_charge_and_finishes_run(self):
        db.write('UPDATE backintel.capability_jobs SET max_attempts=1 WHERE job_id=%s', (self.run['job_id'],))
        request = str(uuid.uuid4())
        db.write('INSERT INTO backintel.analysis_requests(id,run_id,domain,reserved,status) VALUES(%s,%s,%s,%s,%s)',
                 (request, self.run['id'], 'commerce', Decimal('0.01'), 'uncertain'))
        with patch('runtime.jobs._run_worker', side_effect=TimeoutError('Job wall-time budget exceeded')):
            service.dispatch()
        self.assertEqual(db.run(self.run['id'])['status'], 'partial')
        self.assertIsNone(db.goal(self.goal)['last_success'])
        self.assertIsNone(db.query('SELECT charge FROM backintel.analysis_requests WHERE id=%s', (request,), one=True)['charge'])
        self.assertEqual(len(db.query("SELECT body FROM backintel.analysis_events WHERE run_id=%s AND kind='completed'", (self.run['id'],))), 1)

    def test_model_promotion_marks_preserved_answer_stale_after_failed_refresh(self):
        from runtime.analysis_api import goals, findings
        # The combined suite shares source records with import-failure tests.
        # This scenario starts with a healthy source and changes only the model.
        db.write("UPDATE backintel.analysis_sources SET body=body-'last_refresh_error' WHERE id=%s", ('commerce',))
        with patch('runtime.analysis_agent.analyze', return_value={'summary': 'standing fixture', 'tables': []}):
            service.dispatch()
        identity = digest([self.goal, 'model fixture'])
        db.write('INSERT INTO backintel.analysis_models(id,goal_id,snapshot_id,body) VALUES(%s,%s,%s,%s)',
                 (identity, self.goal, self.snapshot, Jsonb({'artifacts': [{'file': 'catboost-facts.joblib'}]})))
        service.promote(identity, self.actor)
        with patch('runtime.analysis_agent.analyze', side_effect=RuntimeError('Fixture provider failure')):
            service.dispatch()
        g = next(g for g in goals(db.authorize(self.actor)) if g['id'] == self.goal)
        self.assertEqual(g['freshness'], 'stale')
        self.assertEqual(findings(self.goal, self.actor)['id'], self.run['id'])

    def test_concurrent_corrections_preserve_both_edits(self):
        from runtime.analysis_api import correction, CorrectionInput
        service.revise_goal(self.goal, self.actor, paused=True)
        reading = threading.Event()
        release = threading.Event()
        second_read = threading.Event()
        second_started = threading.Event()
        original_records = db.records

        def records(snapshot):
            if not reading.is_set():
                reading.set()
                if not release.wait(5):
                    raise TimeoutError('Fixture correction was not released')
            else:
                second_read.set()
            return original_records(snapshot)

        def edit_target():
            second_started.set()
            return correction('commerce', CorrectionInput(record_id=self.rows[0]['id'], target=0, explanation='Fixture target correction'), self.actor)

        with patch.object(db, 'records', side_effect=records), ThreadPoolExecutor(max_workers=2) as workers:
            first = workers.submit(correction, 'commerce', CorrectionInput(record_id=self.rows[0]['id'], features={'age': 41}, explanation='Fixture feature correction'), self.actor)
            try:
                self.assertTrue(reading.wait(5))
                second = workers.submit(edit_target)
                self.assertTrue(second_started.wait(5))
                self.assertFalse(second_read.wait(0.25), 'Second correction read before the first committed')
            finally:
                release.set()
            first.result(timeout=5)
            second.result(timeout=5)
        row = db.records(db.source('commerce')['latest_snapshot'])[0]
        self.assertEqual(row['features']['age'], 41)
        self.assertEqual(row['target'], 0)

    def candidate_fixture(self):
        identity = digest([self.goal, 'promotion fixture'])
        db.write('INSERT INTO backintel.analysis_models(id,goal_id,snapshot_id,body) VALUES(%s,%s,%s,%s)',
                 (identity, self.goal, self.snapshot, Jsonb({'artifacts': [{'file': 'catboost-facts.joblib'}]})))
        return identity

    def test_concurrent_goal_revisions_reject_a_stale_edit_and_keep_history_consistent(self):
        original = db.goal
        first_read = threading.local()
        barrier = threading.Barrier(2)
        def read(identity):
            value = original(identity)
            if not getattr(first_read, 'done', False):
                first_read.done = True
                barrier.wait(timeout=5)
            return value
        def revise(question):
            try:
                return service.revise_goal(self.goal, self.actor, question=question), None
            except ValueError as error:
                self.assertIn('Goal changed', str(error))
                return None, question
        with patch.object(db, 'goal', side_effect=read), ThreadPoolExecutor(max_workers=2) as workers:
            results = list(workers.map(revise, ['Manager first edit', 'Manager second edit']))
        self.assertEqual(sum(result is not None for result, _ in results), 1)
        current = db.goal(self.goal)
        history = db.query('SELECT body FROM backintel.analysis_goal_versions WHERE goal_id=%s AND version=%s', (self.goal, current['version']), one=True)
        self.assertEqual(current['version'], 2)
        self.assertEqual(history['body'], current['body'])
        rejected = next(question for _, question in results if question)
        retried = service.revise_goal(self.goal, self.actor, question=rejected)
        self.assertEqual(retried['version'], 3)
        self.assertEqual(retried['body']['question'], rejected)

    def test_promotion_rechecks_invalidation_after_the_initial_model_read(self):
        candidate = self.candidate_fixture()
        original = db.goal
        def read(identity):
            value = original(identity)
            db.write("UPDATE backintel.analysis_models SET body=body||%s WHERE id=%s", (Jsonb({'invalidated_by': 'fixture correction'}), candidate))
            return value
        with patch.object(db, 'goal', side_effect=read), self.assertRaisesRegex(ValueError, 'invalidated'):
            service.promote(candidate, self.actor)
        self.assertFalse(db.query('SELECT promoted FROM backintel.analysis_models WHERE id=%s', (candidate,), one=True)['promoted'])
        self.assertIsNone(db.goal(self.goal)['active_model'])

    def test_promotion_refresh_uses_newly_active_model(self):
        candidate = self.candidate_fixture()
        first = service.promote(candidate, self.actor)
        self.assertEqual(first['body']['model_id'], candidate)
        second = digest([candidate, 'replacement'])
        db.write('INSERT INTO backintel.analysis_models(id,goal_id,snapshot_id,body) VALUES(%s,%s,%s,%s)',
                 (second, self.goal, self.snapshot, Jsonb({'artifacts':[{'file':'catboost-facts.joblib'}]})))
        self.assertEqual(service.promote(second, self.actor)['body']['model_id'], second)

    def test_ineligible_goal_rejects_promotion_without_committing_work(self):
        candidate = self.candidate_fixture()
        before = db.query('SELECT count(*) FROM backintel.analysis_runs', one=True)['count']
        for paused, confirmed in ((True, True), (False, False)):
            with self.subTest(paused=paused, confirmed=confirmed):
                db.write('UPDATE backintel.analysis_goals SET paused=%s,confirmed=%s WHERE id=%s', (paused, confirmed, self.goal))
                with self.assertRaisesRegex(ValueError, 'Goal changed during promotion'):
                    service.promote(candidate, self.actor)
                self.assertFalse(db.query('SELECT promoted FROM backintel.analysis_models WHERE id=%s', (candidate,), one=True)['promoted'])
                self.assertIsNone(db.goal(self.goal)['active_model'])
                self.assertEqual(db.query('SELECT count(*) FROM backintel.analysis_runs', one=True)['count'], before)

    def test_goal_paused_during_promotion_rolls_back_queued_work(self):
        candidate = self.candidate_fixture()
        original = db.goal
        before = db.query('SELECT count(*) FROM backintel.capability_jobs', one=True)['count']
        def read(identity):
            value = original(identity)
            db.write('UPDATE backintel.analysis_goals SET paused=true WHERE id=%s', (identity,))
            return value
        with patch.object(db, 'goal', side_effect=read), self.assertRaisesRegex(ValueError, 'Confirm.*goal|Goal changed during promotion'):
            service.promote(candidate, self.actor)
        self.assertFalse(db.query('SELECT promoted FROM backintel.analysis_models WHERE id=%s', (candidate,), one=True)['promoted'])
        self.assertIsNone(db.goal(self.goal)['active_model'])
        self.assertEqual(db.query('SELECT count(*) FROM backintel.capability_jobs', one=True)['count'], before)

    def test_request_retries_a_reservation_interrupted_before_dispatch(self):
        from unittest.mock import MagicMock
        from runtime import analysis_agent as agent
        from runtime.evidence import Evidence
        client = MagicMock()
        client.__enter__.return_value = client
        client.get.return_value.json.return_value = {'data': [{'id': CONFIG['analyst']['model'], 'pricing': {'prompt': '0', 'completion': '0'}}]}
        value = {'id': 'fixture-response', 'model': CONFIG['analyst']['served_models'][0], 'usage': {'cost': 0}, 'output': []}
        client.post.return_value.json.return_value = value
        original = db.query
        def interrupted(sql, *args, **kwargs):
            if sql.startswith("UPDATE backintel.analysis_requests SET status='sent'"):
                raise KeyboardInterrupt('Fixture exit before dispatch')
            return original(sql, *args, **kwargs)
        with patch.object(agent, 'credential', return_value='fixture'), patch.object(agent.httpx, 'Client', return_value=client):
            with patch.object(db, 'query', side_effect=interrupted), self.assertRaises(KeyboardInterrupt):
                with db.connect() as c, c.transaction():
                    Evidence(c, 'analysis-job-'+self.run['id']).lock()
                    agent.request(self.run['id'], 0, [])
            self.assertEqual(db.query('SELECT status FROM backintel.analysis_requests WHERE run_id=%s', (self.run['id'],), one=True)['status'], 'reserved')
            client.post.assert_not_called()
            with db.connect() as c, c.transaction():
                Evidence(c, 'analysis-job-'+self.run['id']).lock()
                self.assertEqual(agent.request(self.run['id'], 0, []), value)
        self.assertEqual(client.post.call_count, 1)
        self.assertEqual(db.query('SELECT count(*) FROM backintel.analysis_requests WHERE run_id=%s', (self.run['id'],), one=True)['count'], 1)
        self.assertEqual(len(db.query("SELECT body FROM backintel.analysis_events WHERE run_id=%s AND kind='reservation_released'", (self.run['id'],))), 1)

    def test_exhausted_presend_reservation_releases_global_capacity(self):
        db.reserve(self.run['id'], 'fixture-presend', Decimal('0.01'))
        db.write("UPDATE backintel.capability_jobs SET state='running',attempts=max_attempts,lease_until=now()+interval '1 hour' WHERE job_id=%s", (self.run['job_id'],))
        db.write("UPDATE backintel.analysis_runs SET status='running' WHERE id=%s", (self.run['id'],))
        service.dispatch()
        self.assertIsNone(db.query('SELECT id FROM backintel.analysis_requests WHERE id=%s', ('fixture-presend',), one=True))
        self.assertEqual(db.run(self.run['id'])['status'], 'partial')
        following = service.submit(self.goal, self.actor, question='Following fixture request')
        db.reserve(following['id'], 'fixture-following', Decimal('0.01'))
        self.assertEqual(db.query('SELECT status FROM backintel.analysis_requests WHERE id=%s', ('fixture-following',), one=True)['status'], 'reserved')

    def test_correction_schedules_healthy_goals_after_a_disabled_owner(self):
        from runtime.analysis_api import correction, CorrectionInput
        owner = 'disabled-fixture-'+uuid.uuid4().hex
        db.write('INSERT INTO backintel.analysis_principals(id,token_hash,role,domains) VALUES(%s,%s,%s,%s)', (owner, hashlib.sha256(owner.encode()).hexdigest(), 'manager', ['commerce']))
        goal = service.create_goal({'id': owner}, 'commerce', 'Disabled owner fixture')['id']
        service.revise_goal(goal, {'id': owner}, confirmed=True)
        db.write('UPDATE backintel.analysis_principals SET enabled=false WHERE id=%s', (owner,))
        with patch.object(service, 'wake'):
            result = correction('commerce', CorrectionInput(record_id=self.rows[0]['id'], features={'age': 41}, explanation='Fixture correction'), self.actor)
        outcomes = {item['goal_id']: item for item in result['refreshes']}
        self.assertTrue(result['changed'])
        self.assertEqual(db.source('commerce')['latest_snapshot'], result['snapshot'])
        self.assertEqual(outcomes[goal]['status'], 'blocked')
        self.assertEqual(outcomes[self.goal]['status'], 'queued')

    def test_failed_refresh_keeps_standing_result(self):
        first = {'summary': 'standing fixture', 'tables': [{'title': 'summarize', 'group_by': 'department', 'rows': [{'group': 'A', 'mean': 1}]}]}
        with patch('runtime.analysis_agent.analyze', return_value=first):
            service.dispatch()
        standing = db.goal(self.goal)['last_success']
        changed = [{**self.rows[0], 'target': 0}]
        snapshot = digest(changed)
        db.save_snapshot('commerce', snapshot, {'files': [], 'rows': 1}, changed)
        fresh = service.submit(self.goal, self.actor)
        with patch('runtime.analysis_agent.analyze', side_effect=TimeoutError('fixture provider timeout')):
            service.dispatch()
        self.assertEqual(db.run(fresh['id'])['status'], 'partial')
        self.assertEqual(db.goal(self.goal)['last_success'], standing)
        with patch('runtime.analysis_agent.analyze', return_value={'summary': 'refreshed fixture', 'tables': [{'title': 'summarize', 'group_by': 'department', 'rows': [{'group': 'A', 'mean': 0}]}]}):
            service.submit(self.goal, self.actor)
            service.dispatch()
        self.assertEqual(db.goal(self.goal)['last_success'], fresh['id'])
        self.assertEqual(len(db.query("SELECT * FROM backintel.analysis_events WHERE run_id=%s AND kind='material_change'", (fresh['id'],))), 1)
        from fastapi.testclient import TestClient
        from runtime.analysis_api import app
        response = TestClient(app).get('/api/v1/notifications', headers={'Authorization': 'Bearer campaign-manager'})
        self.assertEqual(response.status_code, 200, response.text)
        notice = next(row for row in response.json() if row['run_id'] == fresh['id'])
        self.assertIsInstance(notice['id'], int)

    def test_revoked_grant_and_changed_budget_reject_existing_work(self):
        service.revise_goal(self.goal, self.actor, budget_usd=.10)
        self.assertFalse(db.goal(self.goal)['confirmed'])
        with self.assertRaises(PermissionError):
            db.check_run(self.run['id'])
        with self.assertRaises(PermissionError):
            db.reserve(self.run['id'], 'superseded-admission', .01)
        db.write("UPDATE backintel.analysis_principals SET enabled=false WHERE id='campaign-analyst'")
        try:
            with self.assertRaises(PermissionError):
                db.authorize({'id': 'campaign-analyst'}, 'commerce')
        finally:
            db.write("UPDATE backintel.analysis_principals SET enabled=true WHERE id='campaign-analyst'")

    def test_request_replay_needs_no_credentials_or_provider_transport(self):
        from unittest.mock import MagicMock
        from runtime import analysis_agent as agent
        client = MagicMock()
        client.__enter__.return_value = client
        client.get.return_value.json.return_value = {'data': [{'id': CONFIG['analyst']['model'], 'pricing': {'prompt': '.000001', 'completion': '.000001'}}]}
        response = {'id': 'fixture-original-response', 'model': CONFIG['analyst']['model'], 'usage': {'cost': .001}, 'output': [], '_backintel_fixture': True}
        client.post.return_value.json.return_value = response
        with patch.object(agent, 'credential', return_value='fixture'), patch.object(agent.httpx, 'Client', return_value=client):
            self.assertEqual(agent.request(self.run['id'], 0, []), response)
        with patch.object(agent, 'credential', side_effect=AssertionError('Replay discovered a credential')), patch.object(agent.httpx, 'Client', side_effect=AssertionError('Replay attempted provider transport')):
            self.assertEqual(agent.request(self.run['id'], 0, []), response)
        self.assertEqual(db.usage(self.run['id'])['provider_calls'], 1)
        self.assertEqual(db.usage(self.run['id'])['provider_usd'], .001)

    def test_expired_grant_blocks_api_and_already_accepted_work(self):
        from fastapi.testclient import TestClient
        from runtime.analysis_api import app
        db.write("UPDATE backintel.analysis_principals SET expires_at=now()-interval '1 second' WHERE id='campaign-manager'")
        try:
            self.assertEqual(TestClient(app).get('/api/v1/me', headers={'Authorization': 'Bearer campaign-manager'}).status_code, 403)
            with self.assertRaises(PermissionError):
                db.authorize(self.actor, 'commerce')
            with self.assertRaises(PermissionError):
                db.reserve(self.run['id'], 'expired-admission', .01)
            with patch('runtime.analysis_agent.analyze', side_effect=lambda identity: db.check_run(identity)):
                service.dispatch()
            self.assertEqual(db.run(self.run['id'])['status'], 'cancelled')
            self.assertEqual(db.query('SELECT count(*) AS n FROM backintel.analysis_requests', one=True)['n'], 0)
        finally:
            db.write("UPDATE backintel.analysis_principals SET expires_at=NULL WHERE id='campaign-manager'")

    def test_grant_expiry_changes_require_manager_and_aware_time(self):
        from fastapi.testclient import TestClient
        from runtime.analysis_api import app
        client = TestClient(app)
        body = {'domains': ['commerce'], 'expires_at': '2099-01-01T00:00:00Z'}
        headers = {'Authorization': 'Bearer campaign-manager'}
        try:
            self.assertEqual(client.patch('/api/v1/principals/campaign-viewer', headers={'Authorization': 'Bearer campaign-analyst'}, json=body).status_code, 403)
            self.assertEqual(client.patch('/api/v1/principals/campaign-viewer', headers=headers, json={**body, 'expires_at': '2099-01-01T00:00:00'}).status_code, 400)
            self.assertEqual(client.patch('/api/v1/principals/campaign-viewer', headers=headers, json=body).status_code, 200)
            before = db.query("SELECT expires_at FROM backintel.analysis_principals WHERE id='campaign-viewer'", one=True)['expires_at']
            self.assertEqual(client.patch('/api/v1/principals/campaign-viewer', headers=headers, json={'domains': ['commerce']}).status_code, 200)
            self.assertEqual(db.query("SELECT expires_at FROM backintel.analysis_principals WHERE id='campaign-viewer'", one=True)['expires_at'], before)
            self.assertEqual(client.patch('/api/v1/principals/campaign-viewer', headers=headers, json={**body, 'expires_at': '2000-01-01T00:00:00Z'}).status_code, 200)
            self.assertEqual(client.get('/api/v1/me', headers={'Authorization': 'Bearer campaign-viewer'}).status_code, 403)
        finally:
            db.write("UPDATE backintel.analysis_principals SET expires_at=NULL,domains=ARRAY['commerce','support'] WHERE id='campaign-viewer'")

    def test_real_private_run_evidence_and_events_are_domain_restricted(self):
        from fastapi.testclient import TestClient
        from runtime.analysis_api import app
        private_actor = {'id': 'campaign-private'}
        db.write('INSERT INTO backintel.analysis_principals(id,token_hash,role,domains) VALUES(%s,%s,%s,%s) ON CONFLICT DO NOTHING',
                 (private_actor['id'], hashlib.sha256(b'campaign-private').hexdigest(), 'manager', ['credit']))
        snapshot = digest(['private-credit', self.rows])
        db.save_snapshot('credit', snapshot, {'files': [], 'rows': 1, 'mode': 'fixture'}, self.rows)
        goal = service.create_goal(private_actor, 'credit', 'Private credit fixture')['id']
        service.revise_goal(goal, private_actor, confirmed=True)
        run = service.submit(goal, private_actor)
        evidence = db.evidence(run['id'], 'calculation', 'private', {'tool': 'summarize', 'mode': 'fixture'})
        client = TestClient(app)
        for route in ('/api/v1/runs/' + run['id'], '/api/v1/runs/' + run['id'] + '/events',
                      '/api/v1/runs/' + run['id'] + '/requests', '/api/v1/evidence/' + evidence,
                      '/api/v1/goals/' + goal + '/findings'):
            with self.subTest(route=route):
                self.assertEqual(client.get(route, headers={'Authorization': 'Bearer campaign-manager'}).status_code, 403)
        self.assertEqual(client.get('/api/v1/evidence/' + evidence, headers={'Authorization': 'Bearer campaign-private'}).status_code, 200)
        with db.connect() as connection:
            from runtime.jobs import cancel
            cancel(connection, run['job_id'])

    def test_credentials_are_redacted_from_failure_and_append_only_evidence(self):
        from fastapi.testclient import TestClient
        from runtime.analysis_api import app
        secret = 'validation-fake-provider-secret'
        with patch.dict(os.environ, {'OPENROUTER_API_KEY': secret}), patch('runtime.analysis_agent.analyze', side_effect=RuntimeError('Provider failure echoed ' + secret + ' and Bearer other-fixture-token')):
            service.dispatch()
            result = TestClient(app).get('/api/v1/runs/' + self.run['id'], headers={'Authorization': 'Bearer campaign-manager'})
        self.assertNotIn(secret, result.text)
        self.assertNotIn('other-fixture-token', result.text)
        self.assertIn('[redacted]', result.text)
        stored = db.query('SELECT body::text AS body FROM backintel.capability_evidence WHERE task_id=%s', ('analysis-job-' + self.run['id'],))
        events = db.query('SELECT body::text AS body FROM backintel.analysis_events WHERE run_id=%s', (self.run['id'],))
        for row in stored + events:
            self.assertNotIn(secret, row['body'])
            self.assertNotIn('other-fixture-token', row['body'])

    def test_ambiguous_provider_timeout_is_not_retried(self):
        from unittest.mock import MagicMock
        from runtime import analysis_agent as agent
        client = MagicMock()
        client.__enter__.return_value = client
        client.get.return_value.json.return_value = {'data': [{'id': CONFIG['analyst']['model'], 'pricing': {'prompt': '0', 'completion': '0'}}]}
        client.post.side_effect = TimeoutError('Fixture ambiguous timeout')
        with patch.object(agent, 'credential', return_value='fixture'), patch.object(agent.httpx, 'Client', return_value=client):
            with self.assertRaises(TimeoutError):
                agent.request(self.run['id'], 0, [])
            with self.assertRaisesRegex(RuntimeError, 'reconcile'):
                agent.request(self.run['id'], 0, [])
        self.assertEqual(client.post.call_count, 1)
        request = db.query('SELECT status,charge FROM backintel.analysis_requests WHERE run_id=%s', (self.run['id'],), one=True)
        self.assertEqual(request['status'], 'uncertain')
        self.assertIsNone(request['charge'])

    def test_scoped_manager_cannot_expand_grants_outside_own_sources(self):
        from fastapi.testclient import TestClient
        from runtime.analysis_api import app
        client = TestClient(app)
        response = client.patch('/api/v1/principals/campaign-viewer',
                                headers={'Authorization': 'Bearer campaign-manager'},
                                json={'domains': ['commerce', 'credit']})
        self.assertEqual(response.status_code, 403)
        self.assertEqual(db.query("SELECT domains FROM backintel.analysis_principals WHERE id='campaign-viewer'", one=True)['domains'], ['commerce', 'support'])

    def test_malformed_analyst_output_is_partial_without_replacing_answer(self):
        from runtime import analysis_agent as agent
        with patch.object(agent, 'analyze', return_value={'mode': 'fixture', 'summary': 'standing fixture', 'tables': []}):
            service.dispatch()
        standing = db.goal(self.goal)['last_success']
        changed = [{**self.rows[0], 'target': 0}]
        db.save_snapshot('commerce', digest(changed), {'mode': 'fixture'}, changed)
        run = service.submit(self.goal, self.actor)
        response = {'_backintel_fixture': True, 'output': [{'type': 'message', 'content': [{'type': 'output_text', 'text': '{malformed fixture'}]}]}
        with patch.object(agent, 'request', return_value=response):
            service.dispatch()
        self.assertEqual(db.run(run['id'])['status'], 'partial')
        self.assertEqual(db.goal(self.goal)['last_success'], standing)

    def test_hostile_tool_request_is_rejected_and_calls_are_bounded(self):
        from runtime import analysis_agent as agent
        response = {'_backintel_fixture': True, 'output': [{'type': 'function_call', 'name': 'execute_sql',
                     'arguments': '{"query":"SELECT secret FROM private_table"}', 'call_id': 'hostile-fixture'}]}
        with patch.object(agent, 'request', return_value=response) as requests, patch.object(agent, 'tool') as tools:
            with self.assertRaisesRegex(RuntimeError, 'call limit'):
                agent.analyze(self.run['id'])
        self.assertEqual(requests.call_count, 6)
        tools.assert_not_called()
        self.assertEqual(db.query('SELECT count(*) AS n FROM backintel.analysis_steps WHERE run_id=%s', (self.run['id'],), one=True)['n'], 0)

    def test_valid_tool_loop_stops_before_thirteenth_execution(self):
        from runtime import analysis_agent as agent
        response = {'_backintel_fixture': True, 'output': [{'type': 'function_call', 'name': 'inspect_source',
                     'arguments': '{}', 'call_id': 'fixture-' + str(i)} for i in range(7)]}
        with patch.object(agent, 'request', return_value=response) as requests, patch.object(agent, 'tool', wraps=agent.tool) as tools:
            with self.assertRaisesRegex(RuntimeError, 'tool limit'):
                agent.analyze(self.run['id'])
        self.assertEqual(requests.call_count, 2)
        self.assertEqual(tools.call_count, 12)

    def test_elapsed_analysis_limit_stops_before_provider_dispatch(self):
        from runtime import analysis_agent as agent
        with patch.object(agent.time, 'monotonic', side_effect=[0, 601]), patch.object(agent, 'request') as requests:
            with self.assertRaisesRegex(TimeoutError, 'time limit'):
                agent.analyze(self.run['id'])
        requests.assert_not_called()


if __name__ == '__main__':
    unittest.main()
