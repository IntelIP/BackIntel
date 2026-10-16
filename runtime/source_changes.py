"""Compare source fingerprints with verified retained originals, using a disk index."""
from decimal import Decimal
import hashlib
import json
import re
import sqlite3
import tempfile

from psycopg import sql

from runtime import analysis_store as db
from runtime.analysis_data import digest
from runtime.source_inputs import _row_key, retained_input


def original_rows(payload):
    """Keep original JSON number spellings and types when reconstructing pages."""
    text = payload.decode('utf-8')
    decoder = json.JSONDecoder(parse_float=Decimal)
    envelope = json.loads(text, parse_float=Decimal)
    position = envelope['columns'].index(envelope['identity_column'])
    boundary = re.search(r'"rows"\s*:\s*\[', text)
    if boundary is None:
        raise ValueError('Retained connector envelope cannot supply exact row fingerprints')
    offset = boundary.end()
    for _ in envelope['rows']:
        while text[offset].isspace():
            offset += 1
        row, end = decoder.raw_decode(text, offset)
        yield _row_key(row[position]), text[offset:end]
        offset = end
        while text[offset].isspace():
            offset += 1
        if text[offset] == ',':
            offset += 1


def pages(source, table, previous, actor, page_rows, stats, check):
    """Yield current rows and changes from one repeatable-read source transaction."""
    table_key = (table['schema'], table['table'])
    old_table = next((item for item in previous.get('tables_collected', [])
                      if (item['schema'], item['table']) == table_key), None)
    comparable = bool(old_table and old_table['identity_column'] == table['identity_column'])
    reusable = comparable and old_table['fields'] == table['fields']
    with tempfile.TemporaryDirectory(prefix='backintel-row-index-') as directory, \
            sqlite3.connect(directory + '/rows.sqlite') as index:
        index.execute('CREATE TABLE originals (key TEXT PRIMARY KEY, hash TEXT, row TEXT, input TEXT, seen INTEGER DEFAULT 0)')
        if comparable:
            for page in previous['inputs']:
                if (page['schema'], page['table']) != table_key:
                    continue
                check()
                original = retained_input(page['raw_input_id'], actor)
                if hashlib.sha256(original['payload']).hexdigest() != page['sha256']:
                    raise ValueError('Retained original failed its source fingerprint check')
                rows = [(key, hashlib.sha256(row.encode()).hexdigest(), row, page['raw_input_id'])
                        for key, row in original_rows(original['payload'])]
                index.executemany('INSERT INTO originals(key,hash,row,input) VALUES(?,?,?,?)', rows)
            if index.execute('SELECT count(*) FROM originals').fetchone()[0] != old_table['expected_rows']:
                raise ValueError('Retained originals do not reconcile with their complete collection')
        if not reusable:
            stats['full_rereads'].append({'schema': table['schema'], 'table': table['table'],
                'reason': 'No compatible retained source collection; all current values must be read.'})
        index.commit()
        columns = sql.SQL(',').join(sql.Identifier(field['name']) for field in table['fields'])
        row_sql = sql.SQL('json_build_array({})::text').format(columns)
        identity = sql.Identifier(table['identity_column'])
        relation = sql.SQL('{}.{}').format(sql.Identifier(table['schema']), sql.Identifier(table['table']))
        query = sql.SQL("SELECT to_json({}) AS identity, encode(sha256(convert_to({}, 'UTF8')), 'hex') AS hash{} FROM {} ORDER BY {}").format(
            identity, row_sql, sql.SQL('') if reusable else sql.SQL(', {} AS row').format(row_sql), relation, identity)
        with source.cursor(name='changes_' + digest(table_key)[:20]) as cursor:
            cursor.execute(query)
            while markers := cursor.fetchmany(page_rows):
                check()
                stats['metadata_rows_scanned'] += len(markers)
                stats['source_bytes_read'] += sum(len(json.dumps([m['identity'], m['hash']]).encode()) for m in markers)
                old = { _row_key(m['identity']): index.execute('SELECT hash,row,input FROM originals WHERE key=?',
                         (_row_key(m['identity']),)).fetchone() for m in markers }
                needed = [m for m in markers if not old[_row_key(m['identity'])] or old[_row_key(m['identity'])][0] != m['hash']]
                fetched = markers if not reusable else []
                if reusable and needed:
                    fetched = source.execute(sql.SQL('SELECT to_json({}) AS identity, {} AS row FROM {} WHERE {}::text=ANY(%s)').format(
                        identity, row_sql, relation, identity), ([str(m['identity']) for m in needed],)).fetchall()
                values = {_row_key(item['identity']): item['row'] for item in fetched}
                if len(values) != (len(needed) if reusable else len(markers)):
                    raise ValueError('Changed source values do not reconcile with their fingerprints')
                stats['value_rows_read'] += len(values)
                stats['source_bytes_read'] += sum(len(row.encode()) for row in values.values())
                check()
                rows, changes = [], []
                for marker in markers:
                    key = _row_key(marker['identity'])
                    retained = old[key]
                    row = values.get(key, retained[1] if retained else None)
                    if row is None or hashlib.sha256(row.encode()).hexdigest() != marker['hash']:
                        raise ValueError('A current row does not match its source fingerprint')
                    kind = 'inserted' if retained is None else 'corrected' if retained[0] != marker['hash'] else 'unchanged'
                    stats[kind] += 1
                    if kind != 'unchanged':
                        changes.append({'key': key, 'kind': kind, 'original_input_id': retained[2] if retained else None})
                    rows.append({'row': row})
                index.executemany('UPDATE originals SET seen=1 WHERE key=?', [(_row_key(m['identity']),) for m in markers])
                yield rows, changes
        deleted = index.execute('SELECT key,input FROM originals WHERE seen=0 ORDER BY key')
        page = 0
        while items := deleted.fetchmany(page_rows):
            check()
            changes = [{'key': key, 'kind': 'deleted', 'original_input_id': ref} for key, ref in items]
            db.save_step(stats['run_id'], 'source-deletions-' + digest([*table_key, page]), 'source_changes',
                         {'schema': table['schema'], 'table': table['table'], 'changes': changes})
            stats['deleted'] += len(changes)
            page += 1
