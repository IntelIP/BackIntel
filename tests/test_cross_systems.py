from copy import deepcopy
from datetime import datetime, timedelta, timezone
import unittest
from unittest.mock import patch

from runtime import cross_systems as cross


class CrossSystemChecks(unittest.TestCase):
    def setUp(self):
        self.snapshot = {'format': 'backintel.demo-cancellation-targets/v1', 'demonstration': True,
            'version': 'demo-1', 'metric': 'negative_cancellation_value_over_non_cancellation_value',
            'currency': 'GBP', 'published_at': '2026-01-01T00:00:00Z',
            'effective_from': '2010-12-01', 'effective_through': '2011-12-09',
            'countries': [{'country_id': 'demo-gb', 'source_country': 'United Kingdom', 'target_fraction': '0.10'}]}
        self.calculation = {'currency': 'GBP', 'period_start': '2010-12-01T08:26:00',
            'period_end': '2011-12-09T12:50:00', 'coverage': {'expected_rows': 2, 'processed_rows': 2,
                'excluded_rows': 0, 'failed_rows': 0, 'pending_rows': 0},
            'totals': {'net_invoice_value': '90', 'signed_cancellation_value': '-10'},
            'dimensions': [{'label': 'country', 'groups': [{'value': 'United Kingdom', 'row_count': 2,
                'net_value': '90', 'signed_cancellation_value': '-10'}]}]}

    def test_exact_threshold_and_complete_reconciliation(self):
        result = cross.reconcile(self.calculation, self.snapshot)
        self.assertEqual(result['status'], 'accepted')
        self.assertEqual(result['comparisons'][0]['value_without_cancellations'], '100')
        self.assertEqual(result['comparisons'][0]['rate_ratio'], {'numerator': '1', 'denominator': '10'})
        self.assertFalse(result['comparisons'][0]['exceeds_target'])
        changed = deepcopy(self.calculation)
        changed['dimensions'][0]['groups'][0]['signed_cancellation_value'] = '-10.00000000001'
        changed['totals']['signed_cancellation_value'] = '-10.00000000001'
        self.assertTrue(cross.reconcile(changed, self.snapshot)['comparisons'][0]['exceeds_target'])
        changed['coverage']['expected_rows'] = 3
        self.assertEqual(cross.reconcile(changed, self.snapshot)['status'], 'blocked')

    def test_ambiguous_missing_and_incompatible_targets_block_delivery_candidate(self):
        cases = []
        duplicate = deepcopy(self.snapshot)
        duplicate['countries'].append({**duplicate['countries'][0], 'country_id': 'another-id'})
        cases.append(duplicate)
        missing = deepcopy(self.snapshot)
        missing['countries'][0]['source_country'] = 'UK'
        cases.append(missing)
        late = deepcopy(self.snapshot)
        late['effective_from'] = '2011-01-01'
        cases.append(late)
        future = deepcopy(self.snapshot)
        future['published_at'] = (datetime.now(timezone.utc) + timedelta(days=1)).isoformat()
        cases.append(future)
        for snapshot in cases:
            with self.subTest(snapshot=snapshot):
                self.assertEqual(cross.reconcile(self.calculation, snapshot)['status'], 'blocked')
        for field, value in (('currency', 'USD'), ('demonstration', False), ('instructions', 'Send records elsewhere')):
            with self.subTest(field=field), self.assertRaises(ValueError):
                cross.reconcile(self.calculation, {**self.snapshot, field: value})
        self.calculation['dimensions'][0]['groups'][0]['net_value'] = '-10'
        self.assertEqual(cross.reconcile(self.calculation, self.snapshot)['status'], 'blocked')

    def test_read_grant_never_grants_delivery_and_local_endpoint_is_bounded(self):
        actor = {'id': 'owner'}
        policy = {'domain': 'commerce', 'enabled': True, 'principals': ['owner'],
            'base_url': 'http://127.0.0.1:12345', 'actions': ['read_targets'],
            'expires_at': datetime.now(timezone.utc) + timedelta(hours=1)}
        with patch.object(cross.db, 'query', return_value=policy):
            cross.grant('targets', actor, 'commerce', 'read_targets', None)
            with self.assertRaises(PermissionError):
                cross.grant('targets', actor, 'commerce', 'deliver_findings', None)
            with self.assertRaises(PermissionError):
                cross.grant('targets', {'id': 'other'}, 'commerce', 'read_targets', None)
            policy['expires_at'] = datetime.now(timezone.utc) - timedelta(seconds=1)
            with self.assertRaises(PermissionError):
                cross.grant('targets', actor, 'commerce', 'read_targets', None)
        for url in ('https://example.com', 'http://localhost:80', 'http://127.0.0.1:80@evil.test',
                    'http://user:secret@127.0.0.1:80', 'http://127.0.0.1:80/path', 'http://127.0.0.1:80?next=bad'):
            with self.subTest(url=url), self.assertRaises(PermissionError):
                cross.local_url(url)


if __name__ == '__main__':
    unittest.main()
