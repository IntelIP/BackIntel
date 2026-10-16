"""Real PostgreSQL changes and independent totals; only interruption is injected."""
from datetime import datetime, timedelta, timezone
from decimal import Decimal
import json
from pathlib import Path
import subprocess
from unittest.mock import patch

import psycopg
from psycopg import sql
from psycopg.conninfo import make_conninfo

from runtime import analysis_store as db, analysis_service as service, source_workflows as workflows, workflow_triggers as triggers
from runtime.jobs import execute as execute_job
from runtime.source_inputs import retained_input, parse_response


def check_incremental(actor, source, package, client, base, token, env, output, source_owner_uri):
    goal = db.goal(source['goal_id'])
    cases = []
    version = package['version']
    method = package['body']['method']

    def progress(name):
        (output/'progress.json').write_text(json.dumps({'case': name, 'completed': cases}, default=str))

    def browser(name, state='checked snapshot', start=False):
        result = subprocess.run(['node', str(Path(__file__).with_name('workflow_incremental_browser.cjs'))],
            env={**env, 'S24_URL':base, 'S24_TOKEN':token, 'S24_DOMAIN':goal['domain'],
                 'S24_QUESTION':goal['body']['question'], 'S24_VERSION':version, 'S24_CASE':name,
                 'S24_STATE':state, 'S24_START':'1' if start else '', 'S24_OUTPUT':str(output)},
            capture_output=True, timeout=1100)
        (output/(name+'-browser.log')).write_bytes(result.stdout+result.stderr)
        assert result.returncode == 0, 'Inspect '+name+'-browser.log'

    def finish(parent):
        service.dispatch(parent['id'])
        collected = db.run(parent['id'])
        assert collected['status'] == 'succeeded', collected.get('error')
        link = db.step(parent['id'], 'refresh-workflow')
        assert link, db.step(parent['id'], 'refresh-workflow-error')
        answered = db.run(link['run_id'])
        assert answered['status'] == 'succeeded', answered.get('error')
        assert db.goal(goal['id'])['last_success'] == answered['id']
        assert workflows.update_status(goal['id'], actor)['state'] == 'checked_snapshot'
        return collected, answered

    def reconcile(answer):
        relation = sql.SQL('{}.{}').format(sql.Identifier(method['schema_name']), sql.Identifier(method['table_name']))
        amount = sql.SQL('{}::numeric * {}::numeric').format(sql.Identifier(method['quantity_field']), sql.Identifier(method['unit_price_field']))
        cancelled = sql.SQL('CASE WHEN left(lower({}::text), %s)=%s THEN {} ELSE 0 END').format(sql.Identifier(method['invoice_field']), amount)
        prefix = method['cancellation_prefix'].lower()
        with psycopg.connect(source_owner_uri) as owner:
            count, net, cancellation = owner.execute(sql.SQL('SELECT count(*),sum({}),sum({}) FROM {}').format(amount, cancelled, relation), (len(prefix), prefix)).fetchone()
            result = answer['result']['calculation']
            expected = {'net_invoice_value': net, 'signed_cancellation_value': cancellation,
                        'value_without_cancellations': net-cancellation, 'cancellation_reduction': -cancellation}
            assert {key: Decimal(value) for key, value in result['totals'].items()} == expected
            assert result['coverage'] == {'expected_rows':count, 'processed_rows':count, 'excluded_rows':0, 'failed_rows':0, 'pending_rows':0}
            for dimension in result['dimensions']:
                field = sql.Identifier(dimension['field'])
                rows = owner.execute(sql.SQL('SELECT {},count(*),sum({}),sum({}) FROM {} GROUP BY {}').format(field, amount, cancelled, relation, field), (len(prefix), prefix)).fetchall()
                assert {value:(n, total, canc) for value,n,total,canc in rows} == {
                    item['value']:(item['row_count'], Decimal(item['net_value']), Decimal(item['signed_cancellation_value'])) for item in dimension['groups']}
        return {'rows':count, 'totals':result['totals'], 'all_product_and_country_groups_match':True}

    progress('application refresh from real source')
    # A compatible string-storage change requires a disclosed full reread;
    # original values, row identities, and the business definition stay unchanged.
    with psycopg.connect(source_owner_uri) as owner:
        owner.execute('ALTER TABLE retail_raw.invoice_lines ALTER COLUMN "Description" TYPE varchar')
    browser('application-refresh', start=True)
    parent = db.query("SELECT * FROM backintel.analysis_runs WHERE goal_id=%s AND body->>'operation'='refresh' ORDER BY created_at DESC LIMIT 1", (goal['id'],), one=True)
    initial, accepted = finish(parent)
    assert initial['result']['changes']['value_rows_read'] == 541909
    assert initial['result']['changes']['full_rereads']
    assert initial['result']['changes']['unchanged'] == 541909
    cases.append({'case':'application refresh', 'collection_run_id':initial['id'], 'answer_run_id':accepted['id'],
                  'changes':initial['result']['changes'], 'reconciliation':reconcile(accepted)})
    progress('real additions corrections deletions and interrupted collection')
    with psycopg.connect(source_owner_uri) as owner:
        owner.execute('UPDATE retail_raw.invoice_lines SET "Quantity"=("Quantity"::numeric+7)::text WHERE source_row_id=1')
        owner.execute('DELETE FROM retail_raw.invoice_lines WHERE source_row_id=2')
        owner.execute('INSERT INTO retail_raw.invoice_lines SELECT 541910,"InvoiceNo","StockCode","Description","Quantity","InvoiceDate","UnitPrice","CustomerID","Country" FROM retail_raw.invoice_lines WHERE source_row_id=3')
    changing = workflows.refresh(version, actor, 'S24-changed-records')
    def interrupt_collection(store, payload):
        real_save = db.save_step
        def stop_after_page(identity, key, kind, body):
            result = real_save(identity, key, kind, body)
            if kind == 'source_page':
                raise InterruptedError('Controlled interruption after retaining a real source page')
            return result
        with patch.object(db, 'save_step', side_effect=stop_after_page):
            return service.handle(store, payload)
    execute_job(changing['job_id'], interrupt_collection, max_wall_seconds=900)
    interrupted = db.run(changing['id'])
    assert interrupted['status'] in ('partial', 'cancelled'), interrupted.get('error')
    assert db.goal(goal['id'])['last_success'] == accepted['id']
    assert workflows.update_status(goal['id'], actor)['state'] == 'update_failed'
    browser('interrupted-collection', 'update failed')
    assert workflows.refresh(version, actor, 'S24-changed-records')['id'] == changing['id']
    changed, answered = finish(changing)
    stats = changed['result']['changes']
    assert (stats['inserted'], stats['corrected'], stats['deleted'], stats['value_rows_read']) == (1, 1, 1, 2), stats
    assert stats['metadata_rows_scanned'] == 541909 and stats['unchanged'] == 541907
    assert changed['result']['reused_pages'] > 0
    history = db.query("SELECT body FROM backintel.analysis_steps WHERE run_id=%s AND kind='source_changes'", (changed['id'],))
    response = client.get('/api/v1/runs/'+changed['id']+'/source-changes')
    response.raise_for_status()
    assert len(response.json()['changes']) == 3
    assert {row['change']['kind'] for row in response.json()['changes']} == {'inserted', 'corrected', 'deleted'}
    for kind, key in (('deleted','integer:2'), ('corrected','integer:1')):
        entry = next(item for row in history for item in row['body']['changes'] if item['kind']==kind and item['key']==key)
        raw = retained_input(entry['original_input_id'], actor)
        assert key in parse_response(raw['payload'])[1]
    assert db.run(initial['id'])['result'] == initial['result']
    count_before = db.query('SELECT count(*) AS count FROM backintel.analysis_runs', one=True)['count']
    assert workflows.refresh(version, actor, 'S24-changed-records')['id'] == changed['id']
    assert db.query('SELECT count(*) AS count FROM backintel.analysis_runs', one=True)['count'] == count_before
    state = client.get('/api/v1/goals/'+goal['id']+'/update-status'); state.raise_for_status()
    assert state.json()['accepted'] == workflows.update_status(goal['id'], actor)['accepted']
    cases.append({'case':'insert correct delete interruption and duplicate request', 'collection_run_id':changed['id'],
                  'answer_run_id':answered['id'], 'changes':stats, 'originals_retained':True, 'reconciliation':reconcile(answered)})
    browser('changed-source')
    progress('collection failure keeps accepted answer')
    with psycopg.connect(source_owner_uri) as owner:
        owner.execute('REVOKE SELECT ON retail_raw.invoice_lines FROM retail_reader')
    failed = workflows.refresh(version, actor, 'S24-read-denied')
    service.dispatch(failed['id'])
    failure = db.run(failed['id'])
    assert failure['status'] in ('partial', 'cancelled'), failure.get('error')
    assert db.goal(goal['id'])['last_success'] == answered['id']
    assert workflows.update_status(goal['id'], actor)['state'] == 'update_failed'
    browser('read-denied', 'update failed')
    with psycopg.connect(source_owner_uri) as owner:
        owner.execute('GRANT SELECT ON retail_raw.invoice_lines TO retail_reader')
    cases.append({'case':'source read failure preserves accepted answer', 'run_id':failed['id'], 'accepted_run_id':answered['id']})
    progress('event and due schedule use the current-source progression')
    now = datetime.now(timezone.utc)
    trigger = triggers.configure(version, actor, {'event_source':'retail.changed', 'timezone':'America/New_York',
        'run_at':(now+timedelta(seconds=1)).isoformat(), 'expires_at':(now+timedelta(minutes=30)).isoformat(),
        'max_runs':2, 'max_spend_usd':0, 'refresh_source':True})
    event = triggers.event(trigger['id'], actor, {'event_id':'known-change','source':'retail.changed'})
    assert event['status'] == 'accepted'
    repeated = triggers.event(trigger['id'], actor, {'event_id':'known-change','source':'retail.changed'})
    assert repeated['status'] == 'reused' and repeated['run_id'] == event['run_id']
    event_collection, event_answer = finish(db.run(event['run_id']))
    assert event_collection['result']['changes']['value_rows_read'] == 0
    due = triggers.due(trigger['id'])
    assert due['status'] == 'accepted', due
    scheduled_collection, scheduled_answer = finish(db.run(due['run_id']))
    assert scheduled_collection['result']['changes']['value_rows_read'] == 0
    assert db.run(due['run_id'])['body']['operation'] == 'refresh'
    removed = triggers.set_state(trigger['id'], actor, 'removed')
    assert removed['state'] == 'removed'
    cases.append({'case':'event and due schedule handlers refresh current source', 'event_run_id':event['run_id'],
        'schedule_run_id':due['run_id'], 'zero_unchanged_values_fetched':True,
        'reconciliation':reconcile(scheduled_answer), 'scope':'Real event and due schedule admission; native timer itself was accepted in S-20.'})
    progress('completed')
    return {'status':'passed', 'scope':'Real local PostgreSQL changes across the full historical retail dataset; only interruption is injected.',
            'cases':cases, 'accepted_answer_run_id':scheduled_answer['id']}
