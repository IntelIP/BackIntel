"""Five domain adapters. Originals stay outside Git; targets never enter features."""
from __future__ import annotations

import csv
import hashlib
import heapq
import json
import math
import os
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

CONFIG = json.loads((Path(__file__).resolve().parents[1] / 'config/analysis.json').read_text())


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()).hexdigest()


def root():
    return Path(os.getenv('BACKINTEL_DATASET_DIR', str(Path.home() / 'Library/Application Support/BackIntel/Datasets'))).resolve()


def source_files(domain):
    spec = CONFIG['sources'][domain]
    directory = root() / domain.title()
    paths = [directory / name for name in spec['files']]
    for p in paths:
        if not p.resolve().is_relative_to(root()) or not p.is_file():
            raise ValueError(f'Missing approved source file: {domain}/{p.name}')
    return paths


def fingerprint(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1048576), b''):
            h.update(block)
    return {'file': path.name, 'sha256': h.hexdigest(), 'bytes': path.stat().st_size}


def number(value):
    if isinstance(value, str):
        value = value.strip()
    if value in (None, '', 'NA', 'NaN', 'nan'):
        return None
    n = float(value)
    return n if math.isfinite(n) else None


def timestamp(value):
    if not value:
        return None
    parsed = datetime.fromisoformat(value.replace('Z', '+00:00'))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return int(parsed.timestamp())


def csv_rows(path):
    with path.open(encoding='utf-8-sig', newline='') as stream:
        yield from csv.DictReader(stream)


def record(identity, features, target, groups, text='', entity=None, event_at=None, label_at=None):
    return {'id': str(identity), 'entity': str(entity or identity), 'features': features,
            'target': target, 'groups': groups, 'text': text[:12000], 'event_at': event_at,
            'label_at': label_at, 'split': None}


GROUP_FEATURES = {
    'commerce': {'department': 'department', 'class': 'class'},
    'support': {'sla_plan': 'sla_plan', 'channel': 'channel'},
    'churn': {'contract': 'Contract', 'internet_service': 'InternetService'},
    'credit': {'income_type': 'NAME_INCOME_TYPE', 'contract_type': 'NAME_CONTRACT_TYPE'},
    'maintenance': {},  # Engine identity is not a mutable feature.
}


def feature_groups(domain, features):
    return {group: features.get(feature, '') for group, feature in GROUP_FEATURES[domain].items()}


def commerce(paths):
    for i, r in enumerate(csv_rows(paths[0])):
        features = {'age': number(r.get('Age')), 'department': r.get('Department Name', ''),
                    'class': r.get('Class Name', ''), 'division': r.get('Division Name', '')}
        # Rating/feedback counts and recommendation are excluded from predictive inputs.
        yield record(r.get('Unnamed: 0', i), features, number(r.get('Recommended IND')),
                     feature_groups('commerce', features),
                     r.get('Review Text', ''))


def support(paths):
    for r in csv_rows(paths[0]):
        created = timestamp(r.get('created_at'))
        duration = number(r.get('resolution_time_hours'))
        features = {k: r.get(k, '') for k in ('customer_segment', 'channel', 'product_area', 'language', 'sla_plan')}
        # Pre-triage scenario: no priority, sentiment, replies, CSAT, reopened or final status.
        yield record(r['ticket_id'], features, duration,
                     feature_groups('support', features),
                     r.get('initial_message', ''), r.get('customer_id'), created,
                     created + int(duration * 3600) if created is not None and duration is not None else None)


def churn(paths):
    numeric = ('tenure', 'MonthlyCharges', 'TotalCharges', 'SeniorCitizen')
    for r in csv_rows(paths[0]):
        outcome = r['Churn'].strip()
        if outcome not in ('Yes', 'No'):
            raise ValueError('Telco Churn requires Yes or No outcomes')
        features = {k: number(v) if k in numeric else v for k, v in r.items() if k not in ('customerID', 'Churn')}
        yield record(r['customerID'], features, float(outcome == 'Yes'),
                     feature_groups('churn', features))


def credit(paths):
    # Deterministic bounded applicant cohort; histories are streamed at their own grain.
    applicants = {}
    for r in csv_rows(paths[0]):
        identity = r['SK_ID_CURR']
        if int(digest(identity)[:8], 16) % 31 == 0:
            applicants[identity] = r
            if len(applicants) >= CONFIG['limits']['source_rows']:
                break
    histories = defaultdict(lambda: {'bureau_count': 0, 'bureau_credit_sum': 0., 'bureau_debt_sum': 0., 'bureau_active': 0})
    for r in csv_rows(paths[1]):
        identity = r['SK_ID_CURR']
        days = number(r.get('DAYS_CREDIT'))
        update = number(r.get('DAYS_CREDIT_UPDATE'))
        if identity not in applicants or days is None or days > 0 or (update is not None and update > 0):
            continue
        h = histories[identity]
        h['bureau_count'] += 1
        h['bureau_credit_sum'] += number(r.get('AMT_CREDIT_SUM')) or 0
        h['bureau_debt_sum'] += number(r.get('AMT_CREDIT_SUM_DEBT')) or 0
        h['bureau_active'] += int(r.get('CREDIT_ACTIVE') == 'Active')
    categorical = ('NAME_INCOME_TYPE', 'NAME_EDUCATION_TYPE', 'NAME_FAMILY_STATUS', 'NAME_HOUSING_TYPE', 'NAME_CONTRACT_TYPE')
    numeric = ('AMT_INCOME_TOTAL', 'AMT_CREDIT', 'AMT_ANNUITY', 'CNT_CHILDREN', 'CNT_FAM_MEMBERS', 'DAYS_BIRTH', 'DAYS_EMPLOYED', 'EXT_SOURCE_1', 'EXT_SOURCE_2', 'EXT_SOURCE_3')
    for identity, r in applicants.items():
        f = {k: r.get(k, '') for k in categorical}
        f.update({k: number(r.get(k)) for k in numeric})
        f.update(histories[identity])
        yield record(identity, f, number(r.get('TARGET')),
                     feature_groups('credit', f))


def engines(path):
    with path.open() as stream:
        for line in stream:
            values = [float(v) for v in line.split()]
            if len(values) != 26:
                raise ValueError('FD001 requires engine, cycle, three settings and 21 sensors')
            yield values


def maintenance(paths):
    train = list(engines(paths[0]))
    life = defaultdict(int)
    for v in train:
        life[int(v[0])] = max(life[int(v[0])], int(v[1]))
    for v in train:
        engine, cycle = int(v[0]), int(v[1])
        f = {f'setting_{i+1}': v[i+2] for i in range(3)}
        f.update({f'sensor_{i+1}': v[i+5] for i in range(21)})
        f['cycle'] = cycle
        r = record(f'train-{engine}-{cycle}', f, float(life[engine]-cycle), {'engine': f'train-{engine}'}, entity=f'train-{engine}')
        r['split'] = 'calibration' if engine % 5 == 0 else 'train'
        yield r
    last = {}
    for v in engines(paths[1]):
        last[int(v[0])] = v
    outcomes = [float(v.strip()) for v in paths[2].read_text().splitlines() if v.strip()]
    if len(outcomes) != len(last):
        raise ValueError('Official test engines and RUL labels do not align')
    for engine, v in sorted(last.items()):
        f = {f'setting_{i+1}': v[i+2] for i in range(3)}
        f.update({f'sensor_{i+1}': v[i+5] for i in range(21)})
        f['cycle'] = v[1]
        r = record(f'test-{engine}', f, outcomes[engine-1], {'engine': f'test-{engine}'}, entity=f'test-{engine}')
        r['split'] = 'test'
        yield r


ADAPTERS = {'commerce': commerce, 'support': support, 'churn': churn, 'credit': credit, 'maintenance': maintenance}


def adapter_identity(domain):
    return {'adapter': fingerprint(Path(__file__))['sha256'],
            'config_sha256': digest({'source': CONFIG['sources'][domain], 'limits': CONFIG['limits']})}


def adapt(domain, paths=None):
    paths = paths or source_files(domain)
    source_identity = [fingerprint(p) for p in paths]
    rows = []
    cohort = []
    identities = set()
    total_rows=0
    for r in ADAPTERS[domain](paths):
        if r['id'] in identities:
            raise ValueError('Duplicate source record identity')
        identities.add(r['id'])
        total_rows+=1
        if CONFIG['sources'][domain]['kind']=='classification' and r['target'] not in (None,0,1):
            raise ValueError('Invalid binary source outcome')
        if domain in ('credit','maintenance'):
            rows.append(r)
        else:
            heapq.heappush(cohort,(-int(digest(r['id']),16),total_rows,r))
            if len(cohort)>CONFIG['limits']['source_rows']:
                heapq.heappop(cohort)
    if cohort:
        rows=[item[2] for item in sorted(cohort,key=lambda item:-item[0])]
    if not rows:
        raise ValueError('Source contains no usable records')
    cutoffs = None
    if domain == 'support':
        ordered = sorted(r['event_at'] for r in rows if r['event_at'] is not None)
        if len(ordered) != len(rows):
            raise ValueError('Support requires valid creation timestamps')
        cutoffs = (ordered[int(len(ordered)*.7)], ordered[int(len(ordered)*.85)])
    for r in rows:
        if r['split'] is not None:
            continue
        if cutoffs:
            phase = 'train' if r['event_at'] < cutoffs[0] else 'calibration' if r['event_at'] < cutoffs[1] else 'test'
            bucket = int(digest(r['entity'])[:8],16)%100
            entity_split = 'train' if bucket<70 else 'calibration' if bucket<85 else 'test'
            r['split'] = phase if phase==entity_split else 'operational'
            bound = cutoffs[0] if r['split'] == 'train' else cutoffs[1]
            if r['split'] in ('train','calibration') and (r['label_at'] is None or r['label_at'] > bound):
                r['split'] = 'unlabeled'
        else:
            bucket = int(digest(r['entity'])[:8], 16) % 100
            r['split'] = 'train' if bucket < 70 else 'calibration' if bucket < 85 else 'test'
    if source_identity != [fingerprint(p) for p in paths]:
        raise ValueError('Source changed during adaptation; retry the import')
    body = {'domain': domain, 'files': source_identity, **adapter_identity(domain),
            'rows': len(rows), 'total_rows':total_rows, 'cohort_policy':'bounded fixed identity hash', 'split_policy': 'engine-official' if domain == 'maintenance' else 'chronological-label-availability' if cutoffs else 'fixed-entity-hash',
            'cutoffs': cutoffs, 'caveat': CONFIG['sources'][domain]['caveat'],
            'record_hash': digest(rows)}
    return digest(body), body, rows


def sample(rows, split):
    limit = CONFIG['limits'][split]
    return sorted((r for r in rows if r['split'] == split and r['target'] is not None), key=lambda r: digest(r['id']))[:limit]
