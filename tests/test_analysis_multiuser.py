"""Real database/API isolation and concurrent admission; no provider is contacted."""
import hashlib
import os
import threading
import unittest
import uuid
from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal
from unittest.mock import patch

from fastapi.testclient import TestClient
from psycopg.conninfo import conninfo_to_dict
from psycopg.types.json import Jsonb

from runtime import analysis_store as db, analysis_service as service
from runtime.analysis_data import CONFIG, digest


@unittest.skipUnless(os.getenv('BACKINTEL_ANALYSIS_CHECK_DB'), 'Requires a disposable analysis-check database')
class MultiUserChecks(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        uri = os.environ['BACKINTEL_ANALYSIS_CHECK_DB']
        name = conninfo_to_dict(uri)['dbname']
        if not (name.startswith('backintel_') and name.endswith('_test')):
            raise RuntimeError('Multi-user fixtures require a disposable backintel_*_test database')
        os.environ['BACKINTEL_APP_DATABASE_URL'] = uri
        from runtime.bootstrap import initialize
        from runtime.analysis_api import app
        initialize()
        db.catalog()
        cls.client = TestClient(app)
    def setUp(self):
        self.users = {role: 'multi-' + role + '-' + uuid.uuid4().hex for role in ('a', 'b', 'viewer')}
        for label, identity in self.users.items():
            db.write('''INSERT INTO backintel.analysis_principals(id,token_hash,role,domains,budget_usd)
                VALUES(%s,%s,%s,%s,%s)''', (identity, hashlib.sha256(identity.encode()).hexdigest(),
                'viewer' if label == 'viewer' else 'manager', ['commerce'], 0 if label == 'viewer' else Decimal('.05')))

        db.write('DELETE FROM backintel.analysis_requests')
        db.write('UPDATE backintel.analysis_goals SET paused=true')
        db.write("UPDATE backintel.capability_jobs SET state='cancelled' WHERE state IN ('queued','retry') AND task_id LIKE 'analysis-job-%'")
        db.write("UPDATE backintel.analysis_sources SET body=body || '{\"terms_acknowledged\":true}'::jsonb")
        rows = [{'id': str(uuid.uuid4()), 'entity': 'fixture', 'features': {'age': 40},
                 'target': 1, 'groups': {'department': 'A'}, 'text': 'fixture', 'split': 'train'}]
        db.save_snapshot('commerce', digest(rows), {'files': [], 'rows': 1, 'mode': 'fixture'}, rows)
        self.goals = {}
        self.runs = {}
        for owner in ('a', 'b'):
            actor = {'id': self.users[owner]}
            self.goals[owner] = []
            self.runs[owner] = []
            for index in range(2):
                goal = service.create_goal(actor, 'commerce', f'Private {owner} question {uuid.uuid4()} {index}')
                service.revise_goal(goal['id'], actor, confirmed=True)
                self.goals[owner].append(goal['id'])
                self.runs[owner].append(service.submit(goal['id'], actor)['id'])

    def headers(self, owner):
        return {'Authorization': 'Bearer ' + self.users[owner]}

    def test_private_objectives_explicit_read_only_sharing_and_queue(self):
        for owner, other in (('a', 'b'), ('b', 'a')):
            headers = self.headers(owner)
            listed = self.client.get('/api/v1/goals', headers=headers)
            self.assertEqual(listed.status_code, 200, listed.text)
            self.assertEqual({g['id'] for g in listed.json()}, set(self.goals[owner]))
            queued = self.client.get('/api/v1/queue', headers=headers).json()
            self.assertEqual({r['id'] for r in queued['jobs']}, set(self.runs[owner]))
            self.assertEqual(queued['shared_capacity']['active_limit'], 2)
            self.assertGreaterEqual(queued['shared_capacity']['waiting'], 4)
            goal, run = self.goals[other][0], self.runs[other][0]
            for path in (f'/runs?goal_id={goal}', f'/goals/{goal}/findings', f'/goals/{goal}/models',
                         f'/goals/{goal}/reviews', f'/runs/{run}', f'/runs/{run}/requests', f'/runs/{run}/events'):
                self.assertEqual(self.client.get('/api/v1' + path, headers=headers).status_code, 403, path)
            self.assertEqual(self.client.patch(f'/api/v1/goals/{goal}', headers=headers, json={'paused': True}).status_code, 403)
            self.assertEqual(self.client.post(f'/api/v1/goals/{goal}/runs', headers=headers, json={}).status_code, 403)
            self.assertEqual(self.client.post(f'/api/v1/runs/{run}/cancel', headers=headers).status_code, 403)
            self.assertEqual(self.client.patch('/api/v1/principals/' + self.users[other], headers=headers,
                             json={'domains': ['commerce'], 'budget_usd': 1}).status_code, 403)
            with self.assertRaises(PermissionError):
                service.submit(goal, {'id': self.users[owner]})
            with self.assertRaises(PermissionError):
                service.revise_goal(goal, {'id': self.users[owner]}, budget_usd=1)
        goal = self.goals['a'][0]
        path = f'/api/v1/goals/{goal}/access/{self.users["viewer"]}'
        shared = self.client.put(path, headers=self.headers('a'), json={'permission': 'read'})
        self.assertEqual(shared.status_code, 200, shared.text)
        visible = self.client.get('/api/v1/goals', headers=self.headers('viewer')).json()
        self.assertEqual([g['id'] for g in visible], [goal])
        self.assertFalse(visible[0]['can_run'])
        self.assertFalse(visible[0]['can_manage'])
        self.assertEqual(self.client.get('/api/v1/runs/' + self.runs['a'][0], headers=self.headers('viewer')).status_code, 200)
        self.assertEqual(self.client.post('/api/v1/runs/' + self.runs['a'][0] + '/cancel', headers=self.headers('viewer')).status_code, 403)
        self.assertEqual(self.client.post(f'/api/v1/goals/{goal}/runs', headers=self.headers('viewer'), json={}).status_code, 403)
        self.assertEqual(self.client.put(path, headers=self.headers('viewer'), json={'permission': 'manage'}).status_code, 403)
        self.assertEqual(self.client.put(path, headers=self.headers('a'), json={'permission': None}).status_code, 200)
        self.assertEqual(self.client.get('/api/v1/runs/' + self.runs['a'][0], headers=self.headers('viewer')).status_code, 403)

    def test_concurrent_owner_budgets_and_request_identity_are_separate(self):
        def reserve(run):
            try:
                db.reserve(run, 'multi-call-' + run, Decimal('.04'))
                return 'accepted'
            except RuntimeError as error:
                return str(error)

        with patch.dict(CONFIG['budget'], {'max_concurrent': 10}):
            with ThreadPoolExecutor(max_workers=2) as workers:
                outcomes = list(workers.map(reserve, self.runs['a']))
            self.assertEqual(outcomes.count('accepted'), 1)
            self.assertIn('User inference budget exhausted', outcomes)
            self.assertEqual(reserve(self.runs['b'][0]), 'accepted')
            for owner in ('a', 'b'):
                usage = self.client.get('/api/v1/queue', headers=self.headers(owner)).json()['your_usage']
                self.assertEqual(Decimal(str(usage['reserved_usd'])), Decimal('.04'))
                self.assertEqual(usage['provider_usd'], 0)
                self.assertEqual(usage['unresolved_charges'], 1)
            prior = db.query('SELECT id FROM backintel.analysis_requests WHERE run_id=ANY(%s)', (self.runs['a'],), one=True)['id']
            db.write("UPDATE backintel.analysis_requests SET status='complete',charge=0,response=%s WHERE id=%s",
                     (Jsonb({'private': 'owner-a'}), prior))
            with self.assertRaisesRegex(PermissionError, 'another run'):
                db.reserve(self.runs['b'][1], prior, Decimal('.01'))

    def test_shared_capacity_bounds_concurrent_admission_and_preserves_replay(self):
        def admit(index):
            owner = {'id': self.users['a' if index % 2 else 'b']}
            goal = self.goals['a' if index % 2 else 'b'][0]
            try:
                return service.submit(goal, owner, question=f'Capacity question {index}')['id']
            except RuntimeError as error:
                return str(error)

        with ThreadPoolExecutor(max_workers=4) as workers:
            results = list(workers.map(admit, range(4)))
        self.assertEqual(sum('six outstanding-job limit' in result for result in results), 2)
        queue = self.client.get('/api/v1/queue', headers=self.headers('a')).json()
        self.assertEqual(queue['shared_capacity']['waiting'], 6)
        self.assertEqual(queue['shared_capacity']['waiting_limit'], 6)
        replay = service.submit(self.goals['a'][0], {'id': self.users['a']})
        self.assertEqual(replay['id'], self.runs['a'][0])
        # A queued job moving to running and back to retry retains its reservation.
        job = db.run(self.runs['b'][0])['job_id']
        for state in ('running', 'retry'):
            db.write('UPDATE backintel.capability_jobs SET state=%s WHERE job_id=%s', (state, job))
            self.assertIn('six outstanding-job limit', admit(10))

    def test_new_admission_does_not_wait_for_a_running_permission_reader(self):
        with ThreadPoolExecutor(max_workers=1) as workers:
            with db.connect() as reader, reader.transaction():
                reader.execute('SELECT id FROM backintel.analysis_goals WHERE id=%s FOR SHARE', (self.goals['a'][0],))
                admitted = workers.submit(service.submit, self.goals['a'][0], {'id': self.users['a']},
                                          question='Another source update while work runs')
                try:
                    admitted.result(timeout=2)
                    blocked = False
                except TimeoutError:
                    blocked = True
            admitted.result(timeout=5)
        self.assertFalse(blocked, 'Read-only admission waited for the running worker')

    def test_dispatch_reuses_a_free_slot_before_the_slow_job_finishes(self):
        entered, first_started, third_started, release = [], threading.Event(), threading.Event(), threading.Event()
        lock = threading.Lock()

        def execute(job_id):
            with lock:
                entered.append(job_id)
                index = len(entered)
            db.write("UPDATE backintel.capability_jobs SET state='running',lease_until=now()+interval '1 minute' WHERE job_id=%s", (job_id,))
            if index == 1:
                first_started.set()
                if not release.wait(8):
                    raise TimeoutError('Test did not release its slow worker')
            if index == 3:
                third_started.set()
            db.write("UPDATE backintel.capability_jobs SET state='cancelled' WHERE job_id=%s", (job_id,))
            return {'job_id': job_id, 'state': 'cancelled'}

        with patch.object(service, '_execute_analysis_job', side_effect=execute), ThreadPoolExecutor(max_workers=1) as workers:
            dispatch = workers.submit(service.dispatch)
            try:
                self.assertTrue(first_started.wait(3))
                self.assertTrue(third_started.wait(3), 'A free slot waited behind an unrelated slow worker')
            finally:
                release.set()
            self.assertEqual(len(dispatch.result(timeout=8)['jobs']), 4)
        self.assertEqual(len(set(entered)), 4)

    def test_short_queries_reuse_connections_without_caching_authority(self):
        pids = {db.query('SELECT pg_backend_pid() AS pid', one=True)['pid'] for _ in range(20)}
        self.assertLess(len(pids), 20)
        db.write('UPDATE backintel.analysis_principals SET enabled=false WHERE id=%s', (self.users['a'],))
        with self.assertRaises(PermissionError):
            db.authorize({'id': self.users['a']})


if __name__ == '__main__':
    unittest.main()
