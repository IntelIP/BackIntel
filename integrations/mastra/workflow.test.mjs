import assert from 'node:assert/strict';
import test from 'node:test';
import { invokeMastra } from './trial.mjs';
import { savedWorkflowTool } from './workflow.mjs';

test('real Mastra agent retains receipts, hides credentials, and rejects denied or unknown operations', async () => {
  const receipt = { id: 'b'.repeat(64), status: 'succeeded', result: {
    calculation: { totals: { net_invoice_value: '12.30' } }, evidence_id: 'source-evidence' } };
  const requests = [];
  let status = 200;
  const options = { baseUrl: 'http://127.0.0.1:2028', authorization: 'Bearer test-only-credential',
    workflowVersion: 'a'.repeat(64), inputRef: 'd'.repeat(64), question: 'Run the saved workflow.',
    fetchImpl: async (url, init) => {
      requests.push({ url, init });
      assert.equal(init.headers.Authorization, 'Bearer test-only-credential');
      assert.equal(init.redirect, 'error');
      return Response.json(receipt, { status });
    } };
  const accepted = await invokeMastra(options);
  assert.deepEqual(accepted.artifact, receipt);
  assert.match(accepted.content, /12.30/);
  assert.equal(accepted.scripted_model_responses, 2);
  assert.deepEqual(requests.map(request => request.init.method), ['POST', 'GET']);
  assert.deepEqual(JSON.parse(requests[0].init.body), { input_ref: 'd'.repeat(64) });
  assert.ok(!JSON.stringify(accepted).includes('test-only-credential'));
  const tool = savedWorkflowTool({ ...options, receipts: [] });
  assert.equal(tool.inputSchema.safeParse({ authorization: 'override' }).success, false);
  receipt.status = 'queued';
  assert.match((await invokeMastra({ ...options, waitSeconds: 0 })).content, /unfinished/);
  status = 403;
  const denied = await invokeMastra(options);
  assert.equal(denied.status, 'error');
  assert.match(denied.content, /Access denied/);
  const before = requests.length;
  const unsupported = await invokeMastra({ ...options, toolName: 'change_source_records' });
  assert.equal(unsupported.status, 'error');
  assert.match(unsupported.content, /not found|not available|not a valid tool|no such tool/i);
  assert.equal(requests.length, before);
  assert.throws(() => savedWorkflowTool({ ...options, receipts: [], baseUrl: 'http://remote.example' }), /HTTPS/);
  status = 200;
  receipt.id = ['b'.repeat(64)];
  const malformed = await invokeMastra(options);
  assert.equal(malformed.status, 'error');
  assert.match(malformed.content, /unsupported run response/);
});
