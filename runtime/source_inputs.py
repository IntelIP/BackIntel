"""Retain unchanged, bounded connector responses before preparation.

The connector supplies a JSON envelope containing columns, identity_column and
rows. Rows are arrays, preserving nulls, empty strings and duplicate-looking
values. A unique source identity links every later derived row to its original.
"""
from decimal import Decimal, InvalidOperation
import hashlib
import json

from psycopg.types.json import Jsonb

from runtime import analysis_store as db
from runtime.analysis_data import digest
from runtime.source_access import require_source_access


def _object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('Duplicate JSON member in source response')
        result[key] = value
    return result


def _invalid_number(value):
    raise ValueError('Non-finite number in source response')


def _row_key(value):
    if isinstance(value, bool) or not isinstance(value, (str, int)) or not str(value) or len(str(value)) > 512:
        raise ValueError('Each original record requires a bounded string or integer identity')
    return ('text:' if isinstance(value, str) else 'integer:') + str(value)


def parse_response(payload):
    if not isinstance(payload, bytes) or not payload:
        raise ValueError('A connector response must contain UTF-8 JSON bytes')
    try:
        envelope = json.loads(payload.decode('utf-8'), parse_float=Decimal,
                              parse_constant=_invalid_number, object_pairs_hook=_object)
    except (UnicodeError, ValueError, RecursionError, InvalidOperation) as error:
        raise ValueError('Malformed source response; the original was not accepted') from error
    if not isinstance(envelope, dict) or set(envelope) != {'columns', 'identity_column', 'rows'}:
        raise ValueError('Unsupported connector response format')
    columns = envelope['columns']
    if (not isinstance(columns, list) or not columns or len(columns) > 256
            or any(not isinstance(name, str) or not name or len(name) > 63 for name in columns)
            or len(set(columns)) != len(columns) or envelope['identity_column'] not in columns):
        raise ValueError('Invalid source columns or original identity column')
    if not isinstance(envelope['rows'], list):
        raise ValueError('Source rows must be an array')
    position = columns.index(envelope['identity_column'])
    row_ids = []
    for row in envelope['rows']:
        if not isinstance(row, list) or len(row) != len(columns):
            raise ValueError('Malformed source row; the original was not accepted')
        if any(value is not None and not isinstance(value, (str, int, bool, Decimal)) for value in row):
            raise ValueError('Unsupported nested source value')
        row_ids.append(_row_key(row[position]))
    if len(set(row_ids)) != len(row_ids):
        raise ValueError('Duplicate source identities; the response was not accepted')
    return envelope, row_ids


def admit_response(goal_id, actor, *, schema, table, source_version, payload, expected_version):
    """Trusted connectors call this after reading through the source boundary."""
    with db.connect() as control, control.transaction():
        goal, policy, _ = require_source_access(goal_id, actor, connection=control, schema=schema, expected_version=expected_version)
        if not isinstance(table, str) or not table or len(table) > 63:
            raise ValueError('A bounded source table name is required')
        if not isinstance(source_version, str) or not 1 <= len(source_version) <= 256:
            raise ValueError('A bounded source snapshot identity is required')
        if not isinstance(payload, bytes) or len(payload) > goal['body']['objective']['limits']['max_source_bytes']:
            raise ValueError('The connector response exceeds its permitted byte limit or format')
        envelope, row_ids = parse_response(payload)
        body = {'payload_sha256': hashlib.sha256(payload).hexdigest(), 'bytes': len(payload),
                'row_count': len(row_ids), 'row_ids': row_ids, 'columns': envelope['columns'],
                'identity_column': envelope['identity_column'], 'format': 'backintel-source-rows-v1',
                'coverage': 'one retained response; whole-workload completeness is not established'}
        identity = digest([goal_id, goal['version'], policy['id'], source_version, schema, table, body['payload_sha256']])
        # Authority locks prevent concurrent revocation; expiry is checked again after validation.
        require_source_access(goal_id, actor, connection=control, schema=schema, expected_version=expected_version)
        control.execute('''INSERT INTO backintel.analysis_raw_inputs
            (id,goal_id,goal_version,source_id,source_version,schema_name,table_name,payload,body)
            VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s) ON CONFLICT DO NOTHING''',
            (identity, goal_id, goal['version'], policy['id'], source_version, schema, table, payload, Jsonb(body)))
    return {'id': identity, **body}


def retained_input(identity, actor):
    with db.connect() as control, control.transaction():
        original = db.query('SELECT * FROM backintel.analysis_raw_inputs WHERE id=%s', (identity,), one=True, connection=control)
        if original is None:
            raise ValueError('Unknown retained input')
        _, policy, _ = require_source_access(original['goal_id'], actor, connection=control,
                                              schema=original['schema_name'], expected_version=original['goal_version'])
        if policy['id'] != original['source_id']:
            raise PermissionError('The retained input belongs to a different source grant')
        original['payload'] = bytes(original['payload'])
        if hashlib.sha256(original['payload']).hexdigest() != original['body']['payload_sha256']:
            raise ValueError('The retained original failed its integrity check')
        require_source_access(original['goal_id'], actor, connection=control,
                              schema=original['schema_name'], expected_version=original['goal_version'])
        return original


def original_record(identity, row_id, actor):
    original = retained_input(identity, actor)
    envelope, row_ids = parse_response(original['payload'])
    try:
        position = row_ids.index(row_id)
    except ValueError as error:
        raise ValueError('Unknown original record identity') from error
    return {'raw_input_id': identity, 'source_row_id': row_id,
            'values': dict(zip(envelope['columns'], envelope['rows'][position]))}
