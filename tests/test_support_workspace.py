import csv
import hashlib
import io
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from threading import Thread
import unittest
from unittest.mock import patch
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from scripts.support_workspace import ROOT, server


class SupportWorkspaceTests(unittest.TestCase):
    def test_upload_changed_input_saved_evidence_and_rejections_without_provider_calls(self):
        sample = (ROOT / 'docs/demo/Sprint3SupportTickets.csv').read_bytes()
        with TemporaryDirectory() as directory:
            web = Path(directory)
            (web / 'index.html').write_text('<div id="root">Current app</div>')
            application = server(0, web)
            thread = Thread(target=application.serve_forever, daemon=True)
            thread.start()
            origin = f'http://127.0.0.1:{application.server_port}'

            def post(body, **headers):
                request = Request(origin + '/api/support-check', data=body,
                                  headers={'Content-Type': 'text/csv', **headers})
                try:
                    with urlopen(request, timeout=5) as response:
                        return response.status, json.load(response)
                except HTTPError as error:
                    return error.code, json.load(error)

            try:
                with patch('runtime.analysis_agent.request', side_effect=AssertionError('Provider dispatch forbidden')):
                    with urlopen(origin + '/', timeout=5) as response:
                        self.assertEqual(response.url, origin + '/support')
                        self.assertIn(b'Current app', response.read())
                    status, initial = post(sample)
                    self.assertEqual(status, 200)
                    self.assertEqual(initial['selected_queues'], ['Email'])
                    self.assertTrue(initial['fictional'])
                    self.assertEqual(initial['evidence']['input_sha256'], hashlib.sha256(sample).hexdigest())
                    self.assertEqual(len(initial['evidence']['records']), 24)
                    self.assertIn('| Email | 8 | 12 |', initial['markdown'])
                    self.assertIn('S3-E08', initial['markdown'])
                    self.assertNotIn('[input.csv]', initial['markdown'])

                    reader = csv.DictReader(io.StringIO(sample.decode()))
                    fields, tickets = reader.fieldnames, list(reader)
                    for ticket in tickets:
                        if ticket['channel'] == 'Chat':
                            ticket['resolution_time_hours'] = '20'
                    stream = io.StringIO()
                    writer = csv.DictWriter(stream, fieldnames=fields)
                    writer.writeheader(); writer.writerows(tickets)
                    status, changed = post(stream.getvalue().encode())
                    self.assertEqual(status, 200)
                    self.assertEqual(changed['selected_queues'], ['Chat'])
                    self.assertFalse(changed['fictional'])
                    self.assertEqual(changed['evidence']['table'][0]['mean'], 20)
                    self.assertIn('S3-C08', changed['markdown'])
                    self.assertNotEqual(changed['evidence']['input_sha256'], initial['evidence']['input_sha256'])

                    tied = stream.getvalue().replace(',20\r\n', ',12\r\n').encode()
                    status, result = post(tied)
                    self.assertEqual(status, 200)
                    self.assertEqual(result['selected_queues'], ['Chat', 'Email'])
                    special = sample.replace(b',Email,', b',Email|A,')
                    status, result = post(special)
                    self.assertEqual(status, 200)
                    self.assertEqual(result['selected_queues'], ['Email|A'])
                    self.assertIn('Email\\|A', result['markdown'])

                    for body, headers, expected in (
                        (b'not,a,support,file\n1,2,3,4\n', {}, 400),
                        (b'ticket_id,channel,resolution_time_hours\nbad,Email,-1\nok,Chat,2\n', {}, 400),
                        (sample, {'Origin': 'https://another-site.example'}, 403),
                        (sample, {'Host': 'another-site.example'}, 403),
                        (sample, {'Content-Type': 'application/json'}, 415),
                        (sample, {'Content-Length': '1048577'}, 413),
                    ):
                        with self.subTest(expected=expected, headers=headers):
                            status, error = post(body, **headers)
                            self.assertEqual(status, expected)
                            self.assertIn('detail', error)
            finally:
                application.shutdown(); application.server_close(); thread.join(timeout=5)


if __name__ == '__main__':
    unittest.main()
