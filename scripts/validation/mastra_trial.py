"""Pass disposable API credentials on stdin to the real local Mastra agent."""
import json
from pathlib import Path
import subprocess


ROOT = Path(__file__).resolve().parents[2]


def invoke_mastra(client, version, input_ref, question, *, tool_name='run_backintel_workflow', lose_response=False):
    request = {'baseUrl': str(client.base_url), 'authorization': client.headers['Authorization'],
               'workflowVersion': version, 'inputRef': input_ref, 'question': question,
               'toolName': tool_name, 'loseResponse': lose_response, 'waitSeconds': 1200}
    result = subprocess.run(['node', str(ROOT/'integrations/mastra/trial.mjs')],
                            input=json.dumps(request), text=True, capture_output=True, timeout=1300, cwd=ROOT)
    if result.returncode:
        raise AssertionError('Mastra trial failed: ' + result.stderr[-2000:])
    lines = [line.removeprefix('BACKINTEL_TRIAL_RESULT=') for line in result.stdout.splitlines()
             if line.startswith('BACKINTEL_TRIAL_RESULT=')]
    assert len(lines) == 1, 'Mastra did not return one trial result'
    return json.loads(lines[0])


def check_mastra(actor, source, package, client, output):
    from scripts.validation.framework_trial import check_framework
    dependency = ROOT/'integrations/mastra/node_modules/@mastra/core/package.json'
    versions = {'@mastra/core': json.loads(dependency.read_text())['version'],
                'node': subprocess.check_output(['node', '--version'], text=True).strip()}
    return check_framework('mastra', versions, invoke_mastra, source, package, client, output)
