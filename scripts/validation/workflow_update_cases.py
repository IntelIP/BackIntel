"""Controlled source-change injections into a disposable historical retail archive.

The workflow executor, PostgreSQL evidence, permission checks, computation,
publication, and browser are real. Source changes and interruptions are deliberate
test injections; this does not claim a live upstream change feed (S-24).
"""
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from decimal import Decimal
import hashlib
import json
from pathlib import Path
import subprocess
from unittest.mock import patch

from runtime import analysis_store as db, analysis_service as service
from runtime import source_workflows as workflows, source_methods as methods, source_answer, source_collection
from runtime.source_inputs import admit_response, retained_input
from runtime.jobs import execute as execute_job

def source_date(value):
    try:
        return datetime.fromisoformat(str(value)).date()
    except ValueError:
        return datetime.strptime(str(value), '%m/%d/%Y %H:%M').date()


def check_updates(actor, source, package, client, base, token, env, output, *, repair_checked=False, completed_cases=None):
    goal = db.goal(source['goal_id'])
    original = db.run(package['body']['accepted']['collection']['run_id'])
    source_totals = source['result']['calculation']['totals']
    cases = completed_cases or []

    def progress(name):
        (output/'progress.json').write_text(json.dumps({'case': name, 'completed': cases}, default=str))

    def replace_collection(name, edit=None, metadata=None, index=0):
        result = deepcopy(original['result'])
        if edit:
            item = result['inputs'][index]
            raw = retained_input(item['raw_input_id'], actor)
            envelope = json.loads(raw['payload'], parse_float=Decimal)
            edit(envelope)
            payload = json.dumps(envelope, default=str, separators=(',', ':')).encode()
            admitted = admit_response(goal['id'], actor, schema=item['schema'], table=item['table'],
                source_version='S21 controlled source-change fixture: '+name, payload=payload, expected_version=goal['version'])
            item.update(raw_input_id=admitted['id'], sha256=hashlib.sha256(payload).hexdigest(), bytes=len(payload), row_count=len(envelope['rows']))
        if metadata:
            metadata(result)
        result['observed_at'] = datetime.now(timezone.utc).isoformat()
        result['limitations'].append('Controlled S-21 source-change fixture; upstream collection is evaluated separately in S-24.')
        result['coverage']['retained_bytes'] = sum(item['bytes'] for item in result['inputs'])
        run = service.submit(goal['id'], actor, question=goal['body']['question']+' [S21 fixture: '+name+']', operation='collection')
        # Supply the declared test input at the connector boundary. Job completion,
        # evidence, permissions, and downstream workflow execution stay real.
        def controlled_input(store, payload):
            with patch.object(source_collection, 'collect', return_value=result):
                return service.handle(store, payload)
        execute_job(run['job_id'], controlled_input, max_wall_seconds=900)
        completed = db.run(run['id'])
        assert completed['status'] == 'succeeded', completed.get('error')
        return run['id']

    def execute(input_ref, version=None, interrupted=False):
        selected_version = version or package['version']
        # A retained decision is evidence, not a reason to rerun a completed
        # failed check when continuing this validation from its archive.
        prior = db.query("""SELECT * FROM backintel.analysis_runs WHERE owner=%s
            AND body->>'workflow_version'=%s AND body->>'input_ref'=%s
            AND body->>'analysis_identity'=%s AND status IN ('partial','failed')
            AND result->'update'->'review' IS NOT NULL ORDER BY created_at DESC LIMIT 1""",
            (actor['id'], selected_version, input_ref, service.analysis_identity()), one=True)
        if prior:
            return prior
        run = workflows.invoke(selected_version, actor, input_ref)
        if interrupted:
            def interrupt_before_answer(store, payload):
                with patch.object(source_answer, 'calculate', side_effect=InterruptedError('Controlled interruption before answering')):
                    return service.handle(store, payload)
            execute_job(run['job_id'], interrupt_before_answer, max_wall_seconds=900)
        else:
            service.dispatch(run['id'])
        finished = db.run(run['id'])
        (output/'latest-run.json').write_text(json.dumps({key:finished[key] for key in ('id','status','error','result')}, default=str))
        return finished

    def read_status():
        expected = workflows.update_status(goal['id'], actor)
        response = client.get('/api/v1/goals/'+goal['id']+'/update-status')
        response.raise_for_status()
        observed = response.json()
        assert observed['state'] == expected['state'] and observed['accepted'] == expected['accepted']
        return observed

    def browser(name, state, decision=''):
        progress(name+' browser')
        result = subprocess.run(['node', str(Path(__file__).with_name('workflow_update_browser.cjs'))],
            env={**env,'S21_URL':base,'S21_TOKEN':token,'S21_DOMAIN':goal['domain'],
                 'S21_QUESTION':goal['body']['question'],'S21_STATE':state,'S21_DECISION':decision,
                 'S21_CASE':name,'S21_OUTPUT':str(output)}, capture_output=True, timeout=90)
        (output/(name+'-browser.log')).write_bytes(result.stdout+result.stderr)
        assert result.returncode == 0, 'Inspect '+name+'-browser.log'

    quantity = package['body']['method']['quantity_field']
    def format_quantity(page):
        i = page['columns'].index(quantity)
        page['rows'][0][i] = ' '+str(page['rows'][0][i])+' '

    if completed_cases:
        assert len(cases) == 5 and cases[-1]['case'] == 'interruption reuses completed work'
        recovered = db.run(cases[-1]['run_id'])
        assert recovered['status'] == 'succeeded'
        assert recovered['result']['calculation']['totals'] == source_totals
        assert db.goal(goal['id'])['last_success'] == recovered['id']
    else:
        progress('safe value-preserving normalization')
        safe_input = replace_collection('safe-format', format_quantity)
        accepted = execute(safe_input)
        assert accepted['status'] == 'succeeded', accepted.get('error')
        assert accepted['result']['calculation']['totals'] == source_totals
        assert db.goal(goal['id'])['last_success'] == accepted['id']
        state = read_status()
        if not repair_checked:
            assert state['state'] == 'checked_snapshot'
        new_version = state['accepted']['workflow_version']
        assert new_version and new_version != package['version']
        assert workflows.load(workflows.read(new_version, actor), actor)['status'] == 'ready'
        assert accepted['result']['update']['recomputed_stages'] == ['preparation','validation','answer']
        cases.append({'case':'safe format repair','run_id':accepted['id'],'version':new_version,'totals':source_totals})
        if not repair_checked:
            browser('accepted-repair', 'checked snapshot')

        progress('missing required field')
        def missing(result):
            result['tables_collected'][0]['fields'] = [f for f in result['tables_collected'][0]['fields'] if f['name'] != quantity]
        failed = execute(replace_collection('missing-field', metadata=missing))
        assert failed['status'] == 'partial' and failed['result']['update']['review']['kind'] == 'schema'
        assert db.goal(goal['id'])['last_success'] == accepted['id']
        assert read_status()['accepted']['run_id'] == accepted['id']
        cases.append({'case':'missing field requires review','run_id':failed['id']})
        browser('missing-field', 'review required', 'Restore the required source fields')

        progress('unreconciled source coverage')
        def missing_page(result):
            result['inputs'].pop()
        failed = execute(replace_collection('lost-page', metadata=missing_page))
        assert failed['status'] == 'partial' and failed['result']['update']['review']['kind'] == 'quality'
        assert db.goal(goal['id'])['last_success'] == accepted['id']
        cases.append({'case':'lost records require reconciliation','run_id':failed['id']})

        progress('invalid source value')
        def invalid(page):
            page['rows'][0][page['columns'].index(quantity)] = 'not-a-number'
        failed = execute(replace_collection('invalid-number', invalid))
        assert failed['status'] == 'partial' and failed['result']['update']['review']['kind'] == 'quality', failed.get('result')
        assert db.goal(goal['id'])['last_success'] == accepted['id']
        cases.append({'case':'invalid value requires review','run_id':failed['id']})

        progress('interruption and recovery')
        interrupted_input = replace_collection('interrupted-format', format_quantity)
        interrupted = execute(interrupted_input, interrupted=True)
        assert interrupted['status'] in ('partial','cancelled')
        assert db.goal(goal['id'])['last_success'] == accepted['id']
        recovered = execute(interrupted_input)
        assert recovered['id'] == interrupted['id'] and recovered['status'] == 'succeeded', recovered.get('error')
        assert recovered['result']['calculation']['totals'] == source_totals
        assert recovered['result']['update']['reused_stages'] == ['preparation','validation']
        assert db.goal(goal['id'])['last_success'] == recovered['id']
        # An old successful invocation must not silently restore its earlier answer.
        assert workflows.invoke(package['version'], actor, safe_input)['id'] == accepted['id']
        assert db.goal(goal['id'])['last_success'] == recovered['id']
        cases.append({'case':'interruption reuses completed work','run_id':recovered['id']})

    progress('measured forecast deterioration')
    study = db.query("SELECT * FROM backintel.analysis_runs WHERE goal_id=%s AND body->>'operation'='method' AND status='succeeded' ORDER BY created_at DESC LIMIT 1", (goal['id'],), one=True)
    forecast_package = methods.save(study['id'], actor)
    actual = study['result']['method_study']['final_test']['actual']
    begin = datetime.fromisoformat(actual[-1]['start']).date()
    changed_index = None
    date_field = package['body']['method']['date_field']
    price_field = package['body']['method']['unit_price_field']
    for index in range(len(original['result']['inputs'])-1, -1, -1):
        page = json.loads(retained_input(original['result']['inputs'][index]['raw_input_id'], actor)['payload'])
        d, p = page['columns'].index(date_field), page['columns'].index(price_field)
        if any(begin <= source_date(row[d]) < begin+timedelta(days=7) and Decimal(str(row[p])) != 0 for row in page['rows']):
            changed_index = index
            break
    assert changed_index is not None
    def deterioration(page):
        q, d, p = page['columns'].index(quantity), page['columns'].index(date_field), page['columns'].index(price_field)
        for row in page['rows']:
            if begin <= source_date(row[d]) < begin+timedelta(days=7) and Decimal(str(row[p])) != 0:
                row[q] = '1000000000000'
                return
        raise AssertionError('No selected forecast observation')
    failed = execute(replace_collection('forecast-deterioration', deterioration, index=changed_index), forecast_package['version'])
    assert failed['status'] == 'partial' and failed['result']['update']['review']['kind'] == 'method_performance', failed.get('result')
    assert db.goal(goal['id'])['last_success'] == recovered['id']
    assert read_status()['state'] == 'review_required'
    cases.append({'case':'worse measured error requires review','run_id':failed['id'], 'measurement':failed['result']['update']['review']['details']})
    browser('method-deterioration', 'review required', 'Review the worse measured forecast error')
    progress('completed')
    return {'status':'passed','cases':cases,'scope':'Real saved-workflow execution over all retained historical retail rows; controlled source-change and interruption fixtures; no live upstream collection claim.',
            'accepted_answer_run_id':recovered['id'],'source_rows':original['result']['coverage']['expected_rows']}
