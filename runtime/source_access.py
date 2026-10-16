"""Shared authority boundary for the selected local PostgreSQL source.

Only trusted application tools use the database session. Models receive neither
the session nor credentials; source rows cannot modify operator-managed grants.
"""
from contextlib import contextmanager
from datetime import datetime, timezone
import os
import time

import psycopg
from psycopg import sql
from psycopg.conninfo import conninfo_to_dict
from psycopg.rows import dict_row

from runtime import analysis_store as db
from runtime.analysis_objectives import normalize_objective
from runtime.analysis_data import digest


def _not_expired(*expirations):
    if any(value is not None and value <= datetime.now(timezone.utc) for value in expirations):
        raise PermissionError('Source or user access has expired')


def require_source_access(goal_id, actor, *, connection, schema=None, expected_version=None):
    """Lock authority through a read or acceptance transaction; recheck expiry."""
    goal = db.query('SELECT * FROM backintel.analysis_goals WHERE id=%s FOR SHARE',
                    (goal_id,), one=True, connection=connection)
    if not goal:
        raise ValueError('Unknown goal')
    if expected_version is not None and goal['version'] != expected_version:
        raise PermissionError('The objective changed before source access')
    db.query('SELECT id FROM backintel.analysis_principals WHERE id=%s FOR SHARE',
             (actor['id'],), one=True, connection=connection)
    principal = db.authorize(actor, goal['domain'], ('manager', 'analyst'), connection=connection, shared=True)
    objective = normalize_objective(goal['body'].get('objective'))
    if objective is None or goal['paused'] or not goal['confirmed']:
        raise PermissionError('Confirm and enable the business objective before accessing its source')
    policy = db.query('SELECT * FROM backintel.analysis_source_connections WHERE id=%s FOR SHARE',
                      (objective['source_ref'],), one=True, connection=connection)
    if not policy or not policy['enabled'] or policy['domain'] != goal['domain'] or principal['id'] not in policy['principals']:
        raise PermissionError('This source is not granted to the current user')
    if not set(objective['allowed_schemas']).issubset(policy['schemas']) or (schema is not None and schema not in objective['allowed_schemas']):
        raise PermissionError('Requested schema is outside the granted source scope')
    expiry = db.query('SELECT expires_at FROM backintel.analysis_principals WHERE id=%s',
                      (principal['id'],), one=True, connection=connection)['expires_at']
    _not_expired(policy['expires_at'], expiry)
    return goal, policy, expiry


def _local_credentials(reference):
    # The reference is operator-managed. Never accept a DSN in goal text or tool arguments.
    value = os.getenv(reference)
    if not value:
        raise RuntimeError('The permitted source credential has not been injected')
    try:
        settings = conninfo_to_dict(value)
    except psycopg.Error:
        raise ValueError('The source credential is not a valid PostgreSQL connection') from None
    allowed = {'host', 'hostaddr', 'port', 'dbname', 'user', 'password', 'sslmode'}
    if set(settings) - allowed or settings.get('host') not in ('localhost', '127.0.0.1', '::1'):
        raise PermissionError('This demonstration permits local PostgreSQL connections only')
    if settings.get('hostaddr') and settings['hostaddr'] not in ('127.0.0.1', '::1'):
        raise PermissionError('Source host address is outside the local scope')
    if not settings.get('dbname') or not settings.get('user') or settings.get('sslmode', 'disable') != 'disable':
        raise PermissionError('The local source requires an explicit database/user and the agreed local transport')
    settings['hostaddr'] = settings.get('hostaddr', '::1' if settings['host'] == '::1' else '127.0.0.1')
    settings['port'] = settings.get('port', '5432')
    settings['password'] = settings.get('password', '')
    settings['sslmode'] = 'disable'
    return settings


@contextmanager
def source_session(goal_id, actor, *, schema=None, expected_version=None):
    with db.connect() as control, control.transaction():
        goal, policy, principal_expiry = require_source_access(goal_id, actor, connection=control, schema=schema, expected_version=expected_version)
        settings = _local_credentials(policy['secret_ref'])
        try:
            with psycopg.connect(**settings, row_factory=dict_row, connect_timeout=5,
                                 options='-c default_transaction_read_only=on -c statement_timeout=30000 -c idle_in_transaction_session_timeout=30000') as source:
                source.execute('SET TRANSACTION ISOLATION LEVEL REPEATABLE READ, READ ONLY')
                role = source.execute('SELECT rolsuper,rolbypassrls,rolcreaterole,rolcreatedb,rolreplication FROM pg_catalog.pg_roles WHERE rolname=current_user').fetchone()
                if not role or any(role.values()):
                    raise PermissionError('Source access requires a dedicated unprivileged read-only identity')
                writable = source.execute("""SELECT
                    has_database_privilege(current_database(),'CREATE') OR has_database_privilege(current_database(),'TEMP')
                    OR EXISTS (SELECT 1 FROM pg_catalog.pg_namespace n WHERE n.nspname NOT LIKE 'pg_%'
                        AND n.nspname<>'information_schema' AND has_schema_privilege(n.oid,'CREATE'))
                    OR EXISTS (SELECT 1 FROM pg_catalog.pg_class t JOIN pg_catalog.pg_namespace n ON n.oid=t.relnamespace
                        WHERE n.nspname NOT LIKE 'pg_%' AND n.nspname<>'information_schema'
                        AND t.relkind IN ('r','p','v','m','f') AND has_table_privilege(t.oid,'INSERT,UPDATE,DELETE,TRUNCATE,REFERENCES,TRIGGER'))
                    AS writable""").fetchone()['writable']
                if writable:
                    raise PermissionError('The source identity has write privileges; reduce its grants before use')
                for permitted in goal['body']['objective']['allowed_schemas']:
                    if not source.execute('SELECT has_schema_privilege(%s,\'USAGE\') AS permitted', (permitted,)).fetchone()['permitted']:
                        raise PermissionError('The source identity lacks the permitted schema access')
                _not_expired(policy['expires_at'], principal_expiry)
                yield source, goal['body']['objective']
                _not_expired(policy['expires_at'], principal_expiry)
        except psycopg.Error as error:
            if error.sqlstate in ('42501', '28000', '28P01'):
                raise PermissionError('PostgreSQL denied the requested source access') from None
            raise RuntimeError('The permitted PostgreSQL source could not complete the read') from None


def inspect_source(goal_id, actor, *, expected_version=None):
    with source_session(goal_id, actor, expected_version=expected_version) as (source, objective):
        return catalog_fields(source, objective['allowed_schemas'])


def catalog_fields(source, schemas):
    return source.execute("""SELECT n.nspname AS schema,t.relname AS table,a.attname AS column,
                pg_catalog.format_type(a.atttypid,a.atttypmod) AS type
            FROM pg_catalog.pg_class t JOIN pg_catalog.pg_namespace n ON n.oid=t.relnamespace
            JOIN pg_catalog.pg_attribute a ON a.attrelid=t.oid
            WHERE n.nspname=ANY(%s) AND t.relkind IN ('r','p','v','m','f')
              AND a.attnum>0 AND NOT a.attisdropped AND has_table_privilege(t.oid,'SELECT')
            ORDER BY n.nspname,t.relname,a.attnum""", (schemas,)).fetchall()


def preview_source(goal_id, actor, schema, table, *, limit=10):
    """Bounded discovery preview; whole-workload collection belongs to S-13."""
    if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= 25:
        raise ValueError('A source preview must request 1–25 rows')
    with source_session(goal_id, actor, schema=schema) as (source, _):
        return source.execute(sql.SQL('SELECT * FROM {}.{} LIMIT %s').format(sql.Identifier(schema), sql.Identifier(table)), (limit,)).fetchall()


def discover(identity):
    """Automatically inspect the granted catalog; collection and meaning follow later."""
    run, goal = db.check_run(identity)
    if run['body']['operation'] != 'discovery':
        raise ValueError('Source discovery requires a discovery job')
    started = time.monotonic()
    fields = inspect_source(goal['id'], {'id': run['owner']}, expected_version=run['goal_version'])
    if not fields:
        raise PermissionError('No readable tables were found in the permitted schemas')
    db.check_run(identity)
    tables = {(field['schema'], field['table']) for field in fields}
    result = {'status': 'succeeded', 'mode': 'real', 'source_ref': goal['body']['objective']['source_ref'],
              'goal_version': run['goal_version'], 'observed_at': datetime.now(timezone.utc).isoformat(),
              'summary': f'Connected to the permitted source and discovered {len(tables)} tables and {len(fields)} fields.',
              'fields': fields, 'elapsed_seconds': round(time.monotonic() - started, 3), 'usage': db.usage(identity),
              'limitations': ['This checks connection access and metadata. Full-data collection, field interpretation and analysis have not run.']}
    result['evidence_id'] = db.evidence(identity, 'source_discovery', digest(result), result)
    return result
