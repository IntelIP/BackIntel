"""Actual Telco baseline/CatBoost checks; partial evidence, never a promoted candidate."""
from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.metadata
import json
import os
import resource
import statistics
import subprocess
import sys
import time
from collections import defaultdict
from pathlib import Path

from runtime.analysis_data import CONFIG, adapt, digest, fingerprint, sample, source_files
from runtime.analysis_models import matrix_features, metrics
from runtime.real_models import model_root

PROJECT = Path(__file__).resolve().parents[1]


def raw_churn_oracle(path):
    """Read original labels directly, without adapter, database, or aggregation helpers."""
    cases = {}
    grouped = defaultdict(list)
    with Path(path).open(encoding='utf-8-sig', newline='') as stream:
        for row in csv.DictReader(stream):
            identity = row['customerID']
            if identity in cases or row['Churn'] not in ('Yes', 'No'):
                raise ValueError('Original Telco identities or outcomes are invalid')
            target = int(row['Churn'] == 'Yes')
            bucket = int(hashlib.sha256(json.dumps(identity, separators=(',', ':')).encode()).hexdigest()[:8], 16) % 100
            split = 'train' if bucket < 70 else 'calibration' if bucket < 85 else 'test'
            cases[identity] = {'target': target, 'contract': row['Contract'], 'split': split}
            grouped[row['Contract']].append(target)
    return cases, {'records': len(cases), 'positives': sum(row['target'] for row in cases.values()),
                   'mean_target': statistics.mean(row['target'] for row in cases.values()),
                   'contract': {key: {'records': len(values), 'positives': sum(values), 'mean_target': statistics.mean(values)} for key, values in sorted(grouped.items())}}


def run(directory):
    import joblib
    import numpy as np
    from catboost import CatBoostClassifier
    from sklearn.feature_extraction import DictVectorizer
    from threadpoolctl import threadpool_limits
    started = time.monotonic()
    paths = source_files('churn')
    originals, oracle = raw_churn_oracle(paths[0])
    snapshot, source, rows = adapt('churn', paths)
    if {row['id'] for row in rows} != set(originals):
        raise ValueError('Adapter cohort differs from the independent original cohort')
    for row in rows:
        raw = originals[row['id']]
        if row['target'] != raw['target'] or row['groups']['contract'] != raw['contract'] or row['split'] != raw['split']:
            raise ValueError('Adapter label, contract, or split differs from original oracle')
        if 'Churn' in row['features'] or 'customerID' in row['features']:
            raise ValueError('Target or record identity entered predictive features')
    train, calibration, test = (sample(rows, split) for split in ('train', 'calibration', 'test'))
    if min(map(len, (train, calibration, test))) < 8 or len({row['target'] for row in train}) != 2:
        raise ValueError('Insufficient held-out original labels')
    groups = [set(row['entity'] for row in group) for group in (train, calibration, test)]
    if groups[0] & groups[1] or groups[0] & groups[2] or groups[1] & groups[2]:
        raise ValueError('An entity crossed model partitions')
    libraries = {name: importlib.metadata.version(name) for name in ('catboost', 'scikit-learn', 'numpy', 'joblib', 'pandas', 'scipy', 'threadpoolctl')}
    approved_catboost = json.loads((PROJECT / 'config/real_models.json').read_text())['catboost']['package'].split('==')[1]
    if libraries['catboost'] != approved_catboost:
        raise ValueError('Installed CatBoost differs from its approved pin')
    parameters = {'iterations': 80, 'depth': 4, 'learning_rate': .08, 'random_seed': 42,
                  'thread_count': CONFIG['limits']['cpu_threads'], 'verbose': False, 'allow_writing_files': False}
    result = {'schema': 'backintel-partial-local-benchmark/v1', 'status': 'passed', 'mode': 'real',
              'comparison_scope': 'partial', 'qualified_for_promotion': False, 'domain': 'churn',
              'missing_routes': ['tabiclv2'], 'analyst_tested': False, 'decide_tested': False,
              'provider_calls': 0, 'provider_usd': 0, 'local_compute_usd': None,
              'snapshot_id': snapshot, 'source': source, 'independent_original_oracle': oracle,
              'libraries': libraries, 'catboost_parameters': parameters,
              'splits': {key: [row['id'] for row in group] for key, group in zip(('train', 'calibration', 'test'), (train, calibration, test))},
              'preparation': 'Training-only DictVectorizer; fixed entity partitions; original held-out labels checked independently.',
              'methods': [], 'artifacts': [], 'limitations': [CONFIG['sources']['churn']['caveat'],
                  'Partial local evidence does not qualify the full model or hosted analyst campaign. No model is promoted.']}
    baseline = statistics.mean(originals[row['id']]['target'] for row in train)
    y = np.array([originals[row['id']]['target'] for row in train])
    with threadpool_limits(limits=CONFIG['limits']['cpu_threads']):
        vectorizer = DictVectorizer(sparse=False)
        x = vectorizer.fit_transform([matrix_features(row) for row in train])
        estimator = CatBoostClassifier(**parameters)
        estimator.fit(x, y)
        for route in ('baseline', 'catboost'):
            method = {'route': route, 'features': 'facts', 'predictions': {}}
            for key, group in (('calibration', calibration), ('test', test)):
                predictions = ([baseline] * len(group) if route == 'baseline' else
                               estimator.predict_proba(vectorizer.transform([matrix_features(row) for row in group]))[:, list(estimator.classes_).index(1)].tolist())
                truth = [originals[row['id']]['target'] for row in group]
                measured = metrics('classification', truth, predictions)
                independent_brier = sum((prediction - target)**2 for prediction, target in zip(predictions, truth)) / len(truth)
                if abs(measured['brier'] - independent_brier) > 1e-12:
                    raise ValueError('Measured Brier score disagrees with independent original-label calculation')
                method[key + '_metrics'] = measured
                method['predictions'][key] = {row['id']: prediction for row, prediction in zip(group, predictions)}
            result['methods'].append(method)
        artifact = directory / 'catboost-facts.joblib'
        joblib.dump({'vectorizer': vectorizer, 'estimator': estimator}, artifact)
        reloaded = joblib.load(artifact)
        restored = reloaded['estimator'].predict_proba(reloaded['vectorizer'].transform([matrix_features(row) for row in test]))[:, 1].tolist()
        expected = list(result['methods'][1]['predictions']['test'].values())
        if not np.allclose(restored, expected, rtol=0, atol=1e-12):
            raise ValueError('Restored actual model changed held-out predictions')
        result['model_restore_predictions_verified'] = True
        result['artifacts'].append(fingerprint(artifact))
    result['wall_seconds'] = time.monotonic() - started
    result['peak_rss_bytes'] = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * (1 if sys.platform == 'darwin' else 1024)
    if result['peak_rss_bytes'] > CONFIG['limits']['worker_bytes'] or result['wall_seconds'] > CONFIG['limits']['model_seconds']:
        raise RuntimeError('Local benchmark exceeded the approved model resource boundary')
    result['resource_boundary'] = {'cpu_threads': CONFIG['limits']['cpu_threads'], 'wall_timeout_seconds': CONFIG['limits']['model_seconds'],
                                   'rss_budget_bytes': CONFIG['limits']['worker_bytes'], 'rss_enforcement': 'parent monitors Linux process RSS; child verifies peak RSS'}
    result['implementation'] = fingerprint(Path(__file__))
    result['candidate_commit'] = subprocess.run(['git', 'rev-parse', 'HEAD'], cwd=PROJECT, capture_output=True, text=True, check=True).stdout.strip()
    result['dirty_tree'] = bool(subprocess.run(['git', 'status', '--porcelain'], cwd=PROJECT, capture_output=True, text=True, check=True).stdout)
    result['identity'] = digest([snapshot, libraries, parameters, result['implementation'], result['splits']])
    (directory / 'receipt.json').write_text(json.dumps(result, indent=2, allow_nan=False) + '\n')
    print(json.dumps({'status': result['status'], 'comparison_scope': result['comparison_scope'], 'rows': oracle['records'],
                      'metrics': [{key: value for key, value in method.items() if key != 'predictions'} for method in result['methods']],
                      'provider_usd': 0, 'receipt': str(directory / 'receipt.json')}))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output')
    parser.add_argument('--child', action='store_true', help=argparse.SUPPRESS)
    args = parser.parse_args()
    directory = Path(args.output) if args.output else model_root() / 'LocalBenchmarks/telco'
    if args.child:
        run(directory)
        return
    directory.mkdir(parents=True, exist_ok=False)
    env = dict(os.environ, OMP_NUM_THREADS='2', OPENBLAS_NUM_THREADS='2', MKL_NUM_THREADS='2', HF_HUB_OFFLINE='1', OPENROUTER_API_KEY='')
    env['BACKINTEL_ANALYST_CREDENTIAL_FILE'] = str(directory / 'no-provider-credential.json')
    deadline = time.monotonic() + CONFIG['limits']['model_seconds']
    with (directory / 'runtime.log').open('w') as log:
        child = subprocess.Popen([sys.executable, '-m', 'scripts.analysis_local_benchmark', '--child', '--output', str(directory)], cwd=PROJECT, env=env, stdout=log, stderr=log)
        try:
            while child.poll() is None:
                if time.monotonic() > deadline:
                    raise TimeoutError('Actual local benchmark exceeded its wall-clock boundary')
                status = Path(f'/proc/{child.pid}/status')
                if status.is_file():
                    try:
                        process_status = status.read_text()
                    except FileNotFoundError:
                        process_status = ''  # The child may have completed between these two reads.
                    rss = next((int(line.split()[1]) * 1024 for line in process_status.splitlines() if line.startswith('VmRSS:')), 0)
                    if rss > CONFIG['limits']['worker_bytes']:
                        raise RuntimeError('Actual local benchmark exceeded its RSS boundary')
                time.sleep(.1)
            if child.returncode:
                raise RuntimeError('Actual local benchmark failed; inspect its private runtime.log')
        finally:
            if child.poll() is None:
                child.kill(); child.wait(timeout=10)
    print(json.dumps({'status': 'passed', 'comparison_scope': 'partial', 'provider_usd': 0, 'receipt': str(directory / 'receipt.json')}))


if __name__ == '__main__':
    main()
