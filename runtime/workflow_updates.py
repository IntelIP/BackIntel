"""Conservative refresh policy for the existing saved-workflow executor."""
from copy import deepcopy
from datetime import datetime
from decimal import Decimal
import time

from psycopg.types.json import Jsonb

from runtime import analysis_store as db
from runtime.analysis_data import digest
from runtime.evidence import Evidence


POLICY = 'Preserve source values and declared business meanings. Missing fields, failed reconciliation, or worse measured forecast error require review.'


class ReviewRequired(ValueError):
    pass


def reject(identity, kind, decision, details=None):
    db.save_step(identity, 'workflow-update-review', 'workflow_update_review',
                 {'kind': kind, 'decision': decision, 'details': details or {}})
    raise ReviewRequired(decision)


def begin(identity, body, binding, collection):
    previous = db.run(body['accepted']['collection']['run_id'])['result']
    old_pages = {page['sha256'] for page in previous['inputs']}
    report = {
        'policy': POLICY, 'status': 'checking', 'input_ref': binding['input_ref'],
        'previous_input_ref': body['accepted']['collection']['run_id'],
        'source_time': collection['observed_at'], 'previous_source_time': previous['observed_at'],
        'changed_input': binding['input_ref'] != body['accepted']['collection']['run_id'],
        'unchanged_source_pages': sum(page['sha256'] in old_pages for page in collection['inputs']),
        'changed_source_pages': sum(page['sha256'] not in old_pages for page in collection['inputs']),
        'definitions_reused': ['field meanings', 'preparation rules', 'analysis method'],
        'reused_stages': [], 'recomputed_stages': [], 'source_changes': collection.get('changes'),
    }
    db.save_step(identity, 'workflow-update-contract', 'workflow_update_contract', report)
    covered = collection['coverage']['expected_rows']
    if (sum(page['row_count'] for page in collection['inputs']) != covered
            or sum(table['expected_rows'] for table in collection['tables_collected']) != covered):
        reject(identity, 'quality', 'Reconcile the retained source records and complete source counts before accepting this update.')
    expected = {(table['schema'], table['table']): table for table in body['preparation']['tables']}
    actual = {(table['schema'], table['table']): table for table in collection['tables_collected']}
    changes = []
    for key, table in expected.items():
        incoming = actual.get(key)
        names = {field['name'] for field in table['fields']}
        found = {field['name'] for field in incoming['fields']} if incoming else set()
        if names != found or not incoming or table['identity_column'] != incoming['identity_column']:
            changes.append({'table': '.'.join(key), 'missing_fields': sorted(names - found),
                            'uninterpreted_fields': sorted(found - names),
                            'identity_changed': bool(incoming and table['identity_column'] != incoming['identity_column'])})
    if changes or actual.keys() != expected.keys():
        reject(identity, 'schema', 'Restore the required source fields and row identity, or approve a new field interpretation before accepting this update.', {'changes': changes})
    return report


def finish(identity, report, result, prepared, checked):
    if checked['status'] != 'passed' or prepared['unresolved_rows']:
        reject(identity, 'quality', 'Resolve the failed value or reconciliation checks before accepting this update.')
    report.update(status='checked', source_rows=checked['source_rows'],
                  preparation_repaired=prepared['repaired'], validation=checked['summary'],
                  method_check=result.get('method_check'))
    result['update'] = report
    db.save_step(identity, 'workflow-update-checked', 'workflow_update_checked', report)
    return result


def method_check(weeks, selected, reference, image, execute):
    """Measure the unchanged method; never search or tune against new outcomes."""
    from runtime.source_methods import baseline, score
    if len(weeks) < 8:
        return {'status': 'review_required', 'decision': 'Restore enough complete weeks to measure the accepted method.'}
    history, actual = weeks[:-4], weeks[-4:]
    output = ({'status': 'valid', 'predictions': baseline(history)} if selected['kind'] == 'baseline'
              else execute(selected, history, image))
    if output['status'] != 'valid':
        return {'status': 'review_required', 'decision': 'Review the saved method because it could not produce valid comparison forecasts.'}
    if actual == reference['actual'] and output['predictions'] == reference['execution']['predictions']:
        return {'status': 'unchanged_observations', 'summary': 'The accepted evaluation observations and predictions are unchanged; no new performance claim.'}
    measured = score(output['predictions'], actual)
    limit = reference['selected']['mean_absolute_weekly_error']
    worse = Decimal(measured['mean_absolute_weekly_error']) > Decimal(limit)
    return {'status': 'review_required' if worse else 'passed', 'metric': 'mean_absolute_weekly_error',
            'currency': 'GBP', 'accepted_error': limit, 'measured': measured,
            'period_start': actual[0]['start'], 'period_end': actual[-1]['start'],
            'decision': 'Review the worse measured forecast error before accepting another forecast; the saved method has not been changed.' if worse else None,
            'summary': 'Measured the unchanged saved method on the latest four complete weeks; no candidate search or promotion.'}


def failed(identity, reason, status):
    report = deepcopy(db.step(identity, 'workflow-update-contract') or {'policy': POLICY})
    review = db.step(identity, 'workflow-update-review')
    validation = db.step(identity, 'validation-report')
    if review is None and ((validation and validation['status'] != 'passed') or db.step(identity, 'preparation-repair')):
        review = {'kind': 'quality', 'decision': 'Resolve the failed value or reconciliation checks before accepting this update.',
                  'details': {'failure_groups': validation['failure_groups'] if validation else []}}
    report.update(status='review_required' if review else 'interrupted' if status == 'partial' else 'failed',
                  error=reason, review=review,
                  decision=review['decision'] if review else 'Resume the interrupted update.' if status == 'partial' else 'Resolve the failed update and run it again.')
    return report


def collection_for(run, *, connection=None):
    if not run:
        return None
    if run['body']['operation'] == 'collection':
        return run
    ref = run['body'].get('input_ref')
    if not ref:
        calculation = (run.get('result') or {}).get('calculation')
        if calculation:
            prepared = db.run(calculation['preparation_run_id'], connection=connection)
            ref = prepared['result']['collection_run_id']
    return db.run(ref, connection=connection) if ref else None


def guard_publication(run, goal, connection):
    if run['body']['question'] != goal['body']['question'] or not goal['last_success']:
        return
    accepted = collection_for(db.run(goal['last_success'], connection=connection), connection=connection)
    incoming = collection_for(run, connection=connection)
    if accepted and incoming and datetime.fromisoformat(accepted['result']['observed_at']) > datetime.fromisoformat(incoming['result']['observed_at']):
        reject(run['id'], 'older_source', 'A newer source answer is already accepted. Keep it or explicitly revise the objective before replacing it with older information.')


def save_version(identity, result, connection):
    from runtime import source_workflows as workflows
    if not result['update']['changed_input']:
        return None
    run = db.run(identity, connection=connection)
    store = Evidence(connection, 'analysis-goal-' + run['goal_id'])
    original = store.find('workflow_package', run['body']['workflow_version'])
    body = deepcopy(workflows.validate_package(original['body'])['body'])
    prepared = db.step(identity, 'workflow-preparation')['value']
    checked = db.step(identity, 'workflow-validation')['value']
    if run['status'] != 'succeeded' or checked['status'] != 'passed':
        raise ValueError('Only a successful checked update can create a repaired workflow version')
    collected = db.run(run['body']['input_ref'], connection=connection)
    body['preparation'] = prepared['recipe']
    for name in ('preparation', 'validation', 'forecast' if body.get('kind') == 'forecast' else 'answer'):
        body['accepted'][name] = {'run_id': identity, 'result_sha256': digest(result)}
    body['accepted']['collection'] = {'run_id': collected['id'], 'result_sha256': digest(collected['result'])}
    body['source_links'] = [{'input_id': page['raw_input_id'], 'prepared_sha256': page['sha256'],
                             'row_count': page['row_count'], 'original': '/api/v1/inputs/' + page['raw_input_id'] + '/original'}
                            for page in prepared['pages']]
    body['calculation_evidence_id'] = result['evidence_id']
    if 'calculation' in result:
        body['source_fingerprint'] = result['calculation']['source_fingerprint']
    body['update'] = {'run_id': identity, 'previous_version': run['body']['workflow_version'], **result['update']}
    package = workflows.package_body(body)
    existing = store.find('workflow_package', package['version'])
    if existing and existing['body'] != package:
        raise ValueError('A saved workflow version cannot be replaced')
    if not existing:
        store.put('workflow_package', package['version'], package, int(time.time()), parents=[result['evidence_id']])
    connection.execute('INSERT INTO backintel.analysis_events(run_id,kind,body) VALUES(%s,%s,%s)',
                       (identity, 'workflow_version', Jsonb({'version': package['version'], 'previous_version': run['body']['workflow_version']})))
    return package['version']


def status(goal):
    latest = db.query("""SELECT * FROM backintel.analysis_runs WHERE goal_id=%s AND goal_version=%s
        AND body->>'operation' IN ('collection','answer','workflow','refresh') ORDER BY created_at DESC LIMIT 1""",
        (goal['id'], goal['version']), one=True)
    question = latest['body']['question'] if latest and latest['body']['operation'] != 'collection' else goal['body']['question']
    accepted = db.query("""SELECT * FROM backintel.analysis_runs WHERE goal_id=%s AND goal_version=%s
        AND body->>'operation' IN ('answer','workflow') AND body->>'question'=%s AND status='succeeded'
        ORDER BY created_at DESC LIMIT 1""", (goal['id'], goal['version'], question), one=True)
    source = collection_for(accepted)
    report = (latest.get('result') or {}).get('update') if latest else None
    continuation_error = db.step(latest['id'], 'refresh-workflow-error') if latest and latest['body']['operation'] == 'refresh' else None
    if continuation_error and not db.step(latest['id'], 'refresh-workflow'):
        report = {'decision': continuation_error['decision']}
    state = ('checked_snapshot' if latest and accepted and latest['id'] == accepted['id'] else
             'review_required' if report and report.get('review') else
             'update_failed' if continuation_error or latest and latest['status'] in ('partial', 'failed', 'denied', 'cancelled') else
             'update_pending' if latest else 'unanswered')
    version = db.query("SELECT body FROM backintel.analysis_events WHERE run_id=%s AND kind='workflow_version' ORDER BY sequence DESC LIMIT 1", (accepted['id'],), one=True) if accepted else None
    return {'state': state, 'question': question, 'policy': POLICY,
            'accepted': {'run_id': accepted['id'], 'summary': accepted['result']['summary'],
                         'source_time': source['result']['observed_at'] if source else None,
                         'workflow_version': version['body']['version'] if version else accepted['body'].get('workflow_version')} if accepted else None,
            'latest': {'run_id': latest['id'], 'status': latest['status'], 'started_at': latest['created_at'],
                       'error': latest['error'], 'report': report} if latest else None}
