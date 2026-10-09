"""Recorded package verification rejects undeclared served files."""
import json
from pathlib import Path
import tempfile
import unittest
from scripts.package_business_demo import sha, verify, copy_execution_package

class PackageIntegrityTests(unittest.TestCase):
    def test_execution_copy_excludes_private_audience_grants(self):
        with tempfile.TemporaryDirectory() as directory:
            source, target = Path(directory)/'source', Path(directory)/'public'
            source.mkdir()
            (source/'AudienceAccess.json').write_text('{"fixture_token":"private"}')
            (source/'receipt.json').write_text('{"mode":"fixture"}')
            copy_execution_package(source, target)
            self.assertFalse((target/'AudienceAccess.json').exists())
            self.assertEqual((target/'receipt.json').read_text(), '{"mode":"fixture"}')

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
