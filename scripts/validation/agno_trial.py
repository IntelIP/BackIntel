"""Actual Agno agent execution with scripted decisions; never calls a model provider."""
from dataclasses import dataclass
from importlib import metadata
from unittest.mock import patch

import httpx
from agno.agent import Agent
from agno.models.base import Model
from agno.models.response import ModelResponse

from runtime.agno_tools import saved_workflow_tool


@dataclass
class ScriptedToolModel(Model):
    id: str = 'scripted-backintel-trial'
    provider: str = 'local-scripted'
    tool_name: str = 'run_backintel_workflow'
    calls: int = 0

    def invoke(self, *args, **kwargs):
        self.calls += 1
        assert self.calls <= 2, 'Scripted model exceeded its two-response limit'
        if self.calls == 1:
            return ModelResponse(role='assistant', tool_calls=[{
                'id': 'scripted-retail-call', 'type': 'function',
                'function': {'name': self.tool_name, 'arguments': '{}'}}])
        return ModelResponse(role='assistant', content='Scripted trial ended. Inspect the BackIntel receipt for the actual outcome.')

    def _parse_provider_response(self, response, **kwargs):
        return response

    def _parse_provider_response_delta(self, response):
        raise NotImplementedError('This fixture checks synchronous, non-streaming runs')

    async def ainvoke(self, *args, **kwargs):
        raise NotImplementedError('This fixture checks synchronous, non-streaming runs')

    def invoke_stream(self, *args, **kwargs):
        raise NotImplementedError('This fixture checks synchronous, non-streaming runs')

    async def ainvoke_stream(self, *args, **kwargs):
        raise NotImplementedError('This fixture checks synchronous, non-streaming runs')


def invoke_agno(client, version, input_ref, question, *, tool_name='run_backintel_workflow', lose_response=False, wait_seconds=1200):
    receipts = []
    workflow = saved_workflow_tool(client, version, receipts=receipts, input_ref=input_ref, wait_seconds=wait_seconds)
    agent = Agent(model=ScriptedToolModel(tool_name=tool_name), tools=[workflow], tool_call_limit=1,
                  telemetry=False, retries=0,
                  instructions='Use only the approved BackIntel workflow. Keep failed or incomplete results explicit.')
    original_request = client.request
    dropped = {}

    def request(method, path, **kwargs):
        response = original_request(method, path, **kwargs)
        response.raise_for_status()
        dropped['id'] = response.json()['id']
        raise httpx.ReadTimeout('Simulated lost admission response', request=response.request)

    if lose_response:
        with patch.object(client, 'request', side_effect=request):
            result = agent.run(question)
    else:
        result = agent.run(question)
    messages = [message.to_dict() for message in result.messages]
    tool_messages = [message for message in messages if message['role'] == 'tool']
    assert len(tool_messages) == 1, 'Expected one bounded tool response'
    message = tool_messages[0]
    return {'status': 'success' if receipts else 'error', 'content': message['content'],
            'artifact': receipts[0] if receipts else None, 'messages': messages, 'dropped_id': dropped.get('id')}


def check_agno(actor, source, package, client, output):
    from scripts.validation.framework_trial import check_framework
    return check_framework('agno', {'agno': metadata.version('agno')}, invoke_agno,
                           source, package, client, output)
