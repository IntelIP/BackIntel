import copy
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from runtime import source_workflows as workflows


class WorkflowPackageChecks(unittest.TestCase):
    def test_replacement_inputs_must_match_the_saved_objective_and_complete_contract(self):
        body = {'goal_id':'goal','goal_version':2,'connection':{'source_ref':'retail'},
                'accepted':{'collection':{'run_id':'accepted'}},
                'input_contract':{'tables':[{'schema':'retail','table':'lines'}]}}
        package = workflows.package_body(body)
        collection = {'id':'replacement','goal_id':'goal','goal_version':2,'status':'succeeded',
                      'body':{'operation':'collection'},'result':{'source_ref':'retail',
                      'coverage':{'expected_rows':5,'collected_rows':5,'pending_rows':0},
                      'inputs':[{'schema':'retail','table':'lines','raw_input_id':'raw'}]}}
        with patch.object(workflows,'read',return_value=package),patch.object(workflows,'load',return_value={'status':'ready'}),\
             patch.object(workflows.db,'goal',return_value={'version':2}),patch.object(workflows.db,'run',return_value=collection):
            binding=workflows.bind(package['version'],'replacement',{'id':'actor'})
            self.assertEqual(binding['input_ref'],'replacement')
            for changed in (
                {**collection,'goal_id':'another-goal'},
                {**collection,'goal_version':1},
                {**collection,'status':'partial'},
                {**collection,'result':{**collection['result'],'coverage':{'expected_rows':6,'collected_rows':5,'pending_rows':1}}},
                {**collection,'result':{**collection['result'],'inputs':[{'schema':'private','table':'payroll'}]}},
            ):
                with patch.object(workflows.db,'run',return_value=changed),self.assertRaises(ValueError):
                    workflows.bind(package['version'],'replacement',{'id':'actor'})

    def test_versions_are_immutable_and_dependency_failures_are_actionable(self):
        package = workflows.package_body({'method': {'quantity': 'units'}, 'connection': {'secret_ref': 'SOURCE_DSN'}})
        self.assertEqual(workflows.validate_package(package), package)
        changed = copy.deepcopy(package)
        changed['body']['method']['quantity'] = 'other'
        with self.assertRaisesRegex(ValueError, 'version digest'):
            workflows.validate_package(changed)
        self.assertNotEqual(workflows.package_body(changed['body'])['version'], package['version'])
        with self.assertRaises(ValueError):
            workflows.validate_package({**package, 'credentials': 'must not accept extra fields'})
        dependencies = workflows.runtime_dependencies('sha256:' + 'a' * 64)
        with patch.object(workflows.sandbox, 'resolve_image', return_value=dependencies['image']):
            self.assertEqual(workflows.dependency_issues(dependencies), [])
            with tempfile.TemporaryDirectory() as folder:
                issues = workflows.dependency_issues(dependencies, root=Path(folder))
                self.assertEqual(len(issues), len(workflows.COMPONENTS))
                self.assertTrue(all('restore this version' in issue for issue in issues))
        with patch.object(workflows.sandbox, 'resolve_image', side_effect=FileNotFoundError()):
            self.assertIn('pinned preparation image is unavailable', workflows.dependency_issues(dependencies)[0])


if __name__ == '__main__':
    unittest.main()
