"""Durable evidence for the exact working tree; real acceptance never uses fixtures."""
import argparse
import datetime
import json
import os
import subprocess
import sys
import uuid
import hashlib
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]


def docker(*args,**kw):
    return subprocess.run(['docker','compose','-f','compose.analysis.yml',*args],cwd=ROOT,capture_output=True,text=True,**kw)


def functional(output, filters=()):
    name='test_analysis_checks_'+uuid.uuid4().hex[:12]
    created=docker('exec','-T','postgres','psql','-U','analysis_demo','-d','postgres','-c',f'CREATE DATABASE {name}')
    if created.returncode:
        return {'status':'blocked','reason':'Isolated check database unavailable','diagnostic':created.stderr[-1500:]}
    uri='postgresql://analysis_demo@postgres:5432/'+name
    try:
        checked=docker('exec','-T','-e','BACKINTEL_ANALYSIS_CHECK_DB='+uri,'runtime','python','-m','unittest','discover','-s','tests','-p','test_analysis.py','-v',*filters,timeout=180)
        (output/'functional.log').write_text(checked.stdout+checked.stderr)
        status='passed' if checked.returncode==0 else 'failed' if 'Ran ' in checked.stderr else 'blocked'
        return {'status':status,'returncode':checked.returncode,'log':str(output/'functional.log'),'provider_calls':0,'provider_usd':0,'mode':'deterministic fixtures and control checks'}
    finally:
        docker('exec','-T','postgres','psql','-U','analysis_demo','-d','postgres','-c',f'DROP DATABASE {name}')


def real(output):
    code="""
import json
from runtime import analysis_store as db
from runtime.analysis_data import CONFIG
result=[]
for domain in CONFIG['sources']:
 s=db.source(domain)
 models=db.query('SELECT m.id,m.body FROM backintel.analysis_models m JOIN backintel.analysis_goals g ON g.id=m.goal_id WHERE g.domain=%s',(domain,))
 runs=db.query("SELECT r.id,r.result FROM backintel.analysis_runs r JOIN backintel.analysis_goals g ON g.id=r.goal_id WHERE g.domain=%s AND r.status='succeeded' AND r.body->>'operation'='analysis'",(domain,))
 valid_models=[m['id'] for m in models if m['body'].get('mode')=='real' and {'catboost','tabiclv2'}.issubset({p['route'] for p in m['body']['methods']})]
 valid_runs=[r['id'] for r in runs if r['result'].get('model')==CONFIG['analyst']['model'] and r['result'].get('usage',{}).get('charge_status')=='measured']
 result.append({'domain':domain,'snapshot':s['latest_snapshot'],'real_comparisons':valid_models,'frontier_answers':valid_runs,'status':'passed' if s['latest_snapshot'] and valid_models and len(valid_runs)>=3 else 'blocked'})
print(json.dumps({'domains':result,'costs':db.query('SELECT status,charge,reserved FROM backintel.analysis_requests')},default=str))
"""
    checked=docker('exec','-T','runtime','python','-c',code,timeout=60)
    if checked.returncode:
        return {'status':'blocked','reason':'Real runtime evidence unavailable','diagnostic':checked.stderr[-1500:]}
    report=json.loads(checked.stdout)
    report['status']='passed' if all(d['status']=='passed' for d in report['domains']) else 'blocked'
    report['provider_usd']=sum(float(c['charge'] or 0) for c in report['costs'])
    report['charge_status']='unknown' if any(c['charge'] is None for c in report['costs']) else 'measured'
    if report['charge_status']=='unknown':report['status']='blocked'
    return report


def static(output):
    commands=[['npm','--prefix','apps/web','run','build'],['npm','--prefix','apps/web','run','deadcode'],
              [sys.executable,'-m','vulture',*[str(p.relative_to(ROOT)) for folder in ('runtime','scripts') for p in (ROOT/folder).glob('analysis_*.py')],'--min-confidence','100'],
              [sys.executable,'-m','compileall','-q','runtime','scripts','tests']]
    results=[]
    for index,command in enumerate(commands):
        result=subprocess.run(command,cwd=ROOT,capture_output=True,text=True,timeout=180)
        (output/f'check-{index}.log').write_text(result.stdout+result.stderr)
        results.append({'command':command,'returncode':result.returncode})
    return {'status':'passed' if all(r['returncode']==0 for r in results) else 'failed','checks':results,'provider_calls':0,'provider_usd':0}


def schema(output):
    result=subprocess.run(['node','scripts/validation/check-contract.mjs','--manifest','tabellio.analysis.validation.json','--check','schema'],cwd=ROOT,capture_output=True,text=True,timeout=30)
    (output/'schema.log').write_text(result.stdout+result.stderr)
    return {'status':'passed' if result.returncode==0 else 'failed','provider_calls':0,'provider_usd':0}


def security(output):
    return functional(output,('-k','role_and_domain_denials','-k','revocation_and_cross_goal_evidence','-k','duplicate_snapshot_run_and_budget','-k','unapproved_provider_response_is_rejected','-k','correction_invalidates_test_member_and_promotion','-k','lower_budget_and_partial_resume'))


def semantic(output):
    code="""import json;from pathlib import Path;p=Path('/models/Analysis/benchmark-evidence.json');print(p.read_text() if p.exists() else '{}')"""
    result=docker('exec','-T','runtime','python','-c',code,timeout=30)
    (output/'benchmark.json').write_text(result.stdout or '{}')
    if result.returncode:return {'status':'blocked','reason':'Benchmark receipt unavailable','provider_calls':0,'provider_usd':0}
    receipt=json.loads(result.stdout)
    domains=receipt.get('domains',[])
    statuses=[d.get('status') for d in domains]
    complete=len(domains)==5 and all(d.get('status')=='passed' and len(d.get('answers',[]))==3 and all(a.get('correct') for a in d['answers']) for d in domains)
    charges=receipt.get('charges',[])
    unknown=any(c.get('charge') is None for c in charges)
    return {'status':'failed' if 'failed' in statuses else 'passed' if complete and not unknown else 'blocked',
            'domains':domains,'provider_calls':len(charges),'provider_usd':sum(float(c['charge']) for c in charges if c.get('charge') is not None),
            'charge_status':'unknown' if unknown else 'measured'}


def visual(output):
    env=os.environ.copy()
    bundled=Path.home()/'.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules'
    if bundled.is_dir():env.setdefault('NODE_PATH',str(bundled))
    result=subprocess.run(['node','scripts/validation/check_analysis_browser.cjs',str(output/'Browser')],cwd=ROOT,env=env,capture_output=True,text=True,timeout=180)
    (output/'browser.log').write_text(result.stdout+result.stderr)
    evidence=output/'Browser/evidence.json'
    return json.loads(evidence.read_text()) if evidence.exists() else {'status':'blocked','reason':'Browser evidence unavailable','provider_calls':0,'provider_usd':0}


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--mode',choices=('functional','real','static','schema','security','semantic','visual'),required=True)
    parser.add_argument('--evidence-path')
    parser.add_argument('--validator-id')
    args=parser.parse_args()
    output=Path(os.getenv('BACKINTEL_ANALYSIS_EVIDENCE_DIR',str(Path.home()/'Library/Application Support/BackIntel/Evidence/Analysis')))/uuid.uuid4().hex
    output.mkdir(parents=True)
    head=subprocess.run(['git','rev-parse','HEAD'],cwd=ROOT,capture_output=True,text=True).stdout.strip()
    dirty=bool(subprocess.run(['git','status','--porcelain'],cwd=ROOT,capture_output=True,text=True).stdout.strip())
    report={'mode':args.mode,'head':head,'dirty':dirty,'candidate_type':'working-tree' if dirty else 'commit','time':datetime.datetime.now(datetime.timezone.utc).isoformat(),'status':'blocked'}
    try:report.update(globals()[args.mode](output))
    except Exception as error:report.update(status='blocked',reason=type(error).__name__+': '+str(error)[:2000])
    report['readiness']='blocked' if dirty else report['status']
    (output/'evidence.json').write_text(json.dumps(report,indent=2))
    if args.evidence_path:
        path=ROOT/args.evidence_path;path.parent.mkdir(parents=True,exist_ok=True)
        artifacts=[]
        for item in output.rglob('*'):
            if item.is_file():
                artifacts.append({'name':item.name,'uri':item.as_uri(),'sha256':hashlib.sha256(item.read_bytes()).hexdigest(),'mediaType':'image/png' if item.suffix=='.png' else 'application/json' if item.suffix=='.json' else 'text/plain','bytes':item.stat().st_size})
        evidence={'$schema':'tabellio-validator-evidence/v0.1','validatorId':args.validator_id or 'analysis-'+args.mode,'status':report['status'],
                  'summary':report.get('reason',f"{args.mode} checks {report['status']}; candidate {report['candidate_type']}"),
                  'metrics':[],'cost':{'telemetryStatus':'unknown' if report.get('charge_status')=='unknown' else 'known','usd':report.get('provider_usd',0),'modelCalls':report.get('provider_calls',0),'toolCalls':0},'artifacts':artifacts}
        path.write_text(json.dumps(evidence,indent=2))
    print(json.dumps({'status':report['status'],'readiness':report['readiness'],'evidence':str(output/'evidence.json')}))
    return 0 if report['status']=='passed' else 1


if __name__=='__main__':sys.exit(main())
