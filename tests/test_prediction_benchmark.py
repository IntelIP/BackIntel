import hashlib
from pathlib import Path
import tempfile
import unittest

from scripts.analysis_prediction_benchmark import verify_source


class PredictionCandidateChecks(unittest.TestCase):
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
