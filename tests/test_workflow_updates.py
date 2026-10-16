from copy import deepcopy
from datetime import date, timedelta
from unittest.mock import patch
from unittest import TestCase

from runtime import workflow_updates as updates


def test_schema_changes_require_review_and_keep_the_saved_meanings():
    table = {'schema': 'retail', 'table': 'lines', 'identity_column': 'id', 'expected_rows': 1,
             'fields': [{'name': 'id'}, {'name': 'quantity'}]}
    body = {'accepted': {'collection': {'run_id': 'old'}}, 'preparation': {'tables': [table]}}
    source = {'observed_at': '2026-10-16T01:00:00+00:00', 'inputs': [{'sha256': 'unchanged', 'row_count': 1}], 'tables_collected': [table], 'coverage': {'expected_rows': 1}}
    with patch.object(updates.db, 'run', return_value={'result': source}), patch.object(updates.db, 'save_step') as save:
        report = updates.begin('run', body, {'input_ref': 'new'}, source)
        assert report['changed_input'] and report['unchanged_source_pages'] == 1
        changed = deepcopy(source)
        changed['tables_collected'][0]['fields'].pop()
        with TestCase().assertRaisesRegex(updates.ReviewRequired, 'required source fields'):
            updates.begin('run', body, {'input_ref': 'bad'}, changed)
        assert save.call_args.args[-1]['details']['changes'][0]['missing_fields'] == ['quantity']
        assert len(body['preparation']['tables'][0]['fields']) == 2


def test_worse_forecast_error_blocks_without_search_or_tuning():
    weeks = [{'start': (date(2026, 1, 5) + timedelta(weeks=i)).isoformat(), 'net_value': '10', 'rows': 1} for i in range(12)]
    reference = {'actual': weeks[-4:], 'selected': {'mean_absolute_weekly_error': '0'},
                 'execution': {'predictions': ['10'] * 4}}
    def forbidden(*args):
        raise AssertionError('The accepted baseline must not request model or candidate work')
    assert updates.method_check(weeks, {'kind': 'baseline'}, reference, 'image', forbidden)['status'] == 'unchanged_observations'
    changed = deepcopy(weeks)
    changed[-1]['net_value'] = '110'
    report = updates.method_check(changed, {'kind': 'baseline'}, reference, 'image', forbidden)
    assert report['status'] == 'review_required'
    assert report['measured']['mean_absolute_weekly_error'] == '25'
    # Changed earlier values must also be measured even when the actual four weeks are unchanged.
    changed = deepcopy(weeks)
    changed[-5]['net_value'] = '50'
    assert updates.method_check(changed, {'kind': 'baseline'}, reference, 'image', forbidden)['status'] == 'review_required'


def test_older_source_cannot_replace_a_newer_answer():
    goal = {'body': {'question': 'Q'}, 'last_success': 'accepted'}
    incoming = {'id': 'incoming', 'body': {'question': 'Q', 'operation': 'workflow', 'input_ref': 'old-source'}}
    rows = {'accepted': {'body': {'operation': 'workflow', 'input_ref': 'new-source'}},
            'old-source': {'result': {'observed_at': '2026-10-15T00:00:00+00:00'}},
            'new-source': {'result': {'observed_at': '2026-10-16T00:00:00+00:00'}}}
    with patch.object(updates.db, 'run', side_effect=lambda key, **kw: rows[key]), patch.object(updates.db, 'save_step'):
        with TestCase().assertRaisesRegex(updates.ReviewRequired, 'newer source answer'):
            updates.guard_publication(incoming, goal, object())
    assert goal['last_success'] == 'accepted'


if __name__ == '__main__':
    test_schema_changes_require_review_and_keep_the_saved_meanings()
    test_worse_forecast_error_blocks_without_search_or_tuning()
    test_older_source_cannot_replace_a_newer_answer()
    print('PASS: schema, forecast-error, and accepted-source guards')
