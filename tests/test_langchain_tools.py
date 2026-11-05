import json
import unittest

import httpx

from runtime.langchain_tools import saved_workflow_tool
from scripts.validation.langchain_trial import scripted_agent, tool_receipt


class LangChainIntegrationChecks(unittest.TestCase):
    def test_real_agent_preserves_the_tool_artifact_and_keeps_credentials_out_of_arguments(self):
        receipt = {'id': 'b' * 64, 'status': 'succeeded', 'result': {'coverage': {'processed_rows': 3},
                   'calculation': {'totals': {'net_invoice_value': '12.30'}}, 'evidence_id': 'source-evidence'}}
        requests = []

        def handler(request):
            requests.append(request)
            self.assertEqual(request.headers['authorization'], 'Bearer test-only-credential')
            return httpx.Response(202, json=receipt)

        with httpx.Client(base_url='http://127.0.0.1:2028', headers={'Authorization': 'Bearer test-only-credential'},
                          transport=httpx.MockTransport(handler)) as client:
            workflow = saved_workflow_tool(client, 'a' * 64, input_ref='d' * 64)
            state, message = tool_receipt(scripted_agent(workflow), 'Run the approved workflow.')
        self.assertEqual(message.artifact, receipt)
        self.assertEqual(json.loads(message.content)['totals'], {'net_invoice_value': '12.30'})
        self.assertEqual(workflow.args_schema.model_json_schema()['properties'], {})
        self.assertNotIn('test-only-credential', str(state))
        self.assertEqual([request.method for request in requests], ['POST', 'GET'])
        self.assertEqual(json.loads(requests[0].content), {'input_ref': 'd' * 64})

    def test_denied_and_unsupported_requests_are_errors_without_an_answer(self):
        requests = []

        def handler(request):
            requests.append(request)
            return httpx.Response(403, json={'detail': 'Source access denied'})

        with httpx.Client(base_url='http://localhost:2028', transport=httpx.MockTransport(handler)) as client:
            workflow = saved_workflow_tool(client, 'a' * 64)
            _, denied = tool_receipt(scripted_agent(workflow), 'Run the workflow.')
            _, unsupported = tool_receipt(scripted_agent(workflow, tool_name='delete_records'), 'Delete records.')
        self.assertEqual(denied.status, 'error')
        self.assertIn('Access denied', denied.content)
        self.assertIsNone(denied.artifact)
        self.assertEqual(unsupported.status, 'error')
        self.assertEqual(len(requests), 1)

    def test_incomplete_runs_are_explicit_and_unsafe_transport_is_rejected(self):
        receipt = {'id': 'c' * 64, 'status': 'queued'}
        with httpx.Client(base_url='http://localhost:2028',
                          transport=httpx.MockTransport(lambda request: httpx.Response(202, json=receipt))) as client:
            _, message = tool_receipt(scripted_agent(saved_workflow_tool(client, 'a' * 64, wait_seconds=0)), 'Run it.')
        content = json.loads(message.content)
        self.assertEqual(content['status'], 'queued')
        self.assertIn('unfinished', content['message'])
        receipt.update(status='partial', error='A newer source answer is already accepted.')
        with httpx.Client(base_url='http://localhost:2028',
                          transport=httpx.MockTransport(lambda request: httpx.Response(202, json=receipt))) as client:
            _, message = tool_receipt(scripted_agent(saved_workflow_tool(client, 'a' * 64)), 'Run it.')
        self.assertEqual(json.loads(message.content)['reason'], receipt['error'])
        for url, redirects in [('http://remote.example', False), ('https://remote.example', True)]:
            with httpx.Client(base_url=url, follow_redirects=redirects) as client, self.assertRaises(ValueError):
                saved_workflow_tool(client, 'a' * 64)


if __name__ == '__main__':
    unittest.main()
