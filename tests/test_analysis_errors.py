"""Synthetic secret values verify redaction without loading any real credential."""
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from runtime.analysis_errors import safe_error


class RedactionChecks(unittest.TestCase):
    def test_environment_file_uri_and_bearer_credentials_are_removed(self):
        with tempfile.TemporaryDirectory() as directory:
            analyst = Path(directory) / 'analyst.json'
            access = Path(directory) / 'access.json'
            analyst.write_text(json.dumps({'key': 'fixture-file-secret'}))
            access.write_text(json.dumps({'manager': 'fixture-role-token'}))
            env = {'OPENROUTER_API_KEY': 'fixture-environment-secret',
                   'BACKINTEL_ANALYST_CREDENTIAL_FILE': str(analyst),
                   'BACKINTEL_ACCESS_CREDENTIAL_FILE': str(access),
                   'DATABASE_URL': 'postgresql://fixture:tiny@localhost/unused',
                   'BACKINTEL_APP_DATABASE_URL': 'postgresql://fixture:escaped%2Fpassword@localhost/unused',
                   'BACKINTEL_TEST_DATABASE_URL': ''}
            values = ['fixture-file-secret', 'fixture-role-token', 'fixture-environment-secret', 'tiny',
                      'escaped/password', 'escaped%2Fpassword', 'fixture-header-secret']
            with patch.dict(os.environ, env):
                result = safe_error('connection failed: ' + '; '.join(values[:-1]) + '; Bearer ' + values[-1])
            for value in values:
                self.assertNotIn(value, result)
            self.assertIn('connection failed', result)
            self.assertEqual(result.count('[redacted]'), 7)

    def test_missing_or_malformed_credential_files_do_not_hide_error_class(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'invalid.json'
            path.write_text('invalid fixture JSON')
            with patch.dict(os.environ, {'OPENROUTER_API_KEY': '', 'DATABASE_URL': '', 'BACKINTEL_APP_DATABASE_URL': '',
                                        'BACKINTEL_TEST_DATABASE_URL': '', 'BACKINTEL_ANALYST_CREDENTIAL_FILE': str(path),
                                        'BACKINTEL_ACCESS_CREDENTIAL_FILE': str(path.parent / 'absent.json')}):
                self.assertEqual(safe_error(TimeoutError('Provider timeout; charge unresolved')), 'Provider timeout; charge unresolved')


if __name__ == '__main__':
    unittest.main()
