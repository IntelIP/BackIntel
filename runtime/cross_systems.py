"""Join an accepted retail workflow to explicitly granted local demonstration targets."""
from datetime import date, datetime, timezone
from fractions import Fraction
import json
from typing import Literal
from urllib.parse import urlsplit

import httpx
from pydantic import AwareDatetime, BaseModel, ConfigDict, Field
from psycopg.types.json import Jsonb

from runtime import analysis_store as db, source_workflows
from runtime.analysis_data import digest
from runtime.source_access import require_source_access
from runtime.source_answer import decimal_text


class Input(BaseModel):
    model_config = ConfigDict(extra='forbid')


class CrossSystemInput(Input):
    target_ref: str = Field(min_length=1, max_length=120)
    request_id: str = Field(min_length=1, max_length=240)


class DeliveryInput(Input):
    destination_ref: str = Field(min_length=1, max_length=120)


class CountryTarget(Input):
    country_id: str = Field(min_length=1, max_length=120)
    source_country: str = Field(min_length=1, max_length=120)
    target_fraction: Literal['0.10']


class TargetSnapshot(Input):
    format: Literal['backintel.demo-cancellation-targets/v1']
    demonstration: Literal[True]
    version: str = Field(min_length=1, max_length=120)
    metric: Literal['negative_cancellation_value_over_non_cancellation_value']
    currency: Literal['GBP']
    published_at: AwareDatetime
    effective_from: date
    effective_through: date
    countries: list[CountryTarget] = Field(min_length=1, max_length=250)


def local_url(value):
    parsed = urlsplit(value)
    if (parsed.scheme != 'http' or parsed.hostname != '127.0.0.1' or not parsed.port
            or parsed.username or parsed.password or parsed.path not in ('', '/')
            or parsed.query or parsed.fragment):
        raise PermissionError('This demonstration permits a literal local HTTP service only')
    return value.rstrip('/')


def exchange(base, method, path, payload=None):
    """No redirects, ambient proxy credentials, or unbounded service responses."""
    with httpx.Client(timeout=10, follow_redirects=False, trust_env=False) as client:
        with client.stream(method, local_url(base) + path, json=payload) as response:
            response.raise_for_status()
            content = bytearray()
            for chunk in response.iter_bytes():
                content.extend(chunk)
                if len(content) > 262144:
                    raise ValueError('The local service response exceeds the permitted size')
    return json.loads(content)


def grant(reference, actor, domain, action, connection):
    row = db.query('SELECT * FROM backintel.analysis_service_grants WHERE id=%s FOR SHARE',
                   (reference,), one=True, connection=connection)
    if (not row or not row['enabled'] or row['domain'] != domain or actor['id'] not in row['principals']
            or action not in row['actions'] or row['expires_at'] <= datetime.now(timezone.utc)):
        raise PermissionError('This user lacks the required local service permission: ' + action)
    local_url(row['base_url'])
    return row


def source(run_id, actor, connection, *, read_only=False):
    run = db.run(run_id, connection=connection)
    goal, _, _ = require_source_access(run['goal_id'], actor, connection=connection,
                                       expected_version=run['goal_version'], read_only=read_only)
    if (run['status'] != 'succeeded' or run['body']['operation'] != 'workflow'
            or not run['result'].get('calculation') or run['result']['mode'] != 'real'):
        raise ValueError('Use a completed real retail saved-workflow execution')
    return run, goal


def reconcile(calculation, snapshot):
    """Exact comparisons; country labels are mapped explicitly, never guessed."""
    targets = TargetSnapshot.model_validate(snapshot)
    issues = []
    if targets.published_at > datetime.now(timezone.utc):
        issues.append('Target publication time is in the future')
    first, last = (date.fromisoformat(calculation[key][:10]) for key in ('period_start', 'period_end'))
    if targets.effective_from > first or targets.effective_through < last:
        issues.append('Targets do not cover the complete source calendar-date period')
    if targets.currency != calculation['currency']:
        issues.append('Source and target currency differ; no currency conversion is authorized')
    groups = [d['groups'] for d in calculation['dimensions'] if d['label'] == 'country']
    if len(groups) != 1:
        raise ValueError('The checked result must contain exactly one country dimension')
    groups = groups[0]
    if len({g['value'] for g in groups}) != len(groups):
        issues.append('Source country identities are repeated')
    coverage = calculation['coverage']
    if (sum(g['row_count'] for g in groups) != coverage['expected_rows']
            or coverage['processed_rows'] != coverage['expected_rows']
            or any(coverage[key] for key in ('excluded_rows', 'failed_rows', 'pending_rows'))):
        issues.append('Country groups do not reconcile to complete source coverage')
    for group_key, total_key in (('net_value', 'net_invoice_value'), ('signed_cancellation_value', 'signed_cancellation_value')):
        if sum((Fraction(g[group_key]) for g in groups), Fraction()) != Fraction(calculation['totals'][total_key]):
            issues.append('Country values do not reconcile to ' + total_key)
    mapping, identities = {}, set()
    for target in targets.countries:
        if target.country_id in identities or target.source_country in mapping:
            issues.append('Conflicting target identity: ' + target.source_country)
        identities.add(target.country_id)
        mapping[target.source_country] = target
    unmatched, comparisons = [], []
    for group in groups:
        label = group['value']
        target = mapping.get(label)
        if not target:
            unmatched.append(label)
            continue
        cancelled = -Fraction(group['signed_cancellation_value'])
        denominator = Fraction(group['net_value']) + cancelled
        if denominator <= 0 or cancelled < 0:
            issues.append('The cancellation rate needs review for ' + str(label))
            continue
        rate = cancelled / denominator
        comparisons.append({'country_id': target.country_id, 'source_country': label,
            'source_rows': group['row_count'], 'cancellation_value': decimal_text(cancelled),
            'value_without_cancellations': decimal_text(denominator),
            'rate_ratio': {'numerator': str(rate.numerator), 'denominator': str(rate.denominator)},
            'rate_percent_display': f'{float(rate) * 100:.4f}', 'target_fraction': target.target_fraction,
            'exceeds_target': rate > Fraction(target.target_fraction)})
    if unmatched:
        issues.append('Some source country labels have no explicit target mapping')
    source_labels = {g['value'] for g in groups}
    return {'status': 'blocked' if issues else 'accepted', 'demonstration': True,
            'question': 'Which recorded country categories exceed the 10% demonstration cancellation-value target?',
            'currency': calculation['currency'], 'period_start': calculation['period_start'],
            'period_end': calculation['period_end'], 'source_rows': coverage['expected_rows'],
            'comparisons': comparisons, 'issues': issues, 'unmatched_source': unmatched,
            'unused_targets': [t.source_country for t in targets.countries if t.source_country not in source_labels],
            'reconciliation': {
                'identities': 'Exact service-owned mappings of source country labels; no inferred aliases or geographic normalization.',
                'units': 'Negative signed C-prefix cancellation value / signed non-cancellation invoice value, both GBP. Exact fractions decide; percentages are display only.',
                'time': 'Targets cover the entire historical source calendar period. Collection, target publication, and retrieval times are separate; source timezone is unknown.'},
            'limitations': ['All targets and target identities are demonstration data, not business policy.',
                'Country values are recorded categories, including Unspecified and European Community; they are not verified geographic identities.',
                'Historical invoice-line values are not audited revenue. No currency conversion or business-record write-back.',
                'The saved analysis method is reused. This comparison makes no new model request.']}


def assess(run_id, actor, policy):
    from runtime.source_coordination import independent_check
    policy = CrossSystemInput.model_validate(policy)
    identity = digest(['cross-system/v1', run_id, policy.target_ref, policy.request_id])
    with db.connect() as connection, connection.transaction():
        run, goal = source(run_id, actor, connection)
        access = grant(policy.target_ref, actor, goal['domain'], 'read_targets', connection)
        prior = db.query('SELECT body FROM backintel.analysis_cross_findings WHERE id=%s',
                         (identity,), one=True, connection=connection)
        if prior:
            return {'id': identity, **prior['body']}
        retrieved_at = None
        try:
            snapshot = exchange(access['base_url'], 'GET', '/targets')
            retrieved_at = datetime.now(timezone.utc).isoformat()
        except (httpx.HTTPError, ValueError):
            snapshot = None
    result = run['result']
    calculation = result['calculation']
    collection_run = db.run(result['input_ref'])
    collection = collection_run['result']
    package = source_workflows.read(result['workflow_version'], actor)
    key = 'cross-source-check-' + digest(calculation)
    checked = db.step(run_id, key)
    if checked is None:
        checked = independent_check(run_id, calculation, collection, {'interpretation': package['body']['interpretation']})
        db.save_step(run_id, key, 'cross_source_check', checked)
    if (checked['status'] != 'passed' or checked['calculation_version'] != digest(calculation)
            or checked['source_version'] != digest(collection)):
        raise ValueError('The independent source reconciliation does not match this result')
    if snapshot is None:
        body = {'status': 'blocked', 'demonstration': True, 'issues': ['The permitted target service is unavailable or returned invalid JSON']}
    else:
        try:
            body = reconcile(calculation, snapshot)
        except ValueError:
            body = {'status': 'blocked', 'demonstration': True, 'issues': ['The target service response does not satisfy the agreed target contract']}
    body.update(run_id=run_id, goal_id=goal['id'], goal_version=run['goal_version'],
                target_ref=policy.target_ref, request_id=policy.request_id,
                source_evidence={'source_ref': calculation['source_ref'], 'collection_run_id': collection_run['id'],
                    'collection_sha256': digest(collection), 'collected_at': collection['observed_at'],
                    'calculation_sha256': digest(calculation), 'independent_check': checked,
                    'answer_evidence_id': result['evidence_id'], 'workflow_version': result['workflow_version']},
                target_evidence={'snapshot': snapshot, 'sha256': digest(snapshot),
                    'retrieved_at': retrieved_at})
    with db.connect() as connection, connection.transaction():
        _, current = source(run_id, actor, connection)
        grant(policy.target_ref, actor, current['domain'], 'read_targets', connection)
        db.write('''INSERT INTO backintel.analysis_cross_findings(id,run_id,target_ref,body)
            VALUES(%s,%s,%s,%s) ON CONFLICT(id) DO NOTHING''',
            (identity, run_id, policy.target_ref, Jsonb(body)), connection=connection)
        return {'id': identity, **db.query('SELECT body FROM backintel.analysis_cross_findings WHERE id=%s',
                                         (identity,), one=True, connection=connection)['body']}


def read(identity, actor, *, connection=None, read_only=True):
    if connection is None:
        with db.connect() as control, control.transaction():
            return read(identity, actor, connection=control, read_only=read_only)
    row = db.query('SELECT * FROM backintel.analysis_cross_findings WHERE id=%s',
                   (identity,), one=True, connection=connection)
    if not row:
        raise ValueError('Unknown cross-system finding')
    _, goal = source(row['run_id'], actor, connection, read_only=read_only)
    grant(row['target_ref'], actor, goal['domain'], 'read_targets', connection)
    return {'id': identity, **row['body']}


def deliver(identity, actor, destination_ref):
    destination_ref = DeliveryInput(destination_ref=destination_ref).destination_ref
    delivery_id = digest(['finding-delivery/v1', identity, destination_ref])
    with db.connect() as connection, connection.transaction():
        finding = read(identity, actor, connection=connection, read_only=False)
        goal = db.goal(finding['goal_id'], connection=connection)
        grant(destination_ref, actor, goal['domain'], 'deliver_findings', connection)
        if finding['status'] != 'accepted':
            raise ValueError('A blocked finding cannot be delivered')
        db.write('''INSERT INTO backintel.analysis_finding_deliveries(id,finding_id,destination_ref)
            VALUES(%s,%s,%s) ON CONFLICT(id) DO NOTHING''',
            (delivery_id, identity, destination_ref), connection=connection)
    # Commit the stable delivery identity before contact. The receiver must honor
    # that same identity after an interrupted acknowledgement or sender restart.
    with db.connect() as connection, connection.transaction():
        finding = read(identity, actor, connection=connection, read_only=False)
        goal = db.goal(finding['goal_id'], connection=connection)
        access = grant(destination_ref, actor, goal['domain'], 'deliver_findings', connection)
        row = db.query('SELECT * FROM backintel.analysis_finding_deliveries WHERE id=%s FOR UPDATE',
                       (delivery_id,), one=True, connection=connection)
        if row['receipt']:
            return {'delivery_id': delivery_id, 'status': 'confirmed', 'receipt': row['receipt'], 'replayed': True}
        payload = {'delivery_id': delivery_id, 'result_id': identity, 'result_sha256': digest(finding), 'finding': finding}
        try:
            received = exchange(access['base_url'], 'POST', '/deliveries', payload)
            verified = exchange(access['base_url'], 'GET', '/deliveries/' + delivery_id)
            expected = {key: payload[key] for key in ('delivery_id', 'result_id', 'result_sha256')}
            if (not isinstance(verified, dict) or received != verified or verified.get('status') != 'accepted'
                    or not verified.get('receipt_id') or any(verified.get(k) != v for k, v in expected.items())):
                raise ValueError('The destination receipt does not confirm this exact finding')
        except (httpx.HTTPError, ValueError):
            return {'delivery_id': delivery_id, 'status': 'pending',
                    'message': 'Receipt is unconfirmed. Retry this same finding and destination; do not create a replacement delivery.'}
        grant(destination_ref, actor, goal['domain'], 'deliver_findings', connection)
        db.write('UPDATE backintel.analysis_finding_deliveries SET receipt=%s WHERE id=%s',
                 (Jsonb(verified), delivery_id), connection=connection)
        return {'delivery_id': delivery_id, 'status': 'confirmed', 'receipt': verified, 'replayed': False}
