"""Fixture-port isolation and accepted completion identity checks."""
import os
import unittest
from unittest.mock import Mock, patch

from fastapi import HTTPException
from starlette.requests import Request

from runtime import analysis_api as api
from scripts.validation.run_analysis_offline import accepted_result, fixture_configuration


class WorkflowChecks(unittest.TestCase):
    def test_production_origin_ignores_fixture_environment(self):
        with patch.dict(os.environ, {'BACKINTEL_VALIDATION_PORT': '28765', 'BACKINTEL_VALIDATION_MODE': 'fixture'}):
            request = Request({'type': 'http', 'method': 'POST', 'headers': [(b'origin', b'http://127.0.0.1:28765')]})
            with self.assertRaises(HTTPException) as caught:
                api.access(request)
            self.assertEqual(caught.exception.status_code, 403)

    def test_fixture_origin_binding_keeps_cross_origin_writes_denied(self):
        origins = frozenset(('http://127.0.0.1:28765', 'http://localhost:28765'))
        with patch.object(api, 'WRITE_ORIGINS', origins), patch.object(api.db, 'principal', return_value={'id': 'fixture'}):
            for origin in ('http://127.0.0.1:28765', 'http://localhost:28765'):
                request = Request({'type': 'http', 'method': 'POST', 'headers': [(b'origin', origin.encode())]})
                self.assertEqual(api.access(request), {'id': 'fixture'})
            for origin in ('http://evil.test:28765', 'https://localhost:28765', 'http://127.0.0.1:2028'):
                request = Request({'type': 'http', 'method': 'POST', 'headers': [(b'origin', origin.encode())]})
                with self.assertRaises(HTTPException):
                    api.access(request)

    def test_aegra_fixture_loader_reuses_patched_origin_dependency(self):
        from pathlib import Path
        from aegra_api.core.app_loader import load_custom_app
        config = fixture_configuration(28765)
        origins = frozenset(config['http']['cors']['allow_origins'])
        with patch.object(api, 'WRITE_ORIGINS', origins), patch.object(api.db, 'principal', return_value={'id': 'fixture'}):
            app = load_custom_app(config['http']['app'])
            route = next(route for route in app.routes if getattr(route, 'path', None) == '/api/v1/me')
            access = route.dependant.dependencies[0].call
            self.assertIs(app, api.app)
            request = Request({'type': 'http', 'method': 'POST', 'headers': [(b'origin', b'http://127.0.0.1:28765')]})
            self.assertEqual(access(request), {'id': 'fixture'})
            request = Request({'type': 'http', 'method': 'POST', 'headers': [(b'origin', b'http://evil.test:28765')]})
            with self.assertRaises(HTTPException):
                access(request)
        self.assertEqual(api.WRITE_ORIGINS, frozenset(('http://127.0.0.1:2028', 'http://localhost:2028')))
        for value in [*config['graphs'].values(), config['auth']['path']]:
            self.assertTrue(Path(value.rsplit(':', 1)[0]).is_file())

    def test_recovery_requires_same_job_and_one_accepted_result(self):
        state = {'id': 'run', 'job_id': 'job', 'result': {'snapshot': 'snapshot'}}
        connection = Mock()
        connection.execute.return_value.fetchone.side_effect = [('sha256',), (1,)]
        result = accepted_result(connection, state, 'job')
        self.assertEqual((result['same_run_id'], result['same_job_id'], result['accepted_result_sha256']), ('run', 'job', 'sha256'))
        with self.assertRaises(AssertionError):
            accepted_result(connection, state, 'different-job')
        for rows in ((('sha256',), (2,)), (None, (1,))):
            connection.execute.return_value.fetchone.side_effect = rows
            with self.assertRaises(AssertionError):
                accepted_result(connection, state, 'job')
