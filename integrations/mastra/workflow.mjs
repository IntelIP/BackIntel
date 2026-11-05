import { createTool } from '@mastra/core/tools';
import { z } from 'zod';
import { setTimeout as delay } from 'node:timers/promises';

// Credentials, workflow selection, and full receipts belong to the application.
export function savedWorkflowTool({ baseUrl, authorization, workflowVersion, inputRef,
  receipts, waitSeconds = 300, fetchImpl = globalThis.fetch }) {
  const identity = /^[0-9a-f]{64}$/;
  if (typeof workflowVersion !== 'string' || !identity.test(workflowVersion) ||
      (inputRef != null && (typeof inputRef !== 'string' || !identity.test(inputRef)))) {
    throw new Error('Use complete saved workflow and permitted collection identities');
  }
  const base = new URL(baseUrl);
  if (base.protocol !== 'https:' && !(base.protocol === 'http:' &&
      ['127.0.0.1', 'localhost', '[::1]'].includes(base.hostname))) {
    throw new Error('Use HTTPS, or a local loopback server for the trial');
  }
  if (base.username || base.password) throw new Error('Keep credentials outside the URL');
  if (!Number.isFinite(waitSeconds) || waitSeconds < 0 || waitSeconds > 1800) {
    throw new Error('Wait time must be between zero and 1800 seconds');
  }
  if (!Array.isArray(receipts)) throw new Error('Supply an application-owned receipt list');

  async function request(method, path, body) {
    let response;
    try {
      response = await fetchImpl(new URL(path, base), {
        method, redirect: 'error', signal: AbortSignal.timeout(30_000),
        headers: { Authorization: authorization, 'Content-Type': 'application/json' },
        ...(body === undefined ? {} : { body: JSON.stringify(body) }),
      });
    } catch {
      throw new Error('BackIntel connection interrupted. Retry this same tool to recover the existing run.');
    }
    if (!response.ok) {
      const reason = [401, 403].includes(response.status) ? 'Access denied' : 'Request rejected';
      throw new Error(`${reason} by BackIntel (HTTP ${response.status}); no answer accepted by this tool.`);
    }
    let result;
    try { result = await response.json(); }
    catch { throw new Error('BackIntel returned an invalid response; no answer is verified.'); }
    if (!result || typeof result !== 'object' || typeof result.id !== 'string' || !identity.test(result.id) ||
        !['queued', 'running', 'succeeded', 'failed', 'cancelled', 'partial'].includes(result.status)) {
      throw new Error('BackIntel returned an unsupported run response; no answer is verified.');
    }
    return result;
  }

  return createTool({
    id: 'run_backintel_workflow',
    description: 'Run or resume the approved retail workflow. Only succeeded means an accepted answer. Queued or running is unfinished. Cannot change the objective, source, permissions, or spending limits.',
    inputSchema: z.object({}).strict(),
    execute: async () => {
      let body = await request('POST', `/api/v1/workflows/${workflowVersion}/runs`,
        inputRef == null ? {} : { input_ref: inputRef });
      const runId = body.id;
      const deadline = performance.now() + waitSeconds * 1000;
      // Always authorize the result endpoint, even when admission reuses a finished run.
      do {
        body = await request('GET', `/api/v1/runs/${runId}`);
        if (body.id !== runId) throw new Error('BackIntel returned a different run; no answer is verified.');
        if (!['queued', 'running'].includes(body.status) || performance.now() >= deadline) break;
        await delay(Math.min(500, Math.max(0, deadline - performance.now())));
      } while (performance.now() < deadline);
      const content = { run_id: runId, workflow_version: workflowVersion, status: body.status };
      if (body.status === 'succeeded') {
        for (const key of ['summary', 'findings', 'coverage', 'evidence_id', 'usage', 'limitations']) {
          if (body.result && key in body.result) content[key] = body.result[key];
        }
        content.totals = body.result?.calculation?.totals ?? null;
      } else {
        content.message = ['queued', 'running'].includes(body.status)
          ? 'The workflow is unfinished; retry the same tool to recover it.'
          : 'The workflow did not succeed. Inspect the retained run; no new answer is accepted.';
        if (body.error) content.reason = body.error;
      }
      receipts.push(body);
      return content;
    },
  });
}
