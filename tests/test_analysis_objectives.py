"""Connected-goal contracts do not silently become legacy dataset analyses."""
import copy
import json
from pathlib import Path
import unittest
from unittest.mock import MagicMock, patch

from pydantic import ValidationError

from runtime import analysis_api as api, analysis_service as service
from runtime.analysis_objectives import normalize_objective
from runtime import analysis_planning as planning


REQUEST = json.loads((Path(__file__).resolve().parents[1] / 'config/reference_scenarios/online_retail.json').read_text())['request']


class ObjectiveChecks(unittest.TestCase):
    def test_planning_uses_saved_objective_without_source_tools_and_labels_fixtures(self):
        objective = normalize_objective(REQUEST['objective'])
        goal = {'body': {'question': REQUEST['question'], 'objective': objective}}
        run = {'goal_version': 3, 'body': {'operation': 'planning', 'question': 'Explain cancellation checks more clearly'}}
        plan = {'summary': 'Check invoice values and cancellation effects.',
                'data_needs': ['Invoice lines from the permitted schema'],
                'steps': [{'action': 'check', 'purpose': 'Preserve cancellations', 'expected_result': 'Signed values reconciled'}],
                'assumptions': [], 'open_questions': ['Source timezone is unknown']}
        reply = {'_backintel_fixture': True, 'output': [{'type': 'message', 'content': [{'type': 'output_text', 'text': json.dumps(plan)}]}]}
        with patch.object(planning.db, 'check_run', return_value=(run, goal)), \
             patch.object(planning.db, 'usage', return_value={}), patch.object(planning.db, 'evidence', return_value='evidence'), \
             patch.object(planning.agent, 'request', return_value=reply) as request:
            result = planning.propose('run')
        self.assertEqual(result['plan'], plan)
        self.assertEqual(result['mode'], 'fixture')
        self.assertEqual(result['goal_version'], 3)
        self.assertEqual(request.call_args.kwargs['tool_specs'], [])
        sent = json.loads(request.call_args.args[2][1]['content'])
        self.assertEqual(sent['objective'], objective)
        self.assertEqual(sent['revision_request'], run['body']['question'])
        self.assertNotIn('9747747', json.dumps(sent))

    def test_planning_check_keeps_access_revision_and_cancellation_controls(self):
        from runtime import analysis_store as db
        objective = normalize_objective(REQUEST['objective'])
        goal = {'domain': 'commerce', 'confirmed': False, 'paused': False, 'version': 3, 'body': {'objective': objective}}
        run = {'goal_id': 'goal', 'owner': 'manager', 'goal_version': 3, 'snapshot_id': None, 'job_id': 'job', 'body': {'operation': 'planning'}}
        with patch.object(db, 'run', return_value=run), patch.object(db, 'goal', return_value=goal), \
             patch.object(db, 'authorize') as authorize, patch.object(db, 'source') as source, \
             patch.object(db, 'query', return_value={'cancel_requested': False}) as query:
            self.assertEqual(db.check_run('run'), (run, goal))
            self.assertEqual(authorize.call_args.args[2], ('manager',))
            source.assert_not_called()
            goal['version'] = 4
            with self.assertRaises(PermissionError):
                db.check_run('run')
            goal['version'] = 3
            query.return_value = {'cancel_requested': True}
            with self.assertRaises(InterruptedError):
                db.check_run('run')

    def test_business_contract_rejects_unsafe_or_ambiguous_structure(self):
        objective = REQUEST['objective']
        self.assertEqual(api.GoalInput.model_validate(REQUEST).objective.source_ref, 'online-retail-postgres')
        self.assertIsNone(normalize_objective(objective)['target'])
        changes = [
            {'source_ref': 'postgresql://user:secret@host/db'},
            {'allowed_actions': ['write']},
            {'allowed_schemas': ['retail_raw; DROP TABLE invoices']},
            {'metric': '   '},
            {'expected_checks': []},
            {'pipeline_code': 'arbitrary code'},
            {'limits': {'max_source_bytes': True, 'timeout_seconds': 30}},
            {'limits': {'max_source_bytes': 100, 'timeout_seconds': 901}},
        ]
        for change in changes:
            with self.subTest(change=change), self.assertRaises(ValidationError):
                normalize_objective(objective | change)

    def test_saved_objective_and_version_share_meaning_and_default_to_no_spend(self):
        connection = MagicMock()
        connection.__enter__.return_value = connection
        with patch.object(service.db, 'authorize'), patch.object(service.db, 'source'), \
             patch.object(service.db, 'connect', return_value=connection), patch.object(service.db, 'goal', return_value={}):
            service.create_goal({'id': 'manager'}, **REQUEST)
        created = connection.execute.call_args_list[0].args[1][3].obj
        version = connection.execute.call_args_list[1].args[1][1].obj
        self.assertEqual(created, version)
        self.assertEqual(created['objective'], normalize_objective(REQUEST['objective']))
        self.assertEqual(created['definitions']['metric'], REQUEST['objective']['metric'])
        self.assertEqual(created['budget_usd'], 0)

    def test_revision_invalidates_old_plan_and_confirmation(self):
        objective = normalize_objective(REQUEST['objective'])
        goal = {'id': 'goal', 'domain': 'commerce', 'version': 2, 'paused': False, 'confirmed': True,
                'body': {'question': REQUEST['question'], 'objective': objective, 'plan': {'steps': ['old']}, 'budget_usd': 0}}
        revised = copy.deepcopy(objective)
        revised['period'] = '2010-12-01 through 2010-12-31'
        connection = MagicMock()
        connection.__enter__.return_value = connection
        connection.execute.return_value.rowcount = 1
        with patch.object(service.db, 'goal', return_value=goal), patch.object(service.db, 'authorize'), \
             patch.object(service.db, 'connect', return_value=connection):
            service.revise_goal('goal', {'id': 'manager'}, objective=revised)
        update = connection.execute.call_args_list[1].args[1]
        self.assertEqual(update[0].obj['objective']['period'], revised['period'])
        self.assertNotIn('plan', update[0].obj)
        self.assertEqual(update[1], 3)
        self.assertFalse(update[3])

    def test_connected_objective_cannot_run_against_legacy_clothing_source(self):
        goal = {'id': 'goal', 'domain': 'commerce', 'body': {'objective': normalize_objective(REQUEST['objective'])}}
        connection = MagicMock()
        connection.cursor.return_value.__enter__.return_value.fetchone.return_value = goal
        with patch.object(service.db, 'source', return_value={'body': {'terms_acknowledged': True}}), \
             patch.object(service.db, 'authorize') as authorize, \
             self.assertRaisesRegex(ValueError, 'connected workflow'):
            service._admit_run(connection, goal, {'id': 'manager'})
        authorize.assert_called_once()
        self.assertEqual(api.GoalUpdate(budget_usd=0).budget_usd, 0)


if __name__ == '__main__':
    unittest.main()
