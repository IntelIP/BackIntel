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
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from scripts.analysis_benchmark_support import (SCENARIOS, candidate_identity, receipt_identity_error, scenario_spec)


def docker(*args,**kw):
    return subprocess.run(['docker','compose','-f','compose.analysis.yml',*args],cwd=ROOT,capture_output=True,text=True,**kw)


def functional(output, filters=()):
    name='backintel_analysis_checks_'+uuid.uuid4().hex[:12]+'_test'
    created=docker('exec','-T','postgres','psql','-U','analysis_demo','-d','postgres','-c',f'CREATE DATABASE {name}')
    if created.returncode:
        return {'status':'blocked','reason':'Isolated check database unavailable','diagnostic':created.stderr[-1500:]}
    uri='postgresql://analysis_demo@postgres:5432/'+name
    try:
        checked=docker('exec','-T','-e','BACKINTEL_ANALYSIS_CHECK_DB='+uri,'runtime','python','-m','unittest','discover','-s','tests','-p','test_analysis*.py','-v',*filters,timeout=180)
        (output/'functional.log').write_text(checked.stdout+checked.stderr)
        status='passed' if checked.returncode==0 else 'failed' if 'Ran ' in checked.stderr else 'blocked'
        return {'status':status,'returncode':checked.returncode,'log':str(output/'functional.log'),'provider_calls':0,'provider_usd':0,'mode':'deterministic fixtures and control checks'}
    finally:
        docker('exec','-T','postgres','psql','-U','analysis_demo','-d','postgres','-c',f'DROP DATABASE {name}')


def real(output):
    return benchmark_receipt(output, require_comparisons=True)


def benchmark_receipt(output, require_comparisons=False):
    """Recheck only current receipt runs; historical DB counts never establish readiness."""
    config=json.loads((ROOT/'config/analysis.json').read_text())
    specs=[scenario_spec(domain,scenario,spec['group']) for domain,spec in config['sources'].items() for scenario in SCENARIOS]
    current=candidate_identity(ROOT)
    code="""
import json
from pathlib import Path
p=Path('/models/Analysis/benchmark-evidence.json')
print(p.read_text() if p.exists() else '{}')
"""
    read=docker('exec','-T','runtime','python','-c',code,timeout=30)
    (output/'benchmark.json').write_text(read.stdout or '{}')
    if read.returncode:
        return {'status':'blocked','reason':'Benchmark receipt unavailable','diagnostic':read.stderr[-1500:]}
    try:
        receipt=json.loads(read.stdout)
        reason=receipt_identity_error(receipt,current,specs)
    except (TypeError,ValueError) as error:
        return {'status':'blocked','reason':'Invalid benchmark receipt: '+str(error)}
    if reason:return {'status':'blocked','reason':reason}
    # Send frozen identity in process input, not shell interpolation. Runtime recalculates raw-source
    # oracles and grades recorded answers again using current persisted calculation evidence.
    verify="""
import json,sys
from pathlib import Path
from runtime import analysis_store as db
from runtime.analysis_data import CONFIG,source_files
from scripts.analysis_benchmark_support import raw_oracle,score_answer,fingerprint,digest
receipt=json.loads(sys.stdin.read());results=[]
folders=('runtime','scripts','config','migrations')
expected={name:sha for name,sha in receipt['candidate']['files'].items() if name.split('/')[0] in folders}
actual={str(p):fingerprint(p)['sha256'] for folder in folders for p in Path(folder).rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.suffix not in ('.pyc','.pyo')}
if actual!=expected:raise RuntimeError('Runtime source file set or bytes differ from candidate')
for domain in CONFIG['sources']:
 result={'domain':domain,'status':'blocked'};results.append(result)
 try:
  entries=[r for r in receipt['domains'] if r.get('domain')==domain]
  if len(entries)!=1:raise RuntimeError('Domain receipt missing or duplicated')
  entry=entries[0]
  goal=db.goal(entry['goal_id'])
  if not goal['body']['question'].endswith(' Benchmark '+receipt['campaign_id']+' '+receipt['candidate']['source_hash']):raise RuntimeError('Goal lacks current campaign source identity')
  oracle=raw_oracle(domain,source_files(domain),CONFIG['limits']['source_rows'])
  if oracle!=entry.get('oracle'):raise RuntimeError('Source oracle differs from receipt')
  snapshot=db.source(domain)['latest_snapshot']
  if snapshot!=entry.get('snapshot_id'):raise RuntimeError('Source snapshot differs from receipt')
  expected=[s for s in receipt['scenarios'] if s['domain']==domain]
  answers=entry.get('answers',[])
  if len(answers)!=len(expected):raise RuntimeError('Required scenario answer missing')
  run_ids=[]
  for spec in expected:
   matches=[a for a in answers if a.get('scenario')==spec]
   if len(matches)!=1 or matches[0].get('status')!='passed':raise RuntimeError('Scenario not passed uniquely')
   checked=matches[0];run=db.run(checked['run_id']);run_ids.append(run['id'])
   if run['goal_id']!=entry['goal_id'] or run['body']['question']!=spec['prompt']:raise RuntimeError('Run differs from scenario')
   evidence={i:db.query('SELECT * FROM backintel.capability_evidence WHERE sha256=%s',(i,),one=True) for f in run['result']['findings'] for i in f['evidence_ids']}
   score=score_answer(run,evidence,spec,oracle,snapshot)
   if any(score[k]!=checked.get(k) for k in ('expected','actual','evidence_ids')):raise RuntimeError('Stored score differs from current evidence')
   if run['result'].get('model')!=CONFIG['analyst']['model'] or run['result'].get('usage',{}).get('charge_status')!='measured':raise RuntimeError('Real model identity or cost missing')
  if REQUIRE_COMPARISONS:
   comparison=entry.get('comparison',{})
   if comparison.get('status')!='passed':raise RuntimeError('Full comparison incomplete')
   run=db.run(comparison['run_id']);run_ids.append(run['id'])
   if run['goal_id']!=entry['goal_id'] or run['snapshot_id']!=snapshot or run['status']!='succeeded':raise RuntimeError('Comparison run is stale')
   model=db.query('SELECT body,snapshot_id FROM backintel.analysis_models WHERE id=%s',(comparison['candidate_id'],),one=True)
   body=model['body']
   if model['snapshot_id']!=snapshot or body.get('mode')!='real' or not {'baseline','catboost','tabiclv2'}.issubset({m['route'] for m in body['methods']}):raise RuntimeError('Required real methods missing')
   if body.get('dependencies',{}).get('implementation_sha256')!=digest({name:fingerprint(Path('runtime')/name)['sha256'] for name in ('analysis_models.py','real_models.py','simulation.py')}):raise RuntimeError('Model implementation differs')
  charges=db.query('SELECT run_id,id,status,charge,reserved FROM backintel.analysis_requests WHERE run_id=ANY(%s)',(run_ids,))
  expected_charges=[c for c in receipt['charges'] if c['run_id'] in run_ids]
  if sorted(json.loads(json.dumps(charges,default=str)),key=lambda c:c['id'])!=sorted(expected_charges,key=lambda c:c['id']):raise RuntimeError('Cost ledger differs from receipt')
  if not charges or any(c['charge'] is None for c in charges):raise RuntimeError('Measured provider charges missing')
  result['status']='passed'
 except Exception as error:
  result['reason']=type(error).__name__+': '+str(error)[:500]
print(json.dumps({'domains':results,'status':'passed' if all(r['status']=='passed' for r in results) else 'blocked'}))
""".replace('REQUIRE_COMPARISONS',repr(require_comparisons))
    checked=docker('exec','-T','runtime','python','-c',verify,input=json.dumps(receipt),timeout=60)
    if checked.returncode:return {'status':'blocked','reason':'Current benchmark evidence could not be verified','diagnostic':checked.stderr[-1500:]}
    report=json.loads(checked.stdout)
    report.update(provider_calls=receipt['provider_calls'],provider_usd=receipt['provider_usd'],charge_status=receipt['charge_status'])
    return report


def static(output):
    commands=[['npm','--prefix','apps/web','run','build'],['npm','--prefix','apps/web','run','test:receipt'],['npm','--prefix','apps/web','run','deadcode'],
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
    names=('role_and_domain_denials','revocation_and_cross_goal_evidence','duplicate_snapshot_run_and_budget',
           'unapproved_provider_response_is_rejected','correction_invalidates_test_member_and_promotion',
           'lower_budget_and_partial_resume','expired_grant','grant_expiry','private_run_evidence',
           'credentials_are_redacted','scoped_manager','ambiguous_provider_timeout','hostile_tool',
           'environment_file_uri_and_bearer')
    return functional(output,tuple(item for name in names for item in ('-k',name)))


def semantic(output):
    return benchmark_receipt(output)


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
