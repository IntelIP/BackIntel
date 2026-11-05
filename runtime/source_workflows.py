"""Version the accepted procedure without copying source records or credentials."""
import hashlib
from importlib import metadata
from pathlib import Path
import subprocess
import sys
import time

from runtime import analysis_store as db, sandbox
from runtime.analysis_data import digest
from runtime.evidence import Evidence
from runtime.source_access import require_source_access

ROOT = Path(__file__).resolve().parents[1]
COMPONENTS = ('preparation_worker.py', 'source_preparation.py', 'source_validation.py', 'source_collection.py', 'source_changes.py',
              'source_answer.py', 'source_inputs.py', 'source_semantics.py', 'source_documents.py', 'analysis_data.py',
              'source_workflows.py', 'source_methods.py', 'workflow_updates.py', 'jobs.py', 'analysis_service.py', 'analysis_store.py', 'source_access.py')
FORMAT = 'backintel.workflow/v1'


def package_body(body):
    return {'format': FORMAT, 'version': digest(body), 'body': body}


def validate_package(package):
    if (not isinstance(package, dict) or set(package) != {'format', 'version', 'body'}
            or package['format'] != FORMAT or not isinstance(package['body'], dict)
            or package['version'] != digest(package['body'])):
        raise ValueError('Workflow package format or version digest is invalid')
    return package


def runtime_dependencies(image):
    return {'python': list(sys.version_info[:2]), 'image': image,
            'packages': {name: metadata.version(name) for name in ('psycopg', 'pydantic')},
            'components': {name: hashlib.sha256((ROOT / 'runtime' / name).read_bytes()).hexdigest()
                           for name in COMPONENTS}}


def dependency_issues(dependencies, *, root=ROOT):
    issues = []
    if list(sys.version_info[:2]) != dependencies['python']:
        issues.append('Use Python ' + '.'.join(map(str, dependencies['python'])) + ' for this workflow version.')
    for name, required in dependencies['packages'].items():
        try:
            installed = metadata.version(name)
        except metadata.PackageNotFoundError:
            installed = None
        if installed != required:
            issues.append(f'Required package {name}=={required} is missing or has changed.')
    if set(dependencies['components']) != set(COMPONENTS):
        issues.append('The workflow component contract is unsupported.')
    for name in COMPONENTS:
        path = root / 'runtime' / name
        if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != dependencies['components'].get(name):
            issues.append(f'Required runtime component {name} is missing or has changed; restore this version or save a newly checked workflow.')
    try:
        if sandbox.resolve_image(dependencies['image']) != dependencies['image']:
            issues.append('The required preparation image has changed.')
    except (OSError, ValueError, subprocess.SubprocessError):
        issues.append('The pinned preparation image is unavailable. Restore the approved local image before running.')
    return issues


def _authorize(body, actor, connection):
    goal, policy, _ = require_source_access(body['goal_id'], actor, connection=connection, read_only=True)
    objective = goal['body']['objective']
    if (body['connection']['source_ref'] != objective['source_ref']
            or body['connection']['secret_ref'] != policy['secret_ref']
            or not set(body['input_contract']['allowed_schemas']).issubset(objective['allowed_schemas'])):
        raise PermissionError('This workflow requires source access outside the current grant')
    return goal


def save(answer_id, actor):
    from runtime import source_documents
    if db.run(answer_id)['body']['operation'] == 'method':
        from runtime.source_methods import save as save_method
        return save_method(answer_id, actor)
    answer = db.run(answer_id)
    with db.connect() as connection, connection.transaction():
        goal, policy, _ = require_source_access(answer['goal_id'], actor, connection=connection,
                                                expected_version=answer['goal_version'])
        db.authorize(actor, goal['domain'], ('manager',), connection=connection)
        if answer['status'] != 'succeeded' or answer['body']['operation'] != 'answer':
            raise ValueError('Save a workflow only from an accepted connected-source answer')
        result = answer['result']
        calculation = result['calculation']
        checked = db.run(calculation['validation_run_id'])
        prepared = db.run(calculation['preparation_run_id'])
        interpreted = db.run(prepared['result']['interpretation_run_id'])
        collected = db.run(prepared['result']['collection_run_id'])
        runs = {'answer': answer, 'validation': checked, 'preparation': prepared,
                'interpretation': interpreted, 'collection': collected}
        if any(run['status'] != 'succeeded' or run['goal_id'] != goal['id']
               or run['goal_version'] != answer['goal_version'] for run in runs.values()):
            raise ValueError('Every workflow step must belong to the same accepted objective version')
        if (checked['result']['status'] != 'passed'
                or checked['result']['preparation_run_id'] != prepared['id']
                or digest(checked['result']) != calculation['validation_sha256']):
            raise ValueError('The answer no longer matches its accepted meaning check')
        objective = goal['body']['objective']
        documentary = source_documents.accepted_evidence(goal, interpreted['result'], actor)
        if documentary != result.get('document_evidence', []):
            raise ValueError('The answer no longer matches its accepted document evidence')
        body = {'goal_id': goal['id'], 'goal_version': answer['goal_version'], 'mode': result['mode'],
                'document_refs': goal['body'].get('document_refs', []), 'document_evidence': documentary,
                'question': answer['body']['question'], 'objective': objective,
                'connection': {'source_ref': objective['source_ref'], 'secret_ref': policy['secret_ref']},
                'input_contract': {'allowed_schemas': objective['allowed_schemas'],
                                   'expected_source_sha256': objective['expected_source_sha256'],
                                   'tables': prepared['result']['recipe']['tables'],
                                   'coverage': 'Every source row; no silent filtering, invented values or manual batches.'},
                'interpretation': interpreted['result']['interpretation'],
                'preparation': prepared['result']['recipe'], 'method': calculation['method'],
                'checks': objective['expected_checks'],
                'limits': {'source': objective['limits'], 'preparation': sandbox.PREPARATION_LIMITS,
                           'max_provider_usd': goal['body']['budget_usd']},
                'dependencies': runtime_dependencies(prepared['result']['image']),
                'output_contract': {'currency': calculation['currency'],
                                    'money_encoding': 'Exact decimal strings; round only for display.',
                                    'totals': sorted(calculation['totals']),
                                    'groups': [{'label': d['label'], 'field': d['field']} for d in calculation['dimensions']],
                                    'required': ['run_id', 'workflow_version', 'coverage', 'period', 'findings',
                                                 'evidence', 'usage', 'limitations'],
                                    'time_basis': 'Preserved source wall-clock dates; unknown timezone stays unknown.'},
                'accepted': {name: {'run_id': run['id'], 'result_sha256': digest(run['result'])}
                             for name, run in runs.items()},
                'source_links': [{'input_id': page['raw_input_id'], 'prepared_sha256': page['sha256'],
                                  'row_count': page['row_count'],
                                  'original': '/api/v1/inputs/' + page['raw_input_id'] + '/original'}
                                 for page in prepared['result']['pages']],
                'calculation_evidence_id': result['evidence_id'],
                'source_fingerprint': calculation['source_fingerprint'], 'limitations': result['limitations']}
        package = package_body(body)
        store = Evidence(connection, 'analysis-goal-' + goal['id'])
        existing = store.find('workflow_package', package['version'])
        if existing:
            if existing['body'] != package:
                raise ValueError('A saved workflow version cannot be replaced')
        else:
            store.put('workflow_package', package['version'], package, int(time.time()),
                      parents=[result['evidence_id']])
        return package


def history(goal_id, actor):
    with db.connect() as connection, connection.transaction():
        require_source_access(goal_id, actor, connection=connection, read_only=True)
        rows = Evidence(connection, 'analysis-goal-' + goal_id).list('workflow_package')
        result = []
        for row in rows:
            body = row['body']['body']
            try:
                _authorize(body, actor, connection)
            except PermissionError:
                continue
            result.append({'version': row['identity'], 'created_at': row['available_at'],
                           'goal_version': body['goal_version'], 'mode': body['mode'], 'question': body['question']})
        return result


def read(version, actor):
    row = db.query("SELECT task_id FROM backintel.capability_evidence WHERE kind='workflow_package' AND identity=%s",
                   (version,), one=True)
    if row is None:
        raise ValueError('This workflow version is not saved in the current execution context')
    with db.connect() as connection, connection.transaction():
        record = Evidence(connection, row['task_id']).find('workflow_package', version)
        package = validate_package(record['body'])
        _authorize(package['body'], actor, connection)
        return package


def load(package, actor):
    """Inspect a saved export in a permitted context; never install or execute it."""
    validate_package(package)
    if read(package['version'], actor) != package:
        raise ValueError('The supplied package differs from the saved workflow version')
    body = package['body']
    issues = dependency_issues(body['dependencies'])
    from runtime import source_documents
    try:
        source_documents.validate_references(body['goal_id'], body.get('document_refs', []), actor)
        if body.get('document_refs'):
            interpreted = db.run(body['accepted']['interpretation']['run_id'])['result']
            documentary = source_documents.accepted_evidence(
                {'id': body['goal_id'], 'body': {'document_refs': body['document_refs']}}, interpreted, actor)
            if documentary != body.get('document_evidence', []):
                raise ValueError('The saved document evidence differs from the retained interpretation')
    except ValueError as error:
        issues.append(str(error))
    for name, reference in body['accepted'].items():
        run = db.query('SELECT status,result FROM backintel.analysis_runs WHERE id=%s', (reference['run_id'],), one=True)
        if not run or run['status'] != 'succeeded' or digest(run['result']) != reference['result_sha256']:
            issues.append(f'The retained {name} result is missing or changed; restore its accepted evidence before reuse.')
    ids = [link['input_id'] for link in body['source_links']]
    retained = db.query('SELECT id FROM backintel.analysis_raw_inputs WHERE id=ANY(%s)', (ids,))
    if len({row['id'] for row in retained}) != len(set(ids)):
        issues.append('Some original source pages are unavailable; restore the retained source archive before reuse.')
    return {'status': 'ready' if not issues else 'unavailable', 'issues': issues, 'package': package}


def bind(version, input_ref, actor):
    package = read(version, actor)
    inspected = load(package, actor)
    if inspected['status'] != 'ready':
        raise ValueError('Workflow dependencies are unavailable: ' + '; '.join(inspected['issues']))
    body = package['body']
    goal = db.goal(body['goal_id'])
    if goal['version'] != body['goal_version']:
        raise ValueError('The objective changed; check and save a workflow for its current version')
    collection = db.run(input_ref or body['accepted']['collection']['run_id'])
    result = collection.get('result') or {}
    coverage = result.get('coverage', {})
    if (collection['body']['operation'] not in ('collection', 'refresh') or collection['status'] != 'succeeded'
            or collection['goal_id'] != body['goal_id'] or collection['goal_version'] != body['goal_version']
            or result.get('source_ref') != body['connection']['source_ref']):
        raise ValueError('Workflow inputs must be a successful permitted collection for this objective version')
    if (coverage.get('collected_rows') != coverage.get('expected_rows') or not coverage.get('expected_rows')
            or any(coverage.get(name, 0) for name in ('excluded_rows', 'failed_rows', 'pending_rows'))):
        raise ValueError('Workflow inputs must cover the complete source without unexplained exclusions')
    expected = {(table['schema'], table['table']) for table in body['input_contract']['tables']}
    if {(page['schema'], page['table']) for page in result['inputs']} != expected:
        raise ValueError('Collected tables differ from the saved workflow input contract')
    return {'workflow_version': version, 'input_ref': collection['id'], 'input_sha256': digest(result),
            'goal_id': body['goal_id'], 'goal_version': body['goal_version']}


def invoke(version, actor, input_ref=None):
    from runtime import analysis_service as service
    package = read(version, actor)
    return service.submit(package['body']['goal_id'], actor, question=package['body']['question'], operation='workflow',
                          workflow_version=version, input_ref=input_ref)


def update_status(goal_id, actor):
    from runtime.workflow_updates import status
    with db.connect() as connection, connection.transaction():
        goal, _, _ = require_source_access(goal_id, actor, connection=connection, read_only=True)
    return status(goal)


def refresh(version, actor, request_id, *, connection=None):
    """Queue current-source collection and its durable saved-workflow continuation."""
    from runtime import analysis_service as service
    package = read(version, actor)
    result = service.submit(package['body']['goal_id'], actor, question=package['body']['question'],
        operation='refresh', workflow_version=version, refresh_key=request_id, connection=connection)
    if connection is None and result['status'] == 'succeeded':
        continue_refresh(result['id'])
    return result


def continue_refresh(identity):
    """Idempotent continuation; the existing dispatcher recovers unfinished admission."""
    run = db.run(identity)
    if run['body']['operation'] != 'refresh' or run['status'] != 'succeeded':
        raise ValueError('Only a complete source refresh can start its saved workflow')
    child = invoke(run['body']['workflow_version'], {'id': run['owner']}, run['id'])
    retained = db.save_step(identity, 'refresh-workflow', 'refresh_workflow', {'run_id': child['id']})
    if retained['run_id'] != child['id']:
        raise ValueError('This refresh already belongs to a different saved-workflow invocation')
    return child


def execute(identity):
    from runtime import source_answer, source_preparation, source_validation, workflow_updates
    run, goal = db.check_run(identity)
    if run['body']['operation'] != 'workflow':
        raise ValueError('Saved workflow execution requires a workflow job')
    actor = {'id': run['owner']}
    binding = bind(run['body']['workflow_version'], run['body']['input_ref'], actor)
    if any(run['body'].get(key) != binding[key] for key in ('workflow_version', 'input_ref', 'input_sha256')):
        raise ValueError('Workflow inputs changed after admission; submit a new invocation')
    body = read(binding['workflow_version'], actor)['body']
    collection = db.run(binding['input_ref'])['result']
    interpretation = db.run(body['accepted']['interpretation']['run_id'])['result']
    update = workflow_updates.begin(identity, body, binding, collection)
    started = time.monotonic()

    def stage(name, work):
        db.check_run(identity)
        if time.monotonic() - started > goal['body']['objective']['limits']['timeout_seconds']:
            raise ValueError('Workflow time limit reached; completed stages remain resumable')
        cached = db.step(identity, 'workflow-' + name)
        if cached is not None:
            if digest(cached['value']) != cached['sha256']:
                raise ValueError('Retained workflow stage failed its integrity check')
            update['reused_stages'].append(name)
            return cached['value']
        db.event(identity, 'workflow_stage', {'stage': name, 'status': 'started'})
        value = work()
        db.save_step(identity, 'workflow-' + name, 'workflow_stage', {'value': value, 'sha256': digest(value)})
        db.event(identity, 'workflow_stage', {'stage': name, 'status': 'completed'})
        update['recomputed_stages'].append(name)
        return value

    prepared = stage('preparation', lambda: source_preparation.prepare(identity, workflow=body, collection_id=binding['input_ref']))
    checked = stage('validation', lambda: source_validation.check(identity, prepared={'id': identity, 'result': prepared},
                                                                 interpretation=interpretation, collection=collection))
    if body.get('kind') == 'forecast':
        from runtime.source_methods import forecast
        result = stage('forecast', lambda: forecast(identity, body, prepared, checked))
        from runtime import source_documents
        result['document_evidence'] = source_documents.accepted_evidence(goal, interpretation, actor)
        result.update(workflow_version=binding['workflow_version'], input_ref=binding['input_ref'])
        return workflow_updates.finish(identity, update, result, prepared, checked)
    result = stage('answer', lambda: source_answer.calculate(identity, body['method'], {'id': identity, 'result': prepared},
                                                             {'id': identity, 'result': checked}, interpretation,
                                                             mode=body['mode'], started=started))
    result.update(workflow_version=binding['workflow_version'], input_ref=binding['input_ref'],
                  coverage=result['calculation']['coverage'])
    return workflow_updates.finish(identity, update, result, prepared, checked)


def main():
    import argparse
    import json
    import os
    from runtime import analysis_service as service
    from runtime.analysis_errors import safe_error
    parser = argparse.ArgumentParser(description='Inspect or run an accepted BackIntel workflow.')
    parser.add_argument('action', choices=('inspect', 'run', 'status', 'refresh'))
    parser.add_argument('version')
    parser.add_argument('--input-ref', help='A complete permitted collection run; defaults to the accepted input.')
    parser.add_argument('--request-id', help='Required for refresh; reuse this identity to resume the same request.')
    parser.add_argument('--no-wait', action='store_true', help='Queue durably and return the run identity.')
    args = parser.parse_args()
    try:
        token = os.getenv('BACKINTEL_ACCESS_TOKEN')
        if not token:
            raise PermissionError('Set BACKINTEL_ACCESS_TOKEN from the existing approved credential store')
        actor = db.principal(token)
        if args.action == 'status':
            result = update_status(read(args.version, actor)['body']['goal_id'], actor)
        elif args.action == 'inspect':
            result = load(read(args.version, actor), actor)
        else:
            if args.action == 'refresh':
                if args.input_ref or not args.request_id:
                    raise ValueError('Refresh requires --request-id and collects the current source')
                result = refresh(args.version, actor, args.request_id)
            else:
                result = invoke(args.version, actor, args.input_ref)
            if not args.no_wait:
                service.dispatch(result['id'])
                result = db.run(result['id'])
                if args.action == 'refresh':
                    followup = db.step(result['id'], 'refresh-workflow')
                    if followup:
                        result = db.run(followup['run_id'])
                with db.connect() as connection, connection.transaction():
                    require_source_access(result['goal_id'], actor, connection=connection,
                                          expected_version=result['goal_version'])
        print(json.dumps(result, default=str))
        return 0 if args.action == 'status' or result.get('status') in ('ready', 'queued', 'running', 'succeeded') else 1
    except Exception as error:
        print(json.dumps({'status': 'failed', 'error': safe_error(error)}))
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
