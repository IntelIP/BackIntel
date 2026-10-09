"""Application records, append-only evidence and durable budget reservations."""
from __future__ import annotations

import hashlib
from contextlib import nullcontext
import time
from decimal import Decimal

import psycopg
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

from runtime.analysis_data import CONFIG, digest
from runtime.evidence import Evidence
from runtime.ledger import dsn


def connect():
    return psycopg.connect(dsn(), autocommit=True)


def query(sql, params=(), one=False, *, connection=None):
    with (nullcontext(connection) if connection is not None else connect()) as c, c.cursor(row_factory=dict_row) as cur:
        cur.execute(sql, params or None)
        return cur.fetchone() if one else cur.fetchall()


def write(sql, params=(), *, connection=None):
    with (nullcontext(connection) if connection is not None else connect()) as c:
        c.execute(sql, params or None)


def principal(token):
    if not token or len(token) > 512:
        raise PermissionError('A local access credential is required')
    p = query('SELECT id,role,domains FROM backintel.analysis_principals WHERE token_hash=%s AND enabled AND (expires_at IS NULL OR expires_at>now())',
              (hashlib.sha256(token.encode()).hexdigest(),), one=True)
    if p is None:
        raise PermissionError('Access credential is invalid, revoked, or expired')
    return p


def authorize(p, domain=None, roles=('manager', 'analyst', 'viewer'), *, connection=None):
    sql = 'SELECT id,role,domains FROM backintel.analysis_principals WHERE id=%s AND enabled AND (expires_at IS NULL OR expires_at>clock_timestamp())'
    if connection is not None:
        sql += ' FOR UPDATE'
    current = query(sql, (p['id'],), one=True, connection=connection)
    if not current or current['role'] not in roles or (domain and domain not in current['domains']):
        raise PermissionError('Role or source access is denied')
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


def goal(identity):
    g = query('SELECT * FROM backintel.analysis_goals WHERE id=%s', (identity,), one=True)
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
        authorize({'id': r['owner']}, run_domain(r), ('manager',))
        if not source(run_domain(r), connection=connection)['body'].get('terms_acknowledged'):
            raise PermissionError('Source terms are not acknowledged')
        if query('SELECT cancel_requested FROM backintel.capability_jobs WHERE job_id=%s', (r['job_id'],), one=True)['cancel_requested']:
            raise InterruptedError('Import cancelled')
        return r, {'domain': run_domain(r)}
    g = goal(r['goal_id'])
    authorize({'id': r['owner']}, g['domain'], ('manager', 'analyst'))
    if not source(g['domain'], connection=connection)['body'].get('terms_acknowledged'):
        raise PermissionError('Source terms are not acknowledged')
    if r['body']['operation']=='analysis' and r['body'].get('model_id'):
        model=query('SELECT body FROM backintel.analysis_models WHERE id=%s',(r['body']['model_id'],),one=True)
        if not model or model['body'].get('invalidated_by'):
            raise PermissionError('Pinned predictor was invalidated by a source correction')
    if not g['confirmed'] or g['paused'] or g['version'] != r['goal_version']:
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
        _, current_goal = check_run(identity)
        cur.execute('SELECT * FROM backintel.analysis_requests WHERE id=%s', (call_id,))
        prior = cur.fetchone()
        if prior:
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
        if cur.fetchone()['count'] >= CONFIG['analyst']['max_calls']:
            raise RuntimeError('Investigation provider call limit reached')
        for scope, cap in (('suite', 'suite_usd'), ('domain', 'domain_usd'), ('run', 'run_usd')):
            clause, args = ('', ()) if scope == 'suite' else (' WHERE domain=%s', (domain,)) if scope == 'domain' else (' WHERE run_id=%s', (identity,))
            cur.execute('SELECT COALESCE(sum(COALESCE(charge,reserved)),0) AS spent FROM backintel.analysis_requests'+clause, args)
            limit=CONFIG['budget'][cap]
            if scope=='run':limit=min(limit,current_goal['body'].get('budget_usd',limit))
            if cur.fetchone()['spent'] + amount > Decimal(str(limit)):
                raise RuntimeError(f'{scope} inference budget exhausted')
        cur.execute('INSERT INTO backintel.analysis_requests(id,run_id,domain,reserved,status) VALUES(%s,%s,%s,%s,\'reserved\')', (call_id, identity, domain, amount))
    return None


def usage(identity):
    rows = query('SELECT status,charge,reserved FROM backintel.analysis_requests WHERE run_id=%s', (identity,))
    return {'provider_calls': len(rows), 'provider_usd': float(sum(r['charge'] or Decimal(0) for r in rows)),
            'charge_status': 'unknown' if any(r['charge'] is None for r in rows) else 'measured',
            'reserved_usd': float(sum(r['reserved'] for r in rows if r['charge'] is None)), 'local_compute_usd': None}
