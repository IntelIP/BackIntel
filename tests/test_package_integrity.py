"""Recorded package verification rejects undeclared served files."""
import json
from pathlib import Path
import tempfile
import unittest
from scripts.package_business_demo import sha, verify

class PackageIntegrityTests(unittest.TestCase):
    def test_only_documented_mutable_state_may_be_unlisted(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'Records').mkdir()
            packet = root / 'Records/Workspace.json'
            packet.write_text(json.dumps({'demo':{'status':'completed','demo_id':'fixture'}}))
            (root / 'Manifest.json').write_text(json.dumps({'demo_id':'fixture','files':[{'path':'Records/Workspace.json','sha256':sha(packet)}]}))
            (root / '.demo-state').mkdir()
            (root / '.demo-state/reviews.json').write_text('{}')
            verify(root)
            (root / 'Records/extra.js').write_text('unexpected')
            with self.assertRaisesRegex(ValueError, 'file set'):
                verify(root)
