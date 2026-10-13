import csv
from contextlib import redirect_stderr, redirect_stdout
import hashlib
import io
import json
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from scripts.sprint3_support_analysis import MAX_BYTES, MAX_TICKETS, analyze, main

ROOT = Path(__file__).resolve().parents[1]
SAMPLE = ROOT / 'docs/demo/Sprint3SupportTickets.csv'


class FreshSupportAnalysisTests(unittest.TestCase):
    def test_changed_tickets_change_the_finding_without_provider_dispatch(self):
        with SAMPLE.open(newline='') as stream:
            reader = csv.DictReader(stream)
            fields, tickets = reader.fieldnames, list(reader)
        for ticket in tickets:
            if ticket['channel'] == 'Chat':
                ticket['resolution_time_hours'] = '20'
        with TemporaryDirectory() as directory:
            source = Path(directory) / 'changed-tickets.csv'
            with source.open('w', newline='') as stream:
                writer = csv.DictWriter(stream, fieldnames=fields)
                writer.writeheader()
                writer.writerows(tickets)
            with patch('runtime.analysis_agent.request', side_effect=AssertionError('Provider dispatch forbidden')):
                result = analyze(source)
                for ticket in tickets:
                    if ticket['channel'] == 'Chat':
                        ticket['resolution_time_hours'] = '12'
                with source.open('w', newline='') as stream:
                    writer = csv.DictWriter(stream, fieldnames=fields)
                    writer.writeheader()
                    writer.writerows(tickets)
                tied = analyze(source)
        self.assertEqual(result['selected_queues'], ['Chat'])
        self.assertEqual(result['evidence']['table'][0]['mean'], 20)
        self.assertEqual(result['evidence']['table'][0]['count'], 8)
        self.assertEqual(len(result['evidence']['records']), 24)
        self.assertFalse(result['fictional'])
        self.assertEqual(tied['selected_queues'], ['Chat', 'Email'])

    def test_command_saves_reports_labels_inputs_and_preserves_existing_output(self):
        with TemporaryDirectory() as directory:
            output = Path(directory) / 'report'
            args = ['--input', str(SAMPLE), '--output', str(output)]
            command = subprocess.run(
                [sys.executable, '-m', 'scripts.support_analysis', *args],
                cwd=ROOT, capture_output=True, text=True, check=True,
            )
            receipt = json.loads(command.stdout)
            self.assertEqual(receipt['selected_queues'], ['Email'])
            self.assertEqual(receipt['report'], str((output / 'report.md').resolve()))
            saved = {file.name: file.read_bytes() for file in output.iterdir()}
            self.assertEqual(set(saved), {'input.csv', 'report.json', 'report.md'})
            self.assertEqual(saved['input.csv'], SAMPLE.read_bytes())
            result = json.loads(saved['report.json'])
            self.assertTrue(result['fictional'])
            self.assertEqual(result['evidence']['input_sha256'], hashlib.sha256(saved['input.csv']).hexdigest())
            self.assertEqual([(row['group'], row['count'], row['mean']) for row in result['evidence']['table']],
                             [('Email', 8, 12), ('Chat', 8, 3.5), ('Phone', 8, 2)])
            self.assertEqual(len(result['evidence']['records']), 24)
            self.assertIn('S3-E08', saved['report.md'].decode())
            self.assertIn('[input.csv](input.csv)', saved['report.md'].decode())
            self.assertIn('[report.json](report.json)', saved['report.md'].decode())
            with patch('runtime.analysis_agent.request', side_effect=AssertionError('Provider dispatch forbidden')):
                with redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as error:
                    main(args)
                self.assertEqual(error.exception.code, 2)
                self.assertEqual(saved, {file.name: file.read_bytes() for file in output.iterdir()})
                source = Path(directory) / 'fictional.csv'
                source.write_bytes(SAMPLE.read_bytes().replace(b',Email,', b',Email|A,'))
                custom = Path(directory) / 'custom'
                with redirect_stdout(io.StringIO()):
                    main(['--input', str(source), '--output', str(custom), '--fictional'])
                self.assertTrue(json.loads((custom / 'report.json').read_text())['fictional'])
                self.assertIn('Email\\|A', (custom / 'report.md').read_text())
                source.write_bytes(b'\xef\xbb\xbf' + SAMPLE.read_bytes())
                supplied = analyze(source)
                self.assertEqual(supplied['selected_queues'], ['Email'])
                self.assertFalse(supplied['fictional'])

    def test_invalid_input_leaves_no_output(self):
        header = b'ticket_id,channel,resolution_time_hours\n'
        invalid = {
            'empty': b'',
            'no tickets': header,
            'missing columns': b'ticket_id,channel\na,Email\nb,Chat\n',
            'duplicate columns': b'ticket_id,channel,resolution_time_hours,channel\na,Email,1,Email\nb,Chat,2,Chat\n',
            'extra cells': header + b'a,Email,1,extra\nb,Chat,2\n',
            'missing value': header + b'a,Email\nb,Chat,2\n',
            'blank identity': header + b' ,Email,1\nb,Chat,2\n',
            'blank queue': header + b'a, ,1\nb,Chat,2\n',
            'duplicate identity': header + b'a,Email,1\na,Chat,2\n',
            'negative duration': header + b'a,Email,-1\nb,Chat,2\n',
            'nonnumeric duration': header + b'a,Email,unknown\nb,Chat,2\n',
            'nonfinite duration': header + b'a,Email,NaN\nb,Chat,inf\n',
            'one queue': header + b'a,Email,1\nb,Email,2\n',
            'too many queues': header + ''.join(f'{i},queue-{i},1\n' for i in range(21)).encode(),
            'too many tickets': header + ''.join(f'{i},queue-{i % 2},1\n' for i in range(MAX_TICKETS + 1)).encode(),
            'oversized': b'a' * (MAX_BYTES + 1),
            'invalid encoding': header + b'\xff,Email,1\nb,Chat,2\n',
            'malformed quoting': header + b'"a,Email,1\nb,Chat,2\n',
        }
        with TemporaryDirectory() as directory, patch(
            'runtime.analysis_agent.request', side_effect=AssertionError('Provider dispatch forbidden')
        ):
            source = Path(directory) / 'input.csv'
            output = Path(directory) / 'report'
            for name, body in invalid.items():
                with self.subTest(name=name):
                    source.write_bytes(body)
                    with redirect_stderr(io.StringIO()) as errors, self.assertRaises(SystemExit) as error:
                        main(['--input', str(source), '--output', str(output)])
                    self.assertEqual(error.exception.code, 2)
                    self.assertIn('error:', errors.getvalue())
                    self.assertFalse(output.exists())


if __name__ == '__main__':
    unittest.main()
