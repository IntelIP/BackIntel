import copy
import json
from fractions import Fraction
import unittest

from runtime.source_answer import decimal_text, exact_number, execute_method, method_inputs, validate_method


class ConnectedAnswerChecks(unittest.TestCase):
    def setUp(self):
        self.method = {'schema_name':'retail','table_name':'lines','quantity_field':'units','unit_price_field':'price',
                       'invoice_field':'invoice','product_field':'product','country_field':'country','date_field':'at',
                       'currency':'GBP','cancellation_prefix':'C','rationale':'Synthetic field bindings for the agreed metric.'}
        self.objective = {'metric':'Sum units multiplied by price in GBP, grouped separately by product and country. C-prefixed cancellations.', 'target':None}
        fields = [{'name':name,'role':role,'confidence':confidence,'unit':unit}
                  for name,role,confidence,unit in [('units','quantity','supported',None),('price','unit_price','supported','GBP'),
                      ('invoice','identifier','ambiguous',None),('product','identifier','ambiguous',None),
                      ('country','category','supported',None),('at','date','supported',None)]]
        self.interpretation = {'interpretation':{'tables':[{'schema_name':'retail','table_name':'lines','fields':fields}]},'profile':{'rows':5}}
        self.page = {'raw_input_id':'source','schema':'retail','table':'lines','identity_column':'id',
                     'columns':['id','units','price','invoice','product','country','at'],'unresolved':[],
                     'rows':[[1,'2','3.25','001','A','UK','2020-12-01T00:00:00'],
                             [2,'-1','3.25','c002','A','UK','2020-12-02T00:00:00'],
                             [3,'1','3.25','003','B','FR','2020-12-03T00:00:00'],
                             [4,'1','-0.01','004','','','2020-12-04T00:00:00'],
                             [5,'1','0.01','005',None,None,'2020-12-05T00:00:00']]}

    def test_generated_bindings_are_scoped_and_canonical(self):
        self.assertEqual(validate_method(self.method,self.interpretation,self.objective),self.method)
        for changed in ({**self.method,'quantity_field':'secret'}, {**self.method,'currency':'USD'},
                        {**self.method,'cancellation_prefix':'X'}, {**self.method,'product_field':'invoice'}):
            with self.assertRaises(ValueError):
                validate_method(changed,self.interpretation,self.objective)
        goal = {'body':{'question':'Synthetic objective','objective':self.objective}}
        reordered = {'body':dict(reversed(list(goal['body'].items())))}
        self.assertEqual(method_inputs(goal,self.interpretation),method_inputs(reordered,self.interpretation))
        revision = method_inputs(goal,self.interpretation,'Recheck the selected fields')
        self.assertEqual(json.loads(revision[1]['content'])['revision_request'],'Recheck the selected fields')
        self.assertNotEqual(revision,method_inputs(goal,self.interpretation))
        with self.assertRaises(ValueError):
            validate_method(self.method,self.interpretation,{**self.objective,'target':'Increase value by 10%'})

    def test_complete_exact_signed_values_groups_and_ties(self):
        result = execute_method(self.method,[self.page],5)
        self.assertEqual(result['totals'],{'net_invoice_value':'6.5','signed_cancellation_value':'-3.25',
                                         'value_without_cancellations':'9.75','cancellation_reduction':'3.25'})
        self.assertEqual(result['coverage']['processed_rows'],5)
        self.assertEqual(result['cancellation_rows'],1)
        product,country = result['dimensions']
        self.assertEqual([group['value'] for group in product['leaders']],['A','B'])
        self.assertEqual([group['value'] for group in country['leaders']],['FR','UK'])
        self.assertEqual({group['value'] for group in product['groups']},{'A','B','',None})
        huge = exact_number('1'+'0'*90)
        tiny = exact_number('0.'+'0'*89+'1')
        self.assertEqual(exact_number(decimal_text(huge+tiny)),huge+tiny)
        self.assertEqual(decimal_text(Fraction(1,8)),'0.125')

    def test_missing_partial_or_duplicated_work_never_becomes_an_answer(self):
        for pages,expected in [([self.page],6),([self.page,self.page],10)]:
            with self.assertRaises(ValueError):
                execute_method(self.method,pages,expected)
        missing = copy.deepcopy(self.page);missing['rows'][0][1]=''
        with self.assertRaises(ValueError):
            execute_method(self.method,[missing],5)
        for value in ('NaN','1e1001'):
            with self.assertRaises(ValueError):
                exact_number(value)


if __name__ == '__main__':
    unittest.main()
