import copy
import unittest

from runtime.source_validation import compare_page, same_meaning


class MeaningChecks(unittest.TestCase):
    def setUp(self):
        self.original = {'raw_input_id':'original','schema':'s','table':'t','columns':['id','price','at','category'],
            'identity_column':'id','rows':[[1,'-2.5000','12/31/2020','001'],[2,'1.25','12/30/2020','']]}
        self.page = {**self.original,'rows':[[1,'-2.5000','2020-12-31T00:00:00','001'],[2,'1.25','2020-12-30T00:00:00','']],'unresolved':[]}
        self.meanings = [{'name':name,'role':role,'confidence':confidence,'unit':unit,'date_format':date}
            for name,role,confidence,unit,date in [('id','identifier','supported',None,None),
                ('price','unit_price','supported','GBP',None),('at','date','supported',None,'month_first'),
                ('category','category','ambiguous',None,None)]]
        self.units = {field['name']:field['unit'] for field in self.meanings}

    def test_independent_values_accept_only_preserved_meaning(self):
        self.assertEqual(compare_page(self.page,self.original,self.meanings,self.units,set()),[])
        price = self.meanings[1]
        self.assertTrue(same_meaning('0.000000000000000000000000000001','0.000000000000000000000000000001',price))
        self.assertFalse(same_meaning('0','0.000000000000000000000000000001',price))
        self.assertFalse(same_meaning('2020-12-31T00:00:00+00:00','12/31/2020',self.meanings[2]))
        self.assertFalse(same_meaning(None,'',self.meanings[3]))

    def test_join_duplication_units_exclusions_and_value_changes_fail(self):
        duplicate = copy.deepcopy(self.page);duplicate['rows'].append(duplicate['rows'][0])
        omitted = copy.deepcopy(self.page);omitted['rows'].pop()
        mixed = {**self.page,'units':{**self.units,'price':'USD'}}
        changed = copy.deepcopy(self.page);changed['rows'][0][1]='2.5'
        categories = copy.deepcopy(self.page);categories['rows'][0][3]='1'
        for page,reason in [(duplicate,'Duplicate identity or join fan-out'),(omitted,'Unexplained source exclusion'),
                            (mixed,'Mixed or changed units are not accepted'),(changed,'Prepared value changed meaning'),
                            (categories,'Prepared value changed meaning')]:
            with self.subTest(reason=reason):
                failures = compare_page(page,self.original,self.meanings,self.units,set())
                self.assertTrue(any(f['reason']==reason and f['raw_input_id']=='original' and f['source_row_ids'] for f in failures))
        self.assertTrue(compare_page(self.page,self.original,self.meanings,{**self.units,'price':'USD'},set()))


if __name__ == '__main__':
    unittest.main()
