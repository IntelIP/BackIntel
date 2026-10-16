"""Real PostgreSQL persistence and job execution; provider replies are simulated."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import MagicMock, patch

from runtime import analysis_api as api, analysis_agent, analysis_service as service, analysis_store as db, jobs
from runtime.bootstrap import initialize
from tests.test_analysis_objectives import REQUEST


@unittest.skipUnless(os.getenv('BACKINTEL_OBJECTIVE_CHECK_DB'), 'Needs a disposable PostgreSQL objective database')
class ObjectiveDatabaseChecks(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        uri = os.environ['BACKINTEL_OBJECTIVE_CHECK_DB']
        from psycopg.conninfo import conninfo_to_dict
        if conninfo_to_dict(uri)['dbname'] != 'backintel_objective_test':
            raise RuntimeError('Objective checks require backintel_objective_test')
        os.environ['BACKINTEL_APP_DATABASE_URL'] = uri
        os.environ['BACKINTEL_TEST_DATABASE_URL'] = uri
        initialize()
        db.catalog()
        for role in ('manager', 'analyst'):
            identity = 'objective-' + role
            db.write('INSERT INTO backintel.analysis_principals(id,token_hash,role,domains) VALUES(%s,%s,%s,%s)',
                     (identity, hashlib.sha256(identity.encode()).hexdigest(), role, ['commerce']))
        cls.actor = {'id': 'objective-manager'}

    def test_real_worker_exit_resumes_one_plan_and_one_fixture_charge(self):
        from runtime import analysis_planning as planning
        goal = service.create_goal(self.actor, **REQUEST)
        service.revise_goal(goal['id'], self.actor, budget_usd=.25)
        run = service.submit(goal['id'], self.actor, operation='planning')
        plan = {'summary': 'Synthetic recovery proposal.', 'data_needs': ['Permitted invoice fields'],
                'steps': [{'action': 'discover', 'purpose': 'Inspect permitted fields', 'expected_result': 'Field meanings recorded'}],
                'assumptions': [], 'open_questions': ['Source timezone unknown']}
        response = {'id': 'fixture-recovery-response', 'model': analysis_agent.CONFIG['analyst']['model'],
                    '_backintel_fixture': True, 'usage': {'cost': .001},
                    'output': [{'type': 'message', 'content': [{'type': 'output_text', 'text': json.dumps(plan)}]}]}
        client = MagicMock()
        client.__enter__.return_value = client
        client.get.return_value.json.return_value = {'data': [{'id': analysis_agent.CONFIG['analyst']['model'],
                                                              'pricing': {'prompt': '.000001', 'completion': '.000001'}}]}
        client.post.return_value.json.return_value = response
        # Exercise actual accounting, but the provider transport is a local test double.
        with patch.object(analysis_agent, 'credential', return_value='fixture'), patch.object(analysis_agent.httpx, 'Client', return_value=client):
            planning.propose(run['id'])
        self.assertEqual(client.post.call_count, 1)
        child = '''
import os,sys
from unittest.mock import patch
from runtime import analysis_planning as planning, analysis_service as service, jobs
original = planning.propose
def interrupted(identity):
    original(identity)
    os._exit(17)
# This subprocess is the worker. Avoid adding a second process inside it.
with patch.object(jobs, '_run_worker', side_effect=jobs._execute_claimed):
    if sys.argv[2] == 'crash':
        with patch.object(planning, 'propose', side_effect=interrupted):
            service.dispatch(sys.argv[1])
    else:
        service.dispatch(sys.argv[1])
        service.dispatch(sys.argv[1])
'''
        with tempfile.TemporaryDirectory(prefix='backintel-recovery-check-') as temporary:
            env = os.environ.copy()
            env.pop('OPENROUTER_API_KEY', None)
            env['BACKINTEL_ANALYST_CREDENTIAL_FILE'] = str(Path(temporary) / 'absent-provider-key.json')
            env['TMPDIR'] = temporary
            command = [sys.executable, '-c', child, run['id']]
            first = subprocess.run(command + ['crash'], env=env, cwd=Path(__file__).resolve().parents[1], capture_output=True, text=True, timeout=30)
            self.assertEqual(first.returncode, 17, first.stderr[-1200:])
            self.assertEqual(db.run(run['id'])['status'], 'running')
            self.assertIsNone(db.run(run['id'])['result'])
            # Advance only the disposable lease clock instead of waiting the production timeout.
            db.write("UPDATE backintel.capability_jobs SET lease_until=now()-interval '1 second' WHERE job_id=%s AND state='running'", (run['job_id'],))
            resumed = subprocess.run(command + ['resume'], env=env, cwd=Path(__file__).resolve().parents[1], capture_output=True, text=True, timeout=30)
            self.assertEqual(resumed.returncode, 0, resumed.stderr[-1200:])
        completed = db.run(run['id'])
        self.assertEqual(completed['status'], 'succeeded', completed.get('error'))
        self.assertEqual(completed['result']['plan'], plan)
        self.assertEqual(completed['result']['mode'], 'fixture')
        self.assertEqual(db.usage(run['id'])['provider_calls'], 1)
        self.assertEqual(db.usage(run['id'])['provider_usd'], .001)
        events = db.query("SELECT count(*) AS n FROM backintel.analysis_events WHERE run_id=%s AND kind='completed'", (run['id'],), one=True)
        self.assertEqual(events['n'], 1)

    def test_saved_plan_revision_replay_and_permissions_without_ingestion(self):
        goal = service.create_goal(self.actor, **REQUEST)
        self.assertEqual(db.goal(goal['id'])['body']['objective'], REQUEST['objective'])
        self.assertIsNone(db.source('commerce')['latest_snapshot'])
        with self.assertRaisesRegex(PermissionError, 'budget'):
            service.submit(goal['id'], self.actor, operation='planning')
        goal = service.revise_goal(goal['id'], self.actor, budget_usd=.25)
        with self.assertRaises(PermissionError):
            service.submit(goal['id'], {'id': 'objective-analyst'}, operation='planning')
        run = service.submit(goal['id'], self.actor, operation='planning')
        self.assertIsNone(run['snapshot_id'])
        self.assertEqual(service.submit(goal['id'], self.actor, operation='planning')['id'], run['id'])
        plan = {'summary': 'Inspect the permitted invoice data before calculating signed values.',
                'data_needs': ['Invoice lines in the permitted source'],
                'steps': [{'action': 'discover', 'purpose': 'Identify invoice fields', 'expected_result': 'Confirmed field meanings'}],
                'assumptions': [], 'open_questions': ['Confirm timezone interpretation']}
        response = {'_backintel_fixture': True, 'output': [{'type': 'message', 'content': [{'type': 'output_text', 'text': json.dumps(plan)}]}]}
        with patch.object(analysis_agent, 'request', return_value=response) as request, \
             patch.object(jobs, '_run_worker', side_effect=jobs._execute_claimed):
            service.dispatch(run['id'])
            completed = db.run(run['id'])
            self.assertEqual(completed['status'], 'succeeded', completed.get('error'))
            self.assertEqual(completed['result']['plan'], plan)
            self.assertEqual(completed['result']['mode'], 'fixture')
            service.dispatch(run['id'])
            self.assertEqual(request.call_count, 1)
        shown = next(item for item in api.goals(self.actor) if item['id'] == goal['id'])
        self.assertEqual(shown['plan_run_id'], run['id'])
        self.assertEqual(shown['plan']['plan'], plan)
        revised = service.revise_goal(goal['id'], self.actor, question='Compare countries, preserving every invoice line.')
        self.assertGreater(revised['version'], goal['version'])
        shown = next(item for item in api.goals(self.actor) if item['id'] == goal['id'])
        self.assertIsNone(shown['plan'])
        with self.assertRaises(PermissionError):
            db.check_run(run['id'])
        with self.assertRaises((ValueError, PermissionError)):
            service.submit(goal['id'], self.actor, operation='analysis')
