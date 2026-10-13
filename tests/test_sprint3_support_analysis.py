import csv
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from scripts.sprint3_support_analysis import analyze


class FreshSupportAnalysisTests(unittest.TestCase):
    def test_changed_tickets_change_the_finding_without_provider_dispatch(self):
        sample = Path(__file__).resolve().parents[1] / 'docs/demo/Sprint3SupportTickets.csv'
        with sample.open(newline='') as stream:
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
        self.assertEqual(result['selected_queues'], ['Chat'])
        self.assertEqual(result['evidence']['table'][0]['mean'], 20)
        self.assertEqual(result['evidence']['table'][0]['count'], 8)
        self.assertEqual(len(result['evidence']['records']), 24)


if __name__ == '__main__':
    unittest.main()
