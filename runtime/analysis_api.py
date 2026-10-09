"""Thin authenticated application routes mounted by Aegra."""
from __future__ import annotations

import asyncio
import json
import os
import httpx
from datetime import datetime
from pathlib import Path

from fastapi import FastAPI, Depends, Request, HTTPException
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict, Field
from psycopg.types.json import Jsonb

from runtime import analysis_store as db
from runtime import analysis_service as service
from runtime.analysis_data import CONFIG, digest, feature_groups
from runtime.jobs import cancel
from runtime.analysis_errors import safe_error

app = FastAPI(title='BackIntel analysis workspace')


class Input(BaseModel):
    model_config = ConfigDict(extra='forbid')


class GoalInput(Input):
    domain: str
    question: str = Field(min_length=1,max_length=2000)


class GoalUpdate(Input):
    question: str | None = Field(default=None,min_length=1,max_length=2000)
    paused: bool | None = None
    confirmed: bool | None = None
    threshold: float | None = Field(default=None,ge=0,le=100000)
    budget_usd: float | None = Field(default=None,gt=0,le=1)


class RunInput(Input):
    question: str | None = Field(default=None,min_length=1,max_length=2000)
    operation: str = 'analysis'


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


@app.get('/api/v1/notifications')
def notifications(p=Depends(access)):
    p=db.authorize(p)
    return db.query("SELECT e.sequence AS id,e.run_id,e.body,e.created_at,g.id AS goal_id,g.domain FROM backintel.analysis_events e JOIN backintel.analysis_runs r ON r.id=e.run_id JOIN backintel.analysis_goals g ON g.id=r.goal_id WHERE e.kind='material_change' AND g.domain=ANY(%s) ORDER BY e.sequence DESC LIMIT 30",(p['domains'],))


@app.get('/api/v1/sources')
def sources(p=Depends(access)):
    p=db.authorize(p)
    return [db.source(row['id']) for row in db.query('SELECT id FROM backintel.analysis_sources WHERE domain=ANY(%s) ORDER BY domain',(p['domains'],))]


@app.post('/api/v1/sources/{domain}/terms')
def terms(domain:str,body:TermsInput,p=Depends(access)):
    db.authorize(p,domain,('manager',))
    with db.connect() as c, c.transaction():
        c.execute('SELECT pg_advisory_xact_lock(hashtextextended(%s,0))', ('analysis-source:'+domain,))
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
    result=db.query('SELECT * FROM backintel.analysis_goals WHERE domain=ANY(%s) ORDER BY created_at DESC',(p['domains'],))
    for g in result:
        source=db.source(g['domain'])
        previous=db.run(g['last_success']) if g['last_success'] else None
        g['freshness']='refresh_failed' if source['body'].get('last_refresh_error') else 'current' if previous and previous['snapshot_id']==source['latest_snapshot'] and previous['goal_version']==g['version'] and previous['body'].get('model_id')==g['active_model'] and previous['body'].get('analysis_identity')==service.analysis_identity() else 'stale' if previous else 'unanswered'
    return result


@app.post('/api/v1/goals',status_code=201)
async def create(body:GoalInput,p=Depends(access)):
    from runtime.analysis_graphs import goal_graph
    g=await asyncio.to_thread(service.create_goal,p,body.domain,body.question)
    proposal=await goal_graph.ainvoke({'goal_id':g['id']})
    return {**g,'proposal':proposal['result']}


@app.patch('/api/v1/goals/{identity}')
def update(identity:str,body:GoalUpdate,p=Depends(access)):
    return service.revise_goal(identity,p,**body.model_dump())


@app.post('/api/v1/goals/{identity}/runs',status_code=202)
def start(identity:str,body:RunInput,p=Depends(access)):
    if body.operation not in ('analysis','training'):
        raise ValueError('Unsupported operation')
    r=service.submit(identity,p,body.question,body.operation)
    try:
        service.wake(r['id'])
    except (OSError,httpx.HTTPError):
        db.event(r['id'],'dispatch_pending',{'message':'Queued durably; the next dispatcher will resume it.'})
    return r


@app.get('/api/v1/runs')
def runs(goal_id:str,p=Depends(access)):
    actor=db.authorize(p,db.goal(goal_id)['domain'])
    return [run_response(r,actor) for r in db.query('SELECT * FROM backintel.analysis_runs WHERE goal_id=%s ORDER BY created_at DESC LIMIT 50',(goal_id,))]


@app.get('/api/v1/runs/{identity}')
def run(identity:str,p=Depends(access)):
    r=db.run(identity)
    actor=db.authorize(p,db.run_domain(r))
    return run_response(r,actor)


@app.post('/api/v1/runs/{identity}/cancel')
def cancel_run(identity:str,p=Depends(access)):
    r=db.run(identity)
    db.authorize(p,db.run_domain(r),('manager',))
    with db.connect() as c, c.transaction():
        c.execute('SELECT id FROM backintel.analysis_runs WHERE id=%s FOR UPDATE', (identity,))
        state=cancel(c,r['job_id'])
        db.write("UPDATE backintel.analysis_runs SET status='cancelled',updated_at=now() WHERE id=%s AND status='queued'",(identity,),connection=c)
    return {'status':state}


@app.post('/api/v1/requests/{identity}/reconcile')
def reconcile(identity:str,p=Depends(access)):
    from runtime.analysis_agent import reconcile_charge
    return reconcile_charge(identity,p)


@app.get('/api/v1/runs/{identity}/requests')
def requests(identity:str,p=Depends(access)):
    db.authorize(p,db.run_domain(db.run(identity)),('manager',))
    return db.query('SELECT id,status,reserved,charge,created_at FROM backintel.analysis_requests WHERE run_id=%s ORDER BY created_at',(identity,))


@app.get('/api/v1/runs/{identity}/events')
def events(identity:str,after:int=0,p=Depends(access)):
    r=db.run(identity)
    db.authorize(p,db.run_domain(r))
    async def stream():
        cursor=after
        for _ in range(60):
            db.authorize(p,db.run_domain(r))
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
    actor=db.authorize(p,g['domain'])
    return run_response(db.run(g['last_success']),actor) if g['last_success'] else None


@app.get('/api/v1/evidence/{identity}')
def evidence(identity:str,p=Depends(access)):
    r=db.query('SELECT * FROM backintel.capability_evidence WHERE sha256=%s',(identity,),one=True)
    if not r or not r['task_id'].startswith('analysis-goal-'):
        raise ValueError('Unknown application evidence')
    g=db.goal(r['task_id'].removeprefix('analysis-goal-'))
    actor=db.authorize(p,g['domain'])
    if actor['role']=='viewer' and (r['kind']=='model_comparison' or r['kind']=='calculation' and r['body'].get('tool')=='interpret_text'):
        raise PermissionError('Raw interpretation and model evidence requires analyst access')
    if r['kind']=='model_comparison':
        return {**r,'body':comparison_response(r['body'],g['id'],actor)}
    return r


def model_summary(body,promoted=False):
    keys=('route','features','calibration_metrics') + (('metrics',) if promoted else ())
    return {'methods':[{key:method[key] for key in keys if key in method}
                       for method in body.get('methods',[])]}

def comparison_response(body,goal_id,actor):
    approved=db.query("SELECT id FROM backintel.analysis_models WHERE goal_id=%s AND body->>'id'=%s AND promoted LIMIT 1",
                      (goal_id,body.get('id')),one=True)
    return body if approved and actor['role']!='viewer' else model_summary(body,bool(approved))

def run_response(r,actor):
    if r.get('result') and 'comparison' in r['result']:
        return {**r,'result':{**r['result'],'comparison':comparison_response(r['result']['comparison'],r['goal_id'],actor)}}
    return r

@app.get('/api/v1/goals/{identity}/models')
def models(identity:str,p=Depends(access)):
    actor=db.authorize(p,db.goal(identity)['domain'])
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
    db.authorize(p,db.goal(identity)['domain'])
    return db.query('SELECT * FROM backintel.analysis_reviews WHERE goal_id=%s ORDER BY id DESC',(identity,))


@app.post('/api/v1/goals/{identity}/reviews',status_code=201)
def review(identity:str,body:ReviewInput,p=Depends(access)):
    db.authorize(p,db.goal(identity)['domain'],('manager','analyst'))
    if body.kind not in ('comment','correction') or (body.run_id and db.run(body.run_id)['goal_id']!=identity):
        raise ValueError('Invalid review context')
    db.write('INSERT INTO backintel.analysis_reviews(goal_id,run_id,actor,body) VALUES(%s,%s,%s,%s)',(identity,body.run_id,p['id'],Jsonb(body.model_dump())))
    return {'saved':True}


@app.post('/api/v1/sources/{domain}/corrections',status_code=201)
def correction(domain:str,body:CorrectionInput,p=Depends(access)):
    db.authorize(p,domain,('manager',))
    with db.connect() as c, c.transaction():
        c.execute('SELECT pg_advisory_xact_lock(hashtextextended(%s,0))', ('analysis-source:'+domain,))
        manager=c.execute("""SELECT id FROM backintel.analysis_principals WHERE id=%s AND enabled
            AND (expires_at IS NULL OR expires_at>clock_timestamp()) AND role='manager'
            AND %s=ANY(domains) FOR UPDATE""", (p['id'],domain)).fetchone()
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
    if set(body.domains)-set(CONFIG['sources']) or identity=='worker': raise ValueError('Invalid application grant')
    if body.expires_at is not None and body.expires_at.tzinfo is None: raise ValueError('Credential expiry requires a timezone')
    with db.connect() as connection, connection.transaction():
        principals = db.query('SELECT id,domains FROM backintel.analysis_principals WHERE id=ANY(%s) ORDER BY id FOR UPDATE',
                              (sorted({identity, p['id']}),), connection=connection)
        target = next((row for row in principals if row['id']==identity), None)
        if target is None: raise ValueError('Unknown application grant')
        affected = sorted(set(body.domains) | set(target['domains']))
        assignments = 'domains=%s,enabled=%s'
        values = [body.domains, body.enabled]
        if 'expires_at' in body.model_fields_set:
            assignments += ',expires_at=%s'
            values.append(body.expires_at)
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
