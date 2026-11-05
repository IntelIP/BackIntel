"""One real Agno agent check for receipts, permissions, and unfinished answers."""
import json
import unittest

import httpx

from runtime.agno_tools import saved_workflow_tool
from scripts.validation.agno_trial import invoke_agno


class AgnoIntegrationChecks(unittest.TestCase):
    def test_real_agent_preserves_receipts_and_enforces_the_tool_boundary(self):
        receipt = {'id': 'b' * 64, 'status': 'succeeded', 'result': {'coverage': {'processed_rows': 3},
                   'calculation': {'totals': {'net_invoice_value': '12.30'}}, 'evidence_id': 'source-evidence'}}
        requests = []
        status = 200

        def handler(request):
            requests.append(request)
            self.assertEqual(request.headers['authorization'], 'Bearer test-only-credential')
            return httpx.Response(status, json=receipt)

        with httpx.Client(base_url='http://127.0.0.1:2028', headers={'Authorization': 'Bearer test-only-credential'},
                          transport=httpx.MockTransport(handler)) as client:
            result = invoke_agno(client, 'a' * 64, 'd' * 64, 'Run the workflow.')
            self.assertEqual(result['artifact'], receipt)
            self.assertEqual(json.loads(result['content'])['totals'], {'net_invoice_value': '12.30'})
            self.assertEqual([request.method for request in requests], ['POST', 'GET'])
            self.assertEqual(json.loads(requests[0].content), {'input_ref': 'd' * 64})
            self.assertNotIn('test-only-credential', str(result))
            tool = saved_workflow_tool(client, 'a' * 64, receipts=[])
            tool.process_entrypoint()
            self.assertEqual(tool.parameters['properties'], {})
            receipt['status'] = 'queued'
            result = invoke_agno(client, 'a' * 64, None, 'Run it.', wait_seconds=0)
            self.assertIn('unfinished', result['content'])
            status = 403
            denied = invoke_agno(client, 'a' * 64, None, 'Run it.')
            self.assertEqual(denied['status'], 'error')
            self.assertIn('Access denied', denied['content'])
            before = len(requests)
            unsupported = invoke_agno(client, 'a' * 64, None, 'Run it.', tool_name='change_source_records')
            self.assertEqual(unsupported['status'], 'error')
            self.assertEqual(len(requests), before)


if __name__ == '__main__':
    unittest.main()
