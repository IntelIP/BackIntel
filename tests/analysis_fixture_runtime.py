"""Explicit offline Aegra entrypoint. No external HTTP transport or real models."""
import hashlib
import json
import os
import sys
import time
import types
from pathlib import Path

import httpx
import uvicorn
from psycopg.types.json import Jsonb

from runtime import analysis_agent as agent, analysis_service as service, analysis_store as db
from runtime.analysis_data import CONFIG, digest


def fixture_send(client, request, *args, **kwargs):
    if request.url.host in ('127.0.0.1', 'localhost', '::1'):
        return ORIGINAL_SEND(client, request, *args, **kwargs)
    if request.url.host != 'openrouter.ai':
        raise RuntimeError('Offline validation forbids external HTTP transport')
    if request.url.path == '/api/v1/models':
        value = {'data': [{'id': CONFIG['analyst']['model'], 'pricing': {'prompt': '0', 'completion': '0'}}]}
    elif request.url.path == '/api/v1/responses':
        payload = json.loads(request.content)
        context = json.loads(next(item['content'] for item in payload['input'] if item.get('role') == 'user'))
        outputs = [item for item in payload['input'] if item.get('type') == 'function_call_output']
        if not outputs:
            name = 'predict' if 'estimated' in context['question'].lower() else 'summarize'
            output = [{'type': 'function_call', 'name': name, 'call_id': 'fixture-calculation',
                       'arguments': json.dumps({'group': context['definitions']['group']})}]
        else:
            calculation = json.loads(outputs[-1]['output'])
            table = calculation.get('table', [])
            mean = table[0]['mean'] if table else None
            summary = ('Explicit fixture: observed mean ' + str(mean) + '.') if mean is not None else 'Explicit fixture: calculation unavailable.'
            if 'fixture_invalid_number' in context['question']:
                summary = 'Explicit fixture: observed mean 999999.'
            answer = {'summary': summary, 'findings': [{'claim': summary, 'kind': 'estimate' if calculation.get('kind') == 'estimate' else 'fact',
                       'evidence_ids': [calculation.get('evidence_id', 'unavailable')]}],
                       'limitations': ['Synthetic validation inputs and deterministic provider/model fixtures.']}
            output = [{'type': 'message', 'content': [{'type': 'output_text', 'text': json.dumps(answer)}]}]
        value = {'id': 'fixture-' + hashlib.sha256(request.content).hexdigest(), 'model': CONFIG['analyst']['model'],
                 'output': output, 'usage': {'cost': 0}, '_backintel_fixture': True}
    else:
        raise RuntimeError('Offline validation has no fixture for this provider route')
    return httpx.Response(200, json=value, request=request)


def fixture_models(identity, *, connection=None):
    run, goal = db.check_run(identity)
    rows = db.records(run['snapshot_id'])
    candidate = digest(['fixture-model', goal['id'], run['snapshot_id']])
    body = {'id': candidate, 'mode': 'fixture', 'methods': [{'route': 'catboost', 'features': 'facts', 'metrics': {'heldout_fixture_error': 123}, 'calibration_metrics': {'calibration_fixture_error': 0}}],
            'artifacts': [{'file': 'catboost-facts.joblib'}], 'splits': {name: [row['id'] for row in rows if row['split'] == name] for name in ('train', 'calibration', 'test')}}
    db.write('INSERT INTO backintel.analysis_models(id,goal_id,snapshot_id,body) VALUES(%s,%s,%s,%s) ON CONFLICT DO NOTHING',
             (candidate, goal['id'], run['snapshot_id'], Jsonb(body)), connection=connection)
    ref = db.evidence(identity, 'model_comparison', candidate, body)
    return {'status': 'succeeded', 'mode': 'fixture', 'summary': 'Explicit fixture predictor comparison.',
            'candidate_id': candidate, 'evidence_id': ref, 'usage': db.usage(identity)}


def install_fixtures():
    agent.credential = lambda: 'offline-fixture-no-provider-credential'
    httpx.Client.send = fixture_send
    service.model_job = fixture_models
    original_import = service._import_source
    def fixture_import(domain, actor, **kwargs):
        # A bounded fixture delay exposes the running import for a hard-kill test.
        time.sleep(1)
        return original_import(domain, actor, **kwargs)
    service._import_source = fixture_import
    sys.modules['runtime.analysis_models'] = types.SimpleNamespace(
        predict=lambda model, rows: {row['id']: .25 for row in rows},
        decide=lambda rows, domain: ([], [{'mode': 'fixture'} for _ in rows]))


def fixture_handle(store, payload):
    install_fixtures()
    return ORIGINAL_HANDLE(store, payload)


def main():
    if os.environ.get('BACKINTEL_VALIDATION_MODE') != 'fixture':
        raise RuntimeError('This entrypoint requires explicit fixture mode')
    from psycopg.conninfo import conninfo_to_dict
    name = conninfo_to_dict(os.environ['BACKINTEL_APP_DATABASE_URL'])['dbname']
    if not (name.startswith('backintel_') and name.endswith('_test')):
        raise RuntimeError('Fixture runtime requires a disposable test database')
    from runtime import analysis_api
    port = int(os.environ['BACKINTEL_VALIDATION_PORT'])
    if not 1 <= port <= 65535:
        raise ValueError('Fixture port must be between 1 and 65535')
    # Only this guarded, disposable fixture entrypoint changes allowed origins.
    analysis_api.WRITE_ORIGINS = frozenset((f'http://127.0.0.1:{port}', f'http://localhost:{port}'))
    from runtime.bootstrap import initialize
    initialize()
    db.catalog()
    values = json.loads(Path(os.environ['BACKINTEL_ACCESS_CREDENTIAL_FILE']).read_text())
    for role, token in values.items():
        db.write('INSERT INTO backintel.analysis_principals(id,token_hash,role,domains) VALUES(%s,%s,%s,%s) ON CONFLICT DO NOTHING',
                 (role, hashlib.sha256(token.encode()).hexdigest(), role, list(CONFIG['sources'])))
    for source in db.query('SELECT * FROM backintel.analysis_sources'):
        if source['body'].get('mode') == 'fixture':
            continue
        db.write('UPDATE backintel.analysis_sources SET body=%s WHERE id=%s',
                 (Jsonb({**source['body'], 'mode': 'fixture', 'caveat': 'Synthetic validation fixture. ' + source['body']['caveat']}), source['id']))
    install_fixtures()
    from analysis_fixture_runtime import fixture_handle as worker_handle
    service.handle = worker_handle
    uvicorn.run('aegra_api.main:app', host='127.0.0.1', port=int(os.environ['BACKINTEL_VALIDATION_PORT']), log_level='warning')


ORIGINAL_SEND = httpx.Client.send
ORIGINAL_HANDLE = service.handle
if __name__ == '__main__':
    main()
