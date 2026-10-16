"""Saved goals and refreshes reuse the capability job queue, not a second scheduler."""
from __future__ import annotations

import json
from contextlib import nullcontext
from pathlib import Path
import subprocess
import sys
import time
import uuid

import httpx
from psycopg.types.json import Jsonb
from psycopg.rows import dict_row

from runtime import analysis_store as db
from runtime.analysis_data import CONFIG, adapt, adapter_identity, digest, fingerprint, source_files
from runtime.analysis_errors import safe_error
from runtime.analysis_objectives import normalize_objective, objective_definitions
from runtime.evidence import Evidence
from runtime.jobs import enqueue, execute, runnable
from scripts.analysis_setup import validate_source_receipt


def _import_source(domain, actor, *, connection=None, run_id=None):
    db.authorize(actor, domain, ('manager',))
    with (nullcontext(connection) if connection is not None else db.connect()) as c, c.transaction():
        c.execute('SELECT pg_advisory_xact_lock(hashtextextended(%s,0))', ('analysis-source:'+domain,))
        source = db.source(domain, connection=c)
        if not source['body'].get('terms_acknowledged'):
            raise PermissionError('Source access and terms must be confirmed before import')
        approved = validate_source_receipt(domain)
        paths = source_files(domain)
        files = [fingerprint(p) for p in paths]
        if files != approved['adapter_receipt']['files']:
            raise PermissionError('Source bytes changed after receipt validation')
        if source['latest_snapshot']:
            prior = db.query('SELECT body FROM backintel.analysis_snapshots WHERE id=%s', (source['latest_snapshot'],), one=True)
            if (prior['body']['files'] == files
                    and all(prior['body'].get(key) == value for key, value in adapter_identity(domain).items())
                    and (domain!='maintenance' or prior['body'].get('unit_mapping')=='dataset-qualified-engine-v2')):
                db.authorize(actor, domain, ('manager',), connection=c)
                return {'snapshot': source['latest_snapshot'], 'changed': False}
        identity, body, rows = adapt(domain, paths)
        if identity != approved['snapshot_id'] or body != approved['adapter_receipt']:
            raise PermissionError('Source changed after receipt validation; reimport with authorization')
        if domain=='maintenance':
            body['unit_mapping']='dataset-qualified-engine-v2'
            identity=digest(body)
        if run_id is not None:
            db.check_run(run_id, connection=c)
            cancelled = c.execute('SELECT cancel_requested FROM backintel.capability_jobs WHERE job_id=%s FOR UPDATE', (db.run(run_id)['job_id'],)).fetchone()[0]
            if cancelled:
                raise InterruptedError('Import cancelled')
        db.authorize(actor, domain, ('manager',), connection=c)
        db.save_snapshot(domain, identity, body, rows, connection=c)
        return {'snapshot': identity, 'changed': source['latest_snapshot'] != identity}

def import_source(domain, actor, *, connection=None, run_id=None):
    db.authorize(actor, domain, ('manager',))
    failure = None
    with (nullcontext(connection) if connection is not None else db.connect()) as c:
        with c.transaction():
            c.execute('SELECT pg_advisory_xact_lock(hashtextextended(%s,0))', ('analysis-source:'+domain,))
            try:
                result = _import_source(domain, actor, connection=c, run_id=run_id)
            except (OSError, ValueError, PermissionError, RuntimeError) as error:
                failure = error
                db.write('UPDATE backintel.analysis_sources SET body=body || %s WHERE id=%s',
                         (Jsonb({'last_refresh_error':safe_error(error),'last_checked_at':time.time()}),domain), connection=c)
            else:
                db.write("UPDATE backintel.analysis_sources SET body=(body-'last_refresh_error') || %s WHERE id=%s",
                         (Jsonb({'last_checked_at':time.time()}),domain), connection=c)
        if failure is not None:
            raise failure
    return result


def create_goal(actor, domain, question, *, objective=None):
    db.authorize(actor, domain, ('manager',))
    db.source(domain)
    if not isinstance(question, str) or not 1 <= len(question.strip()) <= 2000:
        raise ValueError('Question must contain 1–2000 characters')
    objective = normalize_objective(objective)
    identity = str(uuid.uuid4())
    spec = CONFIG['sources'][domain]
    body = {'question': question, 'definitions': {'target': spec['target'], 'kind': spec['kind'], 'group': spec['group'],
            'population': 'registered source snapshot', 'caveat': spec['caveat']},
            'notification_delta': .05 if spec['kind'] == 'classification' else 5., 'refresh_seconds': 3600, 'budget_usd': 1.}
    if objective is not None:
        body['objective'] = objective
        body['definitions'] = objective_definitions(objective)
        body['budget_usd'] = 0.
    with db.connect() as c, c.transaction():
        db.authorize(actor, domain, ('manager',), connection=c)
        c.execute('INSERT INTO backintel.analysis_goals(id,owner,domain,version,body) VALUES(%s,%s,%s,1,%s)', (identity, actor['id'], domain, Jsonb(body)))
        c.execute('INSERT INTO backintel.analysis_goal_versions(goal_id,version,body,actor) VALUES(%s,1,%s,%s)', (identity, Jsonb(body), actor['id']))
    return db.goal(identity)


def revise_goal(identity, actor, question=None, paused=None, confirmed=None, threshold=None, budget_usd=None, objective=None):
    g = db.goal(identity)
    db.authorize(actor, g['domain'], ('manager',))
    body = dict(g['body'])
    if budget_usd is not None:
        if isinstance(budget_usd,bool) or not isinstance(budget_usd,(int,float)) or not 0 <= budget_usd <= CONFIG['budget']['run_usd']:
            raise ValueError('Goal budget must be nonnegative and within the approved run cap')
        body['budget_usd']=budget_usd
    if objective is not None:
        body['objective'] = normalize_objective(objective)
        body['definitions'] = objective_definitions(body['objective'])
    if question is not None:
        if not isinstance(question, str) or not 1 <= len(question.strip()) <= 2000:
            raise ValueError('Invalid question')
        body['question'] = question
    if threshold is not None:
        if not isinstance(threshold, (int, float)) or not 0 <= threshold <= 100000:
            raise ValueError('Invalid notification threshold')
        body['notification_delta'] = threshold
    if body != g['body']:
        body.pop('plan', None)
    version = g['version'] + int(body != g['body'])
    with db.connect() as c, c.transaction():
        manager = c.execute("""SELECT id FROM backintel.analysis_principals WHERE id=%s
            AND enabled AND (expires_at IS NULL OR expires_at>now())
            AND role='manager' AND %s=ANY(domains) FOR UPDATE""", (actor['id'], g['domain'])).fetchone()
        if not manager:
            raise PermissionError('Current manager authority is required to edit a goal')
        changed = c.execute('UPDATE backintel.analysis_goals SET body=%s,version=%s,paused=%s,confirmed=%s WHERE id=%s AND version=%s AND body=%s AND paused=%s AND confirmed=%s',
                  (Jsonb(body), version, g['paused'] if paused is None else paused,
                   False if version != g['version'] else g['confirmed'] if confirmed is None else confirmed, identity, g['version'], Jsonb(g['body']), g['paused'], g['confirmed']))
        if not changed.rowcount:
            raise ValueError('Goal changed during this edit; reload it and try again')
        c.execute('INSERT INTO backintel.analysis_goal_versions(goal_id,version,body,actor) VALUES(%s,%s,%s,%s) ON CONFLICT DO NOTHING', (identity, version, Jsonb(body), actor['id']))
    return db.goal(identity)


def submit(identity, actor, question=None, operation='analysis', *, connection=None, workflow_version=None, input_ref=None, method_policy=None, refresh_key=None):
    g = db.goal(identity)
    with (nullcontext(connection) if connection is not None else db.connect()) as c, c.transaction():
        run_id = _admit_run(c, g, actor, question, operation, workflow_version=workflow_version, input_ref=input_ref, method_policy=method_policy, refresh_key=refresh_key)
        return db.run(run_id, connection=c)


def analysis_identity():
    root = Path(__file__).resolve().parents[1]
    files = sorted([*(root / 'runtime').glob('*.py'), root / 'config/real_models.json'])
    return digest({'implementation':{str(path.relative_to(root)):fingerprint(path)['sha256'] for path in files}, 'config':CONFIG})


def _admit_run(c, g, actor, question=None, operation='analysis', *, workflow_version=None, input_ref=None, method_policy=None, refresh_key=None):
    if operation not in ('analysis', 'training', 'planning', 'discovery', 'collection', 'interpretation', 'preparation', 'validation', 'answer', 'workflow', 'method', 'refresh'):
        raise ValueError('Unsupported operation')
    binding = None
    if method_policy is not None and operation != 'method':
        raise ValueError('Method policy requires a method study')
    if refresh_key is not None and operation != 'refresh':
        raise ValueError('A refresh identity requires a source refresh')
    if operation in ('workflow', 'refresh'):
        from runtime.source_workflows import bind
        if operation == 'refresh' and (input_ref is not None or not isinstance(refresh_key, str) or not 1 <= len(refresh_key) <= 240):
            raise ValueError('A source refresh requires a bounded request identity and reads the current source')
        binding = bind(workflow_version,input_ref,actor)
        if operation == 'refresh':
            binding.update(refresh_key=refresh_key, refresh_owner=actor['id'])
    elif operation == 'method':
        from runtime.source_methods import bind
        if workflow_version is not None:
            raise ValueError('Method studies require a checked source answer')
        binding = bind(input_ref, method_policy, actor)
        question = binding['study_policy']['question']
    elif workflow_version is not None or input_ref is not None:
        raise ValueError('Workflow bindings require a workflow invocation')
    planning = operation in ('planning', 'interpretation', 'answer')
    pre_ingestion = operation in ('planning', 'discovery', 'collection', 'interpretation', 'preparation', 'validation', 'answer', 'workflow', 'method', 'refresh')
    identity = g['id']
    c.execute('SELECT pg_advisory_xact_lock(hashtextextended(%s,0))', ('analysis-source:'+g['domain'],))
    source = db.source(g['domain'], connection=c)
    if not pre_ingestion and not source['body'].get('terms_acknowledged'):
        raise PermissionError('Source terms are not acknowledged')
    with c.cursor(row_factory=dict_row) as cursor:
        cursor.execute('SELECT * FROM backintel.analysis_goals WHERE id=%s FOR UPDATE', (identity,))
        g = cursor.fetchone()
    if g is None:
        raise ValueError('Unknown goal')
    db.authorize(actor, g['domain'], ('manager',) if operation in ('training', 'planning', 'interpretation', 'preparation', 'validation', 'answer', 'workflow', 'method', 'refresh') else ('manager', 'analyst'), connection=c)
    if binding and (binding['goal_id']!=g['id'] or binding['goal_version']!=g['version']):
        raise ValueError('Workflow belongs to a different or superseded objective version')
    if planning and not g['body'].get('objective'):
        raise ValueError('Save a connected-source objective before requesting a plan')
    if planning and g['body'].get('budget_usd', 0) <= 0:
        raise PermissionError('Approve a positive planning budget before requesting a model call')
    if operation in ('discovery', 'collection', 'interpretation', 'preparation', 'validation', 'answer', 'workflow', 'method', 'refresh'):
        from runtime.source_access import require_source_access
        require_source_access(identity, actor, connection=c, expected_version=g['version'])
    if not pre_ingestion and g['body'].get('objective'):
        raise ValueError('This business objective requires its connected workflow; the registered-dataset analyst cannot run it')
    if (not planning and not g['confirmed']) or g['paused']:
        raise ValueError('Confirm the goal definitions and enable the goal first')
    snapshot = None if pre_ingestion else source['latest_snapshot']
    if not pre_ingestion and not snapshot:
        raise ValueError('Import the selected source first')
    if question is not None and (not isinstance(question, str) or not 1 <= len(question.strip()) <= 2000):
        raise ValueError('Invalid follow-up question')
    question = question or g['body']['question']
    implementation = analysis_identity()
    prior_snapshot = None if pre_ingestion else source['body'].get('previous_snapshot')
    context = [identity, g['version'], snapshot, prior_snapshot, operation, question, g['active_model'], implementation]
    run_id = digest(context + [binding] if binding else context)
    if operation == 'method':
        prior = c.execute("SELECT id FROM backintel.analysis_runs WHERE body->>'operation'='method' AND body->>'evaluation_key'=%s AND id<>%s LIMIT 1",
                          (binding['evaluation_key'], run_id)).fetchone()
        if prior:
            raise ValueError('These evaluation data already belong to a frozen method study; reuse that study or collect new evaluation data')
    existing = c.execute('SELECT r.status,j.state FROM backintel.analysis_runs r JOIN backintel.capability_jobs j ON j.job_id=r.job_id WHERE r.id=%s', (run_id,)).fetchone()
    # An active worker owns the job lock and needs the source/goal locks to finish.
    # Replays must return without waiting for that worker while holding these locks.
    if existing and (existing[0] not in ('partial', 'cancelled') or existing[1] == 'running'):
        if existing[0] == 'succeeded' and operation == 'analysis' and question == g['body']['question']:
            # This identity pins the current goal, snapshot, model and implementation.
            c.execute('UPDATE backintel.analysis_goals SET last_success=%s WHERE id=%s', (run_id, identity))
        return run_id
    # The source advisory lock serializes admission across all goals and owners.
    pending = c.execute("""SELECT count(*) FROM backintel.analysis_runs r
        JOIN backintel.analysis_goals g ON g.id=r.goal_id
        JOIN backintel.capability_jobs j ON j.job_id=r.job_id
        WHERE g.domain=%s AND j.state IN ('queued','running','retry')""", (g['domain'],)).fetchone()[0]
    if pending >= 20:
        raise RuntimeError('Source analysis queue has reached its 20 pending-run limit')
    payload = {'run_id': run_id, 'operation': operation}
    c.execute('INSERT INTO backintel.analysis_runs(id,goal_id,owner,snapshot_id,goal_version,body) VALUES(%s,%s,%s,%s,%s,%s) ON CONFLICT DO NOTHING',
              (run_id, identity, actor['id'], snapshot, g['version'], Jsonb({'question': question, 'definitions': g['body']['definitions'], 'operation': operation, 'model_id': g['active_model'], 'analysis_identity': implementation, 'prior_snapshot': prior_snapshot, **(binding or {})})))
    store = Evidence(c, 'analysis-job-'+run_id)
    job_id = enqueue(store, payload, run_id)
    c.execute('UPDATE backintel.analysis_runs SET job_id=%s WHERE id=%s', (job_id, run_id))
    resumable = c.execute('SELECT status FROM backintel.analysis_runs WHERE id=%s FOR UPDATE', (run_id,)).fetchone()[0] in ('partial', 'cancelled')
    if resumable:
        attempts = c.execute('SELECT attempts FROM backintel.capability_jobs WHERE job_id=%s FOR UPDATE', (job_id,)).fetchone()[0]
        if attempts >= 5:
            raise RuntimeError('This investigation reached its five-attempt limit; submit a new question or source snapshot')
        db.release_unsent(run_id, connection=c)
        unresolved = c.execute('SELECT count(*) FROM backintel.analysis_requests WHERE run_id=%s AND charge IS NULL', (run_id,)).fetchone()[0]
        if unresolved:
            raise RuntimeError('Reconcile uncertain charges before resuming this run')
        resumed=c.execute("UPDATE backintel.capability_jobs SET state='queued',cancel_requested=false,result_sha256=NULL,due_at=now(),error=NULL,lease_until=NULL,max_attempts=LEAST(5,GREATEST(max_attempts,attempts+3)) WHERE job_id=%s AND state IN ('completed','cancelled','failed') RETURNING job_id", (job_id,)).fetchone()
        if resumed:
            c.execute("UPDATE backintel.analysis_runs SET owner=%s,status='queued',result=NULL,error=NULL,updated_at=now() WHERE id=%s", (actor['id'], run_id))
    return run_id


def submit_import(domain, actor):
    actor = db.authorize(actor, domain, ('manager',))
    if not db.source(domain)['body'].get('terms_acknowledged'):
        raise PermissionError('Confirm source access and terms before importing')
    with db.connect() as c, c.transaction():
        c.execute('SELECT pg_advisory_xact_lock(81827029)')
        pending = c.execute("SELECT id FROM backintel.analysis_runs WHERE body->>'operation'='import' AND body->>'domain'=%s AND owner=%s AND status IN ('queued','running') ORDER BY created_at DESC LIMIT 1", (domain, actor['id'])).fetchone()
        if pending:
            return db.run(pending[0])
        identity = digest(['source-import', domain, actor['id'], time.time_ns()])
        payload = {'run_id': identity, 'operation': 'import'}
        c.execute('INSERT INTO backintel.analysis_runs(id,owner,body) VALUES(%s,%s,%s)',
                  (identity, actor['id'], Jsonb({'operation': 'import', 'domain': domain})))
        job_id = enqueue(Evidence(c, 'analysis-job-'+identity), payload, identity)
        c.execute('UPDATE backintel.analysis_runs SET job_id=%s WHERE id=%s', (job_id, identity))
    return db.run(identity)


def model_job(identity, *, connection=None):
    r, g = db.check_run(identity)
    # A subprocess enforces wall time and releases predictor/Decide memory between jobs.
    child = subprocess.run([sys.executable, '-m', 'runtime.analysis_models', '--domain', g['domain'], '--snapshot', r['snapshot_id']],
                           capture_output=True, text=True, timeout=CONFIG['limits']['model_seconds']-20)
    if child.returncode:
        raise RuntimeError('Model comparison failed: '+safe_error(child.stderr[-1200:]))
    manifest = json.loads(child.stdout)
    candidate = digest([g['id'], manifest['id'], manifest['artifacts']])
    with (nullcontext(connection) if connection is not None else db.connect()) as c, c.transaction():
        c.execute('SELECT pg_advisory_xact_lock(hashtextextended(%s,0))', ('analysis-source:'+g['domain'],))
        db.check_run(identity, connection=c)
        if db.source(g['domain'], connection=c)['latest_snapshot'] != r['snapshot_id']:
            raise ValueError('Source changed during model comparison; compare the latest snapshot before promotion')
        c.execute('INSERT INTO backintel.analysis_models(id,goal_id,snapshot_id,body) VALUES(%s,%s,%s,%s) ON CONFLICT DO NOTHING',
                  (candidate, g['id'], r['snapshot_id'], Jsonb(manifest)))
    ref = db.evidence(identity, 'model_comparison', candidate, manifest)
    return {'status': 'succeeded', 'summary': 'Real predictor comparison completed. Manager approval is required before use.',
            'candidate_id': candidate, 'evidence_id': ref, 'comparison': manifest, 'usage': db.usage(identity)}


def promote(identity, actor, route='catboost-facts'):
    m = db.query('SELECT * FROM backintel.analysis_models WHERE id=%s', (identity,), one=True)
    if not m:
        raise ValueError('Unknown candidate')
    g = db.goal(m['goal_id'])
    db.authorize(actor, g['domain'], ('manager',))
    with db.connect() as c, c.transaction():
        c.execute('SELECT pg_advisory_xact_lock(hashtextextended(%s,0))', ('analysis-source:'+g['domain'],))
        source = db.source(g['domain'], connection=c)
        locked = c.execute('SELECT body,promoted FROM backintel.analysis_models WHERE id=%s FOR UPDATE', (identity,)).fetchone()
        if locked[0].get('invalidated_by'):
            raise ValueError('This candidate was invalidated by a source correction')
        if m['snapshot_id'] != source['latest_snapshot']:
            raise ValueError('Candidate snapshot is no longer current; compare the current snapshot')
        if route not in ('catboost-facts', 'tabiclv2-facts', 'catboost-facts-decide', 'tabiclv2-facts-decide') or not any(a['file'] == route+'.joblib' for a in locked[0]['artifacts']):
            raise ValueError('Requested predictor was not validated in this comparison')
        if locked[1] and locked[0].get('approved_route') != route:
            raise ValueError('A promoted candidate has an immutable predictor route')
        changed = c.execute('UPDATE backintel.analysis_goals SET active_model=%s WHERE id=%s AND version=%s AND confirmed AND NOT paused RETURNING id', (identity, g['id'], g['version'])).fetchone()
        if not changed:
            raise ValueError('Goal changed during promotion; reload it and try again')
        run_id = _admit_run(c, g, actor)
        manager = c.execute("""SELECT id FROM backintel.analysis_principals WHERE id=%s AND enabled
            AND (expires_at IS NULL OR expires_at>clock_timestamp()) AND role='manager'
            AND %s=ANY(domains) FOR UPDATE""", (actor['id'], g['domain'])).fetchone()
        if not manager:
            raise PermissionError('Current manager authority is required to promote a predictor')
        if not locked[1]:
            body = {**locked[0], 'approved_route': route, 'approved_by': actor['id']}
            c.execute('UPDATE backintel.analysis_models SET promoted=true,body=%s WHERE id=%s', (Jsonb(body), identity))
    return db.run(run_id)


def threshold_crossed(previous, current, threshold):
    """Compare the same table and group; record counts are not target estimates."""
    def means(result):
        return {(table['title'], table['group_by'], row['group']): row['mean']
                for table in result.get('tables', []) for row in table.get('rows', [])
                if 'group_by' in table and isinstance(row.get('mean'), (int, float))}
    before, after = means(previous), means(current)
    return any(abs(after[key] - before[key]) >= threshold and after[key] != before[key]
               for key in before.keys() & after.keys())


def handle(store, payload):
    from runtime.analysis_agent import analyze
    from runtime.analysis_planning import propose
    identity = payload['run_id']
    r = db.run(identity)
    if r['status'] == 'succeeded':
        return store.put('analysis_result', identity, r['result'], int(time.time())) if not store.find('analysis_result', identity) else store.find('analysis_result', identity)
    refresh_before = db.source(r['body']['domain']) if payload['operation'] == 'import' else None
    db.write("UPDATE backintel.analysis_runs SET status='running',updated_at=now() WHERE id=%s", (identity,))
    db.event(identity, 'started', {'operation': payload['operation']})
    try:
        with store.connection.transaction():
            if payload['operation'] == 'import':
                with store.connection.transaction():
                    db.check_run(identity, connection=store.connection)
                    result = import_source(r['body']['domain'], {'id': r['owner']}, connection=store.connection, run_id=identity)
                    db.check_run(identity, connection=store.connection)
                    db.write('UPDATE backintel.analysis_runs SET snapshot_id=%s WHERE id=%s', (result['snapshot'],identity), connection=store.connection)
                    result['goals'] = schedule_snapshot(r['body']['domain'], result, connection=store.connection)
            else:
                if payload['operation'] == 'planning':
                    result = propose(identity)
                elif payload['operation'] == 'discovery':
                    from runtime.source_access import discover
                    result = discover(identity)
                elif payload['operation'] in ('collection', 'refresh'):
                    from runtime.source_collection import collect
                    result = collect(identity)
                elif payload['operation'] == 'interpretation':
                    from runtime.source_semantics import interpret
                    result = interpret(identity)
                elif payload['operation'] == 'preparation':
                    from runtime.source_preparation import prepare
                    result = prepare(identity)
                elif payload['operation'] == 'validation':
                    from runtime.source_validation import check
                    result = check(identity)
                elif payload['operation'] == 'answer':
                    from runtime.source_answer import answer
                    result = answer(identity)
                elif payload['operation'] == 'workflow':
                    from runtime.source_workflows import execute as execute_workflow
                    result = execute_workflow(identity)
                elif payload['operation'] == 'method':
                    from runtime.source_methods import study
                    result = study(identity)
                else:
                    result = model_job(identity, connection=store.connection) if payload['operation'] == 'training' else analyze(identity)
            db.check_run(identity, connection=store.connection)
            # Publish success in the job's transaction so interruption rolls back the
            # run, saved finding, notifications and accepted evidence together.
            with store.connection.transaction():
                connection = store.connection
                if r['goal_id']:
                    domain = db.run_domain(r)
                    connection.execute('SELECT pg_advisory_xact_lock(hashtextextended(%s,0))', ('analysis-source:'+domain,))
                    source = db.source(domain, connection=connection)
                    if payload['operation'] not in ('planning', 'discovery', 'collection', 'interpretation', 'preparation', 'validation', 'answer', 'workflow', 'method', 'refresh') and not source['body'].get('terms_acknowledged'):
                        raise PermissionError('Source terms are not acknowledged')
                    eligible = db.query('SELECT * FROM backintel.analysis_goals WHERE id=%s FOR UPDATE', (r['goal_id'],), one=True, connection=connection)
                    if payload['operation'] != 'planning' and eligible['body'].get('objective'):
                        from runtime.source_access import require_source_access
                        require_source_access(r['goal_id'], {'id': r['owner']}, connection=connection)
                    if (payload['operation'] != 'planning' and not eligible['confirmed']) or eligible['paused'] or eligible['version'] != r['goal_version']:
                        raise PermissionError('Goal became ineligible before publication')
                    if payload['operation'] not in ('planning', 'discovery', 'collection', 'interpretation', 'preparation', 'validation', 'answer', 'workflow', 'method', 'refresh') and (source['latest_snapshot'] != r['snapshot_id'] or eligible['active_model'] != r['body'].get('model_id')):
                        raise PermissionError('Source snapshot or approved model changed before publication')
                owner = db.query("""SELECT id FROM backintel.analysis_principals
                    WHERE id=%s AND enabled AND (expires_at IS NULL OR expires_at>clock_timestamp())
                    AND role=ANY(%s) AND %s=ANY(domains) FOR UPDATE""",
                    (r['owner'], ['manager','analyst'] if payload['operation'] in ('analysis','discovery','collection') else ['manager'], db.run_domain(r)),
                    one=True, connection=connection)
                if not owner:
                    raise PermissionError('Run owner lost access before publication')
                if payload['operation'] == 'workflow':
                    from runtime import workflow_updates
                    workflow_updates.guard_publication(r, eligible, connection)
                connection.execute("UPDATE backintel.analysis_runs SET status='succeeded',result=%s,error=NULL,updated_at=now() WHERE id=%s", (Jsonb(result), identity))
                if payload['operation'] == 'workflow':
                    workflow_updates.save_version(identity, result, connection)
                if payload['operation'] in ('analysis','answer','workflow'):
                    g = db.goal(r['goal_id'])
                    previous = db.run(g['last_success']) if g['last_success'] else None
                    standing = r['body']['question'] == g['body']['question'] and r['goal_version'] == g['version']
                    changed = standing and previous and threshold_crossed(previous['result'], result, g['body']['notification_delta'])
                    if standing:
                        connection.execute('UPDATE backintel.analysis_goals SET last_success=%s WHERE id=%s AND version=%s', (identity, g['id'], r['goal_version']))
                    if changed:
                        connection.execute('INSERT INTO backintel.analysis_events(run_id,kind,body) VALUES(%s,%s,%s)',
                                           (identity, 'material_change', Jsonb({'message': 'A saved goal threshold was crossed.'})))
                connection.execute('INSERT INTO backintel.analysis_events(run_id,kind,body) VALUES(%s,%s,%s)',
                                   (identity, 'completed', Jsonb({'status': 'succeeded'})))
    except Exception as error:
        # No failed refresh replaces last_success; no response is disguised as real success.
        status = 'cancelled' if isinstance(error, (InterruptedError, PermissionError)) else 'partial'
        reason = safe_error(error)
        if payload['operation'] == 'import' and not isinstance(error, InterruptedError):
            db.write("""UPDATE backintel.analysis_sources SET body=body || %s WHERE id=%s
                     AND latest_snapshot IS NOT DISTINCT FROM %s
                     AND COALESCE(body->'last_checked_at','null'::jsonb)=%s""",
                     (Jsonb({'last_refresh_error':reason, 'last_checked_at':time.time()}), r['body']['domain'],
                      refresh_before['latest_snapshot'], Jsonb(refresh_before['body'].get('last_checked_at'))))
        result = {'status': status, 'summary': 'This run did not complete.', 'limitations': [reason], 'usage': db.usage(identity)}
        if payload['operation'] in ('collection', 'refresh'):
            from runtime.source_collection import coverage
            result['coverage'] = coverage(identity)
        if payload['operation'] == 'workflow':
            from runtime import workflow_updates
            result['update'] = workflow_updates.failed(identity, reason, status)
        if payload['operation'] in ('validation','workflow'):
            result['validation'] = db.step(identity, 'validation-report')
        if payload['operation'] in ('preparation','workflow'):
            from runtime.source_preparation import coverage
            result['coverage'] = coverage(identity)
        db.write('UPDATE backintel.analysis_runs SET status=%s,result=%s,error=%s,updated_at=now() WHERE id=%s', (status, Jsonb(result), reason, identity))
        db.event(identity, 'completed', {'status': status, 'reason': reason})
    attempt=db.query('SELECT attempts FROM backintel.capability_jobs WHERE job_id=%s',(r['job_id'],),one=True)['attempts']
    return store.put('analysis_result', f'{identity}:{attempt}', result, int(time.time()))


def _finish_run_failure(connection, job_id, job_state, reason):
    status = 'cancelled' if job_state == 'cancelled' else 'partial'
    run = connection.execute("UPDATE backintel.analysis_runs SET status=%s,error=%s,updated_at=now() WHERE job_id=%s AND status IN ('queued','running') RETURNING id", (status, reason, job_id)).fetchone()
    if run:
        connection.execute('INSERT INTO backintel.analysis_events(run_id,kind,body) VALUES(%s,%s,%s)', (run[0], 'completed', Jsonb({'status': status, 'reason': reason})))


def dispatch(run_id=None):
    # One process owns model work. Drain new arrivals before releasing the worker.
    results = []
    with db.connect() as c:
        if not c.execute('SELECT pg_try_advisory_lock(81827028)').fetchone()[0]:
            return {'status': 'worker_busy'}
        # The exclusive worker lock proves any remaining running analysis job is orphaned.
        c.execute("UPDATE backintel.capability_jobs SET lease_until=now() WHERE state='running' AND task_id LIKE %s", ('analysis-job-%',))
        with c.transaction():
            stranded=c.execute("""SELECT j.job_id,j.error,j.state FROM backintel.capability_jobs j
                JOIN backintel.analysis_runs r ON r.job_id=j.job_id
                WHERE j.task_id LIKE 'analysis-job-%' AND j.state IN ('failed','cancelled')
                AND r.status IN ('queued','running') FOR UPDATE OF j,r""").fetchall()
            for job_id, reason, job_state in stranded:
                _finish_run_failure(c, job_id, job_state, reason)
        continued = set()
        while True:
            from runtime.source_workflows import continue_refresh
            pending_refreshes = db.query("""SELECT r.id FROM backintel.analysis_runs r
                WHERE r.body->>'operation'='refresh' AND r.status='succeeded'
                AND NOT EXISTS (SELECT 1 FROM backintel.analysis_steps s WHERE s.run_id=r.id AND s.id='refresh-workflow')
                ORDER BY r.created_at LIMIT 20""")
            for refresh in pending_refreshes:
                if refresh['id'] in continued:
                    continue
                continued.add(refresh['id'])
                try:
                    continue_refresh(refresh['id'])
                except (ValueError, PermissionError, RuntimeError, OSError) as error:
                    db.save_step(refresh['id'], 'refresh-workflow-error', 'refresh_error', {'decision': safe_error(error)})
            task_ids = [r['task_id'] for r in db.query("SELECT DISTINCT task_id FROM backintel.capability_jobs WHERE task_id LIKE 'analysis-job-%' AND state IN ('queued','retry','running')")]
            with c.transaction():
                failed = c.execute("UPDATE backintel.capability_jobs SET state=CASE WHEN cancel_requested THEN 'cancelled' ELSE 'failed' END,error=CASE WHEN cancel_requested THEN 'Cancelled after worker interruption' ELSE 'Worker lease expired at attempt limit' END,lease_until=NULL WHERE task_id=ANY(%s) AND state='running' AND lease_until<now() AND (cancel_requested OR attempts>=max_attempts) RETURNING job_id,error,state", (task_ids,)).fetchall()
                for job_id, reason, job_state in failed:
                    _finish_run_failure(c, job_id, job_state, reason)
            available = runnable(c, task_ids)
            for abandoned in db.query("SELECT DISTINCT r.run_id FROM backintel.analysis_requests r JOIN backintel.analysis_runs a ON a.id=r.run_id JOIN backintel.capability_jobs j ON j.job_id=a.job_id WHERE r.status='reserved' AND j.state<>'running'"):
                with db.connect() as cleanup, cleanup.transaction():
                    Evidence(cleanup, 'analysis-job-'+abandoned['run_id']).lock()
                    state = cleanup.execute('SELECT j.state FROM backintel.capability_jobs j JOIN backintel.analysis_runs r ON r.job_id=j.job_id WHERE r.id=%s', (abandoned['run_id'],)).fetchone()[0]
                    if state != 'running':
                        db.release_unsent(abandoned['run_id'], connection=cleanup)
            if not available:
                delayed = c.execute("""SELECT EXTRACT(EPOCH FROM min(j.due_at)-now())
                    FROM backintel.capability_jobs j
                    WHERE j.task_id=ANY(%s) AND j.state='retry'
                    AND NOT EXISTS (SELECT 1 FROM backintel.capability_jobs earlier
                        WHERE earlier.task_id=j.task_id AND earlier.sequence<j.sequence
                        AND earlier.state IN ('queued','retry','running','failed'))""", (task_ids,)).fetchone()[0]
                if delayed is None:
                    break
                time.sleep(max(.01, min(1., float(delayed))))
                continue
            for job_id in available:
                r = db.query('SELECT id,body FROM backintel.analysis_runs WHERE job_id=%s', (job_id,), one=True)
                if r:
                    duration = 1800 if r['body']['operation']=='training' else 600
                    if r['body']['operation'] in ('workflow', 'refresh'):
                        duration = max(25,min(1800,db.goal(db.run(r['id'])['goal_id'])['body']['objective']['limits']['timeout_seconds']))
                    result = execute(job_id, handle, max_wall_seconds=duration,
                                     usage_reader=lambda identity=r['id']: db.usage(identity))
                    results.append(result)
                    if result['state'] in ('failed', 'cancelled'):
                        with c.transaction():
                            _finish_run_failure(c, job_id, result['state'], result.get('error', 'Job stopped before acceptance'))
    return {'status': 'completed', 'jobs': results}


def schedule_snapshot(domain, update, *, train=True, connection=None):
    # Import jobs share their publication transaction with follow-up admission;
    # submit's stable run identity reuses jobs already admitted successfully.
    outcomes = []
    for g in db.query('SELECT * FROM backintel.analysis_goals WHERE domain=%s AND confirmed AND NOT paused', (domain,)):
        try:
            actor = {'id': g['owner']}
            run = submit(g['id'], actor, connection=connection)
            latest = db.query('SELECT * FROM backintel.analysis_models WHERE goal_id=%s ORDER BY created_at DESC LIMIT 1', (g['id'],), one=True)
            if train and latest:
                old = {r['id']: r for r in db.records(latest['snapshot_id']) if r['target'] is not None and r['split']=='train'}
                new = {r['id']: r for r in db.records(update['snapshot'], connection=connection) if r['target'] is not None and r['split']=='train'}
                attempt = db.query("SELECT created_at FROM backintel.analysis_runs WHERE goal_id=%s AND body->>'operation'='training' ORDER BY created_at DESC LIMIT 1", (g['id'],), one=True)
                interval = time.time()-(attempt or latest)['created_at'].timestamp()
                changed = any(new.get(identity) != row for identity, row in old.items())
                if (changed or len(new.keys()-old.keys())>=CONFIG['limits']['new_labels']) and interval>=CONFIG['limits']['candidate_interval_seconds']:
                    submit(g['id'], actor, operation='training', connection=connection)
            outcomes.append({'goal_id': g['id'], 'run_id': run['id'], 'status': run['status']})
        except (ValueError, PermissionError, RuntimeError, OSError) as error:
            outcomes.append({'goal_id': g['id'], 'status': 'blocked', 'reason': safe_error(error)})
    return outcomes


def refresh():
    results = []
    for source in db.query('SELECT * FROM backintel.analysis_sources'):
        domain = source['domain']
        if domain not in CONFIG['sources']:
            continue
        owner = db.query("SELECT id FROM backintel.analysis_principals WHERE enabled AND (expires_at IS NULL OR expires_at>now()) AND role='manager' AND %s=ANY(domains) ORDER BY id LIMIT 1", (domain,), one=True)
        if not owner:
            results.append({'domain': domain, 'status': 'blocked', 'reason': 'No manager has permission to refresh this source'})
            continue
        try:
            update = import_source(domain, owner)
            goals = schedule_snapshot(domain, update)
            results.append({'domain': domain, **update, 'goals': goals})
        except (ValueError, PermissionError, RuntimeError, OSError) as error:
            results.append({'domain': domain, 'status': 'blocked', 'reason': safe_error(error)})
    return {'sources': results, 'dispatch': dispatch()}


def wake(run_id):
    from pathlib import Path
    import os
    path = Path(os.getenv('BACKINTEL_ACCESS_CREDENTIAL_FILE', '/run/backintel-credentials/access.json'))
    token = json.loads(path.read_text())['worker']
    base = os.getenv('BACKINTEL_AEGRA_URL','http://127.0.0.1:2026')
    with httpx.Client(timeout=15,headers={'Authorization':'Bearer '+token}) as client:
        thread = client.post(base+'/threads',json={'metadata':{'analysis_run':run_id}})
        thread.raise_for_status()
        response = client.post(base+f"/threads/{thread.json()['thread_id']}/runs",json={'assistant_id':'analysis_run','input':{'run_id':run_id}})
        response.raise_for_status()
    return {'submitted': True,'thread_id':thread.json()['thread_id'],'native_run_id':response.json()['run_id']}
