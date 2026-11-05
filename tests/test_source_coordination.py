import copy
import json
import io
import os
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch

from runtime import source_coordination as coordination
from runtime.analysis_data import digest
from runtime.source_answer import execute_method


class CoordinationChecks(unittest.TestCase):
    def test_toolkit_uses_authenticated_principal(self):
        with patch('sys.argv', ['coordination', 'inspect', 'run']), patch.dict(os.environ, {}, clear=True), \
                patch.object(coordination, 'inspect') as inspect, redirect_stdout(io.StringIO()):
            self.assertEqual(coordination.main(), 1)
            inspect.assert_not_called()
        with patch('sys.argv', ['coordination', 'inspect', 'run']), \
                patch.dict(os.environ, {'BACKINTEL_ACCESS_TOKEN': 'test-token'}), \
                patch.object(coordination.db, 'principal', return_value={'id': 'permitted-owner'}) as principal, \
                patch.object(coordination, 'inspect', return_value={'status': 'succeeded'}) as inspect, \
                redirect_stdout(io.StringIO()):
            self.assertEqual(coordination.main(), 0)
            principal.assert_called_once_with('test-token')
            inspect.assert_called_once_with('run', {'id': 'permitted-owner'})

    def test_policy_requires_confirmed_objective_and_existing_allowance(self):
        goal = {'id': 'goal', 'version': 1, 'confirmed': True, 'paused': False, 'last_success': None,
                'body': {'objective': {'metric': 'GBP'}, 'budget_usd': 0.25}}
        policy = {'request_id': 'request', 'max_spend_usd': 0.25}
        binding = coordination.bind(goal, policy)
        self.assertEqual(binding, coordination.bind({**goal, 'last_success': 'new-answer'}, policy))
        for change in ({'confirmed': False}, {'paused': True}, {'body': {**goal['body'], 'budget_usd': 0}}):
            with self.assertRaises((ValueError, PermissionError)):
                coordination.bind({**goal, **change}, policy)
        with self.assertRaises(ValueError):
            coordination.bind(goal, {**policy, 'max_model_calls': 7})

    def test_interruption_reuses_request_context_and_retains_accepted_contribution(self):
        steps, network, cached = {}, [], {}
        attempts = 0

        def request(identity, index, inputs, **options):
            key = digest([index, inputs, options['tool_specs'], options['tool_choice']])
            options['on_request'](key)
            if key not in cached:
                network.append(key)
                output = ([{'type': 'function_call', 'name': 'check_finding', 'arguments': '{}', 'call_id': 'call'}]
                          if index % 2 == 0 else [{'type': 'message', 'content': [{'type': 'output_text', 'text': json.dumps({
                              'decision': 'accept', 'evidence_id': 'check', 'explanation': 'Matched source.', 'conflicts': []})}]}])
                cached[key] = {'output': output, '_backintel_fixture': True}
            return copy.deepcopy(cached[key])

        def tool():
            nonlocal attempts
            attempts += 1
            if attempts == 1:
                raise InterruptedError('Injected interruption after the provider response')
            return {'evidence_id': 'check', 'status': 'passed', 'conflicts': []}

        def save(identity, key, kind, body):
            return steps.setdefault(key, copy.deepcopy(body))

        def update_state(query, args):
            steps[args[1]] = copy.deepcopy(args[3].obj)

        self.enterContext(patch.object(coordination.db, 'write', side_effect=update_state))

        with patch.object(coordination.db, 'check_run'), patch.object(coordination.db, 'step', side_effect=lambda identity, key: copy.deepcopy(steps.get(key))), \
             patch.object(coordination.db, 'save_step', side_effect=save), patch.object(coordination.db, 'event'), \
             patch.object(coordination.db, 'evidence', return_value='evidence'), patch.object(coordination.agent, 'request', side_effect=request):
            args = ('run', 2, {'question': 'Q'}, {}, coordination.ReviewDecision, 'check_finding', tool,
                    lambda value: coordination.validate_review(value, steps['coord-tool-checking']['value']))
            with self.assertRaises(InterruptedError):
                coordination.specialist(*args)
            self.assertEqual(len(network), 1)
            result = coordination.specialist(*args)
            self.assertEqual(len(network), 2)
            self.assertEqual(coordination.specialist(*args), result)
            self.assertEqual(len(network), 2)
            self.assertEqual(steps['coord-agent-checking']['status'], 'accepted')
            with self.assertRaises(coordination.ReviewRequired):
                coordination.specialist('run', 2, {'question': 'changed'}, *args[3:])

    def test_specialist_cannot_request_another_roles_actions(self):
        self.enterContext(patch.object(coordination.db, 'write'))
        response = {'output': [{'type': 'function_call', 'name': 'grant_access', 'arguments': '{}', 'call_id': 'call'}]}
        with patch.object(coordination.db, 'step', return_value=None), patch.object(coordination.db, 'save_step'), \
             patch.object(coordination.db, 'event'), patch.object(coordination.agent, 'request', return_value=response):
            with self.assertRaises(PermissionError):
                coordination.specialist('run', 0, {}, {}, coordination.ReviewDecision, 'inspect_data',
                                       lambda: self.fail('Forbidden action reached a tool'), lambda value: value)

    def test_independent_check_rejects_changed_amounts_and_group_findings(self):
        method = {'schema_name': 'retail', 'table_name': 'lines', 'quantity_field': 'units', 'unit_price_field': 'price',
                  'invoice_field': 'invoice', 'product_field': 'product', 'country_field': 'country', 'date_field': 'at',
                  'currency': 'GBP', 'cancellation_prefix': 'C', 'rationale': 'Test method'}
        page = {'schema': 'retail', 'table': 'lines', 'identity_column': 'id', 'unresolved': [],
                'columns': ['id', 'units', 'price', 'invoice', 'product', 'country', 'at'],
                'rows': [[1, '2', '3.25', '001', 'A', 'UK', '2020-12-01T00:00:00'],
                         [2, '-1', '3.25', 'C002', 'A', 'UK', '2020-12-02T00:00:00'],
                         [3, '1', '3.25', '003', 'B', 'FR', '2020-12-03T00:00:00']]}
        calculation = execute_method(method, [page], 3)
        collection = {'coverage': {'expected_rows': 3}, 'inputs': [{'schema': 'retail', 'table': 'lines', 'raw_input_id': 'raw'}]}
        interpretation = {'interpretation': {'tables': [{'schema_name': 'retail', 'table_name': 'lines',
            'fields': [{'name': 'at', 'date_format': 'iso'}]}]}}
        with patch.object(coordination.db, 'run', return_value={'goal_id': 'goal', 'owner': 'owner'}), \
             patch.object(coordination.db, 'goal', return_value={'body': {'objective': {'limits': {'timeout_seconds': 60}}}}), \
             patch.object(coordination.db, 'check_run'), patch.object(coordination.db, 'evidence', return_value='check'), \
                patch('runtime.source_inputs.retained_input', return_value={'payload': json.dumps({
                    key: page[key] for key in ('columns', 'identity_column', 'rows')}).encode()}):
            report = coordination.independent_check('run', calculation, collection, interpretation)
            self.assertEqual(report['status'], 'passed')
            decision = {'decision': 'accept', 'evidence_id': 'check', 'conflicts': [], 'explanation': 'Checked.'}
            coordination.validate_review(decision, report)
            for variant in ['amount', 'group', 'extra']:
                changed = copy.deepcopy(calculation)
                if variant == 'amount':
                    changed['totals']['net_invoice_value'] = '999'
                elif variant == 'group':
                    changed['dimensions'][0]['groups'][0]['row_count'] = 99
                else:
                    changed['dimensions'].append(copy.deepcopy(changed['dimensions'][0]))
                rejected = coordination.independent_check('run', changed, collection, interpretation)
                with self.assertRaises(coordination.ReviewRequired):
                    coordination.validate_review(decision, rejected)
            with self.assertRaises(coordination.ReviewRequired):
                coordination.validate_review({**decision, 'evidence_id': 'invented'}, report)


if __name__ == '__main__':
    unittest.main()
