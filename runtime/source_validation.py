"""Independently check prepared values against immutable source responses."""
from datetime import datetime
from decimal import Decimal, InvalidOperation
import time

from runtime import analysis_store as db
from runtime.analysis_data import digest
from runtime.source_inputs import _row_key, parse_response, retained_input
from runtime.source_preparation import prepared_page


def same_meaning(actual, original, field):
    expected = str(original) if isinstance(original, Decimal) else original
    if original is None or original == '' or isinstance(original, str) and not original.strip():
        return type(actual) is type(expected) and actual == expected
    if field['confidence'] != 'supported' or field['role'] not in ('quantity', 'unit_price', 'measure', 'date'):
        return type(actual) is type(expected) and actual == expected
    try:
        if field['role'] != 'date':
            if not isinstance(actual, str) or isinstance(original, bool):
                return False
            left, right = Decimal(actual), Decimal(str(original))
            return left.is_finite() and right.is_finite() and left == right
        if not field['date_format']:
            return type(actual) is type(expected) and actual == expected
        if not isinstance(actual, str):
            return False
        converted = datetime.fromisoformat(actual)
        if field['date_format'] == 'iso':
            source = datetime.fromisoformat(str(original))
        else:
            order = '%m/%d/%Y' if field['date_format'] == 'month_first' else '%d/%m/%Y'
            source = None
            for suffix in ('', ' %H:%M', ' %H:%M:%S', 'T%H:%M', 'T%H:%M:%S'):
                try:
                    source = datetime.strptime(str(original), order + suffix)
                    break
                except ValueError:
                    continue
            if source is None:
                return False
        return converted.isoformat() == source.isoformat()
    except (ValueError, TypeError, InvalidOperation, OverflowError):
        return False


def compare_page(page, original, meanings, declared_units, seen):
    """Return grouped failures with source references, never source values."""
    failures = {}
    def fail(reason, row='all', field=None):
        key = (reason, field)
        group = failures.setdefault(key, {'reason':reason,'raw_input_id':original['raw_input_id'],
                                          'field':field,'source_row_ids':set()})
        group['source_row_ids'].add(row)
    def reported():
        return [{**group,'source_row_ids':sorted(group['source_row_ids'])} for group in failures.values()]
    for key in ('raw_input_id','schema','table','columns','identity_column'):
        if page.get(key) != original[key]:
            fail('Prepared source binding changed')
            return reported()
    units = {field['name']:field['unit'] for field in meanings}
    if declared_units != units or page.get('units', units) != units:
        fail('Mixed or changed units are not accepted')
    if page.get('unresolved'):
        for issue in page['unresolved']:
            index = issue.get('index')
            row = original['rows'][index] if isinstance(index,int) and 0 <= index < len(original['rows']) else None
            row_id = _row_key(row[original['columns'].index(original['identity_column'])]) if row else 'all'
            fail('A conversion remains unresolved', row_id, ','.join(issue.get('fields', [])))
    columns, identity = original['columns'], original['columns'].index(original['identity_column'])
    expected = {_row_key(row[identity]): row for row in original['rows']}
    found = set()
    fields = {field['name']:field for field in meanings}
    if fields.keys() != set(columns):
        fail('Field meanings do not cover the source')
        return reported()
    for values in page.get('rows', []):
        if not isinstance(values, list) or len(values) != len(columns):
            fail('Prepared row width changed')
            continue
        try:
            row_id = _row_key(values[identity])
        except ValueError:
            fail('Prepared identity is invalid')
            continue
        scope = (original['schema'], original['table'], row_id)
        if row_id in found or scope in seen:
            fail('Duplicate identity or join fan-out', row_id)
        seen.add(scope)
        found.add(row_id)
        source = expected.get(row_id)
        if source is None:
            fail('Prepared row has no unchanged source', row_id)
            continue
        for name, actual, raw in zip(columns, values, source):
            if not same_meaning(actual, raw, fields[name]):
                fail('Prepared value changed meaning', row_id, name)
    for missing in expected.keys() - found:
        fail('Unexplained source exclusion', missing)
    return reported()


def check(identity, *, prepared=None, interpretation=None, collection=None):
    started = time.monotonic()
    run, goal = db.check_run(identity)
    if run['body']['operation'] not in ('validation','workflow','coordination') or (run['body']['operation'] in ('workflow','coordination') and any(item is None for item in (prepared,interpretation,collection))):
        raise ValueError('Meaning checks require a validation job')
    prepared = prepared or db.query("SELECT * FROM backintel.analysis_runs WHERE goal_id=%s AND goal_version=%s AND status='succeeded' AND body->>'operation'='preparation' ORDER BY created_at DESC LIMIT 1",
                                    (goal['id'],run['goal_version']),one=True)
    if not prepared:
        raise ValueError('Prepare the complete source before checking meaning')
    contract = {'preparation_run_id':prepared['id'],'preparation_sha256':digest(prepared['result'])}
    prior = db.step(identity,'validation-contract')
    if prior is not None and prior != contract:
        raise ValueError('Prepared data changed; submit a new validation run')
    db.save_step(identity,'validation-contract','validation_contract',contract)
    interpretation = interpretation or db.run(prepared['result']['interpretation_run_id'])['result']
    collection = collection or db.run(prepared['result']['collection_run_id'])['result']
    meanings = {(t['schema_name'],t['table_name']):t['fields'] for t in interpretation['interpretation']['tables']}
    configured = {(t['schema'],t['table']):t['fields'] for t in prepared['result']['recipe']['tables']}
    outputs = prepared['result']['pages']
    by_source = {p['raw_input_id']:p for p in outputs}
    expected_sources = {p['raw_input_id'] for p in collection['inputs']}
    failures, seen, bindings = [], set(), []
    if len(by_source) != len(outputs) or by_source.keys() != expected_sources:
        failures.append({'reason':'Missing or repeated prepared source pages','raw_input_id':None,'field':None,'source_row_ids':['all']})
    if prepared['result']['recipe'].get('joins'):
        failures.append({'reason':'Unverified joins are not accepted','raw_input_id':None,'field':None,'source_row_ids':['all']})
    source_rows, candidate_rows = 0, 0
    actor = {'id':run['owner']}
    for item in collection['inputs']:
        db.check_run(identity)
        if time.monotonic()-started > goal['body']['objective']['limits']['timeout_seconds']:
            raise ValueError('Meaning check time limit reached; no checked answer was accepted')
        raw = retained_input(item['raw_input_id'],actor)
        original, _ = parse_response(raw['payload'])
        original.update(raw_input_id=item['raw_input_id'],schema=item['schema'],table=item['table'])
        source_rows += len(original['rows'])
        metadata = by_source.get(item['raw_input_id'])
        if metadata is None:
            failures.append({'reason':'Unexplained source exclusion','raw_input_id':item['raw_input_id'],'field':None,'source_row_ids':['all']})
            continue
        try:
            page = prepared_page(prepared['id'],metadata['key'],actor)
        except ValueError:
            failures.append({'reason':'Prepared page is missing or changed','raw_input_id':item['raw_input_id'],'field':None,'source_row_ids':['all']})
            continue
        candidate_rows += len(page['rows'])
        if digest(page) != metadata['sha256']:
            failures.append({'reason':'Prepared page changed after publication','raw_input_id':item['raw_input_id'],'field':None,'source_row_ids':['all']})
        key = (item['schema'],item['table'])
        units = {field['name']:field['unit'] for field in configured.get(key,[])}
        failures.extend(compare_page(page,original,meanings[key],units,seen))
        bindings.append({'raw_input_id':item['raw_input_id'],'original_sha256':raw['body']['payload_sha256'],'prepared_sha256':digest(page)})
    if source_rows != collection['coverage']['expected_rows'] or candidate_rows != source_rows:
        failures.append({'reason':'Complete source and prepared counts do not reconcile','raw_input_id':None,'field':None,'source_row_ids':['all']})
    db.check_run(identity)
    report = {'status':'failed' if failures else 'passed','mode':prepared['result']['mode'],
              'summary':'Prepared data failed its independent meaning checks.' if failures else f'All {source_rows} prepared rows match their unchanged originals.',
              'preparation_run_id':prepared['id'],'goal_version':run['goal_version'],'source_ref':goal['body']['objective']['source_ref'],
              'source_rows':source_rows,'candidate_rows':candidate_rows,'failure_groups':failures,'bindings':bindings,
              'elapsed_seconds':round(time.monotonic()-started,3),'usage':db.usage(identity),
              'limitations':['No joins or exclusions are accepted on this workflow. Source-declared units are checked against the interpreted objective; absent physical units remain unknown.',
                             'These checks preserve source meaning. Business findings have not been produced.']}
    report['evidence_id'] = db.evidence(identity,'source_validation',digest(report),report)
    db.save_step(identity,'validation-report','validation_report',report)
    if failures:
        raise ValueError('Prepared data failed its independent meaning checks; affected source records are retained in the validation report')
    return report
