from decimal import Decimal
from datetime import date, timedelta
import json

from unittest import TestCase

from runtime import source_methods as methods


def test_exact_weekly_reconciliation_preserves_adjustments_and_boundary_rows():
    page = {'schema': 'retail_raw', 'table': 'invoice_lines', 'unresolved': [],
            'columns': ['row', 'date', 'quantity', 'price'], 'identity_column': 'row',
            'rows': [[1, '2011-01-02T10:00:00', '1', '0.001'],
                     [2, '2011-01-03T10:00:00', '3', '0.101'],
                     [3, '2011-01-09T10:00:00', '-1', '0.10'],
                     [4, '2011-01-10T10:00:00', '2', '0.002']]}
    method = {'schema_name': 'retail_raw', 'table_name': 'invoice_lines',
              'date_field': 'date', 'quantity_field': 'quantity', 'unit_price_field': 'price', 'currency': 'GBP'}
    series = methods.weekly_series(method, [page], 4)
    assert series['weeks'] == [{'start': '2011-01-03', 'net_value': '0.203', 'rows': 2}]
    assert series['totals'] == {'source': '0.208', 'complete_weeks': '0.203', 'partial_boundary_weeks': '0.005'}
    assert series['coverage']['complete_week_rows'] + series['coverage']['partial_boundary_week_rows'] == 4
    with TestCase().assertRaisesRegex(ValueError, 'more than once'):
        methods.weekly_series(method, [page, page], 8)
    with TestCase().assertRaisesRegex(ValueError, 'complete checked source'):
        methods.weekly_series(method, [page], 5)


def test_selection_never_receives_the_final_weeks_and_keeps_the_baseline_on_ties():
    weeks = [{'start': (date(2011, 1, 3) + timedelta(weeks=i)).isoformat(),
              'net_value': str(i + 1), 'rows': 1} for i in range(32)]
    split = methods.split_series({'weeks': weeks})
    assert len(split['training']) == 24
    assert set(w['start'] for w in split['training']).isdisjoint(w['start'] for w in split['final_test'])
    prompt = json.loads(methods.method_inputs({}, split['training'])[1]['content'])
    assert prompt['development_history'] == weeks[:24]
    observed = []

    def execute(candidate, history, image):
        observed.append(history)
        return {'status': 'valid', 'predictions': methods.baseline(history)}

    result = methods.select_method([{'name': 'Tie', 'code': 'a'}], split['training'], split['validation'], 'image', execute)
    assert observed == [weeks[:24]]
    assert result['selected']['kind'] == 'baseline'
    assert result['candidates'][0]['status'] == 'rejected'
    assert Decimal(result['baseline']['mean_absolute_weekly_error']) == 4


def test_invalid_forecasts_are_rejected_and_selection_uses_actual_error():
    for value in [[True, 1, 2, 3], [1, 2, 3], ['NaN'] * 4, ['Infinity'] * 4, ['1e99'] * 4]:
        with TestCase().assertRaises(ValueError):
            methods.forecast_values(value)
    history = [{'net_value': '10'}] * 4
    actual = [{'net_value': '12'}] * 4

    def execute(candidate, *_):
        if candidate['name'] == 'Broken':
            return {'status': 'rejected', 'reason': 'Invalid output'}
        return {'status': 'valid', 'predictions': ['12'] * 4}

    result = methods.select_method([{'name': 'Broken', 'code': 'a'}, {'name': 'Useful', 'code': 'b'}], history, actual, 'image', execute)
    assert result['selected']['name'] == 'Useful'
    assert result['candidates'][0]['status'] == 'rejected'
    assert result['selected']['validation']['mean_absolute_weekly_error'] == '0'


class SourceMethodsTests(TestCase):
    test_exact_weeks = staticmethod(test_exact_weekly_reconciliation_preserves_adjustments_and_boundary_rows)
    test_protected_selection = staticmethod(test_selection_never_receives_the_final_weeks_and_keeps_the_baseline_on_ties)
    test_invalid_methods = staticmethod(test_invalid_forecasts_are_rejected_and_selection_uses_actual_error)
