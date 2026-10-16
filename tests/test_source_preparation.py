"""Configured transformations and the actual isolated execution boundary."""
import os
from pathlib import Path
import tempfile
import unittest

from runtime import preparation_worker as worker, source_preparation as preparation, sandbox


class PreparationChecks(unittest.TestCase):
    def test_conversions_preserve_precision_and_do_not_invent_values(self):
        self.assertEqual(worker.convert('-0.0100000000000000001', 'decimal'), '-0.0100000000000000001')
        self.assertEqual(worker.convert('00123', 'preserve'), '00123')
        self.assertEqual(worker.convert('12/31/2020 23:59', 'month_first'), '2020-12-31T23:59:00')
        self.assertEqual(worker.convert('2020-01-01T00:00:00+02:00', 'iso'), '2020-01-01T00:00:00+02:00')
        for value in (None, '', '  '):
            self.assertEqual(worker.convert(value, 'decimal'), value)
        for value in ('NaN', 'Infinity', True):
            with self.assertRaises((ValueError, ArithmeticError)):
                worker.convert(value, 'decimal')

    def test_page_rejects_changed_sources_or_lost_records(self):
        original = {'raw_input_id':'original','schema':'s','table':'t','columns':['id','value'],
                    'identity_column':'id','rows':[[1,'value']]}
        page = {**original,'unresolved':[]}
        self.assertEqual(preparation.validate_page(page, original), page)
        for changed in ({**page,'rows':[]}, {**page,'rows':[[2,'value']]}, {**page,'raw_input_id':'other'},
                        {**page,'unresolved':[{'index':1,'fields':['value']}]}):
            with self.assertRaises(ValueError):
                preparation.validate_page(changed, original)

    @unittest.skipUnless(os.getenv('BACKINTEL_PREPARATION_IMAGE'), 'Requires an operator-selected local sandbox image')
    def test_preparation_profile_refuses_host_files_writes_and_network(self):
        image = os.environ['BACKINTEL_PREPARATION_IMAGE']
        with tempfile.TemporaryDirectory(prefix='BackIntelPreparationBoundary') as folder:
            forbidden = Path(folder)/'host-only.txt'
            forbidden.write_text('synthetic host-only marker')
            for source in (f'print(open({str(forbidden)!r}).read())',
                           'open("/input/snapshot.json","w").write("changed")',
                           'import socket; socket.create_connection(("192.0.2.1",443),timeout=1)'):
                with self.subTest(source=source):
                    result = sandbox.run_candidate(source, {}, image, purpose='preparation', timeout_seconds=5)
                    self.assertEqual(result['stop_reason'], 'process_failed', result)
                    self.assertTrue(result['cleanup_confirmed'])
                    self.assertEqual(result['network'], 'none')


if __name__ == '__main__':
    unittest.main()
