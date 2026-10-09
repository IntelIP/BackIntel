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
        db.write('UPDATE backintel.analysis_goals SET paused=true')
        db.write("UPDATE backintel.capability_jobs SET state='cancelled' WHERE state IN ('queued','retry') AND task_id LIKE 'analysis-job-%'")
        self.rows = [{'id': str(uuid.uuid4()), 'entity': 'fixture', 'features': {'age': 40},
                      'target': 1, 'groups': {'department': 'A'}, 'text': 'fixture', 'split': 'train'}]
        self.snapshot = digest(self.rows)
        db.save_snapshot('commerce', self.snapshot, {'files': [], 'rows': 1, 'mode': 'fixture'}, self.rows)
        db.catalog()
        db.write("UPDATE backintel.analysis_sources SET body=body || %s", (Jsonb({'terms_acknowledged':True}),))
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
            if sql.startswith("SELECT r.id AS dispatch_run"):
                with db.connect() as connection:
                    cancel(connection, self.run['job_id'])
            return query(sql, *args, **kwargs)
        with patch.object(agent, 'credential', return_value='fixture'), patch.object(agent.httpx, 'Client', return_value=client), \
                patch.object(db, 'query', side_effect=cancel_before_dispatch), self.assertRaisesRegex(RuntimeError, 'reservation changed'):
            agent.request(self.run['id'], 0, [])
        client.post.assert_not_called()

    def test_grant_changes_recheck_current_actor_instead_of_access_snapshot(self):
        from runtime.analysis_api import grants, GrantInput
        stale = {**self.actor, 'role': 'manager', 'domains': ['commerce', 'support']}
        for change in ('enabled=false', "expires_at=now()-interval '1 second'", "role='analyst'", "domains=ARRAY['commerce']"):
            try:
                db.write('UPDATE backintel.analysis_principals SET '+change+' WHERE id=%s', (self.actor['id'],))
                before = db.query('SELECT enabled,expires_at,role,domains FROM backintel.analysis_principals WHERE id=%s', (self.actor['id'],), one=True)
                with self.subTest(change=change), self.assertRaises(PermissionError):
                    grants(self.actor['id'], GrantInput(domains=['commerce', 'support']), stale)
                self.assertEqual(db.query('SELECT enabled,expires_at,role,domains FROM backintel.analysis_principals WHERE id=%s', (self.actor['id'],), one=True), before)
            finally:
                db.write("UPDATE backintel.analysis_principals SET enabled=true,expires_at=NULL,role='manager',domains=ARRAY['commerce','support'] WHERE id=%s", (self.actor['id'],))
        self.assertEqual(grants(self.actor['id'], GrantInput(domains=['commerce', 'support']), stale), {'saved': True})

    def test_temporary_manager_cannot_extend_or_remove_own_expiry(self):
        from datetime import datetime, timedelta, timezone
        from runtime.analysis_api import grants, GrantInput
        deadline = datetime.now(timezone.utc) + timedelta(hours=2)
        db.write('UPDATE backintel.analysis_principals SET expires_at=%s WHERE id=%s', (deadline, self.actor['id']))
        try:
            for expires_at in (None, deadline + timedelta(hours=1)):
                with self.subTest(expires_at=expires_at), self.assertRaisesRegex(PermissionError, 'own credential expiry'):
                    grants(self.actor['id'], GrantInput(domains=['commerce', 'support'], expires_at=expires_at), self.actor)
                self.assertEqual(db.query('SELECT expires_at FROM backintel.analysis_principals WHERE id=%s', (self.actor['id'],), one=True)['expires_at'], deadline)
            self.assertEqual(grants(self.actor['id'], GrantInput(domains=['commerce']), self.actor), {'saved': True})
            self.assertEqual(db.query('SELECT expires_at FROM backintel.analysis_principals WHERE id=%s', (self.actor['id'],), one=True)['expires_at'], deadline)
            shorter = deadline - timedelta(hours=1)
            self.assertEqual(grants(self.actor['id'], GrantInput(domains=['commerce'], expires_at=shorter), self.actor), {'saved': True})
            self.assertEqual(db.query('SELECT expires_at FROM backintel.analysis_principals WHERE id=%s', (self.actor['id'],), one=True)['expires_at'], shorter)
        finally:
            db.write("UPDATE backintel.analysis_principals SET expires_at=NULL,domains=ARRAY['commerce','support'] WHERE id=%s", (self.actor['id'],))

    def test_grant_change_waits_for_concurrent_revocation_and_cannot_restore_it(self):
        from concurrent.futures import TimeoutError
        from runtime.analysis_api import grants, GrantInput
        stale = {**self.actor, 'role': 'manager', 'domains': ['commerce', 'support']}
        started = threading.Event()
        def restore():
            started.set()
            return grants(self.actor['id'], GrantInput(domains=['commerce', 'support']), stale)
        try:
            with ThreadPoolExecutor(max_workers=1) as workers:
                with db.connect() as connection, connection.transaction():
                    connection.execute('UPDATE backintel.analysis_principals SET enabled=false WHERE id=%s', (self.actor['id'],))
                    pending = workers.submit(restore)
                    self.assertTrue(started.wait(5))
                    with self.assertRaises(TimeoutError): pending.result(timeout=.25)
                with self.assertRaises(PermissionError): pending.result(timeout=5)
            self.assertFalse(db.query('SELECT enabled FROM backintel.analysis_principals WHERE id=%s', (self.actor['id'],), one=True)['enabled'])
        finally:
            db.write('UPDATE backintel.analysis_principals SET enabled=true WHERE id=%s', (self.actor['id'],))

    def test_stale_snapshot_or_model_stops_provider_dispatch(self):
        from unittest.mock import MagicMock
        from runtime import analysis_agent as agent
        client = MagicMock(); client.__enter__.return_value = client
        client.get.return_value.json.return_value = {'data': [{'id': CONFIG['analyst']['model'], 'pricing': {'prompt': '0', 'completion': '0'}}]}
        query = db.query
        for change in ('snapshot', 'model'):
            def change_before_dispatch(sql, *args, **kwargs):
                if sql.startswith('SELECT r.id AS dispatch_run'):
                    if change == 'snapshot':
                        db.save_snapshot('commerce', digest([self.snapshot, 'changed']), {'fixture': True}, self.rows)
                    else:
                        db.write('UPDATE backintel.analysis_goals SET active_model=%s WHERE id=%s', ('new-model', self.goal))
                return query(sql, *args, **kwargs)
            try:
                with self.subTest(change=change), patch.object(agent, 'credential', return_value='fixture'), patch.object(agent.httpx, 'Client', return_value=client), patch.object(db, 'query', side_effect=change_before_dispatch), self.assertRaisesRegex(RuntimeError, 'reservation changed'):
                    agent.request(self.run['id'], 0, [])
                client.post.assert_not_called()
            finally:
                db.write('UPDATE backintel.analysis_sources SET latest_snapshot=%s WHERE id=%s', (self.snapshot, 'commerce'))
                db.write('UPDATE backintel.analysis_goals SET active_model=NULL WHERE id=%s', (self.goal,))
                db.release_unsent(self.run['id'])

    def test_provider_dispatch_holds_inputs_and_persists_sent_before_post(self):
        from unittest.mock import MagicMock
        from concurrent.futures import TimeoutError
        from runtime import analysis_agent as agent
        client = MagicMock(); client.__enter__.return_value = client
        client.get.return_value.json.return_value = {'data': [{'id': CONFIG['analyst']['model'], 'pricing': {'prompt': '0', 'completion': '0'}}]}
        value = {'id': 'fixture-response', 'model': CONFIG['analyst']['served_models'][0], 'usage': {'cost': 0}, 'output': []}
        client.post.return_value.json.return_value = value
        started = threading.Event()
        def change_inputs():
            started.set()
            with db.connect() as connection:
                connection.execute('UPDATE backintel.analysis_sources SET latest_snapshot=%s WHERE id=%s', (self.snapshot, 'commerce'))
                connection.execute('UPDATE backintel.analysis_goals SET active_model=%s WHERE id=%s', ('new-model', self.goal))
        with ThreadPoolExecutor(max_workers=1) as workers:
            pending = []
            def post(*args, **kwargs):
                self.assertEqual(db.query('SELECT status FROM backintel.analysis_requests WHERE run_id=%s', (self.run['id'],), one=True)['status'], 'sent')
                pending.append(workers.submit(change_inputs))
                self.assertTrue(started.wait(5))
                with self.assertRaises(TimeoutError):
                    pending[0].result(timeout=.25)
                return client.post.return_value
            client.post.side_effect = post
            with patch.object(agent, 'credential', return_value='fixture'), patch.object(agent.httpx, 'Client', return_value=client):
                self.assertEqual(agent.request(self.run['id'], 0, []), value)
            pending[0].result(timeout=5)
        self.assertEqual(db.goal(self.goal)['active_model'], 'new-model')

    def test_sent_marker_survives_dispatch_guard_interruption(self):
        from runtime.analysis_agent import provider_dispatch
        db.reserve(self.run['id'], 'interrupted-dispatch', 0)
        with self.assertRaises(KeyboardInterrupt):
            with provider_dispatch(self.run['id'], 'interrupted-dispatch'):
                raise KeyboardInterrupt('Fixture interruption after durable sent marker')
        self.assertEqual(db.query('SELECT status FROM backintel.analysis_requests WHERE id=%s', ('interrupted-dispatch',), one=True)['status'], 'sent')

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
            if sql.startswith("SELECT r.id AS dispatch_run"):
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

    def test_owner_revocation_at_dispatch_prevents_provider_post(self):
        from unittest.mock import MagicMock
        from runtime import analysis_agent as agent
        client = MagicMock()
        client.__enter__.return_value = client
        client.get.return_value.json.return_value = {'data':[{'id':CONFIG['analyst']['model'],'pricing':{'prompt':'0','completion':'0'}}]}
        query = db.query
        for change in ('enabled=false', "expires_at=now()-interval '1 second'", "role='viewer'", "domains=ARRAY['support']"):
            def revoke(sql, *args, **kwargs):
                if sql.startswith("SELECT r.id AS dispatch_run"):
                    db.write('UPDATE backintel.analysis_principals SET '+change+' WHERE id=%s', (self.actor['id'],))
                return query(sql, *args, **kwargs)
            try:
                with self.subTest(change=change), patch.object(agent, 'credential', return_value='fixture'), patch.object(agent.httpx, 'Client', return_value=client), patch.object(db, 'query', side_effect=revoke), self.assertRaisesRegex(RuntimeError, 'reservation changed'):
                    agent.request(self.run['id'], 0, [])
                client.post.assert_not_called()
            finally:
                db.write("UPDATE backintel.analysis_principals SET enabled=true,expires_at=NULL,role='manager',domains=ARRAY['commerce','support'] WHERE id=%s", (self.actor['id'],))
                db.release_unsent(self.run['id'])

    def test_changed_snapshot_or_model_cannot_replace_standing_answer(self):
        with patch('runtime.analysis_agent.analyze', return_value={'summary':'Standing fixture answer'}):
            service.execute(self.run['job_id'], service.handle)
        standing = self.run['id']
        for change in ('snapshot', 'model'):
            with self.subTest(change=change):
                # A different implementation creates a fresh run of the standing question.
                with patch.object(service, 'analysis_identity', return_value=change):
                    run = service.submit(self.goal, self.actor)
                def finish(identity):
                    if change == 'snapshot':
                        snapshot = digest([self.snapshot, 'refreshed'])
                        db.save_snapshot('commerce', snapshot, {'mode':'fixture'}, self.rows)
                    else:
                        db.write('UPDATE backintel.analysis_goals SET active_model=%s WHERE id=%s', ('new-model', self.goal))
                    return {'summary':'Stale completion'}
                with patch('runtime.analysis_agent.analyze', side_effect=finish):
                    service.execute(run['job_id'], service.handle)
                self.assertEqual(db.run(run['id'])['status'], 'cancelled')
                self.assertEqual(db.goal(self.goal)['last_success'], standing)

    def test_cancel_run_rechecks_manager_authority_after_admission(self):
        from runtime import analysis_api as api
        original = db.authorize
        def revoke(actor, domain=None, roles=('manager', 'analyst', 'viewer')):
            admitted = original(actor, domain, roles)
            db.write('UPDATE backintel.analysis_principals SET enabled=false WHERE id=%s', (actor['id'],))
            return admitted
        try:
            with patch.object(db, 'authorize', side_effect=revoke):
                with self.assertRaisesRegex(PermissionError, 'Current manager authority'):
                    api.cancel_run(self.run['id'], self.actor)
            self.assertEqual(db.run(self.run['id'])['status'], 'queued')
        finally:
            db.write('UPDATE backintel.analysis_principals SET enabled=true WHERE id=%s', (self.actor['id'],))

    def test_cancel_run_commits_job_and_run_together(self):
        from runtime import analysis_api as api
        cancel = api.cancel
        def observe(connection, job_id):
            state = cancel(connection, job_id)
            visible = db.query('SELECT r.status,j.state FROM backintel.analysis_runs r JOIN backintel.capability_jobs j ON j.job_id=r.job_id WHERE r.id=%s', (self.run['id'],), one=True)
            self.assertEqual(visible, {'status':'queued','state':'queued'})
            return state
        with patch.object(api, 'cancel', side_effect=observe):
            api.cancel_run(self.run['id'], self.actor)
        self.assertEqual(db.run(self.run['id'])['status'], 'cancelled')
        self.assertEqual(service.submit(self.goal, self.actor)['status'], 'queued')

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
                with patch.object(service, 'validate_source_receipt', return_value={'snapshot_id':snapshot,'adapter_receipt':{'files':[],'mode':'fixture'}}), patch.object(service, 'source_files', return_value=[]), patch.object(service, 'adapt', side_effect=adapt):
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

    def test_import_checks_registered_bytes_before_reusing_a_snapshot(self):
        import tempfile
        from pathlib import Path
        from scripts import analysis_setup
        with tempfile.TemporaryDirectory() as temporary, patch.dict(os.environ, {'BACKINTEL_DATASET_DIR': temporary}):
            incoming = Path(temporary)/'incoming.csv'
            incoming.write_text('customerID,Churn,Contract,tenure,MonthlyCharges,TotalCharges\na,Yes,Monthly,1,2,2\nb,No,Annual,2,2,4\n')
            db.write("UPDATE backintel.analysis_principals SET domains=ARRAY['commerce','support','churn'] WHERE id=%s", (self.actor['id'],))
            self.addCleanup(db.write, "UPDATE backintel.analysis_principals SET domains=ARRAY['commerce','support'] WHERE id=%s", (self.actor['id'],))
            receipt = analysis_setup.import_data('churn', incoming)
            result = service.import_source('churn', self.actor)
            self.assertEqual(result['snapshot'], receipt['snapshot_id'])
            self.assertFalse(service.import_source('churn', self.actor)['changed'])
            installed = Path(temporary)/'Churn'/CONFIG['sources']['churn']['files'][0]
            installed.write_text(installed.read_text().replace('Yes', 'No'))
            with self.assertRaises(PermissionError):
                service.import_source('churn', self.actor)
            self.assertEqual(db.source('churn')['latest_snapshot'], result['snapshot'])
            installed.write_bytes(incoming.read_bytes())
            (installed.parent/'source-receipt.json').unlink()
            with self.assertRaises(PermissionError):
                service.import_source('churn', self.actor)

    def test_source_health_is_written_before_a_later_import_can_enter(self):
        import threading
        failed_health, release, successful_import = threading.Event(), threading.Event(), threading.Event()
        write = db.write
        def importing(domain, actor, **kwargs):
            if actor.get('fail'):
                raise OSError('Earlier failed import')
            successful_import.set()
            return {'snapshot': self.snapshot, 'changed': False}
        def delayed_write(sql, params=(), **kwargs):
            if params and isinstance(params[0], Jsonb) and params[0].obj.get('last_refresh_error') == 'Earlier failed import':
                failed_health.set()
                if not release.wait(5):
                    raise TimeoutError('Fixture health write was not released')
            return write(sql, params, **kwargs)
        with patch.object(service, '_import_source', side_effect=importing), patch.object(db, 'write', side_effect=delayed_write), ThreadPoolExecutor(max_workers=2) as workers:
            failed = workers.submit(service.import_source, 'commerce', {**self.actor, 'fail': True})
            try:
                self.assertTrue(failed_health.wait(5))
                succeeded = workers.submit(service.import_source, 'commerce', self.actor)
                self.assertFalse(successful_import.wait(.2))
            finally:
                release.set()
            with self.assertRaises(OSError):
                failed.result(timeout=5)
            succeeded.result(timeout=5)
        self.assertNotIn('last_refresh_error', db.source('commerce')['body'])

    def test_late_queued_failure_cannot_overwrite_newer_successful_refresh(self):
        run = service.submit_import('commerce', self.actor)
        write = db.write
        def newer_success(sql, params=(), **kwargs):
            if sql.startswith('UPDATE backintel.analysis_sources') and kwargs.get('connection') is None:
                service.import_source('commerce', self.actor)
            return write(sql, params, **kwargs)
        with patch.object(service, '_import_source', side_effect=[OSError('Earlier queued failure'), {'snapshot':self.snapshot, 'changed':False}]), \
                patch.object(db, 'write', side_effect=newer_success):
            service.execute(run['job_id'], service.handle)
        self.assertNotIn('last_refresh_error', db.source('commerce')['body'])
        self.assertEqual(db.run(run['id'])['status'], 'partial')

    def test_operator_can_explicitly_grant_new_configured_sources_to_manager(self):
        import tempfile
        from pathlib import Path
        from scripts import analysis_demo
        with tempfile.TemporaryDirectory() as temporary, patch.dict(os.environ, {'BACKINTEL_ACCESS_CREDENTIAL_FILE': str(Path(temporary)/'access.json')}):
            analysis_demo.seed()
            db.write("UPDATE backintel.analysis_principals SET domains=ARRAY['commerce'] WHERE id IN ('manager','analyst')")
            analysis_demo.seed()
            self.assertEqual(db.query("SELECT domains FROM backintel.analysis_principals WHERE id='manager'", one=True)['domains'], ['commerce'])
            analysis_demo.seed(grant_manager_sources=True)
            self.assertEqual(set(db.query("SELECT domains FROM backintel.analysis_principals WHERE id='manager'", one=True)['domains']), set(CONFIG['sources']))
            self.assertEqual(db.query("SELECT domains FROM backintel.analysis_principals WHERE id='analyst'", one=True)['domains'], ['commerce'])

    def test_failed_queued_import_preserves_refresh_error(self):
        db.write("UPDATE backintel.analysis_sources SET body=body || %s WHERE id='commerce'", (Jsonb({'terms_acknowledged':True}),))
        run = service.submit_import('commerce', self.actor)
        with patch.object(service, 'validate_source_receipt', return_value={'snapshot_id':'unused','adapter_receipt':{'files':[]}}), patch.object(service, 'source_files', return_value=[]), patch.object(service, 'adapt', side_effect=OSError('Fixture source unavailable')):
            service.execute(run['job_id'], service.handle)
        source = db.source('commerce')
        self.assertEqual(source['latest_snapshot'], self.snapshot)
        self.assertIn('Fixture source unavailable', source['body']['last_refresh_error'])
        self.assertGreater(source['body']['last_checked_at'], 0)
        self.assertEqual(db.run(run['id'])['status'], 'partial')

    def test_cancelled_import_preserves_healthy_source(self):
        from runtime.jobs import cancel
        db.write("UPDATE backintel.analysis_sources SET body=body-'last_refresh_error' WHERE id='commerce'")
        run = service.submit_import('commerce',self.actor)
        def interrupted(domain,actor,**kwargs):
            with db.connect() as connection:
                cancel(connection,run['job_id'])
            raise InterruptedError('Fixture import cancelled')
        with patch.object(service,'_import_source',side_effect=interrupted):
            service.execute(run['job_id'],service.handle)
        source = db.source('commerce')
        self.assertFalse(source['body'].get('last_refresh_error'))
        self.assertEqual(source['latest_snapshot'],self.snapshot)
        self.assertEqual(db.run(run['id'])['status'],'cancelled')

    def test_owner_revocation_at_publication_preserves_standing_answer(self):
        with patch('runtime.analysis_agent.analyze',return_value={'summary':'Standing fixture answer'}):
            service.execute(self.run['job_id'],service.handle)
        query=db.query
        for change in ('enabled=false', "expires_at=now()-interval '1 second'", "role='viewer'", "domains=ARRAY['support']"):
            with patch.object(service,'analysis_identity',return_value=change):
                run=service.submit(self.goal,self.actor)
            def revoke(sql,*args,**kwargs):
                if sql.startswith('SELECT id FROM backintel.analysis_principals'):
                    db.write('UPDATE backintel.analysis_principals SET '+change+' WHERE id=%s',(self.actor['id'],))
                return query(sql,*args,**kwargs)
            try:
                with self.subTest(change=change), patch('runtime.analysis_agent.analyze',return_value={'summary':'Revoked fixture answer'}), patch.object(db,'query',side_effect=revoke):
                    service.execute(run['job_id'],service.handle)
                self.assertEqual(db.run(run['id'])['status'],'cancelled')
                self.assertEqual(db.goal(self.goal)['last_success'],self.run['id'])
            finally:
                db.write("UPDATE backintel.analysis_principals SET enabled=true,expires_at=NULL,role='manager',domains=ARRAY['commerce','support'] WHERE id=%s",(self.actor['id'],))

    def test_import_owner_revocation_at_publication_rejects_success(self):
        run=service.submit_import('commerce',self.actor)
        query=db.query
        def revoke(sql,*args,**kwargs):
            if sql.startswith('SELECT id FROM backintel.analysis_principals'):
                db.write('UPDATE backintel.analysis_principals SET enabled=false WHERE id=%s',(self.actor['id'],))
            return query(sql,*args,**kwargs)
        try:
            with patch.object(service,'import_source',return_value={'snapshot':self.snapshot}), patch.object(service,'schedule_snapshot',return_value=[]), patch.object(db,'query',side_effect=revoke):
                service.execute(run['job_id'],service.handle)
            self.assertEqual(db.run(run['id'])['status'],'cancelled')
            self.assertEqual(db.source('commerce')['latest_snapshot'],self.snapshot)
        finally:
            db.write('UPDATE backintel.analysis_principals SET enabled=true WHERE id=%s',(self.actor['id'],))

    def test_empty_corrections_preserve_snapshot_and_explicit_null_removes_target(self):
        from runtime.analysis_api import correction, CorrectionInput
        service.revise_goal(self.goal, self.actor, paused=True)
        for change in ({}, {'features':{'age':40}}, {'target':1}):
            with self.subTest(change=change), self.assertRaisesRegex(ValueError, 'change at least one value'):
                correction('commerce', CorrectionInput(record_id=self.rows[0]['id'], explanation='Fixture no change', **change), self.actor)
            self.assertEqual(db.source('commerce')['latest_snapshot'], self.snapshot)
        correction('commerce', CorrectionInput(record_id=self.rows[0]['id'], target=None, explanation='Fixture remove mistaken label'), self.actor)
        self.assertIsNone(db.records(db.source('commerce')['latest_snapshot'])[0]['target'])

    def test_listings_use_domains_from_current_authorization(self):
        from runtime import analysis_api as api
        stale = {**self.actor, 'domains': ['commerce', 'support']}
        db.write('UPDATE backintel.analysis_principals SET domains=%s WHERE id=%s', (['commerce'], self.actor['id']))
        try:
            for listing in (api.goals, api.sources, api.notifications):
                with self.subTest(listing=listing.__name__), patch.object(db, 'query', wraps=db.query) as query:
                    listing(stale)
                    calls = [call for call in query.call_args_list if 'domain=ANY' in call.args[0]]
                    self.assertEqual(len(calls), 1)
                    self.assertEqual(calls[0].args[1], (['commerce'],))
        finally:
            db.write('UPDATE backintel.analysis_principals SET domains=%s WHERE id=%s', (stale['domains'], self.actor['id']))

    def test_correction_rechecks_manager_after_initial_authorization(self):
        from runtime.analysis_api import correction, CorrectionInput
        authorize = db.authorize
        for change in ('enabled=false', "expires_at=now()-interval '1 second'", "role='analyst'", "domains=ARRAY['support']"):
            def revoke(*args, **kwargs):
                current = authorize(*args, **kwargs)
                db.write('UPDATE backintel.analysis_principals SET '+change+' WHERE id=%s', (self.actor['id'],))
                return current
            try:
                with self.subTest(change=change), patch.object(db, 'authorize', side_effect=revoke), self.assertRaisesRegex(PermissionError, 'Current manager authority'):
                    correction('commerce', CorrectionInput(record_id=self.rows[0]['id'], features={'age': 41}, explanation='Fixture correction'), self.actor)
                self.assertEqual(db.source('commerce')['latest_snapshot'], self.snapshot)
                self.assertEqual(db.records(self.snapshot)[0]['features']['age'], 40)
            finally:
                db.write("UPDATE backintel.analysis_principals SET enabled=true,expires_at=NULL,role='manager',domains=ARRAY['commerce','support'] WHERE id=%s", (self.actor['id'],))

    def test_terms_recheck_manager_after_initial_authorization(self):
        from runtime.analysis_api import terms, TermsInput
        authorize = db.authorize
        db.write("UPDATE backintel.analysis_sources SET body=body||%s WHERE id='commerce'", (Jsonb({'terms_acknowledged': False}),))
        source = db.source('commerce')
        for change in ('enabled=false', "expires_at=now()-interval '1 second'", "role='analyst'", "domains=ARRAY['support']"):
            def revoke(*args, **kwargs):
                current = authorize(*args, **kwargs)
                db.write('UPDATE backintel.analysis_principals SET '+change+' WHERE id=%s', (self.actor['id'],))
                return current
            try:
                with self.subTest(change=change), patch.object(db, 'authorize', side_effect=revoke), self.assertRaisesRegex(PermissionError, 'Current manager authority'):
                    terms('commerce', TermsInput(acknowledged=True, source_spec_sha256=source['body']['source_spec_sha256']), self.actor)
                self.assertEqual(db.source('commerce')['body'], source['body'])
            finally:
                db.write("UPDATE backintel.analysis_principals SET enabled=true,expires_at=NULL,role='manager',domains=ARRAY['commerce','support'] WHERE id=%s", (self.actor['id'],))

    def test_refresh_skips_retired_sources_and_still_dispatches(self):
        with patch.object(db, 'query', side_effect=[[{'domain': 'retired'}, {'domain': 'commerce'}], self.actor]), patch.object(service, 'import_source', return_value={'snapshot': self.snapshot}) as importer, patch.object(service, 'schedule_snapshot', return_value=[]), patch.object(service, 'dispatch', return_value={'fixture': True}) as dispatch:
            result = service.refresh()
        importer.assert_called_once_with('commerce', self.actor)
        dispatch.assert_called_once()
        self.assertEqual([row['domain'] for row in result['sources']], ['commerce'])

    def test_source_listing_skips_retired_domains_with_persisted_grants(self):
        from runtime import analysis_api as api
        before = [source['domain'] for source in api.sources(self.actor)]
        self.assertIn('commerce', before)
        configured = {domain: spec for domain, spec in api.CONFIG['sources'].items() if domain != 'commerce'}
        with patch.dict(api.CONFIG['sources'], configured, clear=True):
            self.assertEqual([source['domain'] for source in api.sources(self.actor)],
                             [domain for domain in before if domain != 'commerce'])
    def test_source_queue_limit_is_atomic_and_replays_remain_available(self):
        from runtime.analysis_api import cancel_run
        for index in range(18):
            service.submit(self.goal, self.actor, question=f'Queued question {index}')
        barrier = threading.Barrier(2)
        def submit(index):
            barrier.wait(timeout=5)
            try:
                return service.submit(self.goal, self.actor, question=f'Racing question {index}')
            except RuntimeError as exc:
                self.assertIn('20 pending-run limit', str(exc))
                return None
        with ThreadPoolExecutor(max_workers=2) as workers:
            results = list(workers.map(submit, range(2)))
        self.assertEqual(sum(row is not None for row in results), 1)
        self.assertEqual(service.submit(self.goal, self.actor)['id'], self.run['id'])
        cancel_run(self.run['id'], self.actor)
        self.assertIsNotNone(service.submit(self.goal, self.actor, question='After cancellation'))

    def test_duration_corrections_reject_negative_and_accept_zero(self):
        from runtime.analysis_api import correction, CorrectionInput
        original = db.query('SELECT domains FROM backintel.analysis_principals WHERE id=%s', (self.actor['id'],), one=True)['domains']
        db.write('UPDATE backintel.analysis_principals SET domains=%s WHERE id=%s', (['commerce', 'support', 'maintenance'], self.actor['id']))
        try:
            for domain in ('support', 'maintenance'):
                rows = [{**self.rows[0], 'target': 5}]
                snapshot = digest([domain, rows])
                db.save_snapshot(domain, snapshot, {'fixture': True}, rows)
                db.write("UPDATE backintel.analysis_sources SET body=body||%s WHERE id=%s", (Jsonb({'terms_acknowledged': True}), domain))
                with self.subTest(domain=domain), self.assertRaisesRegex(ValueError, 'nonnegative'):
                    correction(domain, CorrectionInput(record_id=rows[0]['id'], target=-1, explanation='Invalid duration'), self.actor)
                self.assertEqual(db.source(domain)['latest_snapshot'], snapshot)
                self.assertEqual(db.records(snapshot)[0]['target'], 5)
                with patch.object(service, 'schedule_snapshot', return_value=[]):
                    correction(domain, CorrectionInput(record_id=rows[0]['id'], target=0, explanation='Valid zero duration'), self.actor)
                self.assertEqual(db.records(db.source(domain)['latest_snapshot'])[0]['target'], 0)
        finally:
            db.write('UPDATE backintel.analysis_principals SET domains=%s WHERE id=%s', (original, self.actor['id']))

    def test_maintenance_predictions_use_latest_test_engine_states(self):
        from runtime import analysis_agent as agent, analysis_models
        def row(identity, entity, cycle, split):
            return {'id': identity, 'entity': entity, 'features': {'cycle': cycle}, 'groups': {}, 'target': None, 'split': split}
        rows = [row('training', 'train-1', 99, 'train'), row('old', 'test-1', 1, 'test'),
                row('corrected', 'test-1', 3, 'unlabeled'), row('second', 'test-2', 2, 'test'), row('third', 'test-3', 4, 'test')]
        run = {'snapshot_id': 'snapshot', 'body': {'model_id': 'model'}}
        goal = {'id': 'goal', 'domain': 'maintenance'}
        with patch.object(db, 'check_run', return_value=(run, goal)), patch.object(db, 'step', return_value=None), patch.object(db, 'records', return_value=rows) as records, patch.object(db, 'query', return_value={'id': 'model', 'goal_id': 'goal'}), patch.object(db, 'evidence', return_value='evidence'), patch.object(db, 'save_step', side_effect=lambda identity, key, kind, body: body), patch.object(analysis_models, 'predict', side_effect=lambda model, cohort: [1] * len(cohort)) as predict, patch.dict(agent.CONFIG['limits'], test=2):
            first = agent.tool('run', 'predict', {})
            cohort = predict.call_args.args[1]
            self.assertEqual(len(cohort), 2)
            self.assertEqual(len({r['entity'] for r in cohort}), 2)
            self.assertTrue(all(r['entity'].startswith('test-') and r['id'] != 'old' for r in cohort))
            self.assertEqual(first['sample_size'], 2)
            records.return_value = list(reversed(rows))
            self.assertEqual(agent.tool('run', 'predict', {}), first)
            self.assertEqual(predict.call_args.args[1], cohort)
            with patch.dict(agent.CONFIG['limits'], test=10):
                agent.tool('run', 'predict', {})
                self.assertEqual({r['id'] for r in predict.call_args.args[1]}, {'corrected', 'second', 'third'})

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
        with patch.object(service, 'validate_source_receipt', return_value={'snapshot_id':snapshot,'adapter_receipt':{'files':[],'mode':'fixture'}}), patch.object(service, 'source_files', return_value=[]), patch.object(service, 'adapt', side_effect=adapt), patch.object(db, 'records', side_effect=records), ThreadPoolExecutor(max_workers=2) as workers:
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

    def test_duplicate_submission_does_not_block_an_active_worker(self):
        entered, release = threading.Event(), threading.Event()
        def analyze(identity):
            entered.set()
            if not release.wait(5):
                raise TimeoutError('Fixture analysis was not released')
            return {'summary':'fixture'}
        with patch('runtime.analysis_agent.analyze', side_effect=analyze), ThreadPoolExecutor(max_workers=2) as workers:
            running = workers.submit(service.execute, self.run['job_id'], service.handle)
            try:
                self.assertTrue(entered.wait(5))
                duplicate = workers.submit(service.submit, self.goal, self.actor)
                self.assertEqual(duplicate.result(timeout=2)['id'], self.run['id'])
            finally:
                release.set()
            self.assertEqual(running.result(timeout=5)['state'], 'completed')

    def test_revoked_source_terms_block_admission_and_dispatch(self):
        from unittest.mock import MagicMock
        from runtime import analysis_agent as agent
        db.write("UPDATE backintel.analysis_sources SET body=body || %s WHERE id='commerce'", (Jsonb({'terms_acknowledged':False}),))
        for operation in ('analysis', 'training'):
            with self.assertRaisesRegex(PermissionError, 'terms'):
                service.submit(self.goal, self.actor, operation=operation)
        with self.assertRaisesRegex(PermissionError, 'terms'):
            db.check_run(self.run['id'])
        db.write("UPDATE backintel.analysis_sources SET body=body || %s WHERE id='commerce'", (Jsonb({'terms_acknowledged':True}),))
        client = MagicMock()
        client.__enter__.return_value = client
        client.get.return_value.json.return_value = {'data':[{'id':CONFIG['analyst']['model'],'pricing':{'prompt':'0','completion':'0'}}]}
        query = db.query
        def revoke_before_send(sql, *args, **kwargs):
            if sql.startswith("SELECT r.id AS dispatch_run"):
                db.write("UPDATE backintel.analysis_sources SET body=body || %s WHERE id='commerce'", (Jsonb({'terms_acknowledged':False}),))
            return query(sql, *args, **kwargs)
        with patch.object(agent, 'credential', return_value='fixture'), patch.object(agent.httpx, 'Client', return_value=client), patch.object(db, 'query', side_effect=revoke_before_send), self.assertRaisesRegex(RuntimeError, 'reservation changed'):
            agent.request(self.run['id'], 0, [])
        client.post.assert_not_called()

    def test_revoked_source_terms_block_publication(self):
        from runtime.analysis_api import terms, TermsInput
        original = db.run_domain
        def revoke_before_publication(run):
            terms('commerce', TermsInput(acknowledged=False), self.actor)
            return original(run)
        with patch('runtime.analysis_agent.analyze', return_value={'summary':'fixture'}), patch.object(db, 'run_domain', side_effect=revoke_before_publication):
            service.execute(self.run['job_id'], service.handle)
        self.assertEqual(db.run(self.run['id'])['status'], 'cancelled')
        self.assertIsNone(db.goal(self.goal)['last_success'])

    def test_promotion_rejects_a_superseded_source_snapshot(self):
        candidate = self.candidate_fixture()
        db.save_snapshot('commerce', digest([self.snapshot, 'new']), {'files':[], 'mode':'fixture'}, self.rows)
        with self.assertRaisesRegex(ValueError, 'snapshot is no longer current'):
            service.promote(candidate, self.actor)
        self.assertIsNone(db.goal(self.goal)['active_model'])

    def test_promotion_rolls_back_when_manager_authority_changes_after_admission(self):
        admit = service._admit_run
        candidate = self.candidate_fixture()
        for change in ('enabled=false', "expires_at=now()-interval '1 second'", "role='analyst'", "domains=ARRAY['support']"):
            before = db.query('SELECT count(*) AS n FROM backintel.analysis_runs WHERE goal_id=%s', (self.goal,), one=True)['n']
            def revoke_after_admission(*args, **kwargs):
                run_id = admit(*args, **kwargs)
                db.write('UPDATE backintel.analysis_principals SET '+change+' WHERE id=%s', (self.actor['id'],))
                return run_id
            try:
                with self.subTest(change=change), patch.object(service, '_admit_run', side_effect=revoke_after_admission), self.assertRaisesRegex(PermissionError, 'Current manager authority'):
                    service.promote(candidate, self.actor)
                self.assertIsNone(db.goal(self.goal)['active_model'])
                self.assertFalse(db.query('SELECT promoted FROM backintel.analysis_models WHERE id=%s', (candidate,), one=True)['promoted'])
                self.assertEqual(db.query('SELECT count(*) AS n FROM backintel.analysis_runs WHERE goal_id=%s', (self.goal,), one=True)['n'], before)
            finally:
                db.write("UPDATE backintel.analysis_principals SET enabled=true,expires_at=NULL,role='manager',domains=ARRAY['commerce','support'] WHERE id=%s", (self.actor['id'],))

    def test_snapshot_reversion_compares_previous_installation_not_creation_time(self):
        from runtime.analysis_agent import tool
        first = self.snapshot
        second_rows = [{**self.rows[0], 'target': 0}]
        second = digest(second_rows)
        db.save_snapshot('commerce', second, {'fixture': True}, second_rows)
        middle = service.submit(self.goal, self.actor)
        self.assertEqual(middle['body']['prior_snapshot'], first)
        db.save_snapshot('commerce', first, {'fixture': True}, self.rows)
        reverted = service.submit(self.goal, self.actor)
        self.assertNotEqual(reverted['id'], self.run['id'])
        self.assertEqual(reverted['body']['prior_snapshot'], second)
        comparison = tool(reverted['id'], 'compare_snapshots', {})
        self.assertEqual(comparison['prior_snapshot'], second)
        self.assertEqual(comparison['current'][0]['mean'], 1)
        self.assertEqual(comparison['previous'][0]['mean'], 0)
        db.save_snapshot('commerce', first, {'fixture': True}, self.rows)
        self.assertEqual(db.source('commerce')['body']['previous_snapshot'], second)
        self.assertEqual(service.submit(self.goal, self.actor)['id'], reverted['id'])

    def test_implementation_change_marks_previous_answer_stale(self):
        from runtime.analysis_api import goals
        db.write("UPDATE backintel.analysis_sources SET body=body-'last_refresh_error' WHERE id='commerce'")
        with patch('runtime.analysis_agent.analyze', return_value={'summary':'fixture'}):
            service.execute(self.run['job_id'], service.handle)
        self.assertEqual(next(g for g in goals(db.authorize(self.actor)) if g['id']==self.goal)['freshness'], 'current')
        with patch.object(service, 'analysis_identity', return_value='fixture-new-code'):
            self.assertEqual(next(g for g in goals(db.authorize(self.actor)) if g['id']==self.goal)['freshness'], 'stale')

    def test_correction_after_spec_change_reuses_the_locked_connection(self):
        from runtime.analysis_api import correction, CorrectionInput
        connect = db.connect
        def bounded_connection():
            c = connect()
            c.execute("SET lock_timeout='1s'")
            return c
        with patch.dict(CONFIG['sources']['commerce'], {'license':'fixture-new-terms'}), patch.object(db, 'connect', side_effect=bounded_connection), self.assertRaisesRegex(PermissionError, 'terms'):
            correction('commerce', CorrectionInput(record_id=self.rows[0]['id'], features={'age':41}, explanation='Fixture edit'), self.actor)
        db.catalog('commerce')

    def test_analysis_reuse_tracks_implementation_and_configuration(self):
        self.assertEqual(service.submit(self.goal, self.actor)['id'], self.run['id'])
        fingerprint = service.fingerprint
        def changed(path):
            value = fingerprint(path)
            return {**value, 'sha256':'fixture-new-code'} if path.name == 'analysis_agent.py' else value
        with patch.object(service, 'fingerprint', side_effect=changed):
            self.assertNotEqual(service.submit(self.goal, self.actor)['id'], self.run['id'])
        with patch.dict(CONFIG['analyst'], {'model':'fixture-new-model'}):
            self.assertNotEqual(service.submit(self.goal, self.actor)['id'], self.run['id'])

    def test_goal_revocation_at_publication_does_not_replace_answer(self):
        query = db.query
        for edit in ({'paused':True}, {'confirmed':False}):
            with self.subTest(edit=edit):
                service.revise_goal(self.goal, self.actor, paused=False, confirmed=True)
                run = service.submit(self.goal, self.actor)
                def revoke_before_lock(sql, *args, **kwargs):
                    if sql == 'SELECT * FROM backintel.analysis_goals WHERE id=%s FOR UPDATE':
                        service.revise_goal(self.goal, self.actor, **edit)
                    return query(sql, *args, **kwargs)
                with patch('runtime.analysis_agent.analyze', return_value={'summary':'fixture'}), patch.object(db, 'query', side_effect=revoke_before_lock):
                    service.execute(run['job_id'], service.handle)
                self.assertEqual(db.run(run['id'])['status'], 'cancelled')
                self.assertIsNone(db.goal(self.goal)['last_success'])

    def test_changed_source_spec_revokes_old_consent_and_refreshes_catalog(self):
        db.write("UPDATE backintel.analysis_sources SET body=body || %s WHERE id='commerce'", (Jsonb({'terms_acknowledged':True}),))
        db.catalog('commerce')
        self.assertTrue(db.source('commerce')['body']['terms_acknowledged'])
        with patch.dict(CONFIG['sources']['commerce'], {'license':'fixture-changed-terms'}):
            source = db.source('commerce')
            self.assertFalse(source['body']['terms_acknowledged'])
            self.assertEqual(source['body']['license'], 'fixture-changed-terms')
            self.assertEqual(source['latest_snapshot'], self.snapshot)
            with self.assertRaisesRegex(PermissionError, 'terms'):
                service.import_source('commerce', self.actor)
        db.catalog('commerce')

    def test_source_confirmation_is_bound_to_the_displayed_terms(self):
        from runtime.analysis_api import terms, TermsInput
        old_hash = db.source('commerce')['body']['source_spec_sha256']
        with patch.dict(CONFIG['sources']['commerce'], {'license':'fixture-updated-license'}):
            current = db.source('commerce')
            with self.assertRaisesRegex(ValueError, 'terms changed'):
                terms('commerce', TermsInput(acknowledged=True, source_spec_sha256=old_hash), self.actor)
            self.assertFalse(db.source('commerce')['body']['terms_acknowledged'])
            accepted = terms('commerce', TermsInput(acknowledged=True, source_spec_sha256=current['body']['source_spec_sha256']), self.actor)
            self.assertTrue(accepted['body']['terms_acknowledged'])
        db.catalog('commerce')

    def test_training_candidate_rolls_back_until_job_acceptance(self):
        import json
        from types import SimpleNamespace
        from runtime.jobs import cancel
        for boundary in ('cancel', 'interrupt', 'success'):
            with self.subTest(boundary=boundary):
                run = service.submit(self.goal, self.actor, question=boundary, operation='training')
                manifest = {'id':boundary, 'artifacts':[{'file':'catboost-facts.joblib'}], 'mode':'fixture'}
                candidate = digest([self.goal, boundary, manifest['artifacts']])
                def handler(store, payload):
                    result = service.handle(store, payload)
                    if boundary == 'interrupt':
                        raise KeyboardInterrupt('Fixture interruption before training acceptance')
                    if boundary == 'cancel':
                        with db.connect() as c:
                            cancel(c, run['job_id'])
                    return result
                with patch.object(service.subprocess, 'run', return_value=SimpleNamespace(returncode=0, stdout=json.dumps(manifest))):
                    if boundary == 'interrupt':
                        with self.assertRaises(KeyboardInterrupt):
                            service.execute(run['job_id'], handler)
                        db.write("UPDATE backintel.capability_jobs SET state='cancelled' WHERE job_id=%s", (run['job_id'],))
                    else:
                        service.execute(run['job_id'], handler)
                saved = db.query('SELECT id FROM backintel.analysis_models WHERE id=%s', (candidate,))
                self.assertEqual(bool(saved), boundary == 'success')

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
            db.write("UPDATE backintel.capability_jobs SET state='cancelled' WHERE job_id=%s", (other['job_id'],))
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

    def test_dispatch_drains_delayed_retry_without_another_wake(self):
        db.write('UPDATE backintel.capability_jobs SET max_attempts=2 WHERE job_id=%s', (self.run['job_id'],))
        original = service.handle
        def transient(store, payload):
            attempt = db.query('SELECT attempts FROM backintel.capability_jobs WHERE job_id=%s', (self.run['job_id'],), one=True)['attempts']
            if attempt == 1:
                raise RuntimeError('Fixture transient failure')
            return original(store, payload)
        with patch.object(service, 'handle', side_effect=transient), \
                patch('runtime.analysis_agent.analyze', return_value={'summary': 'explicit fixture', 'tables': [], 'mode': 'fixture'}):
            result = service.dispatch()
        self.assertEqual([job['state'] for job in result['jobs']], ['retry', 'completed'])
        self.assertEqual(db.run(self.run['id'])['status'], 'succeeded')

    def test_delayed_retry_can_be_cancelled_while_dispatch_waits(self):
        from runtime.jobs import cancel
        db.write("UPDATE backintel.capability_jobs SET state='retry',attempts=1,max_attempts=2,due_at=now()+interval '1 second' WHERE job_id=%s", (self.run['job_id'],))
        def cancel_waiting(delay):
            self.assertGreater(delay, 0)
            self.assertLessEqual(delay, 1)
            with db.connect() as connection:
                cancel(connection, self.run['job_id'])
        with patch.object(service.time, 'sleep', side_effect=cancel_waiting) as wait, patch.object(service, 'execute') as execute:
            service.dispatch()
        wait.assert_called_once()
        execute.assert_not_called()
        self.assertEqual(db.query('SELECT state FROM backintel.capability_jobs WHERE job_id=%s', (self.run['job_id'],), one=True)['state'], 'cancelled')

    def test_goal_edits_recheck_manager_after_initial_authorization(self):
        authorize = db.authorize
        before = db.goal(self.goal)
        for change in ('enabled=false', "expires_at=now()-interval '1 second'", "role='analyst'", "domains=ARRAY['support']"):
            def revoke(actor, *args, **kwargs):
                current = authorize(actor, *args, **kwargs)
                db.write('UPDATE backintel.analysis_principals SET '+change+' WHERE id=%s', (actor['id'],))
                return current
            try:
                with self.subTest(change=change), patch.object(db, 'authorize', side_effect=revoke), self.assertRaises(PermissionError):
                    service.revise_goal(self.goal, self.actor, question='An unauthorized edit')
                self.assertEqual(db.goal(self.goal), before)
            finally:
                db.write("UPDATE backintel.analysis_principals SET enabled=true,expires_at=NULL,role='manager',domains=ARRAY['commerce','support'] WHERE id=%s", (self.actor['id'],))

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

    def test_test_evidence_is_withheld_across_api_routes_until_promotion(self):
        from fastapi.testclient import TestClient
        from runtime.analysis_api import app
        private = 'private-record-identifier'
        method = {'route': 'catboost', 'features': 'facts', 'metrics': {'heldout_error': 123},
                  'calibration_metrics': {'selection_error': .2}, 'predictions': {private: .9}}
        manifest = {'id': 'disclosure-fixture', 'methods': [method], 'splits': {'test': [private]},
                    'artifacts': [{'file': private}]}
        candidate = digest([self.goal, 'viewer'])
        db.write('INSERT INTO backintel.analysis_models(id,goal_id,snapshot_id,body) VALUES(%s,%s,%s,%s)',
                 (candidate, self.goal, self.snapshot, Jsonb(manifest)))
        db.write('UPDATE backintel.analysis_runs SET result=%s WHERE id=%s', (Jsonb({'comparison': manifest}), self.run['id']))
        db.write('UPDATE backintel.analysis_goals SET last_success=%s WHERE id=%s', (self.run['id'], self.goal))
        evidence = db.evidence(self.run['id'], 'model_comparison', 'viewer-model', manifest)
        client = TestClient(app)
        routes = ['/api/v1/goals/'+self.goal+'/models', '/api/v1/runs?goal_id='+self.goal,
                  '/api/v1/runs/'+self.run['id'], '/api/v1/goals/'+self.goal+'/findings', '/api/v1/evidence/'+evidence]
        for promoted in (False, True):
            db.write('UPDATE backintel.analysis_models SET promoted=%s WHERE id=%s', (promoted, candidate))
            for role in ('viewer', 'manager'):
                for route in routes:
                    with self.subTest(promoted=promoted, role=role, route=route):
                        response = client.get(route, headers={'Authorization': 'Bearer campaign-'+role})
                        if role == 'viewer' and route.endswith(evidence):
                            self.assertEqual(response.status_code, 403)
                            continue
                        self.assertEqual(response.status_code, 200, response.text)
                        self.assertIn('selection_error', response.text)
                        self.assertEqual('heldout_error' in response.text, promoted)
                        self.assertEqual(private in response.text, promoted and role == 'manager')

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

    def test_dispatch_reconciles_terminal_jobs_left_by_an_interruption(self):
        for index, (job_state, run_state) in enumerate((('failed', 'partial'), ('cancelled', 'cancelled'))):
            with self.subTest(job_state=job_state):
                db.write("UPDATE backintel.analysis_runs SET status='running' WHERE id=%s", (self.run['id'],))
                db.write('UPDATE backintel.capability_jobs SET state=%s,error=%s WHERE job_id=%s',
                         (job_state, 'fixture interrupted finalization', self.run['job_id']))
                service.dispatch()
                service.dispatch()
                self.assertEqual(db.run(self.run['id'])['status'], run_state)
                self.assertEqual(len(db.query("SELECT sequence FROM backintel.analysis_events WHERE run_id=%s AND kind='completed'", (self.run['id'],))), index+1)

    def test_rebuilt_model_files_create_a_distinct_candidate(self):
        import json
        from types import SimpleNamespace
        training = service.submit(self.goal, self.actor, operation='training')
        candidates = []
        for fingerprint in ('a'*64, 'b'*64):
            manifest = {'id':'same-comparison-inputs', 'artifacts':[{'file':'catboost-facts.joblib', 'sha256':fingerprint}]}
            with patch.object(service.subprocess, 'run', return_value=SimpleNamespace(returncode=0, stdout=json.dumps(manifest))):
                candidates.append(service.model_job(training['id'])['candidate_id'])
        self.assertNotEqual(*candidates)
        self.assertEqual(len(db.query('SELECT id FROM backintel.analysis_models WHERE id=ANY(%s)', (candidates,))), 2)

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

        def records(snapshot, **kwargs):
            if not reading.is_set():
                reading.set()
                if not release.wait(5):
                    raise TimeoutError('Fixture correction was not released')
            else:
                second_read.set()
            return original_records(snapshot, **kwargs)

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

    def test_reactivating_a_model_restores_its_exact_standing_answer(self):
        candidate = self.candidate_fixture()
        with patch('runtime.analysis_agent.analyze', return_value={'summary': 'fixture result', 'tables': []}):
            first = service.promote(candidate, self.actor)
            service.dispatch()
            self.assertEqual(db.goal(self.goal)['last_success'], first['id'])
            second = digest([candidate, 'second'])
            db.write('INSERT INTO backintel.analysis_models(id,goal_id,snapshot_id,body) VALUES(%s,%s,%s,%s)',
                     (second, self.goal, self.snapshot, Jsonb({'artifacts':[{'file':'catboost-facts.joblib'}]})))
            newer = service.promote(second, self.actor)
            service.dispatch()
            self.assertEqual(db.goal(self.goal)['last_success'], newer['id'])
            restored = service.promote(candidate, self.actor)
        self.assertEqual(restored['id'], first['id'])
        self.assertEqual(restored['status'], 'succeeded')
        self.assertEqual(db.goal(self.goal)['last_success'], first['id'])
        self.assertEqual(service.submit(self.goal, self.actor)['id'], first['id'])

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
            if sql.startswith("SELECT r.id AS dispatch_run"):
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

    def test_forecasts_require_findings_citing_prediction_evidence(self):
        import json
        from runtime import analysis_agent as agent
        observed = {'tool':'summarize','evidence_id':'observed','kind':'observed','table':[{'group':'A','mean':.2,'count':10}]}
        prediction = {**observed,'tool':'predict','evidence_id':'predicted','kind':'estimate'}
        for question in ('What is the forecast?', 'What is the probability?', 'What is the likelihood?', 'What are the predictions?'):
            db.write("UPDATE backintel.analysis_runs SET body=body || %s WHERE id=%s", (Jsonb({'question':question}),self.run['id']))
            for evidence,kind,expected in (('observed','fact',False), ('predicted','estimate',True)):
                answer = {'summary':'Group A mean is 0.2.', 'limitations':[], 'findings':[{'claim':'Group A mean is 0.2.','kind':kind,'evidence_ids':[evidence]}]}
                calls = {'output':[{'type':'function_call','name':name,'arguments':'{}','call_id':name} for name in ('summarize','predict')]}
                final = {'output':[{'type':'message','content':[{'type':'output_text','text':json.dumps(answer)}]}]}
                with self.subTest(question=question,evidence=evidence), patch.object(agent,'request',side_effect=[calls,final]), patch.object(agent,'tool',side_effect=[observed,prediction]):
                    if expected:
                        self.assertEqual(agent.analyze(self.run['id'])['status'],'succeeded')
                    else:
                        with self.assertRaisesRegex(ValueError,'Requested prediction is unavailable'):
                            agent.analyze(self.run['id'])

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
