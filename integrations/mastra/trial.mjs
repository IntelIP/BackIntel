// Real Mastra agent loop; every model decision is scripted and makes no provider request.
import { Agent } from '@mastra/core/agent';
import { pathToFileURL } from 'node:url';
import { savedWorkflowTool } from './workflow.mjs';

export async function invokeMastra({ question, toolName = 'run_backintel_workflow',
  loseResponse = false, fetchImpl = globalThis.fetch, ...options }) {
  const receipts = [];
  let droppedId = null;
  const workflow = savedWorkflowTool({ ...options, receipts, fetchImpl: async (url, init) => {
    const response = await fetchImpl(url, init);
    if (loseResponse && init.method === 'POST' && response.ok) {
      droppedId = (await response.json()).id;
      throw new Error('Simulated lost admission response');
    }
    return response;
  } });
  let calls = 0;
  function nextResponse() {
    calls += 1;
    if (calls > 2) throw new Error('Scripted model exceeded its two-response limit');
    return calls === 1
      ? { content: [{ type: 'tool-call', toolCallId: 'scripted-retail-call', toolName, input: '{}' }], finishReason: 'tool-calls' }
      : { content: [{ type: 'text', text: 'Scripted trial ended. Inspect the BackIntel receipt for the actual outcome.' }], finishReason: 'stop' };
  }
  const usage = { inputTokens: 0, outputTokens: 0, totalTokens: 0 };
  const model = {
    specificationVersion: 'v2', provider: 'local-scripted', modelId: 'scripted-backintel-trial', supportedUrls: {},
    doGenerate: async () => ({ ...nextResponse(), usage, warnings: [] }),
    doStream: async () => {
      const response = nextResponse();
      return { stream: new ReadableStream({ start(controller) {
        controller.enqueue({ type: 'stream-start', warnings: [] });
        for (const content of response.content) {
          if (content.type === 'tool-call') controller.enqueue(content);
          else {
            controller.enqueue({ type: 'text-start', id: 'closing' });
            controller.enqueue({ type: 'text-delta', id: 'closing', delta: content.text });
            controller.enqueue({ type: 'text-end', id: 'closing' });
          }
        }
        controller.enqueue({ type: 'finish', usage, finishReason: response.finishReason });
        controller.close();
      } }) };
    },
  };
  const agent = new Agent({ id: 'backintel-scripted-trial', name: 'BackIntel scripted trial',
    instructions: 'Use only the approved BackIntel workflow. Keep failed or incomplete results explicit.',
    model, tools: { run_backintel_workflow: workflow }, maxRetries: 0 });
  const result = await agent.generate(question, { maxSteps: 2 });
  const messages = result.messages;
  const invocations = messages.flatMap(message => message.content.parts ?? [])
    .filter(part => part.type === 'tool-invocation').map(part => part.toolInvocation);
  if (invocations.length !== 1) throw new Error('Expected one bounded tool response');
  return { status: receipts.length ? 'success' : 'error',
    content: JSON.stringify(invocations[0]), artifact: receipts[0] ?? null,
    messages, dropped_id: droppedId, scripted_model_responses: calls };
}

if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
  let input = '';
  for await (const chunk of process.stdin) input += chunk;
  const result = await invokeMastra(JSON.parse(input));
  process.stdout.write(`BACKINTEL_TRIAL_RESULT=${JSON.stringify(result)}\n`);
}
