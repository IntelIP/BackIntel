"""Prepare collected source rows in the existing isolated execution boundary."""
from decimal import Decimal
import hashlib
import os
from pathlib import Path
import time

from runtime import analysis_store as db, sandbox
from runtime.analysis_data import digest
from runtime.source_access import require_source_access
from runtime.source_inputs import parse_response, retained_input
from runtime.source_semantics import validate_proposal


def preparation_recipe(interpretation, objective):
    proposal, profile = interpretation['interpretation'], interpretation['profile']
    validate_proposal(proposal, profile, objective)
    meanings = {(table['schema_name'], table['table_name']): table for table in proposal['tables']}
    tables = []
    for observed in profile['tables']:
        meaning = meanings[(observed['schema_name'], observed['table_name'])]
        fields = {field['name']: field for field in meaning['fields']}
        configured = []
        for field in observed['fields']:
            semantic = fields[field['name']]
            operation = 'preserve'
            if semantic['confidence'] == 'supported':
                if semantic['role'] in ('quantity', 'unit_price', 'measure'):
                    operation = 'decimal'
                elif semantic['role'] == 'date' and semantic['date_format']:
                    operation = semantic['date_format']
            configured.append({'name': field['name'], 'operation': operation,
                               'role': semantic['role'], 'unit': semantic['unit'],
                               'confidence': semantic['confidence'], 'limitations': semantic['limitations']})
        tables.append({'schema': observed['schema_name'], 'table': observed['table_name'],
                       'identity_column': observed['identity_column'], 'fields': configured})
    return {'version': 1, 'on_error': 'stop', 'tables': tables,
            'decimal_encoding': 'Exact decimal strings; never binary floating point.',
            'missing_values': 'Preserve null, empty and whitespace-only source values.',
            'classification': 'Retain source categories; uncertain meanings remain unclassified.',
            'timezone': 'Preserve source offsets or wall-clock values; never infer a timezone.'}


def validate_page(page, original):
    for key in ('raw_input_id', 'schema', 'table', 'columns', 'identity_column'):
        if page.get(key) != original[key]:
            raise ValueError('Prepared page changed its source binding')
    rows = page.get('rows')
    if not isinstance(rows, list) or len(rows) != len(original['rows']):
        raise ValueError('Preparation lost or added source rows')
    index = original['columns'].index(original['identity_column'])
    for values, source in zip(rows, original['rows']):
        if not isinstance(values, list) or len(values) != len(original['columns']) or values[index] != source[index]:
            raise ValueError('Preparation changed source identities or row widths')
    unresolved = page.get('unresolved')
    if not isinstance(unresolved, list):
        raise ValueError('Preparation must report unresolved conversions')
    seen = set()
    for issue in unresolved:
        row = issue.get('index')
        fields = issue.get('fields')
        if isinstance(row, bool) or not isinstance(row, int) or not 0 <= row < len(rows) or row in seen:
            raise ValueError('Invalid unresolved row reference')
        if not isinstance(fields, list) or not fields or len(set(fields)) != len(fields) or not set(fields).issubset(original['columns']):
            raise ValueError('Invalid unresolved field reference')
        seen.add(row)
    return page


def prepared_page(identity, page_key, actor):
    run = db.run(identity)
    if run['body']['operation'] not in ('preparation','workflow','coordination'):
        raise ValueError('Prepared pages belong to preparation runs')
    with db.connect() as control, control.transaction():
        require_source_access(run['goal_id'], actor, connection=control, expected_version=run['goal_version'])
        saved = db.step(identity, page_key)
        if not saved or 'page' not in saved or digest(saved['page']) != saved.get('sha256'):
            raise ValueError('Unknown or changed prepared page')
        return saved['page']


def _execute(identity, recipe, pages, image, deadline, attempt):
    remaining = int(deadline - time.monotonic())
    if remaining < 1:
        raise ValueError('Preparation time limit reached; retained pages remain resumable')
    db.check_run(identity)
    source = Path(__file__).with_name('preparation_worker.py').read_text()
    receipt = sandbox.run_candidate(source, {'recipe': recipe, 'pages': pages}, image,
                                    purpose='preparation', timeout_seconds=remaining)
    result = receipt.pop('result')
    stdout = receipt.pop('stdout', '')
    receipt['stdout_sha256'] = hashlib.sha256(stdout.encode()).hexdigest()
    receipt['recipe_sha256'] = digest(recipe)
    db.check_run(identity)
    job_attempt = db.query('SELECT attempts FROM backintel.capability_jobs WHERE job_id=%s', (db.run(identity)['job_id'],), one=True)['attempts']
    db.save_step(identity, f'preparation-execution-{job_attempt}-{attempt}', 'preparation_execution', receipt)
    if receipt['status'] != 'candidate' or result is None:
        raise ValueError('Isolated preparation failed: ' + str(receipt['stop_reason']))
    return result


def coverage(identity):
    contract = db.step(identity, 'preparation-contract')
    expected = db.run(contract['collection_run_id'])['result']['coverage']['expected_rows'] if contract else None
    counts = db.query("""SELECT count(*) AS pages, COALESCE(sum(COALESCE((body->>'row_count')::bigint,
        jsonb_array_length(body->'page'->'rows'))),0) AS rows FROM backintel.analysis_steps
        WHERE run_id=%s AND kind='prepared_page'""", (identity,), one=True)
    return {'expected_rows':expected,'collected_rows':expected,'processed_rows':int(counts['rows']),
            'retained_pages':counts['pages'],'excluded_rows':0,'failed_rows':0,
            'pending_rows':max(0,expected-int(counts['rows'])) if expected is not None else None}


def prepare(identity, *, workflow=None, collection_id=None, interpretation=None, collected=None):
    started = time.monotonic()
    run, goal = db.check_run(identity)
    if run['body']['operation'] not in ('preparation','workflow','coordination') or (run['body']['operation']=='workflow') != (workflow is not None):
        raise ValueError('Preparation requires a preparation job')
    actor = {'id': run['owner']}
    if run['body']['operation'] == 'coordination' and (interpretation is None or collected is None):
        raise ValueError('Coordination must pin its interpretation and collection')
    interpretation = interpretation or (db.run(workflow['accepted']['interpretation']['run_id']) if workflow else
                      db.query("SELECT id,result FROM backintel.analysis_runs WHERE goal_id=%s AND goal_version=%s AND status='succeeded' AND body->>'operation'='interpretation' ORDER BY created_at DESC LIMIT 1",
                               (goal['id'], run['goal_version']), one=True))
    if not interpretation:
        raise ValueError('Interpret the collected source before preparing it')
    collected = collected or db.run(collection_id or interpretation['result']['profile']['collection_run_id'])
    if collected['status'] != 'succeeded':
        raise ValueError('Preparation requires a complete source collection')
    recipe = workflow['preparation'] if workflow else preparation_recipe(interpretation['result'], goal['body']['objective'])
    image = workflow['dependencies']['image'] if workflow else os.getenv('BACKINTEL_PREPARATION_IMAGE')
    if not image:
        raise RuntimeError('The operator must select an existing isolated preparation image')
    image = sandbox.resolve_image(image)
    contract = {'recipe': recipe, 'image': image, 'interpretation_run_id': interpretation['id'],
                'collection_run_id': collected['id'],
                'worker_sha256': hashlib.sha256(Path(__file__).with_name('preparation_worker.py').read_bytes()).hexdigest()}
    prior = db.step(identity, 'preparation-contract')
    if prior is not None and prior != contract:
        raise ValueError('Preparation context changed; retained steps were not reused')
    db.save_step(identity, 'preparation-contract', 'preparation_contract', contract)
    deadline = started + goal['body']['objective']['limits']['timeout_seconds']
    pending, accepted, original_pages, total_bytes = [], [], {}, 0
    for item in collected['result']['inputs']:
        db.check_run(identity)
        if time.monotonic() > deadline:
            raise ValueError('Preparation time limit reached; retained pages remain resumable')
        original = retained_input(item['raw_input_id'], actor)
        total_bytes += original['body']['bytes']
        if total_bytes > goal['body']['objective']['limits']['max_source_bytes']:
            raise ValueError('Preparation input exceeds the agreed source-byte limit')
        envelope, _ = parse_response(original['payload'])
        if workflow:
            table = next((table for table in recipe['tables'] if (table['schema'],table['table'])==(item['schema'],item['table'])),None)
            if (table is None or set(envelope['columns'])!={field['name'] for field in table['fields']}
                    or len(envelope['columns'])!=len(table['fields']) or envelope['identity_column']!=table['identity_column']):
                raise ValueError('Collected fields or row identity differ from the saved workflow input contract')
        page = {'raw_input_id': item['raw_input_id'], 'schema': item['schema'], 'table': item['table'],
                'columns': envelope['columns'], 'identity_column': envelope['identity_column'],
                'rows': [[str(value) if isinstance(value, Decimal) else value for value in row] for row in envelope['rows']]}
        key = 'prepared-page-' + page['raw_input_id']
        saved = db.step(identity, key)
        original_pages[page['raw_input_id']] = page
        if saved is not None:
            if digest(saved['page']) != saved['sha256']:
                raise ValueError('A retained prepared page failed its integrity check')
            accepted.append(validate_page(saved['page'], page))
        else:
            pending.append(page)
    reused_pages = len(accepted)
    reused_rows = sum(len(page['rows']) for page in accepted)
    repaired = bool(db.step(identity, 'preparation-repair'))
    if repaired:
        recipe = {**recipe, 'on_error': 'retain_unresolved'}
    if pending:
        result = _execute(identity, recipe, pending, image, deadline, 'repair' if repaired else 'initial')
        if result.get('status') == 'needs_repair' and not repaired:
            recipe = {**recipe, 'on_error': 'retain_unresolved'}
            db.save_step(identity, 'preparation-repair', 'preparation_repair',
                         {'reason': 'Conversion failed; preserve the original value and mark it unresolved.',
                          'conversion_failures': result['conversion_failures'], 'recipe': recipe})
            repaired = True
            result = _execute(identity, recipe, pending, image, deadline, 'repair')
        if result.get('status') != 'prepared':
            raise ValueError('Preparation did not produce reusable tables')
        returned = result.get('pages', [])
        if len(returned) != len(pending) or {page['raw_input_id'] for page in returned} != {page['raw_input_id'] for page in pending}:
            raise ValueError('Preparation must cover exactly the pending source pages')
        for page in returned:
            validate_page(page, original_pages[page['raw_input_id']])
            db.check_run(identity)
            db.save_step(identity, 'prepared-page-' + page['raw_input_id'], 'prepared_page',
                         {'sha256': digest(page), 'row_count':len(page['rows']), 'page': page})
            accepted.append(page)
    processed = sum(len(page['rows']) for page in accepted)
    expected = collected['result']['coverage']['expected_rows']
    if processed != expected:
        raise ValueError('Prepared rows do not reconcile with the complete collection')
    db.check_run(identity)
    result = {'status': 'succeeded', 'mode': interpretation['result']['mode'], 'summary': f'Prepared {processed} source rows with retained originals.',
              'goal_version': run['goal_version'], 'source_ref': goal['body']['objective']['source_ref'],
              'recipe': recipe, 'image': image, 'interpretation_run_id': interpretation['id'], 'collection_run_id': collected['id'],
              'pages': [{'key': 'prepared-page-' + page['raw_input_id'], 'raw_input_id': page['raw_input_id'],
                         'schema': page['schema'], 'table': page['table'], 'row_count': len(page['rows']),
                         'sha256': digest(page)} for page in accepted],
              'coverage': {'expected_rows': expected, 'processed_rows': processed, 'excluded_rows': 0, 'failed_rows': 0, 'pending_rows': 0},
              'unresolved_rows': sum(len(page['unresolved']) for page in accepted), 'repaired': repaired,
              'reused_pages':reused_pages,'reused_rows':reused_rows,
              'elapsed_seconds': round(time.monotonic() - started, 3), 'usage': db.usage(identity),
              'limitations': ['Preparation is not semantic acceptance or a business answer. Independent meaning checks must pass before analysis.',
                              'Uncertain meanings and failed conversions remain explicit; no source rows or categories were silently removed.',
                              *interpretation['result']['interpretation']['unresolved']]}
    result['evidence_id'] = db.evidence(identity, 'source_preparation', digest(result), result)
    return result
