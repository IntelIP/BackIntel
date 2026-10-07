"""Run real, source-gated comparisons and independently checked frontier questions.

Run inside the isolated analysis runtime. Promotion remains a separate manager action.
"""
import argparse
import json
import os
import uuid
import time
from pathlib import Path

from runtime.analysis_data import CONFIG,root,source_files
from runtime.analysis_errors import safe_error
from scripts.analysis_benchmark_support import (SCENARIOS, SUITE_VERSION, candidate_identity, digest,
    raw_oracle, scenario_spec, score_answer)


def execute(run):
    import httpx
    from runtime import analysis_store as db, analysis_service as service
    from scripts.analysis_demo import access_path
    if db.run(run['id'])['status']=='succeeded':
        return db.run(run['id'])
    service.wake(run['id'])
    token=json.loads(access_path().read_text())['manager']
    deadline=time.monotonic()+CONFIG['limits']['model_seconds']+CONFIG['analyst']['seconds']
    base=os.getenv('BACKINTEL_AEGRA_URL','http://127.0.0.1:2026')
    with httpx.Client(timeout=75,headers={'Authorization':'Bearer '+token}) as client:
        while db.run(run['id'])['status'] in ('queued','running'):
            if time.monotonic()>deadline:
                raise TimeoutError('Benchmark run exceeded the configured model and analyst deadline')
            with client.stream('GET',base+f"/api/v1/runs/{run['id']}/events") as response:
                response.raise_for_status()
                for _ in response.iter_lines():
                    if time.monotonic()>deadline:
                        raise TimeoutError('Benchmark event stream exceeded its deadline')
    return db.run(run['id'])


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--domains',nargs='+',choices=CONFIG['sources'],default=list(CONFIG['sources']))
    parser.add_argument('--partition',choices=('development','held_out','all'),default='all')
    parser.add_argument('--comparisons',action='store_true',help='Also run full predictor comparisons')
    parser.add_argument('--candidate-manifest',help='Clean host candidate_identity JSON; verify complete runtime file set and bytes inside an image without Git')
    parser.add_argument('--execute-real',action='store_true',help='Explicitly execute hosted analyst calls under existing campaign limits')
    parser.add_argument('--output',default=str(Path(os.getenv('BACKINTEL_MODEL_DIR','/models'))/'Analysis/benchmark-evidence.json'))
    args=parser.parse_args()
    specs=[scenario_spec(domain,scenario,CONFIG['sources'][domain]['group']) for domain in args.domains
           for scenario in SCENARIOS if args.partition=='all' or scenario['partition']==args.partition]
    receipt={'schema':SUITE_VERSION,'mode':'real','status':'blocked','domains':[],
             'campaign_id':uuid.uuid4().hex,'candidate':candidate_identity(manifest=args.candidate_manifest),
             'scenarios':specs,'scenario_hash':digest(specs),'charge_status':'measured',
             'provider_calls':0,'provider_usd':0,'charges':[],
             'comparisons_requested':args.comparisons,'partition':args.partition,
             'simulations':['support tickets and FD001 trajectories; static-source arrivals'],
             'promotion':'manager approval remains required'}
    run_ids=[]
    try:
        for domain in args.domains:
            result={'domain':domain,'status':'blocked','answers':[],
                    'comparison':{'status':'blocked','reason':'Full comparison not requested'}}
            receipt['domains'].append(result)
            try:
                oracle=raw_oracle(domain,source_files(domain),CONFIG['limits']['source_rows'])
                result['oracle']=oracle
                if not args.execute_real:
                    result['reason']='Real analyst execution not requested; raw-source preflight only'
                    continue
                if not receipt['candidate'].get('verified') or receipt['candidate'].get('dirty'):
                    result['reason']='Real benchmark requires a verified clean candidate'
                    continue
                from psycopg.types.json import Jsonb
                from runtime import analysis_store as db, analysis_service as service
                actor=db.authorize({'id':'manager'},domain,('manager',))
                source=db.source(domain)
                source_receipt=root()/domain.title()/'source-receipt.json'
                if source_receipt.exists() and json.loads(source_receipt.read_text()).get('terms_acknowledged'):
                    db.write('UPDATE backintel.analysis_sources SET body=%s WHERE id=%s',(Jsonb({**source['body'],'terms_acknowledged':True,'terms_actor':'manager','terms_basis':'operator download receipt'}),domain))
                service.import_source(domain,actor)
                snapshot=db.source(domain)['latest_snapshot']
                result['snapshot_id']=snapshot
                snapshot_body=db.query('SELECT body FROM backintel.analysis_snapshots WHERE id=%s',(snapshot,),one=True)['body']
                if snapshot_body.get('files')!=oracle['files']:
                    raise ValueError('Imported snapshot fingerprints differ from raw source oracle')
                if sorted(row['id'] for row in db.records(snapshot))!=oracle['cohort_ids']:
                    raise ValueError('Imported snapshot cohort differs from raw source oracle')
                # A fresh goal prevents cached successful answers from older code entering this campaign.
                goal=service.create_goal(actor,domain,CONFIG['sources'][domain]['question']+' Benchmark '+receipt['campaign_id']+' '+receipt['candidate']['source_hash'])
                result['goal_id']=goal['id']
                service.revise_goal(goal['id'],actor,confirmed=True)
                for spec in (item for item in specs if item['domain']==domain):
                    checked={'scenario':spec,'status':'blocked'}
                    result['answers'].append(checked)
                    try:
                        submitted=service.submit(goal['id'],actor,question=spec['prompt'])
                        run_ids.append(submitted['id'])
                        answer=execute(submitted)
                        checked['run_id']=answer['id']
                        if answer['status']!='succeeded':
                            raise RuntimeError(answer.get('error') or 'Frontier answer incomplete')
                        evidence={identity:db.query('SELECT * FROM backintel.capability_evidence WHERE sha256=%s',(identity,),one=True)
                                  for finding in answer['result'].get('findings',[]) for identity in finding.get('evidence_ids',[])}
                        checked.update(score_answer(answer,evidence,spec,oracle,snapshot))
                        checked.update(status='passed',usage=answer['result']['usage'])
                    except Exception as error:
                        checked.update(status='failed' if isinstance(error,ValueError) else 'blocked',reason=type(error).__name__+': '+safe_error(error))
                if args.comparisons:
                    try:
                        submitted=service.submit(goal['id'],actor,operation='training')
                        run_ids.append(submitted['id'])
                        training=execute(submitted)
                        if training['status']!='succeeded':
                            raise RuntimeError(training.get('error') or 'Real comparison did not complete')
                        result['candidate_id']=training['result']['candidate_id']
                        result['comparison']={'status':'passed','run_id':training['id'],'candidate_id':result['candidate_id']}
                    except Exception as error:
                        result['comparison']={'status':'blocked','reason':type(error).__name__+': '+safe_error(error)}
                statuses=[item['status'] for item in result['answers']]
                if args.comparisons:statuses.append(result['comparison']['status'])
                result['status']='failed' if 'failed' in statuses else 'passed' if statuses and all(s=='passed' for s in statuses) else 'blocked'
            except Exception as error:
                missing=isinstance(error,(FileNotFoundError,)) or 'Missing approved source file' in str(error)
                result['status']='failed' if isinstance(error,ValueError) and not missing else 'blocked'
                result['reason']=type(error).__name__+': '+safe_error(error)
    finally:
        if run_ids:
            try:
                receipt['charges']=db.query('SELECT run_id,id,status,charge,reserved FROM backintel.analysis_requests WHERE run_id=ANY(%s)',(run_ids,))
                receipt['provider_calls']=len(receipt['charges'])
                receipt['provider_usd']=sum(float(item['charge'] or 0) for item in receipt['charges'])
                receipt['charge_status']='unknown' if not receipt['charges'] or any(item['charge'] is None for item in receipt['charges']) else 'measured'
            except Exception as error:
                receipt.update(charge_status='unknown',cost_error=type(error).__name__+': '+safe_error(error))
        if candidate_identity(manifest=args.candidate_manifest)!=receipt['candidate']:
            receipt['identity_error']='Candidate changed during benchmark execution'
        statuses=[item['status'] for item in receipt['domains']]
        receipt['status']='failed' if 'failed' in statuses else 'passed' if statuses and all(s=='passed' for s in statuses) else 'blocked'
        if receipt['charge_status']!='measured' or receipt.get('identity_error'):
            receipt['status']='blocked'
        output=Path(args.output);output.parent.mkdir(parents=True,exist_ok=True)
        output.write_text(json.dumps(receipt,indent=2,default=str,allow_nan=False))
        print(json.dumps({'status':receipt['status'],'domains':[{k:v for k,v in item.items() if k in ('domain','status','reason')} for item in receipt['domains']],'evidence':str(output)}))
    return 0 if receipt['status']=='passed' else 1


if __name__=='__main__':raise SystemExit(main())
