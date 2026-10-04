"""Run real, source-gated comparisons and independently checked frontier questions.

Run inside the isolated analysis runtime. Promotion remains a separate manager action.
"""
import argparse
import json
import os
import re
import statistics
from collections import defaultdict
from pathlib import Path

import httpx
from psycopg.types.json import Jsonb

from runtime import analysis_store as db
from runtime import analysis_service as service
from runtime.analysis_data import CONFIG,root


def execute(run):
    if db.run(run['id'])['status']=='succeeded':
        return db.run(run['id'])
    service.wake(run['id'])
    token=json.loads(Path('/run/backintel-credentials/access.json').read_text())['manager']
    with httpx.Client(timeout=75,headers={'Authorization':'Bearer '+token}) as client:
        while db.run(run['id'])['status'] in ('queued','running'):
            with client.stream('GET','http://127.0.0.1:2026'+f"/api/v1/runs/{run['id']}/events") as response:
                response.raise_for_status()
                for _ in response.iter_lines():
                    pass
    return db.run(run['id'])


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--domains',nargs='+',choices=CONFIG['sources'],default=list(CONFIG['sources']))
    parser.add_argument('--output',default='/models/Analysis/benchmark-evidence.json')
    args=parser.parse_args()
    receipt={'status':'blocked','domains':[],'simulations':['support tickets and FD001 trajectories; static-source arrivals'],'promotion':'manager approval remains required'}
    try:
        for domain in args.domains:
            result={'domain':domain,'status':'blocked'}
            receipt['domains'].append(result)
            try:
                actor=db.authorize({'id':'manager'},domain,('manager',))
                s=db.source(domain)
                source_receipt=root()/domain.title()/'source-receipt.json'
                if source_receipt.exists() and json.loads(source_receipt.read_text()).get('terms_acknowledged') and not CONFIG['sources'][domain].get('competition'):
                    db.write('UPDATE backintel.analysis_sources SET body=%s WHERE id=%s',(Jsonb({**s['body'],'terms_acknowledged':True,'terms_actor':'manager','terms_basis':'operator download receipt'}),domain))
                service.import_source(domain,actor)
                question=CONFIG['sources'][domain]['question']
                g=db.query('SELECT * FROM backintel.analysis_goals WHERE domain=%s AND owner=%s AND body->>\'question\'=%s ORDER BY created_at LIMIT 1',(domain,actor['id'],question),one=True)
                g=g or service.create_goal(actor,domain,question)
                service.revise_goal(g['id'],actor,confirmed=True)
                training=execute(service.submit(g['id'],actor,operation='training'))
                if training['status']!='succeeded':
                    raise RuntimeError(training.get('error') or 'Real comparison did not complete')
                result['candidate_id']=training['result']['candidate_id']
                rows=db.records(training['snapshot_id'])
                labeled=[r['target'] for r in rows if r['target'] is not None]
                grouped=defaultdict(list)
                for row in rows:
                    if row['target'] is not None:grouped[str(row['groups'][CONFIG['sources'][domain]['group']])].append(row['target'])
                lowest=min(grouped,key=lambda k:(statistics.mean(grouped[k]),k))
                checks=[('How many records are in the current source snapshot? Use inspect_source and report the record count.',str(len(rows))),
                        ('What is the observed mean target in the current snapshot? Use summarize without grouping.',statistics.mean(labeled)),
                        ('Which '+CONFIG['sources'][domain]['group']+' group has the lowest observed mean target? Use summarize grouped by that field.',lowest)]
                result['answers']=[]
                for prompt,expected in checks:
                    answer=execute(service.submit(g['id'],actor,question=prompt))
                    if answer['status']!='succeeded':raise RuntimeError(answer.get('error') or 'Frontier answer incomplete')
                    text=answer['result']['summary']+' '+' '.join(f['claim'] for f in answer['result']['findings'])
                    if isinstance(expected,str):
                        correct=expected in text.replace(',','')
                    else:
                        tokens=re.findall(r'(?<!\w)-?\d[\d,]*(?:\.\d+)?',text)
                        correct=any(round(expected,len(t.split('.')[1]) if '.' in t else 0)==float(t.replace(',','')) for t in tokens)
                    if not correct:raise ValueError('Known-answer narrative disagrees with independent oracle')
                    result['answers'].append({'run_id':answer['id'],'expected':expected,'correct':True,'usage':answer['result']['usage']})
                result['status']='passed'
            except Exception as error:
                result['status']='failed' if isinstance(error,ValueError) else 'blocked'
                result['reason']=type(error).__name__+': '+str(error)[:1500]
        receipt['status']='failed' if any(r['status']=='failed' for r in receipt['domains']) else 'passed' if all(r['status']=='passed' for r in receipt['domains']) else 'blocked'
    finally:
        output=Path(args.output);output.parent.mkdir(parents=True,exist_ok=True)
        receipt['charges']=db.query('SELECT status,charge,reserved FROM backintel.analysis_requests')
        output.write_text(json.dumps(receipt,indent=2,default=str))
        print(json.dumps({'status':receipt['status'],'domains':[{k:v for k,v in r.items() if k in ('domain','status','reason','candidate_id')} for r in receipt['domains']],'evidence':str(output)}))


if __name__=='__main__':main()
