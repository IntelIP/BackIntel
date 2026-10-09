"""Portable imports, credential paths, deadlines, and original-label regression checks."""
import csv
import io
import json
import os
import stat
import ssl
import subprocess
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import MagicMock, patch

from runtime.analysis_data import CONFIG, fingerprint
from scripts import analysis_demo as demo
from scripts import analysis_setup as setup
from scripts.analysis_local_benchmark import raw_churn_oracle


def churn_csv(directory):
    path = Path(directory) / CONFIG['sources']['churn']['files'][0]
    with path.open('w', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=['customerID', 'Churn', 'Contract', 'tenure', 'MonthlyCharges', 'TotalCharges'])
        writer.writeheader()
        writer.writerows([{'customerID': 'a', 'Churn': 'Yes', 'Contract': 'Monthly', 'tenure': 1, 'MonthlyCharges': 2, 'TotalCharges': 2},
                         {'customerID': 'b', 'Churn': 'No', 'Contract': 'Annual', 'tenure': 2, 'MonthlyCharges': 2, 'TotalCharges': 4}])
    return path


class SetupChecks(unittest.TestCase):
    def test_weight_metadata_trusts_configured_ca_with_tls_verification_enabled(self):
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary); certificate = base / 'ca.pem'; key = base / 'synthetic-ca.key'
            subprocess.run(['openssl', 'req', '-x509', '-newkey', 'rsa:2048', '-nodes', '-days', '1',
                            '-keyout', str(key), '-out', str(certificate), '-subj', '/CN=BackIntel setup test CA'],
                           capture_output=True, check=True, timeout=15)
            with patch.dict(os.environ, {'SSL_CERT_FILE': str(certificate)}):
                context = demo.context()
            expected = ssl.PEM_cert_to_DER_cert(certificate.read_text())
            self.assertIn(expected, context.get_ca_certs(binary_form=True))
            self.assertTrue(context.check_hostname)
            self.assertEqual(context.verify_mode, ssl.CERT_REQUIRED)

    def test_valid_import_is_atomic_fingerprinted_and_idempotent(self):
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary); incoming = base / 'incoming'; incoming.mkdir()
            source = churn_csv(incoming)
            with patch.dict(os.environ, {'BACKINTEL_DATASET_DIR': str(base / 'datasets')}):
                receipt = setup.import_data('churn', source)
                self.assertEqual(receipt['files'][0]['sha256'], fingerprint(source)['sha256'])
                self.assertEqual(receipt['files'][0]['rows'], 2)
                self.assertTrue(receipt['terms_acknowledged'])
                self.assertFalse(receipt['competition_rules_accepted_by_tool'])
                self.assertEqual(receipt, setup.import_data('churn', source))
                receipt_path = base / 'datasets/Churn/source-receipt.json'
                receipt_path.unlink()
                self.assertEqual(receipt, setup.import_data('churn', source))
                self.assertEqual(json.loads(receipt_path.read_text()), receipt)
                original = (base / 'datasets/Churn' / source.name).read_bytes()
                source.write_text(source.read_text().replace('Yes', 'No'))
                with self.assertRaisesRegex(ValueError, 'Existing dataset differs'):
                    setup.import_data('churn', source)
                self.assertEqual((base / 'datasets/Churn' / source.name).read_bytes(), original)

    def test_incomplete_home_credit_import_does_not_publish_partial_directory(self):
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary); incoming = base / 'incoming'; incoming.mkdir()
            (incoming / 'application_train.csv').write_text('SK_ID_CURR,TARGET,NAME_INCOME_TYPE\n1,0,Working\n')
            with patch.dict(os.environ, {'BACKINTEL_DATASET_DIR': str(base / 'datasets')}):
                with self.assertRaisesRegex(ValueError, 'bureau.csv'):
                    setup.import_data('credit', incoming)
            self.assertFalse((base / 'datasets/Credit').exists())

    def test_home_credit_local_files_need_no_kaggle_credentials_or_rule_action(self):
        from runtime.analysis_data import digest
        identity = next(str(i) for i in range(1000) if int(digest(str(i))[:8], 16) % 31 == 0)
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary); incoming = base / 'incoming'; incoming.mkdir()
            (incoming / 'application_train.csv').write_text(f'SK_ID_CURR,TARGET,NAME_INCOME_TYPE\n{identity},0,Working\n')
            (incoming / 'bureau.csv').write_text(f'SK_ID_CURR,DAYS_CREDIT,DAYS_CREDIT_UPDATE\n{identity},-1,-1\n')
            with patch.dict(os.environ, {'BACKINTEL_DATASET_DIR': str(base / 'datasets'), 'KAGGLE_API_TOKEN': '', 'KAGGLE_KEY': ''}), patch.object(setup.subprocess, 'run', side_effect=AssertionError('No external access')):
                receipt = setup.import_data('credit', incoming)
            self.assertEqual(receipt['adapter_receipt']['rows'], 1)
            self.assertFalse(receipt['competition_rules_accepted_by_tool'])

    def test_lfs_html_missing_columns_and_invalid_target_are_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary); incoming = base / 'incoming'; incoming.mkdir()
            path = incoming / CONFIG['sources']['churn']['files'][0]
            for text in ('version https://git-lfs.github.com/spec/v1\noid sha256:fake\n', '<html>blocked</html>', 'unrelated\n1\n'):
                path.write_text(text)
                with patch.dict(os.environ, {'BACKINTEL_DATASET_DIR': str(base / 'datasets')}):
                    with self.assertRaises(ValueError):
                        setup.import_data('churn', path)
                self.assertFalse((base / 'datasets/Churn').exists())
            path = churn_csv(incoming)
            path.write_text(path.read_text().replace('Yes', 'Maybe'))
            with patch.dict(os.environ, {'BACKINTEL_DATASET_DIR': str(base / 'datasets')}), self.assertRaisesRegex(ValueError, 'Yes or No'):
                setup.import_data('churn', path)

    def test_original_telco_whitespace_numeric_missing_values_stay_missing(self):
        from runtime.analysis_data import number
        for value in ('', ' ', '\t', ' NA ', ' NaN '):
            self.assertIsNone(number(value))
        self.assertEqual(number(' 42.5 '), 42.5)
        with self.assertRaises(ValueError):
            number('unrecognized')

    def test_zip_traversal_symlinks_duplicates_and_bombs_are_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary); source = churn_csv(base); payload = source.read_bytes()
            wanted = source.name
            for mode in ('traversal', 'link', 'duplicate', 'budget'):
                archive = base / (mode + '.zip')
                with zipfile.ZipFile(archive, 'w') as zipped:
                    if mode == 'traversal':
                        zipped.writestr('../' + wanted, payload)
                    elif mode == 'link':
                        entry = zipfile.ZipInfo(wanted); entry.create_system = 3; entry.external_attr = (stat.S_IFLNK | 0o777) << 16
                        zipped.writestr(entry, 'outside')
                    else:
                        zipped.writestr('one/' + wanted, payload)
                        if mode == 'duplicate':
                            zipped.writestr('two/' + wanted, payload)
                target = base / ('target-' + mode); target.mkdir()
                budget = 1 if mode == 'budget' else setup.MAX_EXTRACTED_BYTES
                with patch.object(setup, 'MAX_EXTRACTED_BYTES', budget), self.assertRaises(ValueError):
                    setup.extract_sources(archive, target, {wanted})
            self.assertFalse((base.parent / wanted).exists())

    def test_nested_zip_extracts_only_expected_sources(self):
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary); source = churn_csv(base)
            inner = io.BytesIO()
            with zipfile.ZipFile(inner, 'w') as zipped:
                zipped.writestr('data/' + source.name, source.read_bytes()); zipped.writestr('ignored.txt', 'extra')
            archive = base / 'outer.zip'
            with zipfile.ZipFile(archive, 'w') as zipped:
                zipped.writestr('inner.zip', inner.getvalue())
            with patch.dict(os.environ, {'BACKINTEL_DATASET_DIR': str(base / 'datasets')}):
                setup.import_data('churn', archive)
            self.assertEqual(sorted(p.name for p in (base / 'datasets/Churn').iterdir()), [source.name, 'source-receipt.json'])

    def test_seed_uses_configured_private_file_without_printing_credentials(self):
        from runtime import analysis_store as db
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / 'private/access.json'
            with patch.dict(os.environ, {'BACKINTEL_ACCESS_CREDENTIAL_FILE': str(path)}), patch.object(db, 'catalog'), patch.object(db, 'write') as write, patch('builtins.print') as output:
                demo.seed()
                values = json.loads(path.read_text())
                demo.seed()
            self.assertEqual(values, json.loads(path.read_text()))
            self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o600)
            self.assertEqual(write.call_count, 8)
            for token in values.values():
                self.assertNotIn(token, repr(output.call_args_list))

    def test_linux_provision_uses_environment_binding_without_keychain(self):
        with patch.object(demo.sys, 'platform', 'linux'), patch.object(demo, 'runtime_access', return_value={}), patch.object(demo, 'keychain', side_effect=AssertionError('Mac-only')), patch.dict(os.environ, {'OPENROUTER_API_KEY': 'synthetic-provider-secret'}), patch('builtins.print') as output:
            demo.provision()
        self.assertNotIn('synthetic-provider-secret', repr(output.call_args_list))
        with patch.object(demo.sys, 'platform', 'linux'), patch.object(demo, 'runtime_access', return_value={}), patch.dict(os.environ, {'OPENROUTER_API_KEY': ''}):
            with self.assertRaisesRegex(RuntimeError, 'Inject OPENROUTER_API_KEY'):
                demo.provision()

    def test_preflight_reports_names_and_presence_without_loading_secret_files(self):
        with tempfile.TemporaryDirectory() as temporary:
            env = {'BACKINTEL_DATASET_DIR': temporary, 'BACKINTEL_MODEL_DIR': temporary, 'OPENROUTER_API_KEY': 'synthetic-provider-secret'}
            with patch.dict(os.environ, env):
                report = setup.preflight()
            text = json.dumps(report)
            self.assertNotIn('synthetic-provider-secret', text)
            self.assertTrue(report['analyst']['environment_binding_present'])
            self.assertFalse(report['full_live_campaign_ready'])
            self.assertEqual(report['provider_calls'], 0)

    def test_checkpoint_import_requires_pinned_size_and_hash(self):
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary); source = base / 'weights'; source.write_bytes(b'fixture checkpoint')
            with patch.dict(os.environ, {'BACKINTEL_MODEL_DIR': str(base / 'models')}):
                with self.assertRaisesRegex(ValueError, 'approved size and SHA-256'):
                    setup.import_weights('classification', source)
            self.assertFalse((base / 'models/Weights').exists())

    def test_checkpoint_download_uses_frozen_revision_then_validates_identity(self):
        spec = json.loads(setup.MODEL_CONFIG.read_text())['tabiclv2']
        with patch.object(demo, 'download') as download, patch.object(setup, 'import_weights', return_value={'status': 'verified'}) as imported:
            self.assertEqual(setup.download_weights('classification')['status'], 'verified')
        self.assertIn(spec['revision'], download.call_args.args[0])
        self.assertIn(spec['checkpoints']['classification']['file'], download.call_args.args[0])
        self.assertEqual(imported.call_args.args[0], 'classification')

    def test_decide_import_rejects_tampering_and_unapproved_revision(self):
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary); incoming = base / 'incoming'; incoming.mkdir()
            config = incoming / 'config.json'; config.write_text('{}')
            tensor = incoming / 'model.safetensors'; tensor.write_bytes(b'synthetic weights')
            receipt = {**CONFIG['decide'], 'files': [fingerprint(config), fingerprint(tensor)]}
            path = incoming / 'backintel-weights.json'; path.write_text(json.dumps(receipt))
            with patch.dict(os.environ, {'BACKINTEL_MODEL_DIR': str(base / 'models')}):
                changed = {**receipt, 'revision': 'unapproved'}; path.write_text(json.dumps(changed))
                with self.assertRaisesRegex(ValueError, 'unapproved revision'):
                    setup.import_weights('decide', incoming)
                path.write_text(json.dumps(receipt)); tensor.write_bytes(b'tampered')
                with self.assertRaisesRegex(ValueError, 'identity mismatch'):
                    setup.import_weights('decide', incoming)
                tensor.write_bytes(b'synthetic weights')
                result = setup.import_weights('decide', incoming)
                self.assertEqual(result['status'], 'receipt-verified')
                self.assertEqual((base / 'models/Decide/model.safetensors').read_bytes(), tensor.read_bytes())

    def test_original_oracle_rejects_unknown_labels_and_duplicates(self):
        with tempfile.TemporaryDirectory() as temporary:
            source = churn_csv(temporary)
            cases, oracle = raw_churn_oracle(source)
            self.assertEqual(oracle['positives'], 1); self.assertEqual(oracle['mean_target'], .5)
            self.assertEqual(cases['a']['contract'], 'Monthly')
            original = source.read_text()
            source.write_text(original.replace('Yes', 'Maybe'))
            with self.assertRaises(ValueError):
                raw_churn_oracle(source)
            source.write_text(original + original.splitlines()[1] + '\n')
            with self.assertRaises(ValueError):
                raw_churn_oracle(source)

    def test_live_benchmark_uses_configured_url_credentials_and_bounded_wait(self):
        from scripts import analysis_benchmark as benchmark
        from runtime import analysis_service, analysis_store
        import httpx
        client = MagicMock(); client.__enter__.return_value = client
        stream = MagicMock(); stream.__enter__.return_value = stream; stream.iter_lines.return_value = []
        client.stream.return_value = stream
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / 'access.json'; path.write_text(json.dumps({'manager': 'fixture'}))
            env = {'BACKINTEL_ACCESS_CREDENTIAL_FILE': str(path), 'BACKINTEL_AEGRA_URL': 'http://127.0.0.1:2028'}
            with patch.dict(os.environ, env), patch.object(analysis_service, 'wake'), patch.object(httpx, 'Client', return_value=client) as transport, patch.object(analysis_store, 'run', side_effect=[{'status': 'queued'}, {'status': 'queued'}, {'status': 'succeeded'}, {'status': 'succeeded'}]):
                self.assertEqual(benchmark.execute({'id': 'fixture'})['status'], 'succeeded')
                transport.assert_called_once_with(timeout=75, headers={'Authorization': 'Bearer fixture'})
            self.assertEqual(client.stream.call_args.args[1], 'http://127.0.0.1:2028/api/v1/runs/fixture/events')
            with patch.dict(os.environ, env), patch.object(analysis_service, 'wake'), patch.object(httpx, 'Client', return_value=client) as transport, patch.object(analysis_store, 'run', return_value={'status': 'queued'}), patch.object(benchmark.time, 'monotonic', side_effect=[0, 99999]):
                with self.assertRaises(TimeoutError):
                    benchmark.execute({'id': 'fixture'})


if __name__ == '__main__':
    unittest.main()
