import hashlib
from pathlib import Path
import tempfile
import unittest

from scripts.analysis_prediction_benchmark import verify_source


class PredictionCandidateChecks(unittest.TestCase):
    def test_restored_predictions_must_be_finite(self):
        from unittest.mock import patch
        from scripts.analysis_prediction_benchmark import child
        import json
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)
            (output/'candidate.json').write_text('{}')
            source = output/'source.csv';source.write_text('fixture')
            rows = [{'id':'row','split':'test'}]
            manifest = {'methods':[{'artifact':'catboost-facts.joblib','route':'catboost','features':'facts','predictions':{'row':.2}}]}
            for value in (float('nan'),float('inf'),float('-inf'),.2):
                with self.subTest(value=value), patch('scripts.analysis_prediction_benchmark.verify_source'), patch('scripts.analysis_prediction_benchmark.sha',return_value='fixture-hash'), patch('scripts.analysis_setup.validate_source_receipt'), patch('runtime.analysis_data.source_files',return_value=[source]), patch('runtime.analysis_data.adapt',return_value=('snapshot',{},rows)), patch('runtime.analysis_data.sample',return_value=rows), patch('runtime.analysis_models.compare',return_value=manifest), patch('runtime.analysis_models.predict',return_value={'row':value}):
                    self.assertEqual(child('commerce',output),0 if value==.2 else 1)
                    receipt=json.loads((output/'receipt.json').read_text())
                    self.assertEqual(receipt.get('model_restore_predictions_verified',False),value==.2)
                    if value!=.2:self.assertIn('Restored predictor differs',receipt['reason'])

    def test_invalid_source_receipt_prevents_predictor_execution(self):
        from unittest.mock import patch
        from scripts.analysis_prediction_benchmark import child
        import json
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)
            (output/'candidate.json').write_text('{}')
            with patch('scripts.analysis_prediction_benchmark.verify_source'), patch('scripts.analysis_setup.validate_source_receipt', side_effect=ValueError('Source receipt does not match current files')) as validate, patch('runtime.analysis_models.compare') as compare:
                self.assertEqual(child('commerce',output),1)
            validate.assert_called_once_with('commerce')
            compare.assert_not_called()
            self.assertEqual(json.loads((output/'receipt.json').read_text())['status'],'failed')

    def test_only_matching_clean_source_can_execute(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / 'runtime.py'
            source.write_text('original')
            identity = {'dirty_tree': False, 'source_hashes': {
                'runtime.py': hashlib.sha256(source.read_bytes()).hexdigest()}}
            verify_source(root, identity)
            source.write_text('changed')
            with self.assertRaisesRegex(ValueError, 'source changed'):
                verify_source(root, identity)
            identity['dirty_tree'] = True
            with self.assertRaisesRegex(ValueError, 'clean source'):
                verify_source(root, identity)

    def test_source_manifest_cannot_escape_checkout(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / 'checkout'
            root.mkdir()
            external = root.parent / 'outside'
            external.write_text('outside')
            identity = {'dirty_tree': False, 'source_hashes': {
                '../outside': hashlib.sha256(external.read_bytes()).hexdigest()}}
            with self.assertRaisesRegex(ValueError, 'source changed'):
                verify_source(root, identity)


if __name__ == '__main__':
    unittest.main()
