"""Run or collect existing offline checks, then compare equivalent campaign receipts.

No provider invocation lives here. Optional real receipts are read-only inputs.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import re
import runpy
import subprocess
import sys
import time
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[2]
STATUSES = ('passed', 'failed', 'blocked')
DOMAINS = ('commerce', 'support', 'maintenance', 'churn', 'credit')


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()).hexdigest()


def file_hash(path):
    hasher = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            hasher.update(block)
    return hasher.hexdigest()


def read_json(path, default=None):
    try:
        return json.loads(Path(path).read_text())
    except (OSError, ValueError):
        return default


def write_json(path, value):
    Path(path).write_text(json.dumps(value, indent=2, allow_nan=False) + '\n')


def identity(checkout):
    def git(*args):
        return subprocess.check_output(['git', *args], cwd=checkout, text=True).strip()
    files = {name: file_hash(checkout / name) for name in git('ls-files', '-z').split('\0')
             if name and (checkout / name).is_file()}
    return {'commit': git('rev-parse', 'HEAD'), 'dirty': bool(git('status', '--porcelain')), 'verified': True,
            'files': files, 'source_hash': digest(files)}


def identity_error(receipt, candidate):
    """A clean matching SHA alone cannot authenticate a receipt for other source bytes."""
    claimed = receipt.get('candidate', {})
    commit = claimed.get('commit', receipt.get('candidate_commit'))
    dirty = claimed.get('dirty', receipt.get('dirty', receipt.get('dirty_tree')))
    if candidate['dirty'] or dirty is not False:
        return 'Clean source identity is not established'
    if commit != candidate['commit']:
        return 'Receipt commit differs from current candidate'
    files = claimed.get('files', receipt.get('candidate_files'))
    if files is not None and files != candidate['files']:
        return 'Receipt source files differ from current candidate'
    if claimed.get('verified') is False:
        return 'Receipt source identity is explicitly unverified'
    if 'source_hashes' in receipt:
        expected = {name: sha for name, sha in candidate['files'].items()
                    if name.startswith(('runtime/', 'config/', 'migrations/', 'requirements'))}
        if receipt['source_hashes'] != expected:
            return 'Prediction source manifest differs from current candidate'
    return None


def unit_result(spec, directory, identity_ok):
    if not identity_ok:
        return 'blocked', 'Unit run identity is missing, dirty, or mismatched'
    results = read_json(directory / 'results.json', [])
    module = next((row for row in results if row.get('module') == spec['module']), {})
    try:
        log = (directory / (Path(spec['module']).stem + '.log')).read_text()
    except OSError:
        return 'blocked', 'Named unit check log is missing'
    name = re.escape(spec['test'])
    found = re.search(r'^' + name + r' \([^\n]+\) \.\.\. (.+)$', log, re.MULTILINE)
    if not found:
        return 'blocked', 'Named check was not reported'
    outcome = found[1].strip()
    if outcome in ('FAIL', 'ERROR'):
        return 'failed', 'Named check failed'
    if outcome != 'ok' or module.get('tests', 0) < 1:
        return 'blocked', 'Named check skipped or incomplete'
    if module.get('status') != 'passed':
        return 'failed', 'Containing test module did not pass'
    return 'passed', 'Named check passed; provider/model behavior remains simulated'


def scenario_result(spec, domain, browser, offline, identity_ok):
    if not identity_ok:
        return 'blocked', 'Offline receipt identity is missing, dirty, or mismatched'
    source = offline if spec['evidence'] == 'runner' else browser
    if source.get('status') not in ('passed', 'failed', 'blocked'):
        return 'blocked', 'Scenario evidence is missing'
    rows = [row for row in source.get('scenarios', [])
            if row.get('id') == spec['id'] and row.get('domain', 'all') == domain]
    expected_variants = spec.get('variants', [])
    if expected_variants:
        variants = {(row.get('role'), row.get('width')) for row in rows}
        expected = {(row['role'], row['width']) for row in expected_variants}
        complete = len(rows) == len(expected) and variants == expected
    else:
        complete = len(rows) == 1
    if not complete or any(row.get('mode') != 'fixture' for row in rows):
        return 'blocked', 'Expected fixture scenario variants are missing or duplicated'
    if any(row.get('status') not in STATUSES for row in rows):
        return 'blocked', 'Scenario status is invalid'
    status = next((status for status in ('failed', 'blocked') if any(row['status'] == status for row in rows)), 'passed')
    return status, 'Explicit scenario assertions, including every required variant'


def prediction_methods_valid(receipt, domain, native):
    """Check the producer's scored methods and saved-model restoration evidence."""
    methods = receipt.get('methods')
    comparison = receipt.get('model_comparison', {}) if native else receipt
    splits = receipt.get('splits', {})
    if not isinstance(methods, list) or not isinstance(comparison, dict) or not isinstance(splits, dict):
        return False
    if native and (comparison.get('methods') != methods or comparison.get('splits') != splits):
        return False
    if any(not isinstance(splits.get(key), list) or not splits[key]
           or any(not isinstance(identity, str) for identity in splits[key])
           or len(set(splits[key])) != len(splits[key]) for key in ('test', 'calibration')):
        return False
    kind = comparison.get('kind', 'classification' if not native else None)
    if kind != ('regression' if domain in ('support', 'maintenance') else 'classification'):
        return False

    def finite(value):
        return type(value) in (int, float) and math.isfinite(value)

    def scored(value, split):
        if not isinstance(value, dict) or type(value.get('n')) is not int or value['n'] != len(splits[split]):
            return False
        keys = ('mae', 'rmse') if kind == 'regression' else ('brier', 'accuracy')
        if any(not finite(value.get(key)) or value[key] < 0 for key in keys):
            return False
        if kind == 'classification':
            if any(value[key] > 1 for key in keys):
                return False
            positives = value.get('positives')
            if type(positives) is not int or not 0 <= positives <= value['n']:
                return False
            for key, required in (('roc_auc', 0 < positives < value['n']), ('average_precision', positives > 0)):
                metric = value.get(key)
                if metric is None and not required:
                    continue
                if not finite(metric) or not 0 <= metric <= 1:
                    return False
        return True

    artifacts = comparison.get('artifacts')
    if not isinstance(artifacts, list) or any(not isinstance(a, dict) for a in artifacts):
        return False
    saved = {}
    for artifact in artifacts:
        name, sha = artifact.get('file'), artifact.get('sha256')
        if not isinstance(name, str) or name in saved or not isinstance(sha, str) or len(sha) != 64:
            return False
        if any(c not in '0123456789abcdef' for c in sha) or type(artifact.get('bytes')) is not int or artifact['bytes'] <= 0:
            return False
        saved[name] = artifact
    actual, restored = set(), set()
    for method in methods:
        if not isinstance(method, dict):
            return False
        route, features = method.get('route'), method.get('features')
        if not isinstance(route, str) or (features is not None and not isinstance(features, str)):
            return False
        identity = (route, features)
        if identity in actual or not scored(method.get('metrics' if native else 'test_metrics'), 'test') or not scored(method.get('calibration_metrics'), 'calibration'):
            return False
        actual.add(identity)
        if route in ('catboost', 'tabiclv2'):
            artifact = f'{route}-{features}.joblib'
            if artifact not in saved or (native and method.get('artifact') != artifact):
                return False
            predictions = method.get('predictions', {})
            if not native and isinstance(predictions, dict):
                predictions = predictions.get('test')
            if not isinstance(predictions, dict) or set(predictions) != set(splits['test']):
                return False
            if any(not finite(p) or (kind == 'classification' and not 0 <= p <= 1) for p in predictions.values()):
                return False
            restored.add(identity)
    features = ('facts', 'facts-decide') if native and domain in ('commerce', 'support') else ('facts',)
    expected = {(route, feature) for route in (('catboost', 'tabiclv2') if native else ('catboost',)) for feature in features}
    expected.add(('baseline', None if native else 'facts'))
    if native and domain in ('commerce', 'support'):
        expected.add(('simple-text', None))
    if actual != expected:
        return False
    if native:
        routes = receipt.get('restored_routes')
        if not isinstance(routes, list) or any(not isinstance(r, dict) for r in routes):
            return False
        expected_routes = [{'route': route, 'features': feature} for route, feature in sorted(restored)]
        if len(routes) != len(expected_routes) or any(route not in routes for route in expected_routes):
            return False
    return True


def real_result(spec, domain, receipts, candidate, checkout=None):
    matches = [receipt for receipt in receipts if receipt.get('domain') == domain
               or any(row.get('domain') == domain for row in receipt.get('domains', []))]
    if len(matches) != 1:
        return 'blocked', 'Supply one current real receipt for this domain', None
    receipt = matches[0]
    error = identity_error(receipt, candidate)
    if error or receipt.get('mode') != 'real':
        return 'blocked', error or 'Receipt is not real execution', None
    if spec['evidence'] == 'prediction' and receipt.get('status') in ('blocked', 'failed'):
        return receipt['status'], receipt.get('reason', 'Real campaign did not complete'), None
    if spec['evidence'] == 'prediction':
        schemas = ('backintel-partial-local-benchmark/v1', 'backintel-local-prediction-benchmark/v1')
        required = ('source', 'splits', 'implementation')
        native = receipt.get('schema') == schemas[1]
        additional = ('source_files', 'source_hashes', 'harness_sha256', 'model_comparison') if native else ('independent_original_oracle',)
        if receipt.get('schema') not in schemas or not all(receipt.get(key) for key in required + additional):
            return 'blocked', 'Native prediction provenance is incomplete', None
        if receipt.get('model_restore_predictions_verified') is not True or not prediction_methods_valid(receipt, domain, native):
            return 'blocked', 'Comparison or saved prediction reproduction is missing', None
        dependencies = receipt.get('model_comparison', {}).get('dependencies') if native else receipt.get('dependencies')
        if not isinstance(dependencies, dict) or not isinstance(dependencies.get('libraries'), dict) or not dependencies['libraries']:
            return 'blocked', 'Prediction dependency identities are missing', None
        implementation_path = 'runtime/analysis_models.py' if native else 'scripts/analysis_local_benchmark.py'
        if native and receipt['harness_sha256'] != candidate['files'].get('scripts/analysis_prediction_benchmark.py'):
            return 'blocked', 'Prediction harness fingerprint differs from candidate', None
        if receipt['implementation'].get('sha256') != candidate['files'].get(implementation_path):
            return 'blocked', 'Prediction implementation fingerprint differs from candidate', None
        status = receipt.get('status')
        if status not in STATUSES:
            return 'blocked', 'Prediction outcome is missing', None
        detail = {key: receipt.get(key) for key in ('source', 'splits', 'implementation', 'libraries', 'catboost_parameters',
                  'comparison_scope', 'missing_routes', 'source_files', 'harness_sha256', 'wall_seconds', 'peak_rss_bytes', 'provider_usd', 'local_compute_usd')}
        detail['methods'] = [{key: value for key, value in method.items() if key not in ('predictions', 'artifact')}
                             for method in receipt['methods']]
        detail['dependencies'] = dependencies
        return status, 'Native partial real prediction comparison; missing routes remain excluded', detail
    helper_path = Path(checkout or ROOT) / 'scripts/analysis_benchmark_support.py'
    if not helper_path.is_file():
        return 'blocked', 'Current real-analyst receipt validator is unavailable', None
    helper = runpy.run_path(str(helper_path))
    if receipt.get('schema') != helper['SUITE_VERSION'] or not receipt.get('scenario_hash'):
        return 'blocked', 'Current analyst scenario identity receipt missing', None
    config = read_json(Path(checkout or ROOT) / 'config/analysis.json', {})
    sources = config.get('sources', {})
    requested_domains = {row.get('domain') for row in receipt.get('domains', [])}
    if not requested_domains or not requested_domains <= sources.keys():
        return 'blocked', 'Analyst receipt includes unknown domains', None
    specs = [helper['scenario_spec'](key, scenario, sources[key]['group'])
             for key in sorted(requested_domains) for scenario in helper['SCENARIOS']]
    # Preserve receipt domain order: the native producer hashes the ordered list.
    specs.sort(key=lambda s: list(row['domain'] for row in receipt['domains']).index(s['domain']))
    validation_error = helper['receipt_identity_error'](receipt, candidate, specs)
    if validation_error:
        return 'blocked', validation_error, None
    row = next(row for row in receipt['domains'] if row.get('domain') == domain)
    if row.get('status') in ('failed', 'blocked'):
        return row['status'], row.get('reason', 'Real analyst domain did not complete'), None
    if receipt['scenario_hash'] != digest(receipt.get('scenarios', [])):
        return 'blocked', 'Analyst scenario definitions do not match their hash', None
    answers = row.get('answers', [])
    definitions = [s for s in receipt.get('scenarios', []) if s.get('domain') == domain]
    expected = {s['id'] for s in definitions}
    actual = {answer.get('scenario', {}).get('id') if isinstance(answer.get('scenario'), dict)
              else answer.get('scenario') for answer in answers}
    if not expected or actual != expected or len(answers) != len(expected) or not row.get('oracle'):
        return 'blocked', 'Analyst scenario coverage or independent oracle is incomplete', None
    if receipt.get('charge_status') not in ('reconciled', 'settled', 'measured'):
        return 'blocked', 'Analyst charges are not reconciled', None
    try:
        data = runpy.run_path(str(Path(checkout or ROOT) / 'runtime/analysis_data.py'))
        oracle = helper['raw_oracle'](domain, data['source_files'](domain), config['limits']['source_rows'])
        if oracle != row['oracle']:
            raise ValueError('Analyst oracle differs from current original source files')
        snapshot = row.get('snapshot_id')
        if not snapshot:
            raise ValueError('Analyst snapshot identity missing')
        for answer in answers:
            definition = next(item for item in definitions if item['id'] == answer['scenario']['id'])
            run = answer.get('run') or {}
            if not answer.get('run_id') or run.get('id') != answer['run_id']:
                raise ValueError('Analyst run identity missing or inconsistent')
            if not any(charge.get('run_id') == run['id'] for charge in receipt['charges']):
                raise ValueError('Analyst run has no provider charge record')
            helper['score_answer'](run, answer.get('evidence') or {}, definition, oracle, snapshot)
    except (KeyError, TypeError, ValueError, AttributeError, OSError, StopIteration) as error:
        return 'blocked', 'Analyst answer evidence could not be independently verified: '+str(error), None
    status = 'passed'
    return status, 'Real analyst answers with explicit scenario checks', {
        'scenario_hash': receipt['scenario_hash'], 'oracle': row['oracle'], 'provider_usd': receipt.get('provider_usd'),
        'provider_calls': receipt.get('provider_calls')}


def collect(args, candidate=None, stages=None):
    checkout = Path(args.checkout).resolve()
    candidate = candidate or identity(checkout)
    manifest = read_json(checkout / 'config/analysis_scenarios.json')
    output = Path(args.output).resolve()
    units = Path(args.units) if args.units else output / 'units'
    offline_dir = Path(args.offline) if args.offline else output / 'offline'
    offline = read_json(offline_dir / 'receipt.json', {})
    browser = read_json(offline_dir / 'browser-evidence.json', {})
    unit_identity = read_json(units / 'campaign-identity.json', {})
    unit_ok = not identity_error(unit_identity, candidate)
    offline_ok = not identity_error(offline, candidate)
    browser_path = offline_dir / 'browser-evidence.json'
    browser_bound = (browser_path.is_file() and
                     offline.get('artifacts', {}).get('browser-evidence.json') == file_hash(browser_path))
    real = {kind: [read_json(path, {}) for path in getattr(args, kind + '_receipt', [])]
            for kind in ('prediction', 'analyst')}
    stages = stages or read_json(output / 'stages.json', [])
    rows = []
    for spec in manifest['scenarios']:
        for domain in spec.get('domains', ['all']):
            detail = None
            if spec['evidence'] == 'unit':
                status, reason = unit_result(spec, units, unit_ok)
            elif spec['evidence'] == 'stage':
                stage = next((row for row in stages if row.get('id') == spec['stage']), {})
                status = stage.get('status', 'blocked') if unit_ok else 'blocked'
                reason = stage.get('reason', 'Stage was skipped or has no current evidence')
            elif spec['evidence'] in ('browser', 'runner'):
                if spec['evidence'] == 'browser' and not browser_bound:
                    status, reason = 'blocked', 'Browser evidence is missing or differs from the runner artifact hash'
                else:
                    status, reason = scenario_result(spec, domain, browser, offline, offline_ok)
            else:
                status, reason, detail = real_result(spec, domain, real[spec['evidence']], candidate, checkout)
            rows.append({'id': spec['id'], 'domain': domain, 'family': spec['family'], 'mode': spec['mode'],
                         'partition': spec['partition'], 'expected': spec['expected'],
                         'status': status, 'reason': reason, 'measurements': detail})
    families = {}
    for row in rows:
        family = families.setdefault(row['family'], {status: 0 for status in STATUSES})
        family[row['status']] += 1
    harness_paths = ['scripts/validation/check_units.py', 'scripts/validation/run_analysis_offline.py',
                     'scripts/validation/check_analysis_offline_browser.cjs', 'tests/analysis_fixture_runtime.py']
    harness_paths += sorted({f"tests/{s['module']}" for s in manifest['scenarios'] if s['evidence'] == 'unit'})
    harness = {p: file_hash(checkout / p) for p in harness_paths if (checkout / p).is_file()}
    harness['campaign_wrapper'] = file_hash(Path(__file__))
    config = read_json(checkout / 'config/analysis.json', {})
    fixture_files = {str(p.relative_to(offline_dir)): file_hash(p)
                     for p in (offline_dir / 'Datasets').rglob('*') if p.is_file()}
    report = {'schema': 'backintel-benchmark-campaign/v1', 'label': args.label,
              'created_at': datetime.now(timezone.utc).isoformat(), 'candidate': candidate,
              'scenario_version': manifest['version'], 'scenario_hash': digest(manifest),
              'scenario_partition_note': manifest['partition_note'], 'harness_hashes': harness,
              'mode': 'offline fixtures plus separately identified optional real receipts',
              'input_fingerprints': {'fixture_files': fixture_files, 'source_definitions': digest(config.get('sources', {})),
                                     'package_lock': file_hash(checkout / 'apps/web/package-lock.json')},
              'limits': {key: config.get(key) for key in ('limits', 'budget', 'analyst')},
              'families': families, 'scenarios': rows, 'stages': stages,
              'offline_measurements': {key: offline.get(key) for key in ('status', 'reason', 'started_at', 'finished_at',
                  'max_child_peak_rss_bytes', 'resource_boundary', 'dependencies', 'provider_calls', 'new_provider_spend_usd')},
              'real_receipts': {kind: [{'path': str(Path(path).resolve()), 'sha256': file_hash(path) if Path(path).is_file() else None}
                              for path in getattr(args, kind + '_receipt', [])] for kind in real},
              'status': 'failed' if any(r['status'] == 'failed' for r in rows) else
                        'blocked' if any(r['status'] == 'blocked' for r in rows) else 'passed'}
    output.mkdir(parents=True, exist_ok=True)
    write_json(output / 'campaign.json', report)
    return report


def run(args):
    checkout = Path(args.checkout).resolve()
    output = Path(args.output).resolve()
    output.mkdir(parents=True, exist_ok=False)
    before = identity(checkout)
    env = dict(os.environ, BACKINTEL_UNIT_OUTPUT=str(output / 'units'),
               BACKINTEL_ANALYST_CREDENTIAL_FILE=str(output / 'no-provider-credential.json'),
               PYTHONDONTWRITEBYTECODE='1')
    for key in ('OPENROUTER_API_KEY', 'OPENAI_API_KEY', 'ANTHROPIC_API_KEY', 'GEMINI_API_KEY'):
        env[key] = ''
    commands = [('units', [sys.executable, 'scripts/validation/check_units.py']),
                ('frontend-build', ['npm', 'run', 'build', '--prefix', 'apps/web']),
                ('frontend-test', ['npm', 'run', 'test:receipt', '--prefix', 'apps/web'])]
    if not args.skip_browser:
        commands.append(('offline', [sys.executable, 'scripts/validation/run_analysis_offline.py', '--mode', 'e2e',
                         '--output', str(output / 'offline'), '--port', str(args.port), '--broker-recovery']))
    stages = []
    for name, command in commands:
        started = time.monotonic()
        with (output / (name + '.log')).open('w') as log:
            try:
                result = subprocess.run(command, cwd=checkout, env=env, stdout=log, stderr=subprocess.STDOUT, timeout=1800)
                status = 'passed' if result.returncode == 0 else 'failed'
                reason = 'Exit code ' + str(result.returncode)
            except (OSError, subprocess.TimeoutExpired) as error:
                status, reason = 'blocked', type(error).__name__
        stages.append({'id': name, 'status': status, 'reason': reason, 'wall_seconds': time.monotonic() - started})
        write_json(output / 'stages.json', stages)
    after = identity(checkout)
    if before != after:
        before['dirty'] = True
        stages.append({'id': 'source-stability', 'status': 'blocked', 'reason': 'Source changed during campaign'})
    (output / 'units').mkdir(exist_ok=True)
    write_json(output / 'units/campaign-identity.json', {'candidate': before})
    return collect(args, candidate=before, stages=stages)


def compare(baseline, candidate):
    keys = ('schema', 'scenario_hash', 'harness_hashes', 'mode', 'input_fingerprints', 'limits')
    reasons = [key + ' differs or is absent' for key in keys
               if key not in baseline or key not in candidate or baseline[key] != candidate[key]]
    if any(r.get('candidate', {}).get('dirty') is not False for r in (baseline, candidate)):
        reasons.append('One candidate is dirty or lacks clean-source evidence')
    if baseline.get('offline_measurements', {}).get('dependencies') != candidate.get('offline_measurements', {}).get('dependencies'):
        reasons.append('Runtime dependencies differ')
    old = {(row['id'], row['domain']): row for row in baseline.get('scenarios', [])}
    new = {(row['id'], row['domain']): row for row in candidate.get('scenarios', [])}
    if old.keys() != new.keys() or not old:
        reasons.append('Scenario coverage differs or is empty')
    rows = []
    for key in sorted(old.keys() | new.keys()):
        left, right = old.get(key, {}), new.get(key, {})
        local_reasons = list(reasons)
        if left.get('mode') != right.get('mode'):
            local_reasons.append('Execution modes differ')
        if 'blocked' in (left.get('status'), right.get('status')):
            local_reasons.append('A run is blocked')
        if left.get('mode') == 'real':
            measurements = [row.get('measurements') or {} for row in (left, right)]
            if any('methods' in row for row in measurements):
                dependencies = [row.get('dependencies') for row in measurements]
                if any(not isinstance(dep, dict) or not dep.get('libraries') for dep in dependencies):
                    local_reasons.append('Real prediction dependency identities are missing')
                else:
                    identities = [{k: v for k, v in dep.items() if k != 'implementation_sha256'} for dep in dependencies]
                    if identities[0] != identities[1]:
                        local_reasons.append('Real prediction dependencies differ')
        if left.get('mode') == 'real' and left.get('measurements') != right.get('measurements'):
            # Implementation and model parameters are tested variables; data and scoring protocol must match.
            for field in ('source', 'splits', 'scenario_hash', 'oracle', 'source_files', 'harness_sha256'):
                if (left.get('measurements') or {}).get(field) != (right.get('measurements') or {}).get(field):
                    local_reasons.append('Real evidence ' + field + ' differs')
        rows.append({'id': key[0], 'domain': key[1], 'baseline': left.get('status', 'blocked'),
                     'candidate': right.get('status', 'blocked'), 'comparable': not local_reasons,
                     'reasons': local_reasons})
    return {'schema': 'backintel-benchmark-comparison/v1', 'protocol_comparable': not reasons,
            'comparable': not reasons and all(row['comparable'] for row in rows),
            'reasons': reasons, 'scenarios': rows,
            'note': 'Status changes only. No aggregate quality score or speed/accuracy improvement claim.'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    for name in ('run', 'collect'):
        command = commands.add_parser(name)
        command.add_argument('--output', required=True)
        command.add_argument('--label', choices=('baseline', 'candidate'), required=True)
        command.add_argument('--checkout', default=str(ROOT))
        command.add_argument('--units')
        command.add_argument('--offline')
        command.add_argument('--prediction-receipt', action='append', default=[])
        command.add_argument('--analyst-receipt', action='append', default=[])
        if name == 'run':
            command.add_argument('--port', type=int, default=2029)
            command.add_argument('--skip-browser', action='store_true')
    comparison = commands.add_parser('compare')
    comparison.add_argument('baseline')
    comparison.add_argument('candidate')
    comparison.add_argument('--output', required=True)
    args = parser.parse_args()
    if args.command == 'compare':
        report = compare(read_json(args.baseline, {}), read_json(args.candidate, {}))
        write_json(args.output, report)
    else:
        report = run(args) if args.command == 'run' else collect(args)
    print(json.dumps({key: report[key] for key in ('status', 'families', 'comparable', 'reasons') if key in report}))
    if args.command == 'compare':
        return 0 if report.get('comparable') else 2
    return {'passed': 0, 'failed': 1}.get(report.get('status'), 2)


if __name__ == '__main__':
    raise SystemExit(main())
