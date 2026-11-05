"""Retained retail data; live interpretation requires an explicit, separately approved flag."""
from copy import deepcopy
import json
import os
from pathlib import Path
import subprocess
import sys
from unittest.mock import patch

import psycopg
from psycopg.conninfo import make_conninfo
from psycopg.types.json import Jsonb

ROOT = Path(__file__).resolve().parents[2]
LIVE_REVISION = ('Independently interpret the attached UCI documentation for the saved objective. '
                 'Cite exact passages for InvoiceNo cancellations and UnitPrice currency when supported; '
                 'keep unsupported or conflicting meanings explicit. Do not reuse a prior proposed interpretation.')


def guard_document_call(identity, call_id):
    """The normal reservation ledger enforces the cumulative US$0.25 cap on this one run."""
    from runtime import analysis_store as db
    run, goal = db.check_run(identity)
    if run['body']['operation'] != 'interpretation' or not 0 < goal['body'].get('budget_usd', 0) <= .25:
        raise PermissionError('Live document interpretation requires its own run and at most US$0.25')
    previous = db.query('SELECT id,status FROM backintel.analysis_requests WHERE run_id=%s', (identity,))
    if any(row['id'] == call_id for row in previous):
        return  # The existing request function handles cached or unresolved requests.
    if len(previous) >= 2:
        raise RuntimeError('The two document interpretation requests have been used')
    if any(row['status'] != 'complete' for row in previous):
        raise RuntimeError('Resolve the existing document request before another call')


def require_reference_citations(evidence):
    for field, terms in (('InvoiceNo', ("'c'", 'cancellation')), ('UnitPrice', ('sterling',))):
        quotes = [item['quote'].casefold() for item in evidence if item['field'] == field]
        if not any(all(term in quote for term in terms) for quote in quotes):
            raise ValueError('The UCI document needs an exact ' + field + ' quotation establishing ' + ' and '.join(terms))


def prepare_case(actor, source, package, output, original):
    from runtime import analysis_store as db, analysis_service as service
    from runtime import source_documents
    from runtime.analysis_data import digest
    from runtime.source_inputs import retained_input, admit_response
    from runtime.ledger import dsn

    with psycopg.connect(dsn(), autocommit=True) as control:
        control.execute('CREATE DATABASE backintel_documents_test')
    test_uri = make_conninfo(dsn(), dbname='backintel_documents_test')
    env = {**os.environ, 'BACKINTEL_DOCUMENT_CHECK_DB': test_uri, 'BACKINTEL_ANALYSIS_CHECK_DB': test_uri,
           'BACKINTEL_TEST_DATABASE_URL': test_uri, 'OPENROUTER_API_KEY': '',
           'BACKINTEL_ANALYST_CREDENTIAL_FILE': '/nonexistent/s27-no-provider.json'}
    with (output/'document-checks.log').open('w') as log:
        checked = subprocess.run([sys.executable, '-m', 'unittest', '-v', 'tests.test_source_documents',
            'tests.test_analysis_objectives', 'tests.test_source_workflows', 'tests.test_source_answer',
            'tests.test_source_coordination', 'tests.test_analysis_multiuser', 'tests.test_analysis_campaign',
            'tests.test_analysis'], cwd=ROOT, env=env, stdout=log, stderr=subprocess.STDOUT, timeout=240)
    assert checked.returncode == 0, 'Document checks failed; inspect document-checks.log'
    goal = service.create_goal(actor, db.goal(source['goal_id'])['domain'],
                               'S-27 document reference: ' + package['body']['question'], objective=package['body']['objective'])
    document = source_documents.admit(goal['id'], actor, title='UCI Online Retail field guide',
        source_url='https://archive.ics.uci.edu/dataset/352/online+retail', media_type='text/html', payload=original.read_bytes())
    # This disposable allowance admits simulated requests only. Transport is replaced below;
    # the runner removes the provider key and verifies the charge ledger is unchanged.
    goal = service.revise_goal(goal['id'], actor, document_refs=[document['id']], budget_usd=.25)
    service.revise_goal(goal['id'], actor, confirmed=True)
    goal = db.goal(goal['id'])
    collected = db.run(package['body']['accepted']['collection']['run_id'])
    ids = {}
    for page in collected['result']['inputs']:
        previous = retained_input(page['raw_input_id'], actor)
        admitted = admit_response(goal['id'], actor, schema=previous['schema_name'], table=previous['table_name'],
            source_version=previous['source_version'], payload=previous['payload'], expected_version=goal['version'])
        ids[previous['id']] = admitted['id']

    def remap(value):
        if isinstance(value, dict):
            return {key: remap(item) for key, item in value.items()}
        if isinstance(value, list):
            return [remap(item) for item in value]
        return ids.get(value, value) if isinstance(value, str) else value

    imported_id = digest([goal['id'], 'retained-collection', collected['id']])
    collection = remap(deepcopy(collected['result']))
    collection['goal_version'] = goal['version']
    db.write('''INSERT INTO backintel.analysis_runs(id,goal_id,owner,goal_version,body,status,result)
                VALUES(%s,%s,%s,%s,%s,'succeeded',%s)''',
             (imported_id, goal['id'], actor['id'], goal['version'],
              Jsonb({**collected['body'], 'question': goal['body']['question'], 'retained_from': collected['id']}), Jsonb(collection)))
    profile = db.run(package['body']['accepted']['interpretation']['run_id'])['result']['profile']
    proposal = deepcopy(package['body']['interpretation'])
    passages = source_documents.context(goal, profile, actor)
    for table in proposal['tables']:
        for field in table['fields']:
            field['citations'] = []
            if field['name'] in ('InvoiceNo', 'UnitPrice'):
                matching = [p for p in passages if field['name'] in p['fields']
                            and ('cancellation' if field['name'] == 'InvoiceNo' else 'sterling') in p['text']]
                assert matching, 'The official document lacks the expected field definition'
                selected = matching[0]
                field['citations'] = [{'document_id': selected['document_id'], 'passage_id': selected['passage_id'], 'quote': selected['text']}]
    (output/'document-context.json').write_text(json.dumps(passages, indent=2))
    return goal, document, proposal


def check_documents(actor, source, package, client, output, original, *, resume=None, live=False):
    from runtime import analysis_store as db, analysis_service as service, jobs, source_workflows, source_documents
    from runtime.analysis_data import digest
    os.environ['BACKINTEL_PREPARATION_IMAGE'] = package['body']['dependencies']['image']
    run_ids = {}
    retained_profile = None
    if resume and (resume/'document-browser.json').exists() and (resume/'workflow-package.json').exists():
        if live:
            raise ValueError('Live interpretation requires the pre-calculation archive, before attachments were detached')
        assert json.loads((resume/'document-browser.json').read_text())['status'] == 'passed'
        for operation in ('interpretation', 'preparation', 'validation', 'answer'):
            retained = json.loads((resume/(operation+'-result.json')).read_text())
            run = db.run(retained['id'])
            assert run['owner'] == actor['id'] and run['status'] == 'succeeded'
            assert digest(run['result']) == digest(retained['result'])
            run_ids[operation] = run['id']
        goal = db.goal(run['goal_id'])
        db.authorize_goal(actor, goal['id'], ('manager',), permission='manage')
        saved = source_workflows.validate_package(json.loads((resume/'workflow-package.json').read_text()))
        document = {'id': saved['body']['document_refs'][0]}
        result = finish_case(actor, source, original, goal, document, saved, run_ids, run['result'])
        result['completed_execution_and_browser_evidence'] = str(resume)
        return result
    if resume:
        retained = json.loads((resume/'interpretation-result.json').read_text())
        interpreted = db.run(retained['id'])
        assert interpreted['status'] == 'succeeded' and digest(interpreted['result']) == digest(retained['result'])
        assert interpreted['owner'] == actor['id']
        goal = db.goal(interpreted['goal_id'])
        source_documents.accepted_evidence(goal, interpreted['result'], actor)
        document = source_documents.read(goal['body']['document_refs'][0], actor)
        document = {'id': document['id'], **document['body']}
        proposal = interpreted['result']['interpretation']
        retained_profile = interpreted['result']['profile']
        if not live:
            run_ids['interpretation'] = interpreted['id']
        for name in ('interpretation-request.json', 'interpretation-result.json', 'document-context.json'):
            (output/name).write_bytes((resume/name).read_bytes())
    else:
        goal, document, proposal = prepare_case(actor, source, package, output, original)

    if live and not resume:
        raise ValueError('Live interpretation must start from the reviewed pre-calculation archive')
    from runtime import analysis_agent, source_semantics
    original_request = analysis_agent.request
    original_interpret = source_semantics.interpret
    attempt = 0
    revision_error = None

    def checked_interpret(identity):
        result = original_interpret(identity)
        require_reference_citations(result['document_evidence'])
        return result

    def response(value):
        return {'_backintel_fixture': not live, 'output': [{'type': 'message', 'content': [{'type': 'output_text', 'text': json.dumps(value)}]}]}

    def model(identity, index, inputs, **kwargs):
        operation = db.run(identity)['body']['operation']
        assert kwargs.get('tool_specs', []) == [], 'Document interpretation acquired executable tools'
        if operation == 'interpretation':
            if live:
                inputs = deepcopy(inputs)
                if revision_error:
                    inputs.append({'role': 'user', 'content': 'The previous proposal failed the local checks: ' + revision_error
                        + '. Revise the proposal using the same objective and supplied passages. Do not change permissions or data.'})
                (output/('interpretation-request-' + str(attempt) + '.json')).write_text(
                    json.dumps({'inputs': inputs, 'answer_schema': kwargs['answer_schema']}, indent=2))
                return original_request(identity, attempt, inputs, **kwargs,
                                        on_request=lambda call_id: guard_document_call(identity, call_id))
            (output/'interpretation-request.json').write_text(json.dumps({'inputs': inputs, 'answer_schema': kwargs['answer_schema']}, indent=2))
            return response(proposal)
        assert operation == 'answer'
        if live:
            db.save_step(identity, 'retained-analysis-method', 'retained_method',
                         {'workflow_version': package['version'], 'source_run_id': source['id'],
                          'method_sha256': digest(package['body']['method']), 'fresh_method_generation': False})
        return response(package['body']['method'])

    with patch('runtime.analysis_agent.request', side_effect=model), \
            patch.object(source_semantics, 'interpret', side_effect=checked_interpret), \
            patch.object(jobs, '_run_worker', side_effect=jobs._execute_claimed):
        for operation in ('interpretation', 'preparation', 'validation', 'answer'):
            if operation in run_ids:
                continue
            for attempt in range(2 if live and operation == 'interpretation' else 1):
                run = service.submit(goal['id'], actor, operation=operation,
                                     question=LIVE_REVISION if live and operation == 'interpretation' else None)
                if live and operation == 'interpretation' and retained_profile is not None:
                    # The restored archive predates per-user budgets. Grant only this
                    # approved run's allowance, excluding its existing charges on resume.
                    db.write('''UPDATE backintel.analysis_principals p SET budget_usd=.25 +
                        (SELECT COALESCE(sum(COALESCE(q.charge,q.reserved)),0)
                         FROM backintel.analysis_requests q JOIN backintel.analysis_runs r ON r.id=q.run_id
                         WHERE r.owner=p.id AND r.id<>%s) WHERE p.id=%s''', (run['id'], actor['id']))
                    db.save_step(run['id'], 'source-profile', 'source_profile', retained_profile)
                print('S-27: executing ' + operation + ' over retained retail data.', flush=True)
                service.dispatch(run['id'])
                finished = db.run(run['id'])
                (output/(operation + '-result.json')).write_text(json.dumps(finished, default=str, indent=2))
                if finished['status'] == 'succeeded':
                    break
                usage = db.usage(run['id'])
                if (not live or operation != 'interpretation' or finished['status'] != 'partial'
                        or usage['provider_calls'] != attempt + 1 or usage['charge_status'] != 'measured'):
                    break
                revision_error = finished.get('error') or 'The proposal did not pass validation'
            assert finished['status'] == 'succeeded', (operation, finished.get('error'))
            run_ids[operation] = run['id']
    answer = db.run(run_ids['answer'])['result']
    baseline = source['result']['calculation']
    for key in ('totals', 'dimensions', 'coverage', 'currency', 'period_start', 'period_end'):
        assert answer['calculation'][key] == baseline[key], key
    assert {'InvoiceNo', 'UnitPrice'} <= {item['field'] for item in answer['document_evidence']}
    assert answer['mode'] == ('real' if live else 'fixture')
    saved = source_workflows.save(run_ids['answer'], actor)
    assert source_workflows.load(saved, actor)['status'] == 'ready'
    assert saved['body']['document_evidence'] == answer['document_evidence']
    assert source_workflows.bind(saved['version'], None, actor)['goal_version'] == goal['version']
    (output/'workflow-package.json').write_text(json.dumps(saved, default=str, indent=2))
    browser_env = {**os.environ, 'S27_URL': str(client.base_url), 'S27_TOKEN': client.headers['authorization'].removeprefix('Bearer '),
                   'S27_GOAL': goal['body']['question'], 'S27_OUTPUT': str(output), 'S27_DOCUMENT_SHA256': document['payload_sha256']}
    with (output/'document-browser.log').open('w') as log:
        browser = subprocess.run(['node', str(ROOT/'scripts/validation/workflow_document_browser.cjs')],
                                 env=browser_env, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT, timeout=120)
    assert browser.returncode == 0, 'Document browser check failed; inspect document-browser.log'
    return finish_case(actor, source, original, goal, document, saved, run_ids, answer)


def finish_case(actor, source, original, goal, document, saved, run_ids, answer):
    from runtime import analysis_service as service, analysis_store as db, source_workflows, source_documents
    for key in ('totals', 'dimensions', 'coverage', 'currency', 'period_start', 'period_end'):
        assert answer['calculation'][key] == source['result']['calculation'][key], key
    service.revise_goal(goal['id'], actor, document_refs=[])
    try:
        source_workflows.bind(saved['version'], None, actor)
    except PermissionError as error:
        assert 'Confirm and enable' in str(error), str(error)
    else:
        raise AssertionError('The changed objective did not require confirmation')
    service.revise_goal(goal['id'], actor, confirmed=True)
    assert source_workflows.read(saved['version'], actor) == saved
    try:
        source_workflows.bind(saved['version'], None, actor)
    except ValueError as error:
        assert 'objective changed' in str(error).lower(), str(error)
    else:
        raise AssertionError('A changed document set did not invalidate the prior workflow')
    assert source_documents.read(document['id'], actor)['payload'] == original.read_bytes()
    interpreted = db.run(run_ids['interpretation'])
    usage = db.usage(interpreted['id'])
    live = interpreted['result']['mode'] == 'real'
    if live:
        assert 0 < usage['provider_calls'] <= 2 and usage['provider_usd'] <= .25 and usage['charge_status'] == 'measured'
        assert db.step(run_ids['answer'], 'retained-analysis-method')
    return {'status': 'passed', 'scope': 'actual retained retail data and official original; '
                + ('live' if live else 'simulated') + ' document interpretation and retained analysis method',
            'goal_id': goal['id'], 'runs': run_ids, 'rows': answer['calculation']['coverage']['processed_rows'],
            'totals': answer['calculation']['totals'], 'document_evidence': answer['document_evidence'],
            'model_calls': usage['provider_calls'], 'provider_cost_usd': usage['provider_usd'], 'calculation_parity': True,
            'workflow_document_change_blocked': True, 'fresh_autonomous_document_interpretation': 'verified' if live else 'not yet verified'}
