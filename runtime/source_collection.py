"""Collect complete permitted PostgreSQL tables without user-written queries."""
import hashlib
import json
import time
from datetime import datetime, timezone

from psycopg import sql

from runtime import analysis_store as db
from runtime.analysis_data import digest
from runtime.source_access import catalog_fields, source_session
from runtime.source_inputs import admit_response, parse_response, retained_input


def _tables(source, schemas):
    tables = {}
    for field in catalog_fields(source, schemas):
        key = (field['schema'], field['table'])
        table = tables.setdefault(key, {'schema': key[0], 'table': key[1], 'fields': []})
        table['fields'].append({'name': field['column'], 'type': field['type']})
    if not tables:
        raise PermissionError('No readable source tables were found')
    for table in tables.values():
        keys = source.execute('''SELECT a.attname AS name
            FROM pg_catalog.pg_index i
            JOIN pg_catalog.pg_class t ON t.oid=i.indrelid
            JOIN pg_catalog.pg_namespace n ON n.oid=t.relnamespace
            CROSS JOIN LATERAL unnest(i.indkey) WITH ORDINALITY AS k(attnum,position)
            JOIN pg_catalog.pg_attribute a ON a.attrelid=t.oid AND a.attnum=k.attnum
            WHERE i.indisprimary AND i.indisvalid AND k.position<=i.indnkeyatts
              AND n.nspname=%s AND t.relname=%s ORDER BY k.position''',
            (table['schema'], table['table'])).fetchall()
        if len(keys) != 1:
            raise ValueError('Collection currently requires one stable primary-key column per table')
        table['identity_column'] = keys[0]['name']
        table['expected_rows'] = source.execute(sql.SQL('SELECT count(*) AS count FROM {}.{}').format(
            sql.Identifier(table['schema']), sql.Identifier(table['table']))).fetchone()['count']
    return list(tables.values())


def _payload(table, rows):
    header = json.dumps({'columns': [f['name'] for f in table['fields']],
                         'identity_column': table['identity_column']}, ensure_ascii=False, separators=(',', ':'))
    return (header[:-1] + ',"rows":[' + ','.join(row['row'] for row in rows) + ']}').encode('utf-8')


def coverage(identity):
    manifest = db.step(identity, 'collection-contract')
    expected = sum(t['expected_rows'] for t in manifest['tables']) if manifest else None
    pages = db.query("SELECT body FROM backintel.analysis_steps WHERE run_id=%s AND kind='source_page' ORDER BY id", (identity,))
    collected = sum(page['body']['row_count'] for page in pages)
    return {'expected_rows': expected, 'collected_rows': collected, 'excluded_rows': 0, 'failed_rows': 0,
            'pending_rows': max(0, expected - collected) if expected is not None else None,
            'analysis_processed_rows': 0, 'retained_bytes': sum(page['body']['bytes'] for page in pages)}


def change_history(identity, actor, *, offset=0, limit=100):
    from runtime.source_access import require_source_access
    if type(offset) is not int or offset < 0 or type(limit) is not int or not 1 <= limit <= 1000:
        raise ValueError('Use a nonnegative offset and a page size of 1 to 1000')
    run = db.run(identity)
    with db.connect() as connection, connection.transaction():
        require_source_access(run['goal_id'], actor, connection=connection, expected_version=run['goal_version'])
        rows = db.query("""SELECT s.body->>'schema' AS schema, s.body->>'table' AS table,
            s.body->>'current_input_id' AS current_input_id, changes.value AS change
            FROM backintel.analysis_steps s CROSS JOIN LATERAL jsonb_array_elements(s.body->'changes')
            WITH ORDINALITY AS changes(value, position)
            WHERE s.run_id=%s AND s.kind='source_changes' ORDER BY s.id, changes.position LIMIT %s OFFSET %s""",
            (identity, limit, offset), connection=connection)
    return {'run_id':identity, 'offset':offset, 'next_offset':offset+len(rows) if len(rows)==limit else None, 'changes':rows}


def collect(identity, *, page_rows=2000):
    from runtime.source_changes import pages as changed_pages
    run, goal = db.check_run(identity)
    if run['body']['operation'] not in ('collection', 'refresh', 'coordination'):
        raise ValueError('Collection requires a collection or refresh job')
    if isinstance(page_rows, bool) or not isinstance(page_rows, int) or not 1 <= page_rows <= 5000:
        raise ValueError('Invalid internal collection page size')
    actor = {'id': run['owner']}
    started = time.monotonic()
    total_bytes, reused_pages = 0, 0
    pages = []
    base = db.step(identity, 'collection-base')
    if base is None:
        prior = db.query("""SELECT id FROM backintel.analysis_runs WHERE goal_id=%s AND owner=%s
            AND goal_version=%s AND status='succeeded' AND body->>'operation' IN ('collection','refresh')
            AND result->>'source_ref'=%s AND id<>%s ORDER BY created_at DESC LIMIT 1""",
            (goal['id'], run['owner'], run['goal_version'], goal['body']['objective']['source_ref'], identity), one=True)
        base = db.save_step(identity, 'collection-base', 'collection_base', {'run_id': prior['id'] if prior else None})
    previous = db.run(base['run_id'])['result'] if base['run_id'] else {}
    old_pages = {page['sha256']: page for page in previous.get('inputs', [])}
    stats = {'run_id': identity, 'previous_collection': base['run_id'], 'inserted': 0, 'corrected': 0,
             'deleted': 0, 'unchanged': 0, 'metadata_rows_scanned': 0, 'value_rows_read': 0,
             'source_bytes_read': 0, 'full_rereads': [],
             'deletion_policy': 'Deleted records leave current totals; originals and deletion history are retained.'}
    observed_at = datetime.now(timezone.utc).isoformat()
    with source_session(goal['id'], actor, expected_version=run['goal_version']) as (source, objective):
        def check():
            db.check_run(identity)
            if time.monotonic() - started > objective['limits']['timeout_seconds']:
                raise ValueError('Collection time limit reached; the workload remains incomplete')
            if max(total_bytes, stats['source_bytes_read']) > objective['limits']['max_source_bytes']:
                raise ValueError('Collection byte limit reached; the workload remains incomplete')
        tables = _tables(source, objective['allowed_schemas'])
        contract = {'tables': tables, 'page_rows': page_rows}
        prior = db.step(identity, 'collection-contract')
        if prior is not None and prior != contract:
            raise ValueError('The source shape or row count changed; start a new refresh instead of combining snapshots')
        db.save_step(identity, 'collection-contract', 'collection_contract', contract)
        snapshot = source.execute('SELECT pg_current_snapshot()::text AS snapshot').fetchone()['snapshot']
        for table in tables:
            count, seen = 0, set()
            for page, (rows, changes) in enumerate(changed_pages(source, table, previous, actor, page_rows, stats, check)):
                payload = _payload(table, rows)
                total_bytes += len(payload)
                check()
                _, row_ids = parse_response(payload)
                if seen.intersection(row_ids):
                    raise ValueError('A repeated source identity was detected; duplicate records were not accepted')
                seen.update(row_ids)
                page_key = 'source-page-' + digest([table['schema'], table['table'], page])
                saved = db.step(identity, page_key)
                checksum = hashlib.sha256(payload).hexdigest()
                if saved is not None:
                    if retained_input(saved['raw_input_id'], actor)['payload'] != payload:
                        raise ValueError('Source content changed during interrupted collection; start a new refresh')
                    reused_pages += 1
                else:
                    retained = old_pages.get(checksum)
                    if retained and (retained['schema'], retained['table']) == (table['schema'], table['table']):
                        raw_id = retained['raw_input_id']
                        reused_pages += 1
                    else:
                        raw_id = admit_response(goal['id'], actor, schema=table['schema'], table=table['table'],
                            source_version=snapshot, payload=payload, expected_version=run['goal_version'])['id']
                    saved = {'raw_input_id': raw_id, 'row_count': len(row_ids), 'bytes': len(payload),
                             'sha256': checksum, 'schema': table['schema'], 'table': table['table'], 'page': page}
                    db.save_step(identity, page_key, 'source_page', saved)
                if changes:
                    db.save_step(identity, 'source-changes-' + digest([table['schema'], table['table'], page]),
                                 'source_changes', {'schema': table['schema'], 'table': table['table'],
                                  'current_input_id': saved['raw_input_id'], 'changes': changes})
                pages.append(saved)
                count += len(row_ids)
                db.event(identity, 'collection_progress', {'table': table['table'], 'collected_rows': count,
                    'expected_rows': table['expected_rows'], 'retained_bytes': total_bytes})
            if count != table['expected_rows']:
                raise ValueError('Collected identities do not reconcile with the source count')
    db.check_run(identity)
    stats.update(affected_rows=stats['inserted'] + stats['corrected'] + stats['deleted'],
                 excluded_rows=0, failed_rows=0, pending_rows=0)
    result = {'status': 'succeeded', 'mode': 'real', 'goal_version': run['goal_version'],
              'source_ref': goal['body']['objective']['source_ref'], 'validated_source_snapshot': snapshot,
              'observed_at': observed_at, 'tables_collected': tables, 'inputs': pages,
              'coverage': coverage(identity), 'reused_pages': reused_pages, 'changes': stats,
              'elapsed_seconds': round(time.monotonic() - started, 3), 'usage': db.usage(identity),
              'summary': f'Collected all {sum(t["expected_rows"] for t in tables)} current source rows; retained originals and change history.',
              'limitations': ['All current keys and row fingerprints are scanned. Only changed values are fetched when compatible originals exist.',
                              'Collection covers this permitted database snapshot; preparation and analysis follow separately.']}
    if result['coverage']['pending_rows'] != 0:
        raise ValueError('Retained collection coverage is incomplete')
    result['evidence_id'] = db.evidence(identity, 'source_collection', digest(result), result)
    return result
