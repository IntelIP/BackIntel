"""Reject stale, changed and incomplete evidence at the PoC merge boundary."""
import copy
import hashlib
import json
from pathlib import Path
import struct
import tempfile
import unittest

from scripts.validation.check_poc_controls import check_controls, load_receipt


class PoCControlsChecks(unittest.TestCase):
    def test_receipt_requires_current_source_and_unchanged_artifacts(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            browser = directory / 'browser-evidence.json'
            browser.write_text(json.dumps({'status': 'passed', 'mode': 'fixture'}))
            candidate = {'commit': 'a' * 40, 'dirty': False, 'files': {'source.py': 'source-hash'}}
            receipt = {'status': 'passed', 'mode': 'e2e', 'candidate_commit': candidate['commit'],
                       'dirty': False, 'candidate_files': candidate['files'], 'provider_calls': 0,
                       'new_provider_spend_usd': 0, 'artifacts': {browser.name: hashlib.sha256(browser.read_bytes()).hexdigest()}}
            path = directory / 'receipt.json'
            path.write_text(json.dumps(receipt))
            self.assertEqual(load_receipt(directory, candidate, candidate['commit'])[0], receipt)
            for changes in ({'candidate_commit': 'b' * 40}, {'dirty': True}, {'candidate_files': {}},
                            {'status': 'failed'}, {'provider_calls': 1}, {'artifacts': {}},
                            {'artifacts': {**receipt['artifacts'], '../outside.json': 'hash'}}):
                with self.subTest(changes=changes), self.assertRaises(ValueError):
                    path.write_text(json.dumps({**receipt, **changes}))
                    load_receipt(directory, candidate, candidate['commit'])
            path.write_text(json.dumps(receipt))
            browser.write_text('{}')
            with self.assertRaisesRegex(ValueError, 'Artifact missing or changed'):
                load_receipt(directory, candidate, candidate['commit'])

    def test_each_control_rejects_its_missing_or_failed_outcome(self):
        views = [{'role': role, 'width': width, 'no_overflow': True, 'keyboard_evidence': True, 'core_denial': True}
                 for role in ('manager', 'analyst', 'viewer') for width in (1440, 390)]
        browser = {'views': views, 'native_clock': {'status': 'passed', 'cleanup': 'removed'},
                   'screenshots': [f"{v['role']}-{v['width']}.png" for v in views],
                   'scenarios': [{'id': 'BI-ACCESS-001', 'status': 'passed', 'role': v['role'], 'width': v['width'],
                                  'write_status': 403, 'core_status': 403} for v in views]}
        recovery = {'status': 'passed', 'completed_events': 1, 'same_run_id': 'run', 'same_job_id': 'job',
                    'accepted_result_sha256': 'hash', 'existing_broker_untouched': True}
        receipt = {'hard_worker_restart': recovery, 'broker_restart': recovery,
                   'database_backup_restore': {'status': 'passed', 'evidence_and_provider_ids_unchanged': True, 'restore_database_cleanup': 'removed'},
                   'database_cleanup': 'removed', 'owned_broker_container_cleanup': 'removed',
                   'artifacts': {name: 'hash' for name in browser['screenshots']}}
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            for view, name in zip(views, browser['screenshots']):
                # Header-only fixture isolates dimension checks; real receipts hash complete Playwright captures.
                (directory / name).write_bytes(b'\x89PNG\r\n\x1a\n' + b'\x00\x00\x00\rIHDR' + struct.pack('>II', view['width'], 1000))
            for mode in ('visual', 'operational', 'security'):
                with self.subTest(mode=mode):
                    check_controls(mode, receipt, browser, directory)
                    missing = {**browser, 'views': views[:-1]}
                    with self.assertRaises(ValueError):
                        check_controls(mode, receipt, missing, directory)
            bad = copy.deepcopy(browser)
            bad['views'][0]['no_overflow'] = False
            with self.assertRaisesRegex(ValueError, 'Layout'):
                check_controls('visual', receipt, bad, directory)
            with self.assertRaisesRegex(ValueError, 'Screenshot missing'):
                check_controls('visual', {**receipt, 'artifacts': {}}, browser, directory)
            bad = copy.deepcopy(receipt)
            bad['hard_worker_restart']['completed_events'] = 2
            with self.assertRaisesRegex(ValueError, 'one completion'):
                check_controls('operational', bad, browser, directory)
            bad = copy.deepcopy(browser)
            bad['scenarios'][0]['write_status'] = 201
            with self.assertRaisesRegex(ValueError, 'Unauthorized writes'):
                check_controls('security', receipt, bad, directory)
