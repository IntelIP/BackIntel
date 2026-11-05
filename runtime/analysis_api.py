"""Thin authenticated application routes mounted by Aegra."""

import asyncio
import json
import os
import httpx
from datetime import datetime
from pathlib import Path

from fastapi import FastAPI, Depends, Request, HTTPException
from fastapi.responses import FileResponse, JSONResponse, Response, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict, Field
from psycopg.types.json import Jsonb

from runtime import analysis_store as db
from runtime import analysis_service as service
from runtime.analysis_data import CONFIG, digest, feature_groups
from runtime.jobs import cancel
from runtime.analysis_errors import safe_error
from runtime.analysis_objectives import ObjectiveContract
from runtime.source_access import require_source_access
from runtime.workflow_triggers import TriggerInput, EventInput

app = FastAPI(title='BackIntel analysis workspace')


class Input(BaseModel):
    model_config = ConfigDict(extra='forbid')


class GoalInput(Input):
    domain: str
    question: str = Field(min_length=1,max_length=2000)
    objective: ObjectiveContract | None = None


class GoalUpdate(Input):
    document_refs: list[str] | None = Field(default=None, max_length=4)
    expected_version: int | None = Field(default=None, ge=1)
    question: str | None = Field(default=None,min_length=1,max_length=2000)
    paused: bool | None = None
    confirmed: bool | None = None
    threshold: float | None = Field(default=None,ge=0,le=100000)
    budget_usd: float | None = Field(default=None,ge=0,le=1)
    objective: ObjectiveContract | None = None


class RunInput(Input):
    question: str | None = Field(default=None,min_length=1,max_length=2000)
    operation: str = 'analysis'


class DocumentInput(Input):
    title: str = Field(min_length=1, max_length=200)
    source_url: str | None = Field(default=None, max_length=2000)
    media_type: str
    content_base64: str = Field(min_length=1, max_length=2_666_668)


class TermsInput(Input):
    acknowledged: bool
    source_spec_sha256: str | None = None


class PromotionInput(Input):
    route: str = 'catboost-facts'


class ReviewInput(Input):
    text: str = Field(min_length=1,max_length=4000)
    kind: str = 'comment'
    run_id: str | None = None


class CorrectionInput(Input):
    record_id: str
    features: dict[str,str | float | None] = Field(default_factory=dict)
    target: float | None = None
    explanation: str = Field(min_length=1,max_length=2000)


class GrantInput(Input):
    domains: list[str]
    enabled: bool = True
    expires_at: datetime | None = None
    budget_usd: float | None = None


class GoalAccessInput(Input):
    permission: str | None = None


WRITE_ORIGINS = frozenset(('http://127.0.0.1:2028', 'http://localhost:2028'))


def access(request: Request):
    if request.method not in ('GET','HEAD'):
        origin=request.headers.get('origin')
        if origin and origin not in WRITE_ORIGINS:
            raise HTTPException(403,'Cross-origin writes are denied')
    return db.principal(request.headers.get('authorization','').removeprefix('Bearer '))


@app.exception_handler(PermissionError)
async def denied(request, error):
    return JSONResponse({'detail':safe_error(error)},status_code=403)


@app.exception_handler(ValueError)
async def invalid(request, error):
    return JSONResponse({'detail':safe_error(error)},status_code=400)


@app.exception_handler(RuntimeError)
async def blocked(request,error):
    return JSONResponse({'detail':safe_error(error)},status_code=409)


@app.get('/api/v1/me')
def me(p=Depends(access)):
    return {**p, 'budget': CONFIG['budget']}


@app.get('/api/v1/queue')
def queue(p=Depends(access)):
    actor = db.authorize(p)
    visible = db.visible_goal_ids(actor)
    jobs = db.query('''SELECT r.id,r.goal_id,r.owner,r.status,j.state,j.created_at,j.updated_at,j.wall_ms,
        EXTRACT(EPOCH FROM COALESCE((SELECT min(e.created_at) FROM backintel.analysis_events e
            WHERE e.run_id=r.id AND e.kind='started'),
            CASE WHEN j.state IN ('completed','failed','cancelled') THEN j.updated_at ELSE clock_timestamp() END)-j.created_at) AS waiting_seconds
        FROM backintel.analysis_runs r JOIN backintel.capability_jobs j ON j.job_id=r.job_id
        WHERE r.goal_id=ANY(%s) OR (r.goal_id IS NULL AND r.owner=%s)
        ORDER BY j.created_at DESC LIMIT 50''', (visible, actor['id']))
    counts = db.query('''SELECT count(*) FILTER (WHERE j.state='running') AS active,
        count(*) FILTER (WHERE j.state IN ('queued','retry')) AS waiting
        FROM backintel.capability_jobs j JOIN backintel.analysis_runs r ON r.job_id=j.job_id''', one=True)
    usage = db.query('''SELECT count(*) AS provider_calls,COALESCE(sum(q.charge),0) AS provider_usd,
        COALESCE(sum(q.reserved) FILTER (WHERE q.charge IS NULL),0) AS reserved_usd,
        count(*) FILTER (WHERE q.charge IS NULL) AS unresolved_charges
        FROM backintel.analysis_requests q JOIN backintel.analysis_runs r ON r.id=q.run_id WHERE r.owner=%s''', (actor['id'],), one=True)
    return {'jobs': jobs, 'shared_capacity': {**counts, 'active_limit': service.execution_limit(),
                                           'waiting_limit': service.waiting_limit(),
                                           'outstanding_limit': service.waiting_limit()},
            'your_usage': {**usage, 'budget_usd': actor['budget_usd'], 'local_compute_usd': None}}


@app.put('/api/v1/goals/{identity}/access/{principal_id}')
def goal_access(identity: str, principal_id: str, body: GoalAccessInput, p=Depends(access)):
    return db.share_goal(identity, principal_id, body.permission, p)


@app.get('/api/v1/notifications')
def notifications(p=Depends(access)):
    p=db.authorize(p)
    return db.query("SELECT e.sequence AS id,e.run_id,e.body,e.created_at,g.id AS goal_id,g.domain FROM backintel.analysis_events e JOIN backintel.analysis_runs r ON r.id=e.run_id JOIN backintel.analysis_goals g ON g.id=r.goal_id WHERE e.kind='material_change' AND g.id=ANY(%s) ORDER BY e.sequence DESC LIMIT 30",(db.visible_goal_ids(p),))


@app.get('/api/v1/sources')
def sources(p=Depends(access)):
    p=db.authorize(p)
    return [db.source(row['id']) for row in db.query('SELECT id FROM backintel.analysis_sources WHERE domain=ANY(%s) ORDER BY domain',([domain for domain in p['domains'] if domain in CONFIG['sources']],))]


@app.post('/api/v1/sources/{domain}/terms')
def terms(domain:str,body:TermsInput,p=Depends(access)):
    db.authorize(p,domain,('manager',),administrator=True)
    with db.connect() as c, c.transaction():
        db.authorize(p,domain,('manager',),connection=c,administrator=True)
        c.execute('SELECT pg_advisory_xact_lock(hashtextextended(%s,0))', ('analysis-source:'+domain,))
        manager=c.execute("""SELECT id FROM backintel.analysis_principals WHERE id=%s AND enabled
            AND (expires_at IS NULL OR expires_at>clock_timestamp()) AND role='manager'
            AND %s=ANY(domains) FOR SHARE""", (p['id'],domain)).fetchone()
        if not manager: raise PermissionError('Current manager authority is required to change source terms')
        source=db.source(domain, connection=c)
        if body.acknowledged and body.source_spec_sha256 != source['body']['source_spec_sha256']:
            raise ValueError('Source terms changed; reload and confirm the current terms')
        updated={**source['body'],'terms_acknowledged':body.acknowledged,'terms_actor':p['id']}
        db.write('UPDATE backintel.analysis_sources SET body=%s WHERE id=%s',(Jsonb(updated),domain), connection=c)
    return db.source(domain)


@app.post('/api/v1/sources/{domain}/refresh',status_code=202)
async def refresh_source(domain:str,p=Depends(access)):
    r=service.submit_import(domain,p)
    try:
        await asyncio.to_thread(service.wake,r['id'])
    except (OSError,httpx.HTTPError):
        db.event(r['id'],'dispatch_pending',{'message':'Import queued durably.'})
    return r


@app.get('/api/v1/goals')
def goals(p=Depends(access)):
    p=db.authorize(p)
    result=db.query('SELECT * FROM backintel.analysis_goals WHERE id=ANY(%s) ORDER BY created_at DESC',(db.visible_goal_ids(p),))
    for g in result:
        from runtime import source_documents
        g['documents'] = source_documents.listing(g, p)
        grant = db.query('SELECT permission FROM backintel.analysis_goal_access WHERE goal_id=%s AND principal_id=%s', (g['id'], p['id']), one=True)
        permission = 'manage' if g['owner'] == p['id'] or p['administrator'] else (grant or {}).get('permission')
        g['can_manage'] = p['role'] == 'manager' and permission == 'manage'
        g['can_run'] = p['role'] in ('manager', 'analyst') and permission in ('run', 'manage')
        proposal = db.query("SELECT id,result FROM backintel.analysis_runs WHERE goal_id=%s AND goal_version=%s AND body->>'operation'='planning' AND status='succeeded' ORDER BY created_at DESC LIMIT 1", (g['id'], g['version']), one=True) if g['body'].get('objective') else None
        g['plan'] = proposal['result'] if proposal else None
        g['plan_run_id'] = proposal['id'] if proposal else None
        g['source_access'] = False
        g['workflows'] = []
        if g['body'].get('objective'):
            try:
                with db.connect() as control, control.transaction():
                    require_source_access(g['id'], p, connection=control, expected_version=g['version'], read_only=True)
                g['source_access'] = True
            except PermissionError:
                g['plan'] = None
                g['plan_run_id'] = None
        if g['source_access']:
            from runtime.source_workflows import history
            g['workflows'] = history(g['id'],p)
        discovery = db.query("SELECT result FROM backintel.analysis_runs WHERE goal_id=%s AND goal_version=%s AND body->>'operation'='discovery' AND status='succeeded' ORDER BY created_at DESC LIMIT 1", (g['id'], g['version']), one=True) if g['source_access'] else None
        g['discovery'] = discovery['result'] if discovery else None
        collection = db.query("SELECT result FROM backintel.analysis_runs WHERE goal_id=%s AND goal_version=%s AND body->>'operation' IN ('collection','refresh') AND status='succeeded' ORDER BY created_at DESC LIMIT 1", (g['id'], g['version']), one=True) if g['source_access'] else None
        g['collection'] = collection['result'] if collection else None
        interpretation = db.query("SELECT result FROM backintel.analysis_runs WHERE goal_id=%s AND goal_version=%s AND body->>'operation'='interpretation' AND status='succeeded' ORDER BY created_at DESC LIMIT 1", (g['id'], g['version']), one=True) if g['source_access'] else None
        g['interpretation'] = interpretation['result'] if interpretation else None
        preparation = db.query("SELECT result FROM backintel.analysis_runs WHERE goal_id=%s AND goal_version=%s AND body->>'operation'='preparation' AND status='succeeded' ORDER BY created_at DESC LIMIT 1", (g['id'], g['version']), one=True) if g['source_access'] else None
        g['preparation'] = preparation['result'] if preparation else None
        validation = db.query("SELECT result FROM backintel.analysis_runs WHERE goal_id=%s AND goal_version=%s AND body->>'operation'='validation' ORDER BY created_at DESC LIMIT 1", (g['id'], g['version']), one=True) if g['source_access'] else None
        g['validation'] = (validation['result'].get('validation') or validation['result']) if validation and validation['result'] else None
        source=db.source(g['domain'])
        previous=db.run(g['last_success']) if g['last_success'] else None
        g['freshness']='refresh_failed' if source['body'].get('last_refresh_error') else 'current' if previous and previous['snapshot_id']==source['latest_snapshot'] and previous['goal_version']==g['version'] and previous['body'].get('model_id')==g['active_model'] and previous['body'].get('analysis_identity')==service.analysis_identity() else 'stale' if previous else 'unanswered'
        if previous and g['body'].get('objective'):
            g['freshness'] = 'checked snapshot'
        if g['source_access']:
            from runtime.workflow_updates import status
            g['update_status'] = status(g)
            if g['update_status']['question'] == g['body']['question']:
                g['freshness'] = g['update_status']['state'].replace('_', ' ')
    return result


@app.get('/api/v1/goals/{identity}/update-status')
def workflow_update_status(identity: str, p=Depends(access)):
    from runtime.source_workflows import update_status
    return update_status(identity, p)


@app.get('/api/v1/reference-scenarios/online-retail')
def retail_scenario(p=Depends(access)):
    db.authorize(p, 'commerce', ('manager',))
    scenario = json.loads((Path(__file__).resolve().parents[1] / 'config/reference_scenarios/online_retail.json').read_text())
    return GoalInput.model_validate(scenario['request']).model_dump(mode='json')


@app.post('/api/v1/goals',status_code=201)
async def create(body:GoalInput,p=Depends(access)):
    from runtime.analysis_graphs import goal_graph
    g=await asyncio.to_thread(service.create_goal,p,body.domain,body.question,objective=body.objective.model_dump() if body.objective else None)
    proposal=await goal_graph.ainvoke({'goal_id':g['id']})
    return {**g,'proposal':proposal['result']}


@app.patch('/api/v1/goals/{identity}')
def update(identity:str,body:GoalUpdate,p=Depends(access)):
    return service.revise_goal(identity,p,**body.model_dump())


@app.get('/api/v1/goals/{identity}/documents')
def goal_documents(identity: str, p=Depends(access)):
    from runtime import source_documents
    db.authorize_goal(p, identity)
    return source_documents.listing(db.goal(identity), p)


@app.post('/api/v1/goals/{identity}/documents', status_code=201)
def retain_document(identity: str, body: DocumentInput, p=Depends(access)):
    import base64
    import binascii
    from runtime import source_documents
    db.authorize_goal(p, identity, ('manager',), permission='manage')
    try:
        payload = base64.b64decode(body.content_base64, validate=True)
    except (ValueError, binascii.Error):
        raise ValueError('Document content must be valid base64-encoded original bytes') from None
    return source_documents.admit(identity, p, title=body.title, source_url=body.source_url,
                                  media_type=body.media_type, payload=payload)


@app.get('/api/v1/documents/{identity}')
def document_details(identity: str, p=Depends(access)):
    from runtime import source_documents
    row = source_documents.read(identity, p)
    return {'id': row['id'], **row['body']}


@app.get('/api/v1/documents/{identity}/original')
def document_original(identity: str, p=Depends(access)):
    from runtime import source_documents
    row = source_documents.read(identity, p)
    return Response(row['payload'], media_type='application/octet-stream', headers={
        'Content-Disposition': 'attachment; filename="document-' + row['id'] + '.txt"',
        'X-Content-Type-Options': 'nosniff', 'Cache-Control': 'no-store'})


@app.post('/api/v1/goals/{identity}/runs',status_code=202)
def start(identity:str,body:RunInput,p=Depends(access)):
    if body.operation not in ('analysis', 'training', 'planning', 'discovery', 'collection', 'interpretation', 'preparation', 'validation', 'answer'):
        raise ValueError('Unsupported operation')
    r=service.submit(identity,p,body.question,body.operation)
    try:
        service.wake(r['id'])
    except (OSError,httpx.HTTPError):
        db.event(r['id'],'dispatch_pending',{'message':'Queued durably; the next dispatcher will resume it.'})
    return r


@app.get('/api/v1/runs')
def runs(goal_id:str,p=Depends(access)):
    actor=db.authorize_goal(p,goal_id)
    result = []
    for r in db.query('SELECT * FROM backintel.analysis_runs WHERE goal_id=%s ORDER BY created_at DESC LIMIT 50',(goal_id,)):
        try:
            result.append(run_response(r,actor))
        except PermissionError:
            continue
    return result


@app.get('/api/v1/runs/{identity}')
def run(identity:str,p=Depends(access)):
    r=db.run(identity)
    actor=db.authorize_run(p,r)
    return run_response(r,actor)


@app.post('/api/v1/runs/{identity}/cancel')
def cancel_run(identity:str,p=Depends(access)):
    r=db.run(identity)
    db.authorize_run(p,r,('manager',),permission='manage')
    with db.connect() as c, c.transaction():
        db.authorize_run(p,r,('manager',),permission='manage',connection=c)
        c.execute('SELECT id FROM backintel.analysis_runs WHERE id=%s FOR UPDATE', (identity,))
        manager=c.execute("""SELECT id FROM backintel.analysis_principals WHERE id=%s AND enabled
            AND (expires_at IS NULL OR expires_at>clock_timestamp()) AND role='manager'
            AND %s=ANY(domains) FOR SHARE""", (p['id'],db.run_domain(r))).fetchone()
        if not manager: raise PermissionError('Current manager authority is required to cancel a run')
        state=cancel(c,r['job_id'])
        db.write("UPDATE backintel.analysis_runs SET status='cancelled',updated_at=now() WHERE id=%s AND status='queued'",(identity,),connection=c)
    return {'status':state}


@app.get('/api/v1/runs/{identity}/prepared/{page_key}')
def prepared(identity:str,page_key:str,p=Depends(access)):
    from runtime.source_preparation import prepared_page
    return prepared_page(identity,page_key,p)


@app.post('/api/v1/runs/{identity}/workflow',status_code=201)
def save_workflow(identity:str,p=Depends(access)):
    from runtime.source_workflows import save
    return save(identity,p)


class WorkflowRunInput(Input):
    input_ref: str | None = Field(default=None,pattern='^[a-f0-9]{64}$')


class WorkflowRefreshInput(Input):
    request_id: str = Field(min_length=1, max_length=240)


from runtime.cross_systems import CrossSystemInput, DeliveryInput


@app.post('/api/v1/runs/{identity}/cross-system', status_code=201)
def cross_system_finding(identity: str, body: CrossSystemInput, p=Depends(access)):
    from runtime.cross_systems import assess
    return assess(identity, p, body.model_dump())


@app.get('/api/v1/cross-system/{identity}')
def read_cross_system_finding(identity: str, p=Depends(access)):
    from runtime.cross_systems import read
    return read(identity, p)


@app.post('/api/v1/cross-system/{identity}/deliveries')
def deliver_cross_system_finding(identity: str, body: DeliveryInput, p=Depends(access)):
    from runtime.cross_systems import deliver
    return deliver(identity, p, body.destination_ref)


from runtime.source_coordination import CoordinationPolicy


@app.post('/api/v1/goals/{identity}/coordination', status_code=202)
def coordinate_objective(identity: str, body: CoordinationPolicy, p=Depends(access)):
    from runtime.source_coordination import invoke
    result = invoke(identity, p, body.model_dump())
    try:
        service.wake(result['id'])
    except (OSError, httpx.HTTPError):
        db.event(result['id'], 'dispatch_pending', {'message': 'Specialists are queued durably.'})
    return result


@app.get('/api/v1/runs/{identity}/coordination')
def coordination_progress(identity: str, p=Depends(access)):
    from runtime.source_coordination import inspect
    return inspect(identity, p)


@app.get('/api/v1/runs/{identity}/source-changes')
def source_change_history(identity:str,offset:int=0,limit:int=100,p=Depends(access)):
    from runtime.source_collection import change_history
    return change_history(identity,p,offset=offset,limit=limit)


@app.post('/api/v1/workflows/{version}/refresh',status_code=202)
def refresh_workflow(version:str,body:WorkflowRefreshInput,p=Depends(access)):
    from runtime.source_workflows import refresh
    r=refresh(version,p,body.request_id)
    try:
        service.wake(r['id'])
    except (OSError,httpx.HTTPError):
        db.event(r['id'],'dispatch_pending',{'message':'Queued durably; the next dispatcher will resume it.'})
    return r


from runtime.source_methods import MethodPolicy


@app.post('/api/v1/runs/{identity}/method-studies',status_code=202)
def start_method_study(identity:str,body:MethodPolicy,p=Depends(access)):
    from runtime.source_methods import invoke
    r=invoke(identity,body.model_dump(),p)
    try:
        service.wake(r['id'])
    except (OSError,httpx.HTTPError):
        db.event(r['id'],'dispatch_pending',{'message':'Queued durably; next dispatcher will resume it.'})
    return r


@app.post('/api/v1/workflows/{version}/runs',status_code=202)
def run_workflow(version:str,body:WorkflowRunInput,p=Depends(access)):
    from runtime.source_workflows import invoke
    r=invoke(version,p,body.input_ref)
    try:
        service.wake(r['id'])
    except (OSError,httpx.HTTPError):
        db.event(r['id'],'dispatch_pending',{'message':'Queued durably; the next dispatcher will resume it.'})
    return r


@app.get('/api/v1/goals/{identity}/workflows')
def workflows(identity:str,p=Depends(access)):
    from runtime.source_workflows import history
    return history(identity,p)


@app.post('/api/v1/workflows/{version}/triggers',status_code=201)
def create_workflow_trigger(version:str,body:TriggerInput,p=Depends(access)):
    from runtime import workflow_triggers as triggers
    result=triggers.configure(version,p,body)
    try:
        triggers.sync_timer(result['id'],p)
    except (OSError,ValueError,KeyError,TypeError,httpx.HTTPError) as error:
        return triggers.timer_failed(result['id'],p,error)
    return triggers.inspect(result['id'],p)


@app.get('/api/v1/goals/{identity}/triggers')
def workflow_trigger_history(identity:str,p=Depends(access)):
    from runtime.workflow_triggers import history
    return history(identity,p)


@app.get('/api/v1/triggers/{identity}')
def workflow_trigger(identity:str,p=Depends(access)):
    from runtime.workflow_triggers import inspect
    return inspect(identity,p)


class TriggerState(Input):
    state: str = Field(pattern='^(active|paused|removed)$')


@app.patch('/api/v1/triggers/{identity}')
def change_workflow_trigger(identity:str,body:TriggerState,p=Depends(access)):
    from runtime import workflow_triggers as triggers
    result=triggers.set_state(identity,p,body.state)
    try:
        triggers.sync_timer(identity,p)
    except (OSError,ValueError,KeyError,TypeError,httpx.HTTPError) as error:
        return triggers.timer_failed(identity,p,error)
    return triggers.inspect(identity,p)


@app.post('/api/v1/triggers/{identity}/events',status_code=202)
def workflow_event(identity:str,body:EventInput,p=Depends(access)):
    from runtime.workflow_triggers import event
    result=event(identity,p,body)
    if result.get('run_id'):
        try:
            service.wake(result['run_id'])
        except (OSError,httpx.HTTPError):
            db.event(result['run_id'],'dispatch_pending',{'message':'Event accepted durably; the dispatcher can resume it.'})
    return result


@app.get('/api/v1/workflows/{version}')
def workflow(version:str,p=Depends(access)):
    from runtime.source_workflows import load, read
    return load(read(version,p),p)


@app.get('/api/v1/workflows/{version}/export')
def export_workflow(version:str,p=Depends(access)):
    from runtime.source_workflows import read
    return JSONResponse(read(version,p),headers={'Cache-Control':'no-store',
                         'Content-Disposition':f'attachment; filename="workflow-{version}.json"'})


@app.post('/api/v1/requests/{identity}/reconcile')
def reconcile(identity:str,p=Depends(access)):
    from runtime.analysis_agent import reconcile_charge
    return reconcile_charge(identity,p)


@app.get('/api/v1/runs/{identity}/requests')
def requests(identity:str,p=Depends(access)):
    db.authorize_run(p,db.run(identity),('manager',))
    return db.query('SELECT id,status,reserved,charge,created_at FROM backintel.analysis_requests WHERE run_id=%s ORDER BY created_at',(identity,))


@app.get('/api/v1/runs/{identity}/events')
def events(identity:str,after:int=0,p=Depends(access)):
    r=db.run(identity)
    db.authorize_run(p,r)
    require_connection_result_access(r,p)
    async def stream():
        cursor=after
        for _ in range(60):
            db.authorize_run(p,r)
            require_connection_result_access(r,p)
            rows=db.query('SELECT * FROM backintel.analysis_events WHERE run_id=%s AND sequence>%s ORDER BY sequence',(identity,cursor))
            for row in rows:
                cursor=row['sequence']
                yield f"id: {cursor}\nevent: {row['kind']}\ndata: {json.dumps(row['body'])}\n\n"
            if db.run(identity)['status'] in ('succeeded','partial','cancelled','failed'):
                break
            await asyncio.sleep(1)
    return StreamingResponse(stream(),media_type='text/event-stream',headers={'Cache-Control':'no-store'})


@app.get('/api/v1/goals/{identity}/findings')
def findings(identity:str,p=Depends(access)):
    g=db.goal(identity)
    actor=db.authorize_goal(p,identity)
    return run_response(db.run(g['last_success']),actor) if g['last_success'] else None


@app.get('/api/v1/evidence/{identity}')
def evidence(identity:str,p=Depends(access)):
    r=db.query('SELECT * FROM backintel.capability_evidence WHERE sha256=%s',(identity,),one=True)
    if not r or not r['task_id'].startswith('analysis-goal-'):
        raise ValueError('Unknown application evidence')
    g=db.goal(r['task_id'].removeprefix('analysis-goal-'))
    actor=db.authorize_goal(p,g['id'])
    if r['kind'] in ('source_discovery','source_collection','source_interpretation','source_preparation','source_validation','connected_calculation','workflow_package'):
        with db.connect() as control, control.transaction():
            body = r['body']['body'] if r['kind']=='workflow_package' else r['body']
            require_source_access(g['id'], actor, connection=control, expected_version=body['goal_version'], read_only=True)
    if actor['role']=='viewer' and (r['kind']=='model_comparison' or r['kind']=='calculation' and r['body'].get('tool')=='interpret_text'):
        raise PermissionError('Raw interpretation and model evidence requires analyst access')
    if r['kind']=='model_comparison':
        return {**r,'body':comparison_response(r['body'],g['id'],actor)}
    return r


def model_summary(body,promoted=False):
    keys=('route','features','calibration_metrics') + (('metrics',) if promoted else ())
    return {'methods':[{key:method[key] for key in keys if key in method}
                       for method in body.get('methods',[])]}


@app.get('/api/v1/inputs/{identity}')
def source_input(identity:str,p=Depends(access)):
    from runtime.source_inputs import retained_input
    original = retained_input(identity, p)
    return {key: value for key, value in original.items() if key != 'payload'}


@app.get('/api/v1/inputs/{identity}/original')
def source_original(identity:str,p=Depends(access)):
    from runtime.source_inputs import retained_input
    original = retained_input(identity, p)
    return Response(original['payload'], media_type='application/json',
                    headers={'Cache-Control': 'no-store', 'Content-Disposition': 'attachment; filename="source-response.json"'})

def comparison_response(body,goal_id,actor):
    approved=db.query("SELECT id FROM backintel.analysis_models WHERE goal_id=%s AND body->>'id'=%s AND promoted LIMIT 1",
                      (goal_id,body.get('id')),one=True)
    return body if approved and actor['role']!='viewer' else model_summary(body,bool(approved))

def require_connection_result_access(r,actor):
    db.authorize_run(actor,r)
    if r['body']['operation'] in ('discovery', 'collection', 'interpretation', 'preparation', 'validation', 'answer', 'workflow', 'method', 'refresh', 'coordination'):
        with db.connect() as control, control.transaction():
            require_source_access(r['goal_id'], actor, connection=control, expected_version=r['goal_version'], read_only=True)


def run_response(r,actor):
    require_connection_result_access(r,actor)
    if r['body']['operation'] == 'coordination':
        from runtime.source_coordination import inspect
        r = {**r, 'coordination': inspect(r['id'], actor)}
    if r['body']['operation'] in ('preparation','workflow'):
        from runtime.source_preparation import coverage
        r = {**r,'coverage':r['result']['coverage'] if r['status']=='succeeded' else coverage(r['id'])}
    if r.get('result') and 'comparison' in r['result']:
        return {**r,'result':{**r['result'],'comparison':comparison_response(r['result']['comparison'],r['goal_id'],actor)}}
    return r

@app.get('/api/v1/goals/{identity}/models')
def models(identity:str,p=Depends(access)):
    actor=db.authorize_goal(p,identity)
    candidates=db.query('SELECT * FROM backintel.analysis_models WHERE goal_id=%s ORDER BY created_at DESC',(identity,))
    if actor['role']=='viewer':
        return [{**{key:m[key] for key in ('id','goal_id','snapshot_id','promoted','created_at')},
                 'body':model_summary(m['body'],m['promoted'])} for m in candidates]
    return [{**m,'body':m['body'] if m['promoted'] else model_summary(m['body'])} for m in candidates]

@app.post('/api/v1/models/{identity}/promote',status_code=202)
def promote(identity:str,body:PromotionInput,p=Depends(access)):
    r=service.promote(identity,p,body.route)
    try:
        service.wake(r['id'])
    except (OSError,httpx.HTTPError):
        pass
    return r


@app.get('/api/v1/goals/{identity}/reviews')
def reviews(identity:str,p=Depends(access)):
    db.authorize_goal(p,identity)
    return db.query('SELECT * FROM backintel.analysis_reviews WHERE goal_id=%s ORDER BY id DESC',(identity,))


@app.post('/api/v1/goals/{identity}/reviews',status_code=201)
def review(identity:str,body:ReviewInput,p=Depends(access)):
    db.authorize_goal(p,identity,('manager','analyst'),permission='run')
    if body.kind not in ('comment','correction') or (body.run_id and db.run(body.run_id)['goal_id']!=identity):
        raise ValueError('Invalid review context')
    with db.connect() as c, c.transaction():
        db.authorize_goal(p, identity, ('manager','analyst'), permission='run', connection=c)
        db.write('INSERT INTO backintel.analysis_reviews(goal_id,run_id,actor,body) VALUES(%s,%s,%s,%s)',(identity,body.run_id,p['id'],Jsonb(body.model_dump())),connection=c)
    return {'saved':True}


@app.post('/api/v1/sources/{domain}/corrections',status_code=201)
def correction(domain:str,body:CorrectionInput,p=Depends(access)):
    db.authorize(p,domain,('manager',),administrator=True)
    with db.connect() as c, c.transaction():
        c.execute('SELECT pg_advisory_xact_lock(hashtextextended(%s,0))', ('analysis-source:'+domain,))
        db.authorize(p,domain,('manager',),connection=c,administrator=True)
        manager=c.execute("""SELECT id FROM backintel.analysis_principals WHERE id=%s AND enabled
            AND (expires_at IS NULL OR expires_at>clock_timestamp()) AND role='manager'
            AND %s=ANY(domains) FOR SHARE""", (p['id'],domain)).fetchone()
        if not manager: raise PermissionError('Current manager authority is required to correct a source')
        source=db.source(domain, connection=c)
        if not source['body'].get('terms_acknowledged'):
            raise PermissionError('Source terms are not acknowledged')
        rows=db.records(source['latest_snapshot'], connection=c)
        row=next((r for r in rows if r['id']==body.record_id),None)
        if not row or set(body.features)-set(row['features']):
            raise ValueError('Unknown record or feature')
        for feature, value in body.features.items():
            if value is None:
                continue
            kinds = {isinstance(r['features'][feature], str) for r in rows
                     if r['features'].get(feature) is not None}
            if kinds != {isinstance(value, str)}:
                raise ValueError(f'Correction must preserve the established type of {feature}')
        target_supplied = 'target' in body.model_fields_set
        if all(row['features'][key] == value for key, value in body.features.items()) and (not target_supplied or row['target'] == body.target):
            raise ValueError('Correction must change at least one value')
        row['features'].update(body.features)
        row['groups'].update(feature_groups(domain, row['features']))
        if target_supplied:
            if body.target is not None and CONFIG['sources'][domain]['kind']=='classification' and body.target not in (0,1):
                raise ValueError('Classification target must be 0 or 1')
            if body.target is not None and domain in ('support','maintenance') and body.target < 0:
                raise ValueError('Duration and remaining-life targets must be nonnegative')
            row['target']=body.target
            row['split']='unlabeled'  # A late correction never contaminates a historical benchmark.
        prior=db.query('SELECT body FROM backintel.analysis_snapshots WHERE id=%s',(source['latest_snapshot'],),one=True,connection=c)['body']
        updated={**prior,'corrected_from':source['latest_snapshot'],'correction':{**body.model_dump(),'actor':p['id']},'record_hash':digest(rows)}
        identity=digest(updated)
        db.save_snapshot(domain,identity,updated,rows,connection=c)
        for model in db.query('SELECT m.id,m.body FROM backintel.analysis_models m JOIN backintel.analysis_goals g ON g.id=m.goal_id WHERE g.domain=%s',(domain,)):
            splits=model['body'].get('splits',{})
            if body.record_id in splits.get('train',[])+splits.get('calibration',[])+splits.get('test',[]):
                c.execute('UPDATE backintel.analysis_models SET body=%s WHERE id=%s',(Jsonb({**model['body'],'invalidated_by':identity}),model['id']))
                c.execute('UPDATE backintel.analysis_goals SET active_model=NULL WHERE active_model=%s',(model['id'],))
    refreshes=service.schedule_snapshot(domain,{'snapshot':identity},train=False)
    for refresh in refreshes:
        if 'run_id' in refresh:
            try:service.wake(refresh['run_id'])
            except (OSError,httpx.HTTPError):db.event(refresh['run_id'],'dispatch_pending',{'message':'Correction queued durably.'})
    return {'snapshot':identity,'changed':True,'message':'Previous findings remain available and are stale.','refreshes':refreshes}


@app.patch('/api/v1/principals/{identity}')
def grants(identity:str,body:GrantInput,p=Depends(access)):
    db.authorize(p,roles=('manager',),administrator=True)
    if body.budget_usd is not None and not 0 <= body.budget_usd <= CONFIG['budget']['suite_usd']:
        raise ValueError('User budget must be nonnegative and within the shared spending cap')
    if set(body.domains)-set(CONFIG['sources']) or identity=='worker': raise ValueError('Invalid application grant')
    if body.expires_at is not None and body.expires_at.tzinfo is None: raise ValueError('Credential expiry requires a timezone')
    with db.connect() as connection, connection.transaction():
        principals = db.query('SELECT id,domains,expires_at FROM backintel.analysis_principals WHERE id=ANY(%s) ORDER BY id FOR UPDATE',
                              (sorted({identity, p['id']}),), connection=connection)
        target = next((row for row in principals if row['id']==identity), None)
        db.authorize(p,roles=('manager',),connection=connection,administrator=True)
        if target is None: raise ValueError('Unknown application grant')
        if (identity == p['id'] and target['expires_at'] is not None and 'expires_at' in body.model_fields_set
                and (body.expires_at is None or body.expires_at > target['expires_at'])):
            raise PermissionError('Managers cannot extend or remove their own credential expiry')
        affected = sorted(set(body.domains) | set(target['domains']))
        assignments = 'domains=%s,enabled=%s'
        values = [body.domains, body.enabled]
        if 'expires_at' in body.model_fields_set:
            assignments += ',expires_at=%s'
            values.append(body.expires_at)
        if body.budget_usd is not None:
            assignments += ',budget_usd=%s'
            values.append(body.budget_usd)
        saved = db.query(f"""UPDATE backintel.analysis_principals SET {assignments} WHERE id=%s AND EXISTS (
            SELECT 1 FROM backintel.analysis_principals actor WHERE actor.id=%s AND actor.enabled
              AND (actor.expires_at IS NULL OR actor.expires_at>clock_timestamp())
              AND actor.role='manager' AND actor.domains @> %s::text[]) RETURNING id""",
            (*values, identity, p['id'], affected), one=True, connection=connection)
        if not saved: raise PermissionError('Grant changes require current manager access to every affected source')
    return {'saved':True}


web=Path(os.getenv('BACKINTEL_WEB_DIR',str(Path(__file__).resolve().parents[1]/'apps/web/dist')))
if (web/'assets').is_dir():
    app.mount('/assets',StaticFiles(directory=web/'assets'),name='assets')


@app.get('/')
def shell():
    if not (web/'index.html').is_file():
        return JSONResponse({'detail':'Build apps/web before opening the workspace.'},status_code=503)
    return FileResponse(web/'index.html',headers={'Content-Security-Policy':"default-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; base-uri 'self'"})
