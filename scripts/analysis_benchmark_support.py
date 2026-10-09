"""Independent benchmark oracles, fixed questions and fail-closed receipt identity."""
from __future__ import annotations

import csv
import hashlib
import json
import math
import re
import subprocess
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SUITE_VERSION = 'backintel-answers/v3'
SCENARIOS = (
    {'id': 'record_count', 'partition': 'development'},
    {'id': 'observed_mean', 'partition': 'development'},
    {'id': 'lowest_group', 'partition': 'development'},
    {'id': 'highest_group', 'partition': 'held_out'},
)
TARGETS = {'commerce':'recommendation', 'support':'resolution_hours', 'churn':'churn',
           'credit':'default', 'maintenance':'remaining_cycles'}
UNITS = {'commerce': 'fraction', 'churn': 'fraction', 'credit': 'fraction',
         'support': 'hours', 'maintenance': 'cycles'}


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()).hexdigest()


def fingerprint(path):
    path = Path(path)
    sha = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1048576), b''):
            sha.update(block)
    return {'file': path.name, 'sha256': sha.hexdigest(), 'bytes': path.stat().st_size}


def candidate_identity(root=ROOT, manifest=None):
    """Hash actual files, including untracked source. Never trust an injected SHA alone."""
    root = Path(root)
    runtime_dirs = ('runtime', 'scripts', 'config', 'migrations')
    def runtime_files():
        return {str(path.relative_to(root)): fingerprint(path)['sha256']
                for directory in runtime_dirs for path in (root / directory).rglob('*')
                if path.is_file() and '__pycache__' not in path.parts and path.suffix not in ('.pyc', '.pyo')}
    if manifest is not None:
        try:
            supplied = json.loads(Path(manifest).read_text())
            if supplied.get('dirty') is not False or supplied.get('verified') is not True or not supplied.get('commit'):
                raise ValueError('Supplied host identity is dirty or unverified')
            if supplied.get('source_hash') != digest(supplied['files']):
                raise ValueError('Supplied host file manifest hash differs')
            expected = {name: sha for name, sha in supplied['files'].items() if name.split('/')[0] in runtime_dirs}
            required = {'runtime/analysis_agent.py', 'runtime/analysis_data.py', 'runtime/analysis_store.py',
                        'runtime/analysis_service.py', 'scripts/analysis_benchmark.py',
                        'scripts/analysis_benchmark_support.py', 'config/analysis.json'}
            if not required.issubset(expected) or not any(name.startswith('migrations/') for name in expected):
                raise ValueError('Supplied host runtime file manifest is incomplete')
            actual = runtime_files()
            if actual != expected:
                raise ValueError('Runtime file set or bytes differ from supplied host manifest')
            return {**supplied, 'runtime_files': actual, 'host_manifest': fingerprint(manifest),
                    'identity_basis': 'Host Git identity supplied; complete runtime file set and bytes verified locally; container Git not independently verified'}
        except (OSError, KeyError, TypeError, ValueError) as error:
            return {'commit': None, 'dirty': True, 'verified': False, 'reason': str(error)}
    try:
        def git(*args):
            return subprocess.check_output(['git', *args], cwd=root, text=True, stderr=subprocess.DEVNULL).strip()
        commit = git('rev-parse', 'HEAD')
        dirty = bool(git('status', '--porcelain'))
        names = git('ls-files', '--cached', '--others', '--exclude-standard', '-z').split('\0')
        files = {name: fingerprint(root / name)['sha256'] if (root / name).is_file() else None
                 for name in sorted(set(names)) if name}
        actual = runtime_files()
        dirty = dirty or bool(set(actual) - set(files))
        files.update(actual)
        return {'commit': commit, 'dirty': dirty, 'verified': True, 'files': files, 'source_hash': digest(files)}
    except (OSError, subprocess.CalledProcessError) as error:
        return {'commit': None, 'dirty': True, 'verified': False, 'reason': type(error).__name__}


def scenario_spec(domain, scenario, group):
    """Freeze exact prompts before execution. Means use original units, never percent."""
    key = scenario['id']
    target = {'record_count': 'Use inspect_source. Report the snapshot record count.',
              'observed_mean': 'Use summarize without grouping. Report the observed target mean.',
              'lowest_group': f'Use summarize grouped by {group}, ascending. Report the group with the lowest observed mean.',
              'highest_group': f'Use summarize grouped by {group}, descending. Report the group with the highest observed mean.'}[key]
    unit = 'records' if key == 'record_count' else UNITS[domain]
    form = ('Source contains <number> records.' if key == 'record_count' else
            'The mean is <number>.' if key == 'observed_mean' else 'Group <group label> mean is <number>.')
    prompt = (target + ' Break equal means by ascending group label. Use original units, not percentages. '
              'Keep the normal outer answer schema. Return exactly one fact finding using this claim form: '
              + form + ' Replace placeholders with the calculated number and exact group label. '
              'Use that claim as the summary and cite its calculation evidence, including the record count. '
              'State limitations in the limitations list. If the calculation is unavailable, state that limitation instead of inventing values.')
    spec = {**scenario, 'domain': domain, 'group_field': group, 'unit': unit, 'prompt': prompt,
            'target': TARGETS[domain], 'tolerance': 1e-9, 'tie_policy': 'ascending group label', 'suite_version': SUITE_VERSION}
    return {**spec, 'sha256': digest(spec)}


def raw_oracle(domain, paths, limit):
    """Read labels/groups directly, never calling production adapters or aggregation."""
    paths = [Path(path) for path in paths]
    def csv_records(path):
        with path.open(encoding='utf-8-sig', newline='') as stream:
            yield from csv.DictReader(stream)
    def number(value):
        if value is None or str(value).strip() in ('', 'NA', 'NaN', 'nan'):
            return None
        parsed = float(value)
        return parsed if math.isfinite(parsed) else None
    rows = []
    if domain == 'maintenance':
        train = [line.split() for line in paths[0].read_text().splitlines() if line.strip()]
        test = [line.split() for line in paths[1].read_text().splitlines() if line.strip()]
        if any(len(row) != 26 for row in train + test):
            raise ValueError('Invalid FD001 row width')
        maxima = defaultdict(int)
        for row in train:
            maxima[int(row[0])] = max(maxima[int(row[0])], int(row[1]))
        rows = [(f'train-{int(row[0])}-{int(row[1])}', float(maxima[int(row[0])] - int(row[1])), f'train-{int(row[0])}') for row in train]
        labels = [float(value) for value in paths[2].read_text().split()]
        engines = sorted({int(row[0]) for row in test})
        if engines != list(range(1, len(labels) + 1)):
            raise ValueError('Official FD001 labels do not align with test engines')
        rows.extend((f'test-{engine}', labels[engine-1], f'test-{engine}') for engine in engines)
    else:
        mapping = {'commerce': ('Unnamed: 0', 'Recommended IND', 'Department Name'),
                   'support': ('ticket_id', 'resolution_time_hours', 'sla_plan'),
                   'churn': ('customerID', 'Churn', 'Contract'),
                   'credit': ('SK_ID_CURR', 'TARGET', 'NAME_INCOME_TYPE')}
        identity_key, target_key, group_key = mapping[domain]
        for index, record in enumerate(csv_records(paths[0])):
            identity = str(record.get(identity_key, index))
            if domain == 'credit' and int(digest(identity)[:8], 16) % 31:
                continue
            value = record.get(target_key)
            if domain == 'churn':
                if str(value).strip() not in ('Yes', 'No'):
                    raise ValueError('Invalid original churn label')
                value = float(str(value).strip() == 'Yes')
            else:
                value = number(value)
            if domain in ('commerce', 'credit') and value not in (None, 0, 1):
                raise ValueError('Invalid original binary label')
            rows.append((identity, value, record.get(group_key, '')))
    if len({row[0] for row in rows}) != len(rows):
        raise ValueError('Duplicate original record identity')
    if domain != 'maintenance':
        rows = sorted(rows, key=lambda row: digest(row[0]))[:limit]
    if not rows:
        raise ValueError('Original cohort has no records')
    groups = defaultdict(list)
    for _, value, group in rows:
        groups[str(group)].append(value)
    def stats(values):
        labeled = [value for value in values if value is not None]
        return {'count': len(values), 'labeled': len(labeled), 'mean': math.fsum(labeled) / len(labeled) if labeled else None}
    overall = stats([row[1] for row in rows])
    return {'domain': domain, 'files': [fingerprint(path) for path in paths], 'records': len(rows),
            'cohort_hash': digest(sorted(rows)), 'cohort_ids': sorted(row[0] for row in rows),
            'overall': overall, 'groups': {group: stats(values) for group, values in sorted(groups.items())}}


def expected_result(spec, oracle):
    key = spec['id']
    group = 'all'
    stats = oracle['overall']
    if key in ('lowest_group', 'highest_group'):
        available = [(name, value) for name, value in oracle['groups'].items() if value['mean'] is not None]
        if not available:
            raise ValueError('Original cohort has no labeled groups')
        group, stats = min(available, key=lambda pair: ((-1 if key == 'highest_group' else 1) * pair[1]['mean'], pair[0]))
    value = oracle['records'] if key == 'record_count' else stats['mean']
    if value is None:
        raise ValueError('Original cohort has no labeled values')
    return {'metric': key, 'group': group, 'value': value, 'count': stats['count'], 'unit': spec['unit']}


def score_answer(run, evidence, spec, oracle, snapshot, mode='real'):
    """An exact structured answer and its cited calculation must both match raw input."""
    answer = run.get('result') or {}
    expected = expected_result(spec, oracle)
    if run.get('status') != 'succeeded' or run.get('snapshot_id') != snapshot:
        raise ValueError('Answer status or snapshot differs from the benchmark')
    if answer.get('mode') != mode or answer.get('sources') != {'snapshot': snapshot, 'domain': spec['domain']}:
        raise ValueError('Answer execution mode or source identity differs')
    number = r'(?P<value>-?(?:\d+(?:\.\d+)?|\.\d+)(?:[eE][+-]?\d+)?)'
    pattern = (r'Source contains ' + number + r' records\.' if spec['id'] == 'record_count' else
               r'The mean is ' + number + r'\.' if spec['id'] == 'observed_mean' else
               r'Group ' + re.escape(expected['group']) + r' mean is ' + number + r'\.')
    summary = answer.get('summary')
    match = re.fullmatch(pattern, summary) if isinstance(summary, str) else None
    if not match:
        raise ValueError('Answer summary is not the required structured metric claim')
    value = float(match['value'])
    if not math.isfinite(value) or not math.isclose(value, expected['value'], rel_tol=0, abs_tol=spec['tolerance']):
        raise ValueError('Answer measurement disagrees with original data')
    # Group, unit and count are independently checked against the cited calculation below.
    actual = {**expected, 'value': value}
    findings = answer.get('findings', [])
    if len(findings) != 1 or findings[0].get('kind') != 'fact':
        raise ValueError('Benchmark requires one supported fact')
    same_claim = findings[0].get('claim') == summary
    if not same_claim or not findings[0].get('evidence_ids'):
        raise ValueError('Finding does not state and cite the structured answer')
    supported = False
    for identity in findings[0]['evidence_ids']:
        record = evidence.get(identity) or {}
        body = record.get('body', {})
        if record.get('kind') != 'calculation' or record.get('task_id') != 'analysis-goal-' + run['goal_id'] or body.get('snapshot') != snapshot:
            raise ValueError('Calculation has the wrong snapshot or goal')
        result = body.get('result', {})
        args = body.get('arguments', {})
        if spec['id'] == 'record_count':
            supported |= body.get('tool') == 'inspect_source' and result.get('records') == expected['value']
        elif body.get('tool') == 'summarize' and result.get('kind') == 'observed' and result.get('target') == spec['target']:
            desired_group = spec['group_field'] if spec['id'].endswith('_group') else None
            if args.get('group') != desired_group:
                continue
            expected_order = 'descending' if spec['id'] == 'highest_group' else 'ascending'
            if args.get('order', 'ascending') != expected_order:
                continue
            table = result.get('table', [])
            row = table[0] if table else {}
            supported |= (row.get('group') == expected['group'] and row.get('count') == expected['count']
                          and isinstance(row.get('mean'), (int, float))
                          and math.isclose(row['mean'], expected['value'], rel_tol=0, abs_tol=spec['tolerance']))
    if not supported:
        raise ValueError('Cited calculation does not support the requested result')
    return {'correct': True, 'expected': expected, 'actual': actual,
            'evidence_ids': findings[0]['evidence_ids'], 'scenario': spec}


def receipt_identity_error(receipt, candidate, specs):
    """Old, dirty or incompatible evidence cannot qualify as current acceptance."""
    if not candidate.get('verified') or candidate.get('dirty'):
        return 'Current code identity is unverified or dirty'
    prior = receipt.get('candidate', {})
    if prior.get('dirty') or not prior.get('verified') or any(prior.get(key) != candidate.get(key) for key in ('commit', 'source_hash')):
        return 'Receipt belongs to different, dirty or unverified code'
    if receipt.get('schema') != SUITE_VERSION or receipt.get('mode') != 'real':
        return 'Receipt is not a current real benchmark'
    if receipt.get('scenario_hash') != digest(specs):
        return 'Receipt uses different scenarios'
    if receipt.get('identity_error'):
        return 'Candidate changed during benchmark execution'
    if receipt.get('charge_status') != 'measured':
        return 'Required provider cost telemetry is missing'
    charges = receipt.get('charges')
    if not isinstance(charges, list):
        return 'Provider charge ledger is missing'
    try:
        amounts = [float(item['charge']) for item in charges]
        if any(not math.isfinite(amount) or amount < 0 for amount in amounts):
            return 'Provider charge ledger contains invalid costs'
        if receipt.get('provider_calls') != len(charges) or not math.isclose(float(receipt['provider_usd']), math.fsum(amounts), rel_tol=0, abs_tol=1e-9):
            return 'Provider totals differ from the charge ledger'
    except (KeyError, TypeError, ValueError):
        return 'Provider charge ledger contains missing costs'
    return None
