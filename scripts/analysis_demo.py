"""Local setup and secure launch. No automatic competition-rule acceptance."""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
import secrets
import ssl
import subprocess
import urllib.request
import zipfile
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]


def seed():
    from runtime.analysis_data import CONFIG
    from runtime import analysis_store as db
    db.catalog()
    directory=Path('/run/backintel-credentials')
    directory.mkdir(parents=True,exist_ok=True,mode=0o700)
    path=directory/'access.json'
    values=json.loads(path.read_text()) if path.exists() else {role:secrets.token_urlsafe(32) for role in ('manager','analyst','viewer','worker')}
    for role,token in values.items():
        db.write('INSERT INTO backintel.analysis_principals(id,token_hash,role,domains) VALUES(%s,%s,%s,%s) ON CONFLICT(id) DO UPDATE SET token_hash=excluded.token_hash',
                 (role,hashlib.sha256(token.encode()).hexdigest(),role,list(CONFIG['sources'])))
    path.write_text(json.dumps(values));path.chmod(0o600)
    print('Local access grants ready; credential values are hidden.')


def context():
    import certifi
    return ssl.create_default_context(cafile=certifi.where())


def download(url,path):
    path.parent.mkdir(parents=True,exist_ok=True)
    temporary=path.with_suffix(path.suffix+'.partial')
    result=subprocess.run(['curl','--silent','--show-error','--fail','--location','--retry','2',
                           '--connect-timeout','30','--max-time','600','--continue-at','-',
                           '--output',str(temporary),url],capture_output=True,text=True)
    if result.returncode:
        raise RuntimeError('Source download did not complete; a partial download is retained for resumption')
    temporary.replace(path)


def acquire(domain,acknowledge):
    from runtime.analysis_data import CONFIG,root
    spec=CONFIG['sources'][domain]
    if spec.get('competition'):
        raise RuntimeError('Home Credit requires human Kaggle rule acceptance. Place application_train.csv and bureau.csv in the Credit dataset directory.')
    if not acknowledge:
        raise RuntimeError('Confirm the linked source terms before downloading with --acknowledge-terms')
    directory=root()/domain.title()
    archive=directory/'original.zip'
    if not archive.exists():
        download('https://www.kaggle.com/api/v1/datasets/download/'+spec['kaggle'],archive)
    needed=set(spec['files'])
    def extract(z):
        for member in z.infolist():
            name=Path(member.filename).name
            if name in needed:
                target=directory/name
                if not target.exists():
                    with z.open(member) as stream,target.open('xb') as output:
                        for chunk in iter(lambda:stream.read(1048576),b''):
                            output.write(chunk)
                needed.remove(name)
            elif name.lower().endswith('.zip') and member.file_size<200_000_000:
                extract(zipfile.ZipFile(io.BytesIO(z.read(member))))
    with zipfile.ZipFile(archive) as z:
        extract(z)
    if needed:
        raise RuntimeError('Expected source files are missing: '+', '.join(sorted(needed)))
    (directory/'source-receipt.json').write_text(json.dumps({'kaggle':spec['kaggle'],'license':spec['license'],'terms_acknowledged':True,'attribution':spec['name']}))
    print(json.dumps({'domain':domain,'status':'downloaded','directory':str(directory)}))


def weights():
    from runtime.analysis_data import CONFIG, fingerprint
    directory=ROOT/'artifacts/Models/Decide'
    spec=CONFIG['decide']
    req=urllib.request.Request('https://huggingface.co/api/models/'+spec['repository']+'/revision/'+spec['revision'])
    with urllib.request.urlopen(req,context=context(),timeout=30) as stream:
        meta=json.load(stream)
    paths=[item['rfilename'] for item in meta['siblings'] if item['rfilename'].endswith(('.json','.safetensors','.model'))]
    receipts=[]
    for name in paths:
        path=directory/name
        if not path.exists():
            download('https://huggingface.co/'+spec['repository']+'/resolve/'+spec['revision']+'/'+name+'?download=true',path)
        receipts.append({**fingerprint(path),'file':name})
    (directory/'backintel-weights.json').write_text(json.dumps({**spec,'files':receipts}))
    print('Pinned Decide weights prepared; receipt contains hashes and provenance limitations.')


def runtime_access():
    value=subprocess.run(['docker','compose','-f','compose.analysis.yml','exec','-T','runtime','python','-c',"from pathlib import Path;print(Path('/run/backintel-credentials/access.json').read_text())"],cwd=ROOT,capture_output=True,text=True,check=True)
    return json.loads(value.stdout)


def keychain(action,role,value=None):
    result=subprocess.run(['swift',str(ROOT/'scripts/analysis_access.swift'),action,role],input=value,capture_output=True,text=True)
    if result.returncode:
        raise RuntimeError('Local Keychain access failed; no credential was printed')
    return result.stdout


def provision():
    values=runtime_access()
    for role in ('manager','analyst','viewer'):
        keychain('set',role,values[role])
    result=subprocess.run(['security','find-generic-password','-s','BackIntel OpenRouter','-a','runtime','-w'],capture_output=True,text=True,check=True)
    credential=json.dumps({'key':result.stdout.strip()})
    code="import os,sys; p='/run/backintel-credentials/analyst.json'; fd=os.open(p,os.O_WRONLY|os.O_CREAT|os.O_TRUNC,0o600);os.write(fd,sys.stdin.buffer.read());os.close(fd)"
    subprocess.run(['docker','compose','-f','compose.analysis.yml','exec','-T','runtime','python','-c',code],cwd=ROOT,input=credential,text=True,check=True,capture_output=True)
    print('Cached OpenRouter credential injected into tmpfs. Local role credentials saved in Keychain.')


def schedule():
    import httpx
    token=runtime_access()['worker']
    with httpx.Client(base_url='http://127.0.0.1:2028',headers={'Authorization':'Bearer '+token},timeout=30) as client:
        existing=client.post('/runs/crons/search',json={'limit':100})
        existing.raise_for_status()
        crons=existing.json()
        if not any(c.get('metadata',{}).get('backintel_analysis') for c in crons):
            response=client.post('/runs/crons',json={'assistant_id':'analysis_refresh','schedule':'0 * * * *','input':{},'metadata':{'backintel_analysis':True}})
            response.raise_for_status()
    print('Native hourly refresh schedule registered; unchanged sources make no analyst calls.')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    sub=parser.add_subparsers(dest='command',required=True)
    for name in ('seed','weights','provision','schedule'):
        sub.add_parser(name)
    a=sub.add_parser('acquire');a.add_argument('--domain',required=True,choices=('commerce','support','churn','maintenance','credit'));a.add_argument('--acknowledge-terms',action='store_true')
    a=sub.add_parser('open');a.add_argument('--role',choices=('manager','analyst','viewer'),default='manager')
    args=parser.parse_args()
    if args.command=='acquire':
        acquire(args.domain,args.acknowledge_terms)
    elif args.command=='open':
        token=keychain('get',args.role).strip()
        url='http://127.0.0.1:2028/#access='+token
        subprocess.run(['osascript','-'],input='open location '+json.dumps(url),capture_output=True,text=True,check=True)
        print('Workspace opened using the local '+args.role+' grant.')
    else:
        globals()[args.command]()


if __name__=='__main__':
    main()
