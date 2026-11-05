"""Disposable S-33 checks; simulated decisions and injected faults stay explicit."""
import copy
import json
import os
import subprocess
import sys
from decimal import Decimal
from functools import partial
from pathlib import Path
from unittest.mock import patch

from runtime import analysis_agent as agent, analysis_service as service, analysis_store as db
from runtime import source_coordination as coordination
from runtime.analysis_data import digest
from runtime.jobs import execute as execute_job


def validation_handler(store, payload, *, package=None, reject_finding=False):
    """Install fault injection inside the existing isolated job process."""
    original_request = agent.request
    from runtime import source_answer
    original_calculate = source_answer.calculate

    def request(identity, index, inputs, **options):
        if package is None:
            response = original_request(identity, index, inputs, **options)
        else:
            key = digest([identity, index, inputs, options['tool_specs']])
            options['on_request'](key)
            response = db.step(identity, 'validation-response-' + key)
            if response is None:
                if index % 2 == 0:
                    result = [{'type': 'function_call', 'name': options['tool_specs'][0]['name'],
                               'arguments': '{}', 'call_id': key}]
                else:
                    if index == 1:
                        value = package['body']['interpretation']
                    elif index == 3:
                        value = package['body']['method']
                    else:
                        checked = json.loads(inputs[-1]['output'])
                        value = {'decision': 'accept', 'evidence_id': checked['evidence_id'],
                                 'explanation': 'Simulated decision for the integration check.', 'conflicts': []}
                    result = [{'type': 'message', 'content': [
                        {'type': 'output_text', 'text': json.dumps(value)}]}]
                response = {'output': result, '_backintel_fixture': True}
                db.save_step(identity, 'validation-response-' + key, 'validation_fixture_response', response)
        if index == 2 and not reject_finding and db.step(identity, 'validation-interrupted') is None:
            db.save_step(identity, 'validation-interrupted', 'validation_fault',
                         {'reason': 'Interruption after a retained analysis request; response must be reused.'})
            raise InterruptedError('Validation interruption after the analysis request was retained')
        return response

    def calculate(*args, **kwargs):
        answer = original_calculate(*args, **kwargs)
        if reject_finding:
            answer['calculation']['totals']['net_invoice_value'] = '0'
        return answer

    with patch.object(agent, 'request', side_effect=request), \
            patch.object(source_answer, 'calculate', side_effect=calculate):
        return service.handle(store, payload)


def check_coordination(actor, source, package, client, output, *, live=False, resume=None, max_spend_usd=0.5):
    goal_id = source['goal_id']
    service.revise_goal(goal_id, actor, budget_usd=0.5)
    goal = service.revise_goal(goal_id, actor, confirmed=True)
    policy = {'request_id': 's33-' + ('live' if live else 'fixture'),
              'max_model_calls': 6, 'max_spend_usd': max_spend_usd}
    preview = {'mode': 'live' if live else 'fixture', 'question': goal['body']['question'],
               'policy': policy, 'roles': dict(coordination.ROLES),
               'sent': ['objective and operating limits', 'field names and meanings',
                        'aggregate profiles and independent check results'],
               'excluded': ['raw records', 'identifier values']}
    (output/'request-scope.json').write_text(json.dumps(preview, indent=2))

    def dispatch(run, *, reject=False):
        handler = partial(validation_handler, package=package if not live or reject else None,
                          reject_finding=reject)
        result = execute_job(run['job_id'], handler, max_wall_seconds=1800,
                             usage_reader=lambda: db.usage(run['id']))
        (output/('rejected-job.json' if reject else 'job-attempt.json')).write_text(
            json.dumps(result, default=str, indent=2))
        return db.run(run['id'])

    run = coordination.invoke(goal_id, actor, policy)
    (output/'run.json').write_text(json.dumps({'run_id': run['id'], 'goal_id': goal_id}))
    if resume:
        interrupted = json.loads(resume.read_text())
        assert interrupted['run_id'] == run['id'] and run['status'] == 'succeeded', 'Resume requires the same completed implementation and objective'
        assert db.step(run['id'], 'validation-interrupted')
        finished = run
    else:
        previous_answer = db.goal(goal_id)['last_success']
        first = dispatch(run)
        assert db.step(run['id'], 'validation-interrupted'), first.get('error')
        assert first['status'] in ('partial', 'cancelled'), first.get('error')
        assert db.goal(goal_id)['last_success'] == previous_answer
        interrupted = coordination.inspect(run['id'], actor)
        assert coordination.invoke(goal_id, actor, policy)['id'] == run['id']
        finished = dispatch(run)
    assert interrupted['agents'][0]['status'] == 'accepted'
    accepted = copy.deepcopy(interrupted['agents'][0])
    (output/'interrupted-progress.json').write_text(json.dumps(interrupted, default=str, indent=2))
    assert finished['status'] == 'succeeded', finished.get('error')
    assert finished['result']['mode'] == ('real' if live else 'fixture')
    checked = db.step(run['id'], 'coord-tool-checking')['value']
    assert checked['status'] == 'passed' and not checked['conflicts']
    assert finished['result']['calculation']['coverage'] == {
        'expected_rows': 541909, 'processed_rows': 541909, 'excluded_rows': 0,
        'failed_rows': 0, 'pending_rows': 0}
    response = client.get('/api/v1/runs/' + run['id'] + '/coordination')
    response.raise_for_status()
    visible = response.json()
    assert all(item['status'] == 'accepted' for item in visible['agents'])
    assert [len(item['request_ids']) for item in visible['agents']] == [2, 2, 2]
    assert visible['agents'][0] == accepted
    assert set(interrupted['agents'][1]['request_ids']) <= set(visible['agents'][1]['request_ids'])
    before = db.usage(run['id'])
    duplicate = client.post('/api/v1/goals/' + goal_id + '/coordination', json=policy)
    duplicate.raise_for_status()
    assert duplicate.json()['id'] == run['id']
    assert db.usage(run['id']) == before
    if live:
        assert before['provider_calls'] == 6 and before['provider_usd'] <= max_spend_usd
    else:
        assert db.query("SELECT count(*) AS n FROM backintel.analysis_steps WHERE run_id=%s AND kind='validation_fixture_response'",
                        (run['id'],), one=True)['n'] == 6
        assert before['provider_calls'] == 0
    (output/'shared-progress.json').write_text(json.dumps(visible, default=str, indent=2))
    (output/'checked-answer.json').write_text(json.dumps(finished['result'], default=str, indent=2))
    env = {**os.environ, 'BACKINTEL_ACCESS_TOKEN': client.headers['Authorization'].removeprefix('Bearer ')}
    cli = subprocess.run([sys.executable, '-m', 'runtime.source_coordination', 'inspect', run['id']],
                         env=env, capture_output=True, text=True, timeout=30, check=True)
    assert json.loads(cli.stdout) == visible
    def check_browser(rejected=False):
        browser = subprocess.run(['node', str(Path(__file__).with_name('workflow_coordination_browser.cjs'))],
            env={**env, 'S33_URL': str(client.base_url), 'S33_DOMAIN': goal['domain'],
                 'S33_QUESTION': goal['body']['question'], 'S33_OUTPUT': str(output),
                 'S33_EXPECT_REJECTED': '1' if rejected else '',
                 'S33_EXPECTED_NET': finished['result']['calculation']['totals']['net_invoice_value'],
                 'OPENROUTER_API_KEY': ''}, capture_output=True, timeout=120)
        log = output/('rejected-browser.log' if rejected else 'browser.log')
        log.write_bytes(browser.stdout + browser.stderr)
        assert browser.returncode == 0, 'See ' + log.name

    latest = db.query("SELECT id FROM backintel.analysis_runs WHERE goal_id=%s AND body->>'operation'='coordination' ORDER BY created_at DESC LIMIT 1",
                      (goal_id,), one=True)
    if latest['id'] == run['id']:
        check_browser()
        accepted_browser = output
    else:
        assert resume and (resume.parent/'browser.log').read_text().startswith('PASS:')
        accepted_browser = resume.parent

    bad = coordination.invoke(goal_id, actor, {**policy, 'request_id': policy['request_id'] + '-rejected'})
    rejected = dispatch(bad, reject=True)
    assert rejected['status'] == 'partial' and 'net_invoice_value' in rejected['error'], rejected.get('error')
    assert db.goal(goal_id)['last_success'] == run['id']
    rejected_progress = coordination.inspect(bad['id'], actor)
    assert rejected_progress['agents'][2]['status'] == 'rejected'
    (output/'rejected-progress.json').write_text(json.dumps(rejected_progress, default=str, indent=2))
    check_browser(rejected=True)

    uncertain = digest(['validation-uncertain-charge', bad['id']])
    db.reserve(bad['id'], uncertain, Decimal('0.01'))
    try:
        db.write("UPDATE backintel.analysis_requests SET status='uncertain' WHERE id=%s", (uncertain,))
        try:
            coordination.invoke(goal_id, actor, {**policy, 'request_id': policy['request_id'] + '-rejected'})
        except RuntimeError as error:
            assert 'Reconcile' in str(error), str(error)
        else:
            raise AssertionError('An uncertain simulated charge allowed a retry')
    finally:
        db.write('DELETE FROM backintel.analysis_requests WHERE id=%s', (uncertain,))

    source_ref = goal['body']['objective']['source_ref']
    try:
        db.write('UPDATE backintel.analysis_source_connections SET enabled=false WHERE id=%s', (source_ref,))
        assert client.get('/api/v1/runs/' + run['id'] + '/coordination').status_code == 403
        assert client.post('/api/v1/goals/' + goal_id + '/coordination', json=policy).status_code == 403
    finally:
        db.write('UPDATE backintel.analysis_source_connections SET enabled=true WHERE id=%s', (source_ref,))
    return {'status': 'passed', 'mode': 'live' if live else 'fixture', 'run_id': run['id'],
            'full_dataset_checked': True, 'duplicate_reused': True, 'toolkit_api_browser_agree': True,
            'interrupted_request_reused': True, 'accepted_progress_preserved': True,
            'injected_incorrect_finding_rejected': True, 'source_permission_denial': True,
            'accepted_browser_evidence': str(accepted_browser), 'rejected_browser_checked': True,
            'simulated_uncertain_charge_blocked_retry': True, 'model_calls': 6 if live else 0,
            'usage': before, 'remaining': [] if live else ['actual agents']}
