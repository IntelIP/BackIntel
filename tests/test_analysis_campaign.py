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

    def test_failed_refresh_keeps_standing_result(self):
        first = {'summary': 'standing fixture', 'tables': [{'title': 'summarize', 'rows': [{'group': 'A', 'mean': 1}]}]}
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
        with patch('runtime.analysis_agent.analyze', return_value={'summary': 'refreshed fixture', 'tables': [{'title': 'summarize', 'rows': [{'group': 'A', 'mean': 0}]}]}):
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


if __name__ == '__main__':
    unittest.main()
