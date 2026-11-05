"""Installation boundaries that prevent inherited access and accidental model spending."""

import os
from pathlib import Path
import unittest
from unittest.mock import patch

from scripts.local_platform import native_database_url, owned_container, runtime_environment


class LocalPlatformChecks(unittest.TestCase):
    def setUp(self):
        self.state = {'id': 'owned', 'container': 'backintel-platform-owned',
                      'database_url': 'postgresql://local/backintel_app',
                      'source_url': 'postgresql://reader/local_source',
                      'preparation_image': 'sha256:local'}

    def test_default_discards_inherited_access_and_spending(self):
        with patch.dict(os.environ, {'PATH': '/preserved', 'OPENROUTER_API_KEY': 'must-not-leak',
                                     'OPENAI_API_KEY': 'must-not-leak',
                                     'BACKINTEL_SOURCE_OTHER': 'private-source',
                                     'BACKINTEL_APP_DATABASE_URL': 'private-database',
                                     'PYTHONPATH': '/private/old-runtime',
                                     'PGPASSWORD': 'private-password'}, clear=True):
            env = runtime_environment(Path('/private/install'), self.state)
        self.assertEqual(env['PATH'], '/preserved')
        self.assertEqual(env['OPENROUTER_API_KEY'], '')
        self.assertEqual(env['DATABASE_URL'], self.state['database_url'])
        self.assertNotIn('BACKINTEL_SOURCE_OTHER', env)
        self.assertNotIn('PGPASSWORD', env)
        self.assertNotIn('OPENAI_API_KEY', env)
        self.assertNotIn('PYTHONPATH', env)

    def test_live_access_requires_both_finite_allowance_and_key(self):
        for amount in (None, 0, -1, float('nan'), float('inf'), .51):
            with self.subTest(amount=amount), self.assertRaises(ValueError):
                runtime_environment(Path('/private/install'), self.state,
                                    allow_models=True, budget_usd=amount)
        with patch.dict(os.environ, {}, clear=True), self.assertRaises(ValueError):
            runtime_environment(Path('/private/install'), self.state,
                                allow_models=True, budget_usd=.25)
        with patch.dict(os.environ, {'OPENROUTER_API_KEY': 'explicit-test-key'}, clear=True):
            env = runtime_environment(Path('/private/install'), self.state,
                                      allow_models=True, budget_usd=.25)
        self.assertEqual(env['OPENROUTER_API_KEY'], 'explicit-test-key')

    def test_shutdown_refuses_an_unrelated_container(self):
        with patch('scripts.local_platform.docker', return_value='[{"Config":{"Labels":{}}}]'):
            with self.assertRaisesRegex(ValueError, 'does not belong'):
                owned_container(self.state)

    def test_native_connection_url_preserves_escaped_credentials(self):
        from urllib.parse import urlsplit, unquote
        url = native_database_url("host=127.0.0.1 port=5432 dbname=backintel_app user=postgres password='test/a?b#c'")
        parts = urlsplit(url)
        self.assertEqual(parts.scheme, 'postgresql')
        self.assertEqual(parts.hostname, '127.0.0.1')
        self.assertEqual(parts.port, 5432)
        self.assertEqual(unquote(parts.password), 'test/a?b#c')
        self.assertEqual(parts.query, '')


if __name__ == '__main__':
    unittest.main()
