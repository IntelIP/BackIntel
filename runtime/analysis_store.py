"""Application records, append-only evidence and durable budget reservations."""
from __future__ import annotations

import hashlib
from contextlib import nullcontext
import time
from decimal import Decimal
from threading import Lock

import psycopg
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb
from psycopg_pool import ConnectionPool

from runtime.analysis_data import CONFIG, digest
from runtime.evidence import Evidence
from runtime.ledger import dsn


_query_pools = {}
_query_pool_lock = Lock()


def _reset_query_connection(connection):
    connection.execute('RESET ALL; SELECT pg_advisory_unlock_all()')


def _query_pool():
    identity = dsn()
    with _query_pool_lock:
        if identity not in _query_pools:
            # Only short, autocommit queries use this pool. Explicit transaction
            # and dispatcher locks keep their dedicated connect() lifecycle.
            _query_pools[identity] = ConnectionPool(identity, min_size=0, max_size=16,
                kwargs={'autocommit': True}, reset=_reset_query_connection, open=True)
        return _query_pools[identity]


def connect():
    return psycopg.connect(dsn(), autocommit=True)


def query(sql, params=(), one=False, *, connection=None):
    with (nullcontext(connection) if connection is not None else _query_pool().connection()) as c, c.cursor(row_factory=dict_row) as cur:
        cur.execute(sql, params or None)
        return cur.fetchone() if one else cur.fetchall()


def write(sql, params=(), *, connection=None):
    with (nullcontext(connection) if connection is not None else _query_pool().connection()) as c:
        c.execute(sql, params or None)


def principal(token):
    if not token or len(token) > 512:
        raise PermissionError('A local access credential is required')
    p = query('SELECT id,role,domains,administrator,budget_usd FROM backintel.analysis_principals WHERE token_hash=%s AND enabled AND (expires_at IS NULL OR expires_at>now())',
              (hashlib.sha256(token.encode()).hexdigest(),), one=True)
    if p is None:
        raise PermissionError('Access credential is invalid, revoked, or expired')
    return p


def authorize(p, domain=None, roles=('manager', 'analyst', 'viewer'), *, connection=None, shared=True, administrator=False):
    sql = 'SELECT id,role,domains,administrator,budget_usd FROM backintel.analysis_principals WHERE id=%s AND enabled AND (expires_at IS NULL OR expires_at>clock_timestamp())'
    if connection is not None:
        sql += ' FOR SHARE' if shared else ' FOR UPDATE'
    current = query(sql, (p['id'],), one=True, connection=connection)
    if not current or current['role'] not in roles or (domain and domain not in current['domains']) or (administrator and not current['administrator']):
        raise PermissionError('Role or source access is denied')
    return current


def authorize_goal(p, identity, roles=('manager', 'analyst', 'viewer'), *, permission='read', connection=None, shared=True):
    """A source/domain grant never implicitly shares somebody else's objective."""
    levels = {'read': ('read', 'run', 'manage'), 'run': ('run', 'manage'), 'manage': ('manage',)}
    if permission not in levels:
        raise ValueError('Unknown objective permission')
    lock = ' FOR SHARE' if connection is not None else ''
    g = query('SELECT owner,domain FROM backintel.analysis_goals WHERE id=%s' + lock,
              (identity,), one=True, connection=connection)
    if not g:
        raise ValueError('Unknown goal')
    current = authorize(p, g['domain'], roles, connection=connection, shared=shared)
    if current['id'] == g['owner'] or current['administrator']:
        return current
    grant = query('SELECT permission FROM backintel.analysis_goal_access WHERE goal_id=%s AND principal_id=%s' + lock,
                  (identity, current['id']), one=True, connection=connection)
    if not grant or grant['permission'] not in levels[permission]:
        raise PermissionError('This objective is not shared with the current user for this action')
    return current


def visible_goal_ids(p):
    current = authorize(p)
    current['domains'] = [domain for domain in current['domains'] if domain in CONFIG['sources']]
    return [row['id'] for row in query('''SELECT g.id FROM backintel.analysis_goals g
        WHERE g.domain=ANY(%s) AND (g.owner=%s OR %s OR EXISTS (
            SELECT 1 FROM backintel.analysis_goal_access a WHERE a.goal_id=g.id AND a.principal_id=%s))''',
        (current['domains'], current['id'], current['administrator'], current['id']))]


def share_goal(identity, target, permission, actor):
    if permission not in (None, 'read', 'run', 'manage'):
        raise ValueError('Unknown objective permission')
    with connect() as c, c.transaction():
        c.execute('SELECT id FROM backintel.analysis_goals WHERE id=%s FOR UPDATE', (identity,))
        authorize_goal(actor, identity, ('manager',), permission='manage', connection=c)
        g = goal(identity)
        if target == g['owner']:
            raise ValueError('The owner retains objective access')
        authorize({'id': target}, g['domain'], connection=c, shared=True)
        if permission is None:
            c.execute('DELETE FROM backintel.analysis_goal_access WHERE goal_id=%s AND principal_id=%s', (identity, target))
        else:
            c.execute('''INSERT INTO backintel.analysis_goal_access(goal_id,principal_id,permission) VALUES(%s,%s,%s)
                ON CONFLICT(goal_id,principal_id) DO UPDATE SET permission=EXCLUDED.permission''', (identity, target, permission))
    return {'goal_id': identity, 'principal_id': target, 'permission': permission}


def authorize_run(p, r, roles=('manager', 'analyst', 'viewer'), *, permission='read', connection=None):
    if r['goal_id']:
        return authorize_goal(p, r['goal_id'], roles, permission=permission, connection=connection)
    current = authorize(p, run_domain(r), roles, connection=connection)
    if r['owner'] != current['id'] and not current['administrator']:
        raise PermissionError('This job belongs to another user')
    return current


def catalog(domain=None, *, connection=None):
    selected = CONFIG['sources'].items() if domain is None else [(domain, CONFIG['sources'][domain])]
    with (nullcontext(connection) if connection is not None else connect()) as c, c.transaction():
        for identity, spec in selected:
            c.execute('SELECT pg_advisory_xact_lock(hashtextextended(%s,0))', ('analysis-source:'+identity,))
            c.execute("""INSERT INTO backintel.analysis_sources(id,domain,body) VALUES(%s,%s,%s)
                ON CONFLICT(id) DO UPDATE SET body=EXCLUDED.body,updated_at=now()
                WHERE backintel.analysis_sources.body->>'source_spec_sha256' IS DISTINCT FROM EXCLUDED.body->>'source_spec_sha256'""",
                (identity, identity, Jsonb({**spec, 'source_spec_sha256':digest(spec), 'terms_acknowledged':False})))


def source(domain, *, connection=None):
    s = query('SELECT * FROM backintel.analysis_sources WHERE id=%s', (domain,), one=True, connection=connection)
    if not s:
        raise ValueError('Unknown source')
    if s['body'].get('source_spec_sha256') != digest(CONFIG['sources'][domain]):
        catalog(domain, connection=connection)
        s = query('SELECT * FROM backintel.analysis_sources WHERE id=%s', (domain,), one=True, connection=connection)
    return s


def save_snapshot(domain, identity, body, rows, *, connection=None):
    with (nullcontext(connection) if connection is not None else connect()) as c, c.transaction():
        c.execute('SELECT pg_advisory_xact_lock(hashtextextended(%s,0))', ('analysis-source:'+domain,))
        c.execute('INSERT INTO backintel.analysis_snapshots(id,source_id,body) VALUES(%s,%s,%s) ON CONFLICT DO NOTHING', (identity, domain, Jsonb(body)))
        with c.cursor() as cur:
            cur.executemany('INSERT INTO backintel.analysis_records(snapshot_id,id,body) VALUES(%s,%s,%s) ON CONFLICT DO NOTHING',
                            [(identity, r['id'], Jsonb(r)) for r in rows])
        c.execute("""UPDATE backintel.analysis_sources SET body=CASE WHEN latest_snapshot IS DISTINCT FROM %s
            THEN body || jsonb_build_object('previous_snapshot', latest_snapshot) ELSE body END,
            latest_snapshot=%s,updated_at=now() WHERE id=%s""", (identity, identity, domain))
        e = Evidence(c, 'analysis-source-'+domain)
        e.put('source_snapshot', identity, body, int(time.time())) if not e.find('source_snapshot', identity) else None


def records(snapshot, *, connection=None):
    return [r['body'] for r in query('SELECT body FROM backintel.analysis_records WHERE snapshot_id=%s ORDER BY id', (snapshot,), connection=connection)]


def goal(identity, *, connection=None):
    g = query('SELECT * FROM backintel.analysis_goals WHERE id=%s' + (' FOR SHARE' if connection is not None else ''),
              (identity,), one=True, connection=connection)
    if g is None:
        raise ValueError('Unknown goal')
    return g


def run(identity, *, connection=None):
    r = query('SELECT * FROM backintel.analysis_runs WHERE id=%s', (identity,), one=True, connection=connection)
    if r is None:
        raise ValueError('Unknown run')
    return r


def run_domain(r):
    return goal(r['goal_id'])['domain'] if r['goal_id'] else r['body']['domain']


def check_run(identity, *, connection=None):
    r = run(identity, connection=connection)
    if r['body']['operation'] == 'import':
        authorize({'id': r['owner']}, run_domain(r), ('manager',), administrator=True)
        if not source(run_domain(r), connection=connection)['body'].get('terms_acknowledged'):
            raise PermissionError('Source terms are not acknowledged')
        if query('SELECT cancel_requested FROM backintel.capability_jobs WHERE job_id=%s', (r['job_id'],), one=True)['cancel_requested']:
            raise InterruptedError('Import cancelled')
        return r, {'domain': run_domain(r)}
    g = goal(r['goal_id'], connection=connection)
    planning = r['body']['operation'] in ('planning', 'interpretation', 'preparation', 'validation', 'answer', 'workflow', 'method', 'refresh', 'coordination')
    authorize_goal({'id': r['owner']}, g['id'], ('manager',) if planning else ('manager', 'analyst'), permission='run', connection=connection, shared=True)
    if planning and (not g['body'].get('objective') or r['snapshot_id'] is not None):
        raise PermissionError('Planning requires an objective and cannot use an imported snapshot')
    if r['body']['operation'] in ('discovery', 'collection', 'interpretation', 'preparation', 'validation', 'answer', 'workflow', 'method', 'refresh', 'coordination'):
        from contextlib import nullcontext
        from runtime.source_access import require_source_access
        with (nullcontext(connection) if connection is not None else connect()) as control, control.transaction():
            require_source_access(g['id'], {'id': r['owner']}, connection=control, expected_version=r['goal_version'])
        if r['snapshot_id'] is not None:
            raise PermissionError('Connection discovery cannot use a registered-dataset snapshot')
    elif not planning and not source(g['domain'], connection=connection)['body'].get('terms_acknowledged'):
        raise PermissionError('Source terms are not acknowledged')
    if r['body']['operation']=='analysis' and r['body'].get('model_id'):
        model=query('SELECT body FROM backintel.analysis_models WHERE id=%s',(r['body']['model_id'],),one=True)
        if not model or model['body'].get('invalidated_by'):
            raise PermissionError('Pinned predictor was invalidated by a source correction')
    if ((not planning or r['body']['operation'] == 'coordination') and not g['confirmed']) or g['paused'] or g['version'] != r['goal_version']:
        raise PermissionError('Goal is unconfirmed, paused or this run was superseded')
    if query('SELECT cancel_requested FROM backintel.capability_jobs WHERE job_id=%s', (r['job_id'],), one=True)['cancel_requested']:
        raise InterruptedError('Run cancelled')
    return r, g


def event(identity, kind, body):
    write('INSERT INTO backintel.analysis_events(run_id,kind,body) VALUES(%s,%s,%s)', (identity, kind, Jsonb(body)))


def step(identity, key):
    r = query('SELECT body FROM backintel.analysis_steps WHERE run_id=%s AND id=%s', (identity, key), one=True)
    return r['body'] if r else None


def save_step(identity, key, kind, body):
    write('INSERT INTO backintel.analysis_steps(run_id,id,kind,body) VALUES(%s,%s,%s,%s) ON CONFLICT DO NOTHING', (identity, key, kind, Jsonb(body)))
    return step(identity, key)


def evidence(identity, kind, key, body):
    r = run(identity)
    with connect() as c:
        store = Evidence(c, 'analysis-goal-'+r['goal_id'])
        existing = store.find(kind, key)
        if existing:
            return existing['sha256']
        return store.put(kind, key, body, int(time.time()))['sha256']


def release_unsent(identity, *, connection=None):
    """Release pre-dispatch reservations while the caller owns the run task lock."""
    with (nullcontext(connection) if connection is not None else connect()) as c, c.transaction():
        c.execute('SELECT pg_advisory_xact_lock(81827027)')
        removed = c.execute("DELETE FROM backintel.analysis_requests WHERE run_id=%s AND status='reserved' AND response IS NULL RETURNING id,reserved", (identity,)).fetchall()
        for request_id, amount in removed:
            c.execute('INSERT INTO backintel.analysis_events(run_id,kind,body) VALUES(%s,%s,%s)',
                      (identity, 'reservation_released', Jsonb({'request_id': request_id, 'reserved_usd': str(amount), 'reason': 'Attempt ended before provider dispatch'})))
    return len(removed)


def reserve(identity, call_id, amount):
    """The suite lock makes simultaneous domain/run limits one admission decision."""
    if isinstance(amount, bool):
        raise ValueError('Reservation must be a finite nonnegative cost')
    amount = Decimal(str(amount))
    if not amount.is_finite() or amount < 0:
        raise ValueError('Reservation must be a finite nonnegative cost')
    if amount > Decimal(str(CONFIG['budget']['request_usd'])):
        raise RuntimeError('Provider request reservation limit exceeded')
    r = run(identity)
    domain = goal(r['goal_id'])['domain']
    with connect() as c, c.transaction(), c.cursor(row_factory=dict_row) as cur:
        cur.execute('SELECT pg_advisory_xact_lock(81827027)')
        _, current_goal = check_run(identity, connection=c)
        cur.execute('SELECT * FROM backintel.analysis_requests WHERE id=%s', (call_id,))
        prior = cur.fetchone()
        if prior:
            if prior['run_id'] != identity:
                raise PermissionError('This provider request belongs to another run')
            if prior['status'] == 'complete':
                return prior['response']
            raise RuntimeError('Unresolved provider request; reconcile before any retry')
        cur.execute("SELECT count(*) FROM backintel.analysis_requests WHERE status IN ('sent','uncertain')")
        if cur.fetchone()['count']:
            raise RuntimeError('Suite has an unresolved provider charge')
        cur.execute("SELECT count(*) FROM backintel.analysis_requests WHERE status='reserved'")
        if cur.fetchone()['count'] >= CONFIG['budget']['max_concurrent']:
            raise RuntimeError('Provider request concurrency limit reached')
        cur.execute('SELECT count(*) FROM backintel.analysis_requests')
        if cur.fetchone()['count'] >= CONFIG['budget']['max_attempts']:
            raise RuntimeError('Campaign provider attempt limit reached')
        cur.execute('SELECT count(*) FROM backintel.analysis_requests WHERE run_id=%s', (identity,))
        policy = r['body'].get('coordination_policy') or r['body'].get('study_policy', {})
        if cur.fetchone()['count'] >= min(CONFIG['analyst']['max_calls'], policy.get('max_model_calls', CONFIG['analyst']['max_calls'])):
            raise RuntimeError('Investigation provider call limit reached')
        owner = authorize({'id': r['owner']}, domain, ('manager', 'analyst'), connection=c, shared=True)
        cur.execute('''SELECT COALESCE(sum(COALESCE(q.charge,q.reserved)),0) AS spent
            FROM backintel.analysis_requests q JOIN backintel.analysis_runs r ON r.id=q.run_id WHERE r.owner=%s''', (r['owner'],))
        if cur.fetchone()['spent'] + amount > owner['budget_usd']:
            raise RuntimeError('User inference budget exhausted')
        for scope, cap in (('suite', 'suite_usd'), ('domain', 'domain_usd'), ('run', 'run_usd')):
            clause, args = ('', ()) if scope == 'suite' else (' WHERE domain=%s', (domain,)) if scope == 'domain' else (' WHERE run_id=%s', (identity,))
            cur.execute('SELECT COALESCE(sum(COALESCE(charge,reserved)),0) AS spent FROM backintel.analysis_requests'+clause, args)
            limit=CONFIG['budget'][cap]
            if scope=='run':limit=min(limit,current_goal['body'].get('budget_usd',limit),policy.get('max_spend_usd',limit))
            if cur.fetchone()['spent'] + amount > Decimal(str(limit)):
                raise RuntimeError(f'{scope} inference budget exhausted')
        cur.execute('INSERT INTO backintel.analysis_requests(id,run_id,domain,reserved,status) VALUES(%s,%s,%s,%s,\'reserved\')', (call_id, identity, domain, amount))
    return None


def usage(identity):
    rows = query('SELECT status,charge,reserved FROM backintel.analysis_requests WHERE run_id=%s', (identity,))
    return {'provider_calls': len(rows), 'provider_usd': float(sum(r['charge'] or Decimal(0) for r in rows)),
            'charge_status': 'unknown' if any(r['charge'] is None for r in rows) else 'measured',
            'reserved_usd': float(sum(r['reserved'] for r in rows if r['charge'] is None)), 'local_compute_usd': None}
