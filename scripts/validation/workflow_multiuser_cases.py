"""Multi-user acceptance against disposable databases, with no paid provider requests."""
import json
import os
from pathlib import Path
import subprocess
import sys
import hashlib
import secrets
import time
from copy import deepcopy
from concurrent.futures import ThreadPoolExecutor

import psycopg
from psycopg.conninfo import make_conninfo
from psycopg.types.json import Jsonb


ROOT = Path(__file__).resolve().parents[2]


def check_multiuser(actor, source, package, client, output, *, checks_only=False):
    if not checks_only:
        return check_retail(actor, source, package, client, output)
    from runtime.ledger import dsn
    test_name = 'backintel_multiuser_test'
    with psycopg.connect(dsn(), autocommit=True) as connection:
        connection.execute('CREATE DATABASE backintel_multiuser_test')
    test_uri = make_conninfo(dsn(), dbname=test_name)
    env = {**os.environ, 'BACKINTEL_APP_DATABASE_URL': test_uri, 'BACKINTEL_TEST_DATABASE_URL': test_uri,
           'BACKINTEL_ANALYSIS_CHECK_DB': test_uri, 'OPENROUTER_API_KEY': '', 'OPENAI_API_KEY': '',
           'PGOPTIONS': '-c lock_timeout=15000 -c statement_timeout=40000'}
    with (output/'multiuser-checks.log').open('w') as log:
        checked = subprocess.run([sys.executable, '-m', 'unittest', '-v', 'tests.test_analysis_multiuser',
                                  'tests.test_analysis_campaign', 'tests.test_analysis'], cwd=ROOT, env=env,
                                 stdout=log, stderr=subprocess.STDOUT, text=True, timeout=240)
    assert checked.returncode == 0, 'Multi-user and regression checks failed; inspect multiuser-checks.log'
    return {'status': 'passed', 'scope': 'isolated synthetic API and concurrent budget checks only',
            'model_calls': 0, 'provider_cost_usd': 0, 'retail_acceptance': 'not run'}


def import_reference(actor, source, package, owner, source_ref, question):
    """Copy accepted evidence into one private objective, without new inference."""
    from runtime import analysis_store as db, analysis_service as service, source_workflows as workflows
    from runtime.analysis_data import digest
    from runtime.evidence import Evidence
    from runtime.source_inputs import retained_input, admit_response
    from runtime.workflow_updates import collection_for
    collection = collection_for(db.run(db.goal(source['goal_id'])['last_success']))
    policy = db.query('SELECT * FROM backintel.analysis_source_connections WHERE id=%s',
                      (package['body']['connection']['source_ref'],), one=True)
    objective = {**package['body']['objective'], 'source_ref': source_ref}
    goal = service.create_goal(owner, policy['domain'], question, objective=objective)
    service.revise_goal(goal['id'], owner, confirmed=True)
    goal = db.goal(goal['id'])
    # These are imported, already accepted artifacts, not new planning or calculation.
    # The caller must execute fresh jobs to demonstrate new results.
    provenance = {'mode': 'retained-reference-import', 'original_workflow': package['version'],
                  'original_collection': collection['id'], 'fresh_model_calls': 0}
    ids = {source['goal_id']: goal['id'], policy['id']: source_ref}
    accepted_runs = {key: db.run(ref['run_id']) for key, ref in package['body']['accepted'].items()}
    accepted_runs['collection'] = collection
    for previous in accepted_runs.values():
        ids[previous['id']] = digest([goal['id'], 'retained-reference', previous['id']])
    for page in collection['result']['inputs']:
        original = retained_input(page['raw_input_id'], actor)
        admitted = admit_response(goal['id'], owner, schema=original['schema_name'], table=original['table_name'],
            source_version=original['source_version'], payload=original['payload'], expected_version=goal['version'])
        ids[original['id']] = admitted['id']

    def remap(value):
        if isinstance(value, dict):
            return {key: remap(item) for key, item in value.items()}
        if isinstance(value, list):
            return [remap(item) for item in value]
        return ids.get(value, value) if isinstance(value, str) else value

    body = remap(deepcopy(package['body']))
    body.update(goal_id=goal['id'], goal_version=goal['version'], objective=objective, question=question,
                provenance=provenance)
    body['accepted'] = {}
    for key, previous in accepted_runs.items():
        result = remap(previous['result'])
        identity = ids[previous['id']]
        db.write('''INSERT INTO backintel.analysis_runs(id,goal_id,owner,goal_version,body,status,result)
                    VALUES(%s,%s,%s,%s,%s,'succeeded',%s)''',
                 (identity, goal['id'], owner['id'], goal['version'],
                  Jsonb({**remap(previous['body']), 'question': question, 'retained_from': previous['id'],
                         'provenance': provenance}), Jsonb(result)))
        body['accepted'][key] = {'run_id': identity, 'result_sha256': digest(result)}
    body['source_links'] = [{'input_id': ids[page['raw_input_id']], 'row_count': page['row_count'],
                             'original': '/api/v1/inputs/' + ids[page['raw_input_id']] + '/original'}
                            for page in collection['result']['inputs']]
    body['dependencies'] = workflows.runtime_dependencies(body['dependencies']['image'])
    imported = workflows.package_body(body)
    with db.connect() as connection:
        Evidence(connection, 'analysis-goal-' + goal['id']).put('workflow_package', imported['version'], imported, int(time.time()))
    assert workflows.load(imported, owner)['status'] == 'ready'
    return imported


def check_retail(actor, source, package, client, output):
    """Restore accepted inputs into four private contexts, then actually recompute each answer."""
    from runtime import analysis_store as db, analysis_service as service, source_workflows as workflows
    from runtime.analysis_data import digest
    policy = db.query('SELECT * FROM backintel.analysis_source_connections WHERE id=%s',
                      (package['body']['connection']['source_ref'],), one=True)
    tokens = {name: secrets.token_urlsafe(32) for name in ('a', 'b', 'viewer')}
    principals = {name: 's30-' + name for name in tokens}
    for name, token in tokens.items():
        db.write('''INSERT INTO backintel.analysis_principals(id,token_hash,role,domains,budget_usd)
                    VALUES(%s,%s,%s,%s,%s)''', (principals[name], hashlib.sha256(token.encode()).hexdigest(),
                    'viewer' if name == 'viewer' else 'manager', [policy['domain']],
                    {'a': '.05', 'b': '.07', 'viewer': '0'}[name]))

    def request(name, method, path, expected=200, **kwargs):
        response = client.request(method, '/api/v1' + path,
                                  headers={'Authorization': 'Bearer ' + tokens[name]}, **kwargs)
        assert response.status_code == expected, (name, method, path, response.status_code, response.text[:500])
        return response.json()

    goals, plans, runs = {name: [] for name in ('a', 'b')}, {}, {}
    for name in goals:
        owner = {'id': principals[name]}
        source_ref = 's30-retail-' + name
        db.write('''INSERT INTO backintel.analysis_source_connections(id,domain,secret_ref,schemas,principals)
                    VALUES(%s,%s,%s,%s,%s)''', (source_ref, policy['domain'], policy['secret_ref'], policy['schemas'],
                    [owner['id']] + ([principals['viewer']] if name == 'a' else [])))
        for number in (1, 2):
            imported = import_reference(actor, source, package, owner, source_ref,
                f'Owner {name.upper()} analysis {number}: ' + package['body']['question'])
            goal = db.goal(imported['body']['goal_id'])
            goals[name].append(goal['id'])
            plans[goal['id']] = imported
            print(f'S-30: retained source and accepted recipe ready for owner {name}, analysis {number}.', flush=True)

    assert request('viewer', 'GET', '/goals') == []
    for name, other in (('a', 'b'), ('b', 'a')):
        assert {g['id'] for g in request(name, 'GET', '/goals')} == set(goals[name])
        request(name, 'GET', '/workflows/' + plans[goals[other][0]]['version'], expected=403)
        request(name, 'PATCH', '/goals/' + goals[other][0], expected=403, json={'paused': True})
    shared_goal = goals['a'][0]
    request('a', 'PUT', f'/goals/{shared_goal}/access/{principals["viewer"]}', json={'permission': 'read'})
    assert [g['id'] for g in request('viewer', 'GET', '/goals')] == [shared_goal]
    request('viewer', 'POST', '/goals/' + shared_goal + '/runs', expected=403, json={})
    with db.connect() as admission_lock:
        admission_lock.execute('SELECT pg_advisory_lock(81827028)')
        for name in goals:
            for goal_id in goals[name]:
                accepted = request(name, 'POST', '/workflows/' + plans[goal_id]['version'] + '/runs', expected=202,
                                   json={'input_ref': plans[goal_id]['body']['accepted']['collection']['run_id']})
                runs[goal_id] = accepted['id']
        assert len(set(runs.values())) == 4
        for name, other in (('a', 'b'), ('b', 'a')):
            other_run = runs[goals[other][0]]
            request(name, 'GET', '/runs/' + other_run, expected=403)
            request(name, 'POST', '/runs/' + other_run + '/cancel', expected=403)
        request('viewer', 'POST', '/runs/' + runs[shared_goal] + '/cancel', expected=403)
        initial = {name: request(name, 'GET', '/queue') for name in tokens}
        assert initial['a']['shared_capacity']['waiting'] == 4
        assert {j['id'] for j in initial['a']['jobs']} == {runs[g] for g in goals['a']}
        assert {j['id'] for j in initial['b']['jobs']} == {runs[g] for g in goals['b']}
        assert {j['id'] for j in initial['viewer']['jobs']} == {runs[shared_goal]}
    samples = []
    started = time.monotonic()
    with ThreadPoolExecutor(max_workers=1) as pool:
        dispatched = pool.submit(service.dispatch)
        browser_env = {**os.environ, 'S30_URL': str(client.base_url), 'S30_TOKENS': json.dumps(tokens),
                       'S30_OUTPUT': str(output), 'S30_SHARED_QUESTION': db.goal(shared_goal)['body']['question']}
        browser_log = (output/'multiuser-browser.log').open('w')
        browser = subprocess.Popen(['node', 'scripts/validation/workflow_multiuser_browser.cjs'], cwd=ROOT,
                                   env=browser_env, stdout=browser_log, stderr=subprocess.STDOUT)
        try:
            while True:
                current = request('a', 'GET', '/queue')['shared_capacity']
                assert current['active'] <= 2, current
                samples.append({'elapsed_seconds': round(time.monotonic() - started, 3), **current})
                states = db.query('SELECT status FROM backintel.analysis_runs WHERE id=ANY(%s)', (list(runs.values()),))
                if all(row['status'] not in ('queued', 'running') for row in states):
                    break
                assert time.monotonic() - started < 1200, 'The four-analysis workload did not finish within the test deadline'
                try:
                    if dispatched.done():
                        import threading
                        threading.Event().wait(1)
                    else:
                        dispatched.result(timeout=1)
                except TimeoutError:
                    pass
            dispatched.result()
            assert browser.wait(timeout=60) == 0, 'Inspect multiuser-browser.log'
        finally:
            if browser.poll() is None:
                browser.terminate(); browser.wait(timeout=10)
            browser_log.close()
    assert any(s['active'] == 2 and s['waiting'] >= 1 for s in samples), 'Two active jobs with visible waiting work were not observed'
    report = []
    for name in goals:
        for goal_id in goals[name]:
            actual = request(name, 'GET', '/runs/' + runs[goal_id])
            assert actual['status'] == 'succeeded', actual
            calculation = actual['result']['calculation']
            for field in ('totals', 'dimensions', 'currency', 'period_start', 'period_end', 'coverage'):
                assert calculation[field] == baseline['result']['calculation'][field], field
            report.append({'owner': name, 'goal_id': goal_id, 'run_id': actual['id'], 'status': actual['status'],
                           'calculation_sha256': digest(calculation), 'coverage': calculation['coverage'],
                           'usage': db.usage(actual['id'])})
            (output/f'multiuser-{name}-{goals[name].index(goal_id)+1}-result.json').write_text(json.dumps(actual, default=str, indent=2))
    final = {name: request(name, 'GET', '/queue') for name in tokens}
    assert all(q['your_usage']['provider_calls'] == 0 for q in final.values())
    (output/'multiuser-queues.json').write_text(json.dumps({'initial': initial, 'samples': samples, 'final': final}, default=str, indent=2))
    return {'status': 'passed', 'scope': 'two owners, one read-only viewer, four actual retained-retail workflow executions',
            'planning': 'Retained accepted method and interpretation; no new autonomous model decisions.',
            'runs': report, 'elapsed_seconds': round(time.monotonic() - started, 3),
            'maximum_observed_active_jobs': max(s['active'] for s in samples), 'model_calls': 0,
            'provider_cost_usd': 0, 'local_compute_usd': None}
