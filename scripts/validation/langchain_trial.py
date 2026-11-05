"""Real LangChain tool execution with explicitly scripted model decisions and zero paid calls."""
import json
from importlib import metadata
from unittest.mock import patch

import httpx
from langchain.agents import create_agent
from langchain.agents.middleware import ModelCallLimitMiddleware, ToolCallLimitMiddleware
from langchain_core.language_models.fake_chat_models import FakeMessagesListChatModel
from langchain_core.messages import AIMessage, ToolMessage, messages_to_dict

from runtime.langchain_tools import saved_workflow_tool


class ScriptedToolModel(FakeMessagesListChatModel):
    """A test response sequence, not a live language model or a reasoning-quality test."""
    def bind_tools(self, tools, **kwargs):
        return self


def scripted_agent(workflow_tool, *, tool_name='run_backintel_workflow'):
    model = ScriptedToolModel(responses=[
        AIMessage(content='', tool_calls=[{'name': tool_name, 'args': {}, 'id': 'scripted-retail-call'}]),
        AIMessage(content='Scripted trial ended. Inspect the BackIntel tool receipt for the actual outcome.')])
    return create_agent(model=model, tools=[workflow_tool], middleware=[
        ModelCallLimitMiddleware(run_limit=2), ToolCallLimitMiddleware(run_limit=1)],
        system_prompt='Use only the approved BackIntel workflow. Keep failed or incomplete results explicit.')


def tool_receipt(agent, question):
    result = agent.invoke({'messages': [{'role': 'user', 'content': question}]}, {'recursion_limit': 32})
    receipts = [message for message in result['messages'] if isinstance(message, ToolMessage)]
    assert len(receipts) == 1, 'Expected one bounded tool invocation'
    return result, receipts[0]


def check_langchain(actor, source, package, client, output):
    from runtime import analysis_store as db
    from runtime.workflow_updates import collection_for

    question = package['body']['question']
    baseline = db.run(db.goal(source['goal_id'])['last_success'])
    collection = collection_for(baseline)
    assert collection is not None and collection['status'] == 'succeeded'
    assert collection['result']['coverage']['expected_rows'] == 541909
    input_ref = collection['id']
    workflow = saved_workflow_tool(client, package['version'], input_ref=input_ref, wait_seconds=1200)
    dropped = {}
    original_request = client.request

    def lose_admission_response(method, path, **kwargs):
        response = original_request(method, path, **kwargs)
        response.raise_for_status()
        dropped['id'] = response.json()['id']
        raise httpx.ReadTimeout('Simulated lost client response after actual admission', request=response.request)

    print('LangChain trial: simulate lost admission response, then recover the real workflow.', flush=True)
    with patch.object(client, 'request', side_effect=lose_admission_response):
        _, interrupted = tool_receipt(scripted_agent(workflow), question)
    assert interrupted.status == 'error' and 'interrupted' in interrupted.content
    # Recreate the agent and tool as a restarted client would; recovery belongs to BackIntel.
    recovered_agent = scripted_agent(saved_workflow_tool(client, package['version'], input_ref=input_ref, wait_seconds=1200))
    state, accepted = tool_receipt(recovered_agent, question)
    result = accepted.artifact
    (output/'langchain-messages.json').write_text(json.dumps(messages_to_dict(state['messages']), default=str, indent=2))
    (output/'langchain-result.json').write_text(json.dumps(result, default=str, indent=2))
    assert accepted.status == 'success' and result['status'] == 'succeeded', accepted.content
    assert result['id'] == dropped['id'], 'Recovery created another run'
    native = db.run(result['id'])
    assert result['result'] == native['result'], 'Framework changed the checked answer'
    calculation = result['result']['calculation']
    expected = baseline['result']['calculation']
    for field in ('totals', 'dimensions', 'currency', 'period_start', 'period_end', 'coverage'):
        assert calculation[field] == expected[field], f'Calculation differs: {field}'
    assert result['result']['coverage'] == result['coverage']
    before_replay = db.query('SELECT id FROM backintel.analysis_runs ORDER BY id')
    _, replay = tool_receipt(scripted_agent(workflow), question)
    assert replay.artifact == result, 'Replay changed the retained result'
    assert db.query('SELECT id FROM backintel.analysis_runs ORDER BY id') == before_replay
    accepted_goal = db.goal(source['goal_id'])
    print('LangChain trial: accepted answer recovered; verify denied and unsupported requests.', flush=True)
    db.write('UPDATE backintel.analysis_source_connections SET enabled=false WHERE id=%s',
             (package['body']['connection']['source_ref'],))
    try:
        _, denied = tool_receipt(scripted_agent(workflow), question)
        assert denied.status == 'error' and 'Access denied' in denied.content
    finally:
        db.write('UPDATE backintel.analysis_source_connections SET enabled=true WHERE id=%s',
                 (package['body']['connection']['source_ref'],))
    _, unsupported = tool_receipt(scripted_agent(workflow, tool_name='change_source_records'), question)
    assert unsupported.status == 'error' and 'not a valid tool' in unsupported.content
    assert db.goal(source['goal_id']) == accepted_goal, 'Denied request changed the accepted answer'
    assert db.query('SELECT id FROM backintel.analysis_runs ORDER BY id') == before_replay
    receipt = {'status': 'passed', 'scope': 'local working tree; real historical retail workflow; scripted model decisions',
               'frameworks': {name: metadata.version(name) for name in ('langchain', 'langchain-core', 'langgraph')},
               'workflow_version': package['version'], 'run_id': result['id'],
               'baseline_run_id': baseline['id'], 'input_ref': input_ref,
               'coverage': result['coverage'], 'totals': calculation['totals'],
               'model_calls': 0, 'provider_cost_usd': 0,
               'checks': ['actual LangChain agent and authenticated tool', 'complete source calculation unchanged',
                          'full result and evidence retained as artifact', 'lost response recovered by a fresh agent',
                          'replay reused the same run', 'revoked source access denied', 'unsupported operation rejected'],
               'limits': ['model decisions and final agent prose are scripted', 'no live model quality or cost evaluation',
                          'local reference only; independent installation and release remain open']}
    (output/'workflow-package.json').write_text(json.dumps(package, default=str, indent=2))
    return receipt
