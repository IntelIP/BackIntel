"""Shared real-data acceptance checks for external framework trials."""
import json


def check_framework(name, versions, invoke, source, package, client, output):
    from runtime import analysis_store as db
    from runtime.workflow_updates import collection_for

    question = package['body']['question']
    baseline = db.run(db.goal(source['goal_id'])['last_success'])
    collection = collection_for(baseline)
    assert collection and collection['status'] == 'succeeded'
    assert collection['result']['coverage']['expected_rows'] == 541909
    args = (client, package['version'], collection['id'], question)
    print(f'{name}: lose the admission response, then recover with a fresh agent.', flush=True)
    interrupted = invoke(*args, lose_response=True)
    assert interrupted['status'] == 'error' and 'interrupted' in interrupted['content']
    accepted = invoke(*args)
    result = accepted['artifact']
    (output/f'{name}-result.json').write_text(json.dumps(result, default=str, indent=2))
    assert accepted['status'] == 'success' and result['status'] == 'succeeded', accepted['content']
    assert result['id'] == interrupted['dropped_id'], 'Recovery created another run'
    assert result['result'] == db.run(result['id'])['result'], 'Framework changed the checked answer'
    calculation = result['result']['calculation']
    for field in ('totals', 'dimensions', 'currency', 'period_start', 'period_end', 'coverage'):
        assert calculation[field] == baseline['result']['calculation'][field], f'Calculation differs: {field}'
    assert result['result']['coverage'] == result['coverage']
    before_replay = db.query('SELECT id FROM backintel.analysis_runs ORDER BY id')
    replay = invoke(*args)
    assert replay['artifact'] == result, 'Replay changed the retained result'
    assert db.query('SELECT id FROM backintel.analysis_runs ORDER BY id') == before_replay
    accepted_goal = db.goal(source['goal_id'])
    print(f'{name}: answer matched; check revoked access and an unsupported tool.', flush=True)
    db.write('UPDATE backintel.analysis_source_connections SET enabled=false WHERE id=%s',
             (package['body']['connection']['source_ref'],))
    try:
        denied = invoke(*args)
        assert denied['status'] == 'error' and 'Access denied' in denied['content']
    finally:
        db.write('UPDATE backintel.analysis_source_connections SET enabled=true WHERE id=%s',
                 (package['body']['connection']['source_ref'],))
    unsupported = invoke(*args, tool_name='change_source_records')
    assert unsupported['status'] == 'error' and unsupported['artifact'] is None
    assert any(text in unsupported['content'].lower() for text in ('not found', 'not find', 'not a valid tool', 'no such tool', 'not available'))
    assert db.goal(source['goal_id']) == accepted_goal, 'Denied request changed the accepted answer'
    assert db.query('SELECT id FROM backintel.analysis_runs ORDER BY id') == before_replay
    cases = dict(interrupted=interrupted, accepted=accepted, replay=replay, denied=denied, unsupported=unsupported)
    (output/f'{name}-messages.json').write_text(json.dumps({case: {k: v for k, v in record.items() if k != 'artifact'}
                                                          for case, record in cases.items()}, default=str, indent=2))
    (output/'workflow-package.json').write_text(json.dumps(package, default=str, indent=2))
    return {'status': 'passed', 'scope': 'local working tree; real historical retail workflow; scripted model decisions',
            'frameworks': versions, 'workflow_version': package['version'], 'run_id': result['id'],
            'baseline_run_id': baseline['id'], 'input_ref': collection['id'],
            'coverage': result['coverage'], 'totals': calculation['totals'], 'model_calls': 0, 'provider_cost_usd': 0,
            'checks': [f'actual {name} agent and authenticated tool', 'complete source calculation unchanged',
                       'full result and evidence retained', 'lost response recovered by a fresh agent',
                       'replay reused the same run', 'revoked source access denied', 'unsupported operation rejected'],
            'limits': ['model decisions and final agent prose are scripted', 'no live model quality or cost evaluation',
                       'local reference only; independent installation and release remain open']}
