"""Evaluate a clean checkout's local predictors in bounded, network-free containers.

The host owns candidate identity and container cleanup. The child runs the existing
adapters and comparison code; no database, hosted analyst, or model promotion is used.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time
import uuid


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def candidate(root):
    def git(*args):
        return subprocess.check_output(['git', '-C', str(root), *args], text=True).strip()
    if git('status', '--porcelain'):
        raise ValueError('Prediction benchmarks require a clean committed checkout')
    names = git('ls-files').splitlines()
    files = {name: sha(root / name) for name in names
             if name.startswith(('runtime/', 'config/', 'migrations/')) or name.startswith('requirements')}
    return {'candidate_commit': git('rev-parse', 'HEAD'), 'dirty_tree': False,
            'source_hashes': files, 'harness_sha256': sha(__file__)}


def verify_source(root, identity):
    if identity.get('dirty_tree') is not False or not identity.get('source_hashes'):
        raise ValueError('Missing clean source identity')
    for name, expected in identity['source_hashes'].items():
        path = (root / name).resolve()
        if not path.is_relative_to(root.resolve()) or sha(path) != expected:
            raise ValueError('Candidate source changed: ' + name)


def child(domain, output):
    sys.path.insert(0, '/app')
    from runtime.analysis_data import CONFIG, adapt, root, source_files
    from runtime.analysis_models import compare, predict
    from runtime.analysis_data import sample
    started = time.monotonic()
    identity = json.loads((output / 'candidate.json').read_text())
    verify_source(Path('/app'), identity)
    receipt = {**identity, 'schema': 'backintel-local-prediction-benchmark/v1',
               'domain': domain, 'mode': 'real', 'comparison_scope': 'local-predictors',
               'analyst_tested': False, 'provider_calls': 0, 'provider_usd': 0,
               'local_compute_usd': None, 'network': 'disabled', 'status': 'blocked'}
    try:
        permission = root() / domain.title() / 'source-receipt.json'
        if not permission.exists() or json.loads(permission.read_text()).get('terms_acknowledged') is not True:
            raise FileNotFoundError('Dataset or source-use confirmation is unavailable')
        paths = source_files(domain)
        snapshot, source, rows = adapt(domain, paths)
        receipt.update(snapshot_id=snapshot, source=source,
                       source_files=[{'file': p.name, 'sha256': sha(p), 'bytes': p.stat().st_size} for p in paths],
                       splits={split: [row['id'] for row in sample(rows, split)] for split in ('train', 'calibration', 'test')})
        manifest = compare(domain, rows, snapshot)
        receipt.update(model_comparison=manifest, methods=manifest['methods'],
                       implementation={'file': 'runtime/analysis_models.py', 'sha256': sha('/app/runtime/analysis_models.py')})
        restored = []
        test = sample(rows, 'test')
        for method in manifest['methods']:
            if 'artifact' not in method:
                continue
            predictions = predict({'body': {**manifest,
                                   'approved_route': method['artifact'].removesuffix('.joblib')}}, test)
            expected = method['predictions']
            if set(predictions) != set(expected) or any(abs(predictions[k] - expected[k]) > 1e-8 for k in expected):
                raise AssertionError('Restored predictor differs from saved test predictions')
            restored.append({'route': method['route'], 'features': method['features']})
        receipt.update(status='passed', model_restore_predictions_verified=True, restored_routes=restored)
    except (FileNotFoundError, ImportError) as error:
        receipt.update(status='blocked', reason=type(error).__name__ + ': ' + str(error))
    except Exception as error:
        receipt.update(status='failed', reason=type(error).__name__ + ': ' + str(error))
    receipt['wall_seconds'] = time.monotonic() - started
    (output / 'receipt.json').write_text(json.dumps(receipt, indent=2, allow_nan=False) + '\n')
    print(json.dumps({k: receipt.get(k) for k in ('domain', 'status', 'reason', 'wall_seconds')}), flush=True)
    return 0 if receipt['status'] == 'passed' else 1


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--checkout', type=Path, default=Path(__file__).resolve().parent.parent)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--datasets', type=Path)
    parser.add_argument('--models', type=Path)
    parser.add_argument('--image')
    parser.add_argument('--domains', nargs='+', choices=['commerce', 'support', 'churn', 'maintenance', 'credit'],
                        default=['commerce', 'support', 'churn', 'maintenance', 'credit'])
    parser.add_argument('--child', choices=['commerce', 'support', 'churn', 'maintenance', 'credit'], help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.child:
        return child(args.child, args.output)
    if not all((args.datasets, args.models, args.image)):
        parser.error('--datasets, --models and --image are required on the host')
    root = args.checkout.resolve()
    identity = candidate(root)
    config = json.loads((root / 'config/analysis.json').read_text())
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    results = []
    for domain in args.domains:
        verify_source(root, identity)
        folder = output / domain
        folder.mkdir()
        (folder / 'candidate.json').write_text(json.dumps(identity, indent=2) + '\n')
        name = 'backintel-predict-' + uuid.uuid4().hex[:12]
        command = ['docker', 'run', '--name', name, '--network', 'none', '--cpus', '2',
                   '--memory', str(config['limits']['worker_bytes']), '--read-only', '--tmpfs', '/tmp:rw,size=256m',
                   '--entrypoint', 'python', '-e', 'PYTHONDONTWRITEBYTECODE=1', '-e', 'HF_HUB_OFFLINE=1',
                   '-e', 'HF_HOME=/tmp/huggingface', '-e', 'OPENROUTER_API_KEY=', '-e', 'OPENAI_API_KEY=',
                   '-e', 'BACKINTEL_DATASET_DIR=/datasets', '-e', 'BACKINTEL_MODEL_DIR=/models',
                   '-e', 'OMP_NUM_THREADS=2', '-e', 'OPENBLAS_NUM_THREADS=2', '-e', 'MKL_NUM_THREADS=2',
                   '-v', str(root) + ':/app:ro', '-v', str(Path(__file__).resolve()) + ':/benchmark.py:ro',
                   '-v', str(args.datasets.resolve()) + ':/datasets:ro', '-v', str(folder) + ':/evidence',
                   '-v', str(folder) + ':/models',
                   '-v', str(args.models.resolve() / 'Weights') + ':/models/Weights:ro',
                   '-v', str(args.models.resolve() / 'Decide') + ':/models/Decide:ro',
                   args.image, '/benchmark.py', '--child', domain, '--output', '/evidence']
        print('Evaluating ' + domain, flush=True)
        failure = None
        try:
            with (folder / 'runtime.log').open('w') as log:
                run = subprocess.run(command, stdout=log, stderr=log,
                                     timeout=config['limits']['model_seconds'] + 60)
            if run.returncode and not (folder / 'receipt.json').exists():
                failure = 'Container exited before a prediction receipt; inspect runtime.log'
        except subprocess.TimeoutExpired:
            failure = 'Prediction exceeded its configured wall-clock limit'
        finally:
            subprocess.run(['docker', 'rm', '--force', name], capture_output=True, timeout=30)
        path = folder / 'receipt.json'
        if failure or not path.exists():
            record = {**identity, 'domain': domain, 'mode': 'real', 'status': 'failed',
                      'reason': failure or 'Missing prediction receipt', 'provider_calls': 0, 'provider_usd': 0}
            path.write_text(json.dumps(record, indent=2) + '\n')
        record = json.loads(path.read_text())
        results.append({'domain': domain, 'status': record['status'], 'receipt': str(path), 'sha256': sha(path)})
        print(json.dumps(results[-1]), flush=True)
    status = 'failed' if any(r['status'] == 'failed' for r in results) else 'blocked' if any(r['status'] == 'blocked' for r in results) else 'passed'
    (output / 'predictions.json').write_text(json.dumps({**identity, 'status': status, 'domains': results,
        'provider_calls': 0, 'provider_usd': 0, 'mode': 'real-local-predictors'}, indent=2) + '\n')
    return 0 if status == 'passed' else 1


if __name__ == '__main__':
    raise SystemExit(main())
