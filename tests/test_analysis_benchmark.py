"""Adversarial receipt/scoring checks; no database, model or provider required."""
import copy
import csv
import json
import subprocess
import tempfile
import unittest
from pathlib import Path

from scripts import analysis_benchmark_support as scoring


class BenchmarkChecks(unittest.TestCase):
    def test_default_preflight_preserves_paid_receipt(self):
        import os
        from unittest.mock import patch
        from scripts import analysis_benchmark as producer
        with tempfile.TemporaryDirectory() as directory:
            accepted = Path(directory)/'Analysis/benchmark-evidence.json'
            accepted.parent.mkdir()
            accepted.write_text('{"status":"passed","paid_fixture":true}')
            before = accepted.read_bytes()
            with patch.dict(os.environ, {'BACKINTEL_MODEL_DIR':directory}), \
                 patch('sys.argv', ['analysis_benchmark', '--domains', 'churn']), \
                 patch.object(producer, 'source_files', return_value=[self.path]), \
                 patch.object(producer, 'candidate_identity', return_value={}):
                self.assertEqual(producer.main(), 1)
            self.assertEqual(accepted.read_bytes(), before)
            self.assertTrue((accepted.parent/'benchmark-preflight.json').is_file())

    def test_campaign_recomputes_answers_and_accepts_current_schema(self):
        from copy import deepcopy
        from unittest.mock import patch
        from scripts.validation import benchmark_campaign as campaign
        helper = vars(scoring).copy()
        helper['SCENARIOS'] = [scoring.SCENARIOS[1]]
        helper['receipt_identity_error'] = lambda *args: None
        answer = {'scenario':self.spec, 'status':'passed', 'correct':True,
                  'run_id':'run', 'run':self.run, 'evidence':self.evidence}
        receipt = {'schema':scoring.SUITE_VERSION, 'mode':'real', 'charge_status':'measured',
                   'scenarios':[self.spec], 'scenario_hash':scoring.digest([self.spec]),
                   'charges':[{'run_id':'run'}], 'domains':[{'domain':'churn', 'status':'passed',
                   'oracle':self.oracle, 'snapshot_id':'snapshot', 'answers':[answer]}]}
        def read_script(path):
            return helper if str(path).endswith('analysis_benchmark_support.py') else {'source_files':lambda domain:[self.path]}
        with patch.object(campaign, 'identity_error', return_value=None), patch.object(campaign.runpy, 'run_path', side_effect=read_script):
            self.assertEqual(campaign.real_result({'evidence':'analyst'}, 'churn', [receipt], {})[0], 'passed')
            for field in ('run', 'evidence', 'oracle', 'measurement', 'charge'):
                forged = deepcopy(receipt)
                row = forged['domains'][0]
                if field == 'oracle': row[field] = {'fabricated':True}
                elif field == 'measurement':
                    row['answers'][0]['run']['result']['summary'] = 'The mean is 99.'
                    row['answers'][0]['run']['result']['findings'][0]['claim'] = 'The mean is 99.'
                elif field == 'charge': forged['charges'] = [{'run_id':'other-run'}]
                else: row['answers'][0][field] = {}
                with self.subTest(field=field):
                    self.assertEqual(campaign.real_result({'evidence':'analyst'}, 'churn', [forged], {})[0], 'blocked')

    def test_real_validator_accepts_the_producers_dependency_digest(self):
        import ast
        from unittest.mock import patch
        from runtime import analysis_models as models
        tree=ast.parse((scoring.ROOT/'scripts/validation/check_analysis.py').read_text())
        assignment=next(node for node in ast.walk(tree) if isinstance(node,ast.Assign) and any(isinstance(target,ast.Name) and target.id=='verify' for target in node.targets))
        code=assignment.value.func.value.value.replace('REQUIRE_COMPARISONS','True')
        guard=next(node for node in ast.walk(ast.parse(code)) if isinstance(node,ast.If) and isinstance(node.body[0],ast.Raise) and 'Model implementation differs' in ast.unparse(node.body[0]))
        check=compile(ast.Module(body=[guard],type_ignores=[]),'<comparison identity check>','exec')
        with patch.object(models,'versions',return_value={}), patch.object(models,'checkpoint',return_value=(None,{})):
            body={'dependencies':models.runtime_dependencies('churn')}
        scope={'body':body,'Path':Path,'fingerprint':scoring.fingerprint,'digest':scoring.digest}
        exec(check,scope)
        body['dependencies']['implementation_sha256']=scoring.fingerprint(scoring.ROOT/'runtime/analysis_models.py')['sha256']
        with self.assertRaisesRegex(RuntimeError,'Model implementation differs'):
            exec(check,scope)

    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.path = Path(self.directory.name) / 'telco.csv'
        with self.path.open('w', newline='') as stream:
            writer = csv.DictWriter(stream, fieldnames=['customerID', 'Churn', 'Contract'])
            writer.writeheader()
            writer.writerows([{'customerID':'one','Churn':'No','Contract':'Annual'},
                              {'customerID':'two','Churn':'Yes','Contract':'Monthly'},
                              {'customerID':'three','Churn':'No','Contract':'Monthly'}])
        self.oracle = scoring.raw_oracle('churn', [self.path], 100)
        self.spec = scoring.scenario_spec('churn', scoring.SCENARIOS[1], 'contract')
        value = scoring.expected_result(self.spec, self.oracle)
        claim = f"The mean is {value['value']}."
        self.run = {'id':'run','goal_id':'goal','snapshot_id':'snapshot','status':'succeeded',
                    'result':{'summary':claim,'findings':[{'claim':claim,'kind':'fact','evidence_ids':['proof']}],
                              'mode':'real','sources':{'domain':'churn','snapshot':'snapshot'}}}
        self.evidence = {'proof':{'kind':'calculation','task_id':'analysis-goal-goal',
                                 'body':{'snapshot':'snapshot','tool':'summarize','arguments':{},
                                         'result':{'kind':'observed','target':'churn','table':[{'group':'all',**self.oracle['overall']}]}}}}

    def score(self):
        return scoring.score_answer(self.run,self.evidence,self.spec,self.oracle,'snapshot')

    def test_structured_answer_and_independent_calculation_pass(self):
        from runtime.analysis_agent import validate_answer
        result = self.evidence['proof']['body']['result']
        self.run['result']['limitations'] = []
        answer = {key: self.run['result'][key] for key in ('summary', 'findings', 'limitations')}
        self.run['result'].update(validate_answer(answer, [{**result, 'tool': 'summarize', 'evidence_id': 'proof'}]))
        self.assertTrue(self.score()['correct'])
        self.assertEqual(self.oracle['records'],3)
        self.assertAlmostEqual(self.oracle['overall']['mean'],1/3)

    def test_every_scenario_claim_passes_runtime_validation_and_independent_scoring(self):
        from runtime.analysis_agent import validate_answer
        for domain in scoring.TARGETS:
            for scenario in scoring.SCENARIOS:
                spec = scoring.scenario_spec(domain, scenario, 'contract')
                expected = scoring.expected_result(spec, self.oracle)
                count_case = scenario['id'] == 'record_count'
                grouped = scenario['id'].endswith('_group')
                claim = (f"Source contains {expected['value']} records." if count_case else
                         f"Group {expected['group']} mean is {expected['value']}." if grouped else
                         f"The mean is {expected['value']}.")
                result = ({'records': expected['value']} if count_case else
                          {'kind': 'observed', 'target': spec['target'], 'table': [
                              {'group': expected['group'], 'mean': expected['value'], 'count': expected['count']}]})
                tool = 'inspect_source' if count_case else 'summarize'
                arguments = {'group': 'contract' if grouped else None,
                             'order': 'descending' if scenario['id'] == 'highest_group' else 'ascending'}
                evidence = {'proof': {'kind': 'calculation', 'task_id': 'analysis-goal-goal', 'body': {
                    'snapshot': 'snapshot', 'tool': tool, 'arguments': arguments, 'result': result}}}
                answer = {'summary': claim, 'limitations': [], 'findings': [
                    {'claim': claim, 'kind': 'fact', 'evidence_ids': ['proof']}]}
                with self.subTest(domain=domain, scenario=scenario['id']):
                    validate_answer(answer, [{**result, 'tool': tool, 'evidence_id': 'proof'}], group='contract')
                    run = {**self.run, 'result': {**answer, 'mode': 'real', 'sources': {'domain': domain, 'snapshot': 'snapshot'}}}
                    self.assertTrue(scoring.score_answer(run, evidence, spec, self.oracle, 'snapshot')['correct'])
                    if not count_case:
                        result['table'][0]['count'] += 1
                        with self.assertRaisesRegex(ValueError, 'calculation'):
                            scoring.score_answer(run, evidence, spec, self.oracle, 'snapshot')

    def test_incidental_numbers_and_group_names_never_pass(self):
        for text in ('The rate is 0.99; source identifier 0.3333333333333333.',
                     'Monthly is lowest, though Annual also exists.', '3 records; wrong mean 50%.'):
            with self.subTest(text=text):
                self.run['result']['summary']=text
                self.run['result']['findings'][0]['claim']=text
                with self.assertRaisesRegex(ValueError,'structured'):
                    self.score()

    def test_wrong_value_group_unit_snapshot_goal_and_mode_fail(self):
        original=copy.deepcopy(self.run)
        for claim in ('The mean is 99.', 'Group Monthly mean is 0.3333333333333333.',
                      'The mean is 33.33333333333333%.', 'The mean is True.'):
            with self.subTest(claim=claim):
                self.run=copy.deepcopy(original)
                self.run['result']['summary']=claim
                self.run['result']['findings'][0]['claim']=claim
                with self.assertRaises(ValueError):self.score()
        self.run=copy.deepcopy(original)
        self.evidence['proof']['body']['snapshot']='old'
        with self.assertRaisesRegex(ValueError,'snapshot'):self.score()
        self.evidence['proof']['body']['snapshot']='snapshot'
        self.evidence['proof']['task_id']='analysis-goal-other'
        with self.assertRaisesRegex(ValueError,'goal'):self.score()
        self.evidence['proof']['task_id']='analysis-goal-goal'
        self.run['result']['mode']='fixture'
        with self.assertRaisesRegex(ValueError,'mode'):self.score()

    def test_correct_summary_with_wrong_or_missing_calculation_fails(self):
        table=self.evidence['proof']['body']['result']['table']
        table[0]['mean']=.75
        with self.assertRaisesRegex(ValueError,'calculation'):self.score()
        table[0]['mean']=1/3
        self.evidence['proof']['body']['arguments']={'group':'contract'}
        with self.assertRaisesRegex(ValueError,'calculation'):self.score()
        self.evidence={}
        with self.assertRaises(ValueError):self.score()

    def test_contradictory_or_uncited_finding_fails(self):
        self.run['result']['findings'][0]['claim']='The mean is 100.'
        with self.assertRaisesRegex(ValueError,'Finding'):self.score()
        self.run['result']['findings'][0]['claim']=self.run['result']['summary']
        self.run['result']['findings'][0]['evidence_ids']=[]
        with self.assertRaisesRegex(ValueError,'Finding'):self.score()

    def test_extreme_ties_and_original_units_are_explicit(self):
        self.oracle['groups']={'Z':{'count':2,'labeled':2,'mean':.5},'A':{'count':2,'labeled':2,'mean':.5}}
        for scenario in scoring.SCENARIOS[2:]:
            spec=scoring.scenario_spec('churn',scenario,'contract')
            self.assertEqual(scoring.expected_result(spec,self.oracle)['group'],'A')
            self.assertEqual(spec['unit'],'fraction')
        self.assertEqual(scoring.SCENARIOS[3]['partition'],'held_out')
        self.assertNotEqual(scoring.scenario_spec('churn',scoring.SCENARIOS[2],'contract')['sha256'],
                            scoring.scenario_spec('churn',scoring.SCENARIOS[3],'contract')['sha256'])

    def test_raw_cohort_hash_selection_is_order_independent_and_detects_duplicates(self):
        oracle=scoring.raw_oracle('churn',[self.path],2)
        lines=self.path.read_text().splitlines()
        self.path.write_text('\n'.join([lines[0],*reversed(lines[1:])])+'\n')
        reordered=scoring.raw_oracle('churn',[self.path],2)
        self.assertEqual(oracle['cohort_hash'],reordered['cohort_hash'])
        self.assertNotEqual(oracle['files'],reordered['files'])
        self.path.write_text('\n'.join([*lines,lines[1]])+'\n')
        with self.assertRaisesRegex(ValueError,'Duplicate'):scoring.raw_oracle('churn',[self.path],2)

    def test_maintenance_oracle_includes_official_labels_at_engine_grain(self):
        root=Path(self.directory.name)
        train,test,labels=(root/name for name in ('train.txt','test.txt','labels.txt'))
        line=lambda engine,cycle:' '.join(map(str,[engine,cycle]+[0]*24))+'\n'
        train.write_text(line(1,1)+line(1,2))
        test.write_text(line(1,1)+line(1,2))
        labels.write_text('7\n')
        result=scoring.raw_oracle('maintenance',[train,test,labels],100)
        self.assertEqual(result['records'],3)
        self.assertEqual(result['groups']['train-1']['mean'],.5)
        self.assertEqual(result['groups']['test-1']['mean'],7)

    def test_source_missing_is_not_substituted(self):
        self.path.unlink()
        with self.assertRaises(FileNotFoundError):scoring.raw_oracle('churn',[self.path],100)

    def test_stale_dirty_fixture_and_changed_scenarios_cannot_qualify(self):
        candidate={'commit':'head','source_hash':'source','dirty':False,'verified':True}
        receipt={'candidate':dict(candidate),'schema':scoring.SUITE_VERSION,'mode':'real',
                 'scenario_hash':scoring.digest([self.spec]),'charge_status':'measured',
                 'charges':[],'provider_calls':0,'provider_usd':0}
        self.assertIsNone(scoring.receipt_identity_error(receipt,candidate,[self.spec]))
        for field,value in (('commit','old'),('source_hash','other'),('dirty',True),('verified',False)):
            changed=copy.deepcopy(receipt);changed['candidate'][field]=value
            self.assertIsNotNone(scoring.receipt_identity_error(changed,candidate,[self.spec]))
        for field,value in (('mode','fixture'),('schema','old'),('scenario_hash','wrong'),('charge_status','unknown'),('provider_usd',5),('charges',[{'charge':None}])):
            changed=copy.deepcopy(receipt);changed[field]=value
            self.assertIsNotNone(scoring.receipt_identity_error(changed,candidate,[self.spec]))
        self.assertIsNotNone(scoring.receipt_identity_error(receipt,{**candidate,'dirty':True},[self.spec]))

    def test_missing_source_cli_writes_blocked_receipt_without_runtime_dependencies(self):
        import os
        import sys
        output=Path(self.directory.name)/'receipt.json'
        result=subprocess.run([sys.executable,'-m','scripts.analysis_benchmark','--domains','credit','--output',str(output)],
                              cwd=scoring.ROOT,env={**os.environ,'BACKINTEL_DATASET_DIR':str(Path(self.directory.name)/'missing')},
                              capture_output=True,text=True)
        self.assertEqual(result.returncode,1,result.stderr)
        receipt=json.loads(output.read_text())
        self.assertEqual(receipt['status'],'blocked')
        self.assertIn('Missing approved source file',receipt['domains'][0]['reason'])
        self.assertEqual(receipt['provider_calls'],0)
        self.assertEqual(receipt['provider_usd'],0)

    def test_embedded_validator_executes_and_reports_missing_domain(self):
        import ast
        import os
        import sys
        tree=ast.parse((scoring.ROOT/'scripts/validation/check_analysis.py').read_text())
        assignment=next(node for node in ast.walk(tree) if isinstance(node,ast.Assign)
                        and any(isinstance(target,ast.Name) and target.id=='verify' for target in node.targets))
        code=assignment.value.func.value.value.replace('REQUIRE_COMPARISONS','False')
        setup="""import sys,types
runtime=types.ModuleType('runtime')
store=types.ModuleType('runtime.analysis_store')
data=types.ModuleType('runtime.analysis_data')
data.CONFIG={'sources':{'credit':{}}}
data.source_files=lambda domain: (_ for _ in ()).throw(AssertionError('No source read expected'))
runtime.analysis_store=store
sys.modules.update({'runtime':runtime,'runtime.analysis_store':store,'runtime.analysis_data':data})
"""
        result=subprocess.run([sys.executable,'-c',setup+code],cwd=self.directory.name,
                              env={**os.environ,'PYTHONPATH':str(scoring.ROOT)},
                              input=json.dumps({'candidate':{'files':{}},'domains':[]}),capture_output=True,text=True)
        self.assertEqual(result.returncode,0,result.stderr)
        receipt=json.loads(result.stdout)
        self.assertEqual(receipt['status'],'blocked')
        self.assertEqual(receipt['domains'][0]['reason'],'RuntimeError: Domain receipt missing or duplicated')

    def test_host_manifest_verifies_complete_runtime_set_without_claiming_container_git(self):
        root=Path(self.directory.name)/'image';root.mkdir()
        names=('runtime/analysis_agent.py','runtime/analysis_data.py','runtime/analysis_store.py',
               'runtime/analysis_service.py','scripts/analysis_benchmark.py',
               'scripts/analysis_benchmark_support.py','config/analysis.json','migrations/001.sql')
        for name in names:
            file=root/name;file.parent.mkdir(parents=True,exist_ok=True);file.write_text('fixture source')
        files={name:scoring.fingerprint(root/name)['sha256'] for name in names}
        manifest=Path(self.directory.name)/'host.json'
        host={'commit':'host-commit','dirty':False,'verified':True,'files':files,'source_hash':scoring.digest(files)}
        manifest.write_text(json.dumps(host))
        actual=scoring.candidate_identity(root,manifest)
        self.assertTrue(actual['verified'])
        self.assertIn('container Git not independently verified',actual['identity_basis'])
        (root/'runtime/extra.py').write_text('extra')
        self.assertFalse(scoring.candidate_identity(root,manifest)['verified'])
        (root/'runtime/extra.py').unlink()
        (root/'runtime/analysis_agent.py').write_text('changed')
        self.assertFalse(scoring.candidate_identity(root,manifest)['verified'])
        (root/'runtime/analysis_agent.py').write_text('fixture source')
        host['dirty']=True;manifest.write_text(json.dumps(host))
        self.assertFalse(scoring.candidate_identity(root,manifest)['verified'])

    def test_candidate_identity_tracks_actual_untracked_files(self):
        root=Path(self.directory.name)
        subprocess.run(['git','init','-q',str(root)],check=True)
        subprocess.run(['git','-C',str(root),'add','telco.csv'],check=True)
        # Use a temporary index/tree rather than creating a commit in the user's repository.
        tree=subprocess.check_output(['git','-C',str(root),'write-tree'],text=True).strip()
        env={'GIT_AUTHOR_NAME':'Fixture','GIT_AUTHOR_EMAIL':'fixture@example.invalid',
             'GIT_COMMITTER_NAME':'Fixture','GIT_COMMITTER_EMAIL':'fixture@example.invalid'}
        import os
        commit=subprocess.check_output(['git','-C',str(root),'commit-tree',tree,'-m','Fixture'],env={**os.environ,**env},text=True).strip()
        subprocess.run(['git','-C',str(root),'update-ref','HEAD',commit],check=True)
        before=scoring.candidate_identity(root)
        self.assertFalse(before['dirty'])
        (root/'new.py').write_text('value = 1\n')
        after=scoring.candidate_identity(root)
        self.assertTrue(after['dirty'])
        self.assertIn('new.py',after['files'])
        self.assertNotEqual(before['source_hash'],after['source_hash'])


if __name__=='__main__':unittest.main()
