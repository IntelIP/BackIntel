"""Campaign receipts must not turn missing, skipped or stale evidence into passes."""
import copy
import json
from argparse import Namespace
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from scripts.validation import benchmark_campaign as campaign


class CampaignReceiptChecks(unittest.TestCase):
    def test_collect_binds_browser_bytes_to_runner_receipt(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'config').mkdir()
            (root / 'apps/web').mkdir(parents=True)
            (root / 'offline').mkdir()
            campaign.write_json(root / 'config/analysis.json', {'sources': {}})
            campaign.write_json(root / 'apps/web/package-lock.json', {})
            spec = {'id': 'BI-DATA-001', 'family': 'grounded_answers', 'evidence': 'browser',
                    'mode': 'fixture', 'partition': 'development', 'expected': 'Oracle matches', 'domains': ['commerce']}
            campaign.write_json(root / 'manifest.json', {'version': 'v1', 'partition_note': 'development', 'scenarios': [spec]})
            browser_path = root / 'offline/browser-evidence.json'
            browser = {'status': 'failed', 'scenarios': [{'id': spec['id'], 'domain': 'commerce',
                       'mode': 'fixture', 'status': 'failed'}]}
            campaign.write_json(browser_path, browser)
            candidate = {'commit': 'abc', 'dirty': False, 'files': {}, 'verified': True}
            runner = {'candidate': candidate, 'status': 'failed',
                      'artifacts': {'browser-evidence.json': campaign.file_hash(browser_path)}}
            campaign.write_json(root / 'offline/receipt.json', runner)
            args = Namespace(checkout=str(root), output=str(root / 'report'), units=None,
                             offline=str(root / 'offline'), prediction_receipt=[], analyst_receipt=[], label='candidate')
            with patch.object(campaign, 'SCENARIOS', root / 'manifest.json'):
                self.assertEqual(campaign.collect(args, candidate)['scenarios'][0]['status'], 'failed')
                browser['scenarios'][0]['status'] = 'passed'
                browser['status'] = 'passed'
                campaign.write_json(browser_path, browser)
                self.assertEqual(campaign.collect(args, candidate)['scenarios'][0]['status'], 'blocked')
                runner['artifacts'] = {}
                campaign.write_json(root / 'offline/receipt.json', runner)
                self.assertEqual(campaign.collect(args, candidate)['scenarios'][0]['status'], 'blocked')

    def test_identity_rejects_dirty_missing_and_changed_sources(self):
        candidate = {'commit': 'abc', 'dirty': False, 'files': {'runtime/app.py': 'sha'}}
        valid = {'candidate_commit': 'abc', 'dirty_tree': False}
        self.assertIsNone(campaign.identity_error(valid, candidate))
        for receipt in ({}, {**valid, 'dirty_tree': True}, {**valid, 'candidate_commit': 'old'},
                        {**valid, 'source_hashes': {}},
                        {**valid, 'candidate_files': {'runtime/app.py': 'other'}}):
            self.assertIsNotNone(campaign.identity_error(receipt, candidate))

    def test_named_checks_need_actual_unskipped_success(self):
        spec = {'module': 'test_analysis.py', 'test': 'test_answer'}
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'results.json').write_text(json.dumps([{'module': spec['module'], 'tests': 1, 'status': 'passed'}]))
            for outcome, status in [('ok', 'passed'), ("skipped 'database unavailable'", 'blocked'), ('FAIL', 'failed')]:
                (root / 'test_analysis.log').write_text('test_answer (test_analysis.Checks.test_answer) ... ' + outcome + '\n')
                self.assertEqual(campaign.unit_result(spec, root, True)[0], status)
            (root / 'test_analysis.log').write_text('Ran 100 tests\nOK\n')
            self.assertEqual(campaign.unit_result(spec, root, True)[0], 'blocked')
            self.assertEqual(campaign.unit_result(spec, root, False)[0], 'blocked')

    def test_browser_requires_all_role_width_variants_and_fixture_mode(self):
        variants = [{'role': role, 'width': width} for role in ('manager', 'viewer') for width in (1440, 390)]
        spec = {'id': 'BI-ACCESS-001', 'evidence': 'browser', 'variants': variants}
        rows = [{'id': spec['id'], 'domain': 'commerce', 'status': 'passed', 'mode': 'fixture', **v} for v in variants]
        browser = {'status': 'passed', 'scenarios': rows}
        self.assertEqual(campaign.scenario_result(spec, 'commerce', browser, {}, True)[0], 'passed')
        for incomplete in (rows[:-1], rows + [rows[0]], [{**r, 'mode': 'real'} for r in rows]):
            self.assertEqual(campaign.scenario_result(spec, 'commerce', {**browser, 'scenarios': incomplete}, {}, True)[0], 'blocked')

    def test_real_prediction_needs_native_identity_and_provenance(self):
        spec = {'evidence': 'prediction'}
        candidate = {'commit': 'abc', 'dirty': False, 'files': {'runtime/analysis_models.py': 'sha'}}
        receipt = {'schema': 'backintel-local-prediction-benchmark/v1', 'domain': 'churn', 'mode': 'real',
                   'candidate_commit': 'abc', 'dirty_tree': False, 'source_hashes': candidate['files'],
                   'status': 'passed', 'source': {'files': ['source']}, 'source_files': ['source'],
                   'splits': {'test': ['a']}, 'implementation': {'sha256': 'sha'}, 'harness_sha256': 'harness',
                   'model_comparison': {'methods': ['baseline', 'catboost']},
                   'model_restore_predictions_verified': True, 'methods': [{}, {}]}
        self.assertEqual(campaign.real_result(spec, 'churn', [receipt], candidate)[0], 'passed')
        for change in ({'mode': 'fixture'}, {'dirty_tree': True}, {'splits': {}}, {'model_restore_predictions_verified': False}):
            self.assertEqual(campaign.real_result(spec, 'churn', [{**receipt, **change}], candidate)[0], 'blocked')
        self.assertEqual(campaign.real_result(spec, 'credit', [receipt], candidate)[0], 'blocked')

    def test_comparison_refuses_incompatible_or_missing_evidence(self):
        baseline = {'schema': 'backintel-benchmark-campaign/v1', 'scenario_hash': 'scenario',
                    'harness_hashes': {'runner': 'hash'}, 'mode': 'fixture', 'input_fingerprints': {'data': 'hash'},
                    'limits': {'calls': 1}, 'candidate': {'dirty': False},
                    'offline_measurements': {'dependencies': {'python': '3.12'}},
                    'scenarios': [{'id': 'A', 'domain': 'all', 'mode': 'fixture', 'status': 'passed'}]}
        self.assertTrue(campaign.compare(baseline, copy.deepcopy(baseline))['comparable'])
        for key in ('scenario_hash', 'harness_hashes', 'input_fingerprints', 'mode', 'limits'):
            changed = copy.deepcopy(baseline)
            changed[key] = 'different'
            report = campaign.compare(baseline, changed)
            self.assertFalse(report['comparable'])
            self.assertFalse(report['scenarios'][0]['comparable'])
        self.assertFalse(campaign.compare({}, {})['comparable'])
        blocked = copy.deepcopy(baseline)
        blocked['scenarios'][0]['status'] = 'blocked'
        self.assertFalse(campaign.compare(baseline, blocked)['scenarios'][0]['comparable'])

    def test_prediction_implementation_is_the_tested_variable(self):
        baseline = {'schema': 'backintel-benchmark-campaign/v1', 'scenario_hash': 'scenario',
                    'harness_hashes': {'runner': 'same'}, 'mode': 'real', 'input_fingerprints': {'data': 'same'},
                    'limits': {'seconds': 100}, 'candidate': {'commit': 'old', 'dirty': False},
                    'scenarios': [{'id': 'P', 'domain': 'churn', 'mode': 'real', 'status': 'passed',
                                   'measurements': {'source': {'hash': 'same'}, 'splits': {'test': ['a']},
                                                    'implementation': {'sha256': 'old'}, 'harness_sha256': 'same'}}]}
        candidate = copy.deepcopy(baseline)
        candidate['candidate']['commit'] = 'new'
        candidate['scenarios'][0]['measurements']['implementation'] = {'sha256': 'new'}
        candidate['scenarios'][0]['measurements']['catboost_parameters'] = {'depth': 6}
        self.assertTrue(campaign.compare(baseline, candidate)['comparable'])
        for field in ('splits', 'source', 'harness_sha256'):
            mismatched = copy.deepcopy(candidate)
            mismatched['scenarios'][0]['measurements'][field] = 'different'
            self.assertFalse(campaign.compare(baseline, mismatched)['comparable'])


if __name__ == '__main__':
    unittest.main()
