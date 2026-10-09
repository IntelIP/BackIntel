"""Real CPU models, trained-only preprocessing, equal-cohort evaluation."""
from __future__ import annotations

import gc
import json
import os
import resource
import time
from pathlib import Path, PurePosixPath

from runtime.analysis_data import CONFIG, digest, fingerprint, sample
from runtime.real_models import checkpoint, file_sha, model_root, _tabicl, versions, CONFIG as MODEL_CONFIG


def matrix_features(row):
    values = {}
    for name, value in row['features'].items():
        if value is None:
            values[name] = 0.
            values[name+':missing'] = 1.
        elif isinstance(value, (int, float)):
            values[name] = float(value)
        else:
            values[name] = str(value)[:120] or '(missing)'
    return values


def metrics(kind, truth, predicted):
    import numpy as np
    from sklearn.metrics import average_precision_score, brier_score_loss, mean_absolute_error, mean_squared_error, roc_auc_score
    y, p = np.asarray(truth), np.asarray(predicted)
    if kind == 'regression':
        return {'mae': float(mean_absolute_error(y,p)), 'rmse': float(mean_squared_error(y,p)**.5), 'n': len(y)}
    p = np.clip(p,0,1)
    bins = []
    for lo in np.linspace(0,.8,5):
        mask = (p >= lo) & (p <= 1 if lo > .79 else p < lo+.2)
        if mask.any():
            bins.append({'count': int(mask.sum()), 'predicted': float(p[mask].mean()), 'observed': float(y[mask].mean())})
    return {'roc_auc': float(roc_auc_score(y,p)) if len(set(y))>1 else None,
            'average_precision': float(average_precision_score(y,p)) if y.sum() else None,
            'brier': float(brier_score_loss(y,p)), 'accuracy': float(((p>=.5)==y).mean()),
            'calibration': bins, 'n': len(y), 'positives': int(y.sum())}


def validate_decide_weights(directory):
    receipt = directory / 'backintel-weights.json'
    if not receipt.is_file() or receipt.is_symlink() or directory.is_symlink():
        raise RuntimeError('Pinned Decide weights have not been prepared')
    spec = json.loads(receipt.read_text())
    if any(spec.get(key) != CONFIG['decide'][key] for key in ('repository', 'revision')) or not spec.get('files'):
        raise ValueError('Decide repository or revision is not approved')
    declared = set()
    for item in spec['files']:
        name = PurePosixPath(item['file'])
        path = directory / str(name)
        if name.is_absolute() or '..' in name.parts or '\\' in str(name) or str(name) in declared or not path.resolve().is_relative_to(directory.resolve()):
            raise ValueError('Decide receipt contains unsafe or duplicate path')
        declared.add(str(name))
        if not path.is_file() or path.stat().st_size != item['bytes'] or file_sha(path) != item['sha256']:
            raise ValueError('Decide weight identity mismatch')
    actual = set()
    for path in directory.rglob('*'):
        if path.is_symlink():
            raise ValueError('Decide package contains a linked path')
        if path.is_file() and path != receipt:
            actual.add(path.relative_to(directory).as_posix())
    if declared != actual or 'config.json' not in declared or not any(name.endswith('.safetensors') for name in declared):
        raise ValueError('Decide receipt is not a complete model package')
    return spec


def decide(rows, domain):
    """Pin weights locally. Raw classification scores are not claimed as probabilities."""
    from gliner2 import AutoExtractor
    import torch
    torch.set_num_threads(CONFIG['limits']['cpu_threads'])
    directory = model_root() / 'Decide'
    spec = validate_decide_weights(directory)
    identity = {'model': CONFIG['decide'], 'weights': spec,
                'libraries': versions(('gliner2','torch','numpy')),
                'implementation_sha256': file_sha(Path(__file__))}
    extractor = AutoExtractor.from_pretrained(str(directory))
    labels = ['positive opinion', 'negative opinion', 'mixed opinion'] if domain=='commerce' else ['urgent service failure', 'routine request', 'access problem']
    enriched, observations = [], []
    for row in rows:
        text = row['text'][:4000]
        expected = {**identity, 'labels': labels, 'input_sha256': digest(text), 'mode': 'real', 'probability_calibrated': False}
        key = digest(expected)
        expected['identity'] = key
        cache = model_root()/'DecideObservations'/f'{key}.json'
        if cache.exists():
            observation = json.loads(cache.read_text())
            if any(observation.get(name) != value for name, value in expected.items()):
                raise ValueError('Decide observation cache does not match current implementation and input')
        else:
            result = extractor.classify_text(text, {'signal': labels})
            observation = {**expected, 'output': result}
            cache.parent.mkdir(parents=True,exist_ok=True)
            cache.write_text(json.dumps(observation))
        observation={**observation,'provider':'local-gliner2','question_schema':{'signal':labels}}
        label = observation['output']
        if isinstance(label, dict):
            label = label.get('signal', label.get('label', label.get('classification', label.get('labels'))))
        if isinstance(label,list):
            label = label[0] if label else '(unknown)'
        if isinstance(label,dict):
            label = label.get('label', '(unknown)')
        if label not in labels:
            raise ValueError('Decide did not return an approved classification label')
        enriched.append({**row,'features':{**row['features'],'decide_label':label}})
        observations.append({**observation, 'label': label})
    del extractor
    gc.collect()
    return enriched, observations


def runtime_dependencies(domain, route=None):
    tabicl = route is None or route.startswith('tabiclv2-')
    semantic = domain in ('commerce','support') and (route is None or route.endswith('facts-decide'))
    packages = ['scikit-learn','numpy','joblib']
    if route is None or route.startswith('catboost-'):
        packages.append('catboost')
    if tabicl:
        packages.append('tabicl')
    if tabicl or semantic:
        packages.append('torch')
    if semantic:
        packages.append('gliner2')
    checkpoint_spec = checkpoint(CONFIG['sources'][domain]['kind'])[1] if tabicl else None
    implementation = {name:file_sha(Path(__file__).with_name(name))
                      for name in ('analysis_models.py','real_models.py','simulation.py')}
    return {'libraries': versions(packages), 'checkpoint': checkpoint_spec,
            'tabiclv2_parameters': json.loads(MODEL_CONFIG.read_text())['tabiclv2']['parameters'] if tabicl else None,
            'decide': CONFIG['decide'] if semantic else None,
            'implementation_sha256': digest(implementation)}


def compare(domain, rows, snapshot):
    import joblib
    import numpy as np
    import torch
    from catboost import CatBoostClassifier, CatBoostRegressor
    from sklearn.feature_extraction import DictVectorizer
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.linear_model import LogisticRegression, Ridge
    torch.set_num_threads(2)
    kind = CONFIG['sources'][domain]['kind']
    train, calibration, test = (sample(rows,k) for k in ('train','calibration','test'))
    if len(train)<16 or len(calibration)<8 or len(test)<8:
        raise ValueError('Insufficient independently held-out labeled examples')
    if kind=='classification' and len({r['target'] for r in train})<2:
        raise ValueError('Training requires both classification outcomes')
    start=time.monotonic()
    dependencies = runtime_dependencies(domain)
    identity = digest(['model-comparison-v2',domain,snapshot,CONFIG['limits'],dependencies,[r['id'] for r in train+calibration+test]])
    directory=model_root()/'Analysis'/identity
    manifest=directory/'manifest.json'
    prior=json.loads(manifest.read_text()) if manifest.exists() else None
    directory.mkdir(parents=True,exist_ok=True)
    output={'id':identity,'domain':domain,'snapshot':snapshot,'kind':kind,'mode':'real','methods':[],
            'splits':{k:[r['id'] for r in group] for k,group in zip(('train','calibration','test'),(train,calibration,test))},
            'preparation':'training-only DictVectorizer; explicit numeric missing flags; unseen categories omitted',
            'dependencies':dependencies, 'artifacts':[], 'caveat':CONFIG['sources'][domain]['caveat'], 'provider_calls':0,'provider_usd':0,'local_compute_usd':None}
    if prior is not None:
        # Rebind cached files to this request; recompute every reported score below.
        for key, value in output.items():
            if key not in ('methods','artifacts') and prior.get(key) != value:
                raise ValueError('Cached comparison metadata mismatch: '+key)
        features=['facts','facts-decide'] if domain in ('commerce','support') else ['facts']
        files=[f'{route}-{feature}.joblib' for feature in features for route in ('catboost','tabiclv2')]
        if domain in ('commerce','support'):
            files.append('observations.json')
        artifacts=prior.get('artifacts',[])
        expected={name:file_sha(directory/name) for name in files}
        if len(artifacts)!=len(files) or {a['file']:a['sha256'] for a in artifacts}!=expected:
            raise ValueError('Model artifact identity mismatch')
    y=np.array([r['target'] for r in train]); yt=[r['target'] for r in test]
    baseline=float(np.mean(y))
    yc=[r['target'] for r in calibration]
    output['methods'].append({'route':'baseline','metrics':metrics(kind,yt,[baseline]*len(test)),
                              'calibration_metrics':metrics(kind,yc,[baseline]*len(calibration))})
    def check_limits():
        peak=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        peak_bytes=peak if os.uname().sysname=='Darwin' else peak*1024
        if time.monotonic()-start>CONFIG['limits']['model_seconds'] or peak_bytes>CONFIG['limits']['worker_bytes']:
            raise RuntimeError('Model resource limit exceeded')
    if domain in ('commerce','support'):
        tfidf=TfidfVectorizer(max_features=2000,min_df=2)
        xt=tfidf.fit_transform([r['text'] for r in train])
        simple=LogisticRegression(max_iter=300,random_state=42) if kind=='classification' else Ridge()
        simple.fit(xt,y)
        predicted=simple.predict_proba(tfidf.transform([r['text'] for r in test]))[:,list(simple.classes_).index(1)] if kind=='classification' else simple.predict(tfidf.transform([r['text'] for r in test]))
        calibrated=simple.predict_proba(tfidf.transform([r['text'] for r in calibration]))[:,list(simple.classes_).index(1)] if kind=='classification' else simple.predict(tfidf.transform([r['text'] for r in calibration]))
        output['methods'].append({'route':'simple-text','metrics':metrics(kind,yt,predicted),
                                  'calibration_metrics':metrics(kind,yc,calibrated)})
    sets=[('facts',train+calibration+test)]
    if domain in ('commerce','support'):
        semantic,observations=decide(train+calibration+test,domain)
        sets.append(('facts-decide',semantic))
        obs_path=directory/'observations.json'
        obs_path.write_text(json.dumps(observations))
        output['artifacts'].append(fingerprint(obs_path))
    for feature_set,cases in sets:
        a=cases[:len(train)]; b=cases[len(train)+len(calibration):]; cal=cases[len(train):len(train)+len(calibration)]
        vectorizer=DictVectorizer(sparse=False)
        x=vectorizer.fit_transform([matrix_features(r) for r in a]); xx=vectorizer.transform([matrix_features(r) for r in cal+b])
        for route in ('catboost','tabiclv2'):
            check_limits(); method_start=time.monotonic()
            artifact=directory/f'{route}-{feature_set}.joblib'
            if prior is not None:
                package=joblib.load(artifact)
                estimator=package['estimator']
                xx=package['vectorizer'].transform([matrix_features(r) for r in cal+b])
            else:
                if route=='catboost':
                    cls=CatBoostClassifier if kind=='classification' else CatBoostRegressor
                    estimator=cls(iterations=80,depth=4,learning_rate=.08,random_seed=42,thread_count=2,verbose=False,allow_writing_files=False)
                else:
                    path,_=checkpoint(kind); estimator=_tabicl(kind,path)
                estimator.fit(x,y)
                joblib.dump({'vectorizer':vectorizer,'estimator':estimator},artifact)
            predicted=estimator.predict_proba(xx)[:,list(estimator.classes_).index(1)] if kind=='classification' else estimator.predict(xx)
            calibrated, predicted = predicted[:len(cal)], predicted[len(cal):]
            output['artifacts'].append(fingerprint(artifact))
            output['methods'].append({'route':route,'features':feature_set,'artifact':artifact.name,
                'metrics':metrics(kind,yt,predicted),'calibration_metrics':metrics(kind,yc,calibrated),'wall_seconds':time.monotonic()-method_start,
                                      'predictions':{r['id']:float(p) for r,p in zip(test,predicted)}})
            del estimator; gc.collect(); check_limits()
    output['wall_seconds']=time.monotonic()-start
    output['peak_rss_bytes']=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*(1 if os.uname().sysname=='Darwin' else 1024)
    manifest.write_text(json.dumps(output,allow_nan=False))
    return output


def predict(model, rows):
    import joblib
    body=model['body']
    # Validate only the approved predictor's runtime, not unused comparison routes.
    route=body.get('approved_route','catboost-facts')
    current=runtime_dependencies(body['domain'],route)
    recorded=body.get('dependencies') or {}
    expected={key:recorded.get(key) for key in current}
    if 'libraries' in current:
        expected['libraries']={name:recorded.get('libraries',{}).get(name) for name in current['libraries']}
    for key in ('checkpoint','tabiclv2_parameters','decide'):
        if key in current and current[key] is None:
            expected[key]=None
    if expected != current:
        raise ValueError('Active model runtime dependencies changed; prepare and approve a new comparison')
    directory=model_root()/'Analysis'/body['id']
    name=route+'.joblib'
    expected=next((f['sha256'] for f in body['artifacts'] if f['file']==name),None)
    if expected is None or file_sha(directory/name)!=expected:
        raise ValueError('Active model file identity mismatch')
    prepared=rows
    if route.endswith('facts-decide'):
        prepared,_=decide(rows,body['domain'])
    package=joblib.load(directory/name)
    x=package['vectorizer'].transform([matrix_features(r) for r in prepared])
    estimator=package['estimator']
    values=estimator.predict_proba(x)[:,list(estimator.classes_).index(1)] if body['kind']=='classification' else estimator.predict(x)
    return {r['id']:float(v) for r,v in zip(rows,values)}


if __name__ == '__main__':
    import argparse
    from runtime.analysis_store import records
    parser=argparse.ArgumentParser()
    parser.add_argument('--domain',choices=CONFIG['sources'],required=True)
    parser.add_argument('--snapshot',required=True)
    arguments=parser.parse_args()
    import contextlib
    import sys
    with contextlib.redirect_stdout(sys.stderr):
        result=compare(arguments.domain,records(arguments.snapshot),arguments.snapshot)
    print(json.dumps(result,allow_nan=False))
