"""S-34: actual PostgreSQL records plus a separate demonstration target/inbox process."""
from copy import deepcopy
from datetime import datetime, timezone
from fractions import Fraction
import json
import os
from pathlib import Path
import select
import sqlite3
import subprocess
import sys
from unittest.mock import patch

import httpx
import psycopg

ROOT = Path(__file__).resolve().parents[2]


def check_cross_systems(actor, source, package, client, output, source_uri, *, resume=None):
    from runtime import analysis_service as service, analysis_store as db, jobs, source_workflows
    os.environ['BACKINTEL_PREPARATION_IMAGE'] = package['body']['dependencies']['image']
    targets = json.loads((ROOT/'config/reference_scenarios/retail_cancellation_targets.json').read_text())
    target_path, inbox = output/'demonstration-targets.json', output/'local-inbox.sqlite'
    target_path.write_text(json.dumps(targets, indent=2))
    process = None

    def start(port=0):
        nonlocal process
        process = subprocess.Popen([sys.executable, str(ROOT/'scripts/validation/cross_system_service.py'),
            '--targets', str(target_path), '--database', str(inbox), '--port', str(port), '--drop-first-ack'],
            stdout=subprocess.PIPE, stderr=(output/'target-service.log').open('a'), text=True)
        assert select.select([process.stdout], [], [], 10)[0], 'Local target service did not start'
        return json.loads(process.stdout.readline())['url']

    try:
        base = start()
        for reference, actions in (('s34-targets', ['read_targets']), ('s34-local-inbox', ['deliver_findings'])):
            db.write('''INSERT INTO backintel.analysis_service_grants(id,domain,principals,base_url,actions,expires_at)
                VALUES(%s,%s,%s,%s,%s,now()+interval '1 hour') ON CONFLICT(id) DO UPDATE SET
                principals=EXCLUDED.principals,base_url=EXCLUDED.base_url,actions=EXCLUDED.actions,
                expires_at=EXCLUDED.expires_at,enabled=true''',
                (reference, db.goal(source['goal_id'])['domain'], [actor['id']], base, actions))
        if resume:
            from runtime.analysis_data import digest
            retained = json.loads((resume/'workflow-result.json').read_text())
            run = db.run(retained['id'])
            assert run['owner'] == actor['id'] and digest(run['result']) == digest(retained['result'])
        else:
            with patch.object(jobs, '_run_worker', side_effect=jobs._execute_claimed):
                collected = service.submit(source['goal_id'], actor, operation='collection', question='S-34 fresh historical retail collection')
                print('S-34: collecting from the permitted PostgreSQL source.', flush=True)
                service.dispatch(collected['id'])
                collected = db.run(collected['id'])
                assert collected['status'] == 'succeeded', collected.get('error')
                run = source_workflows.invoke(package['version'], actor, collected['id'])
                print('S-34: executing the checked saved method over the complete source.', flush=True)
                service.dispatch(run['id'])
        run = db.run(run['id'])
        assert run['status'] == 'succeeded', run.get('error')
        for key in ('totals', 'dimensions', 'coverage', 'currency', 'period_start', 'period_end'):
            assert run['result']['calculation'][key] == source['result']['calculation'][key], key
        (output/'workflow-result.json').write_text(json.dumps(run, default=str, indent=2))
        policy = {'target_ref': 's34-targets', 'request_id': output.name}
        route = '/api/v1/runs/' + run['id'] + '/cross-system'
        print('S-34: reconciling source records, country identities, and demonstration targets.', flush=True)
        requested_at = datetime.now(timezone.utc)
        response = client.post(route, json=policy, timeout=1100)
        response.raise_for_status()
        finding = response.json()
        assert finding['status'] == 'accepted', finding.get('issues')
        assert finding['source_evidence']['collected_at'] == db.run(run['result']['input_ref'])['result']['observed_at']
        assert requested_at <= datetime.fromisoformat(finding['target_evidence']['retrieved_at']) <= datetime.now(timezone.utc)
        assert len(finding['comparisons']) == 38 and finding['source_rows'] == 541909
        assert client.post(route, json=policy).json() == finding
        assert client.get('/api/v1/cross-system/' + finding['id']).json() == finding
        (output/'finding.json').write_text(json.dumps(finding, indent=2))
        # Independent expected business result from the source service, with no
        # reuse of the saved method, prepared records, or comparison function.
        with psycopg.connect(source_uri) as connection:
            rows = connection.execute('''SELECT "Country",count(*),
                COALESCE(sum("Quantity"::numeric * "UnitPrice"::numeric) FILTER (WHERE "InvoiceNo" ILIKE 'c%%'),0),
                COALESCE(sum("Quantity"::numeric * "UnitPrice"::numeric) FILTER (WHERE "InvoiceNo" NOT ILIKE 'c%%'),0)
                FROM retail_raw.invoice_lines GROUP BY "Country"''').fetchall()
        expected = {country: {'rows': count, 'cancelled': -Fraction(cancelled), 'denominator': Fraction(denominator)}
                    for country, count, cancelled, denominator in rows}
        for comparison in finding['comparisons']:
            independent = expected[comparison['source_country']]
            assert comparison['source_rows'] == independent['rows']
            assert Fraction(comparison['cancellation_value']) == independent['cancelled']
            assert Fraction(comparison['value_without_cancellations']) == independent['denominator']
            assert comparison['exceeds_target'] == (independent['cancelled'] / independent['denominator'] > Fraction(1, 10))
        delivery_route = '/api/v1/cross-system/' + finding['id'] + '/deliveries'
        forbidden = client.post(delivery_route, json={'destination_ref': 's34-targets'})
        assert forbidden.status_code == 403, forbidden.text
        with sqlite3.connect(inbox) as connection:
            assert connection.execute('SELECT count(*) FROM deliveries').fetchone()[0] == 0
        first = client.post(delivery_route, json={'destination_ref': 's34-local-inbox'})
        first.raise_for_status()
        assert first.json()['status'] == 'pending'
        process.terminate(); process.wait(timeout=10)
        start(int(base.rsplit(':', 1)[1]))
        delivered = client.post(delivery_route, json={'destination_ref': 's34-local-inbox'})
        delivered.raise_for_status()
        receipt = delivered.json()
        assert receipt['status'] == 'confirmed' and receipt['delivery_id'] == first.json()['delivery_id']
        assert client.post(delivery_route, json={'destination_ref': 's34-local-inbox'}).json()['replayed'] is True
        with sqlite3.connect(inbox) as connection:
            stored = connection.execute('SELECT payload,receipt FROM deliveries').fetchall()
        assert len(stored) == 1 and json.loads(stored[0][0])['finding'] == finding
        assert json.loads(stored[0][1]) == receipt['receipt']
        conflict = json.loads(stored[0][0]); conflict['finding']['question'] = 'Changed finding'
        from runtime.analysis_data import digest
        conflict['result_sha256'] = digest(conflict['finding'])
        assert httpx.post(base + '/deliveries', json=conflict, trust_env=False).status_code == 409
        (output/'delivery.json').write_text(json.dumps(receipt, indent=2))
        cases = {}
        for name in ('conflicting-identity', 'unmatched-country', 'wrong-currency', 'incomplete-effective-period'):
            changed = deepcopy(targets); changed['version'] = name
            if name == 'conflicting-identity':
                changed['countries'].append({**changed['countries'][0], 'country_id': 'conflicting-demo-id'})
            elif name == 'unmatched-country':
                changed['countries'] = changed['countries'][1:]
            elif name == 'wrong-currency':
                changed['currency'] = 'USD'
            else:
                changed['effective_from'] = '2011-01-01'
            target_path.write_text(json.dumps(changed))
            blocked = client.post(route, json={**policy, 'request_id': output.name + ':' + name})
            blocked.raise_for_status(); blocked = blocked.json()
            assert blocked['status'] == 'blocked', name
            denied = client.post('/api/v1/cross-system/' + blocked['id'] + '/deliveries', json={'destination_ref': 's34-local-inbox'})
            assert denied.status_code == 400, denied.text
            cases[name] = {'status': blocked['status'], 'issues': blocked['issues']}
        target_path.write_text(json.dumps(targets, indent=2))
        db.write("UPDATE backintel.analysis_service_grants SET enabled=false WHERE id='s34-local-inbox'")
        assert client.post(delivery_route, json={'destination_ref': 's34-local-inbox'}).status_code == 403
        db.write("UPDATE backintel.analysis_source_connections SET enabled=false WHERE id=%s", (package['body']['connection']['source_ref'],))
        assert client.get('/api/v1/cross-system/' + finding['id']).status_code == 403
        db.write("UPDATE backintel.analysis_source_connections SET enabled=true WHERE id=%s", (package['body']['connection']['source_ref'],))
        assert client.get('/api/v1/cross-system/' + finding['id'], headers={'Authorization': 'Bearer invalid'}).status_code in (401, 403)
        process.terminate(); process.wait(timeout=10); process = None
        unavailable = client.post(route, json={**policy, 'request_id': output.name + ':unavailable-source'})
        unavailable.raise_for_status()
        assert unavailable.json()['status'] == 'blocked'
        with sqlite3.connect(inbox) as connection:
            assert connection.execute('SELECT count(*) FROM deliveries').fetchone()[0] == 1
        result = {'status': 'passed', 'scope': 'historical PostgreSQL retail and a separate local demonstration target/inbox service',
            'rows': 541909, 'country_categories': 38, 'run_id': run['id'], 'finding_id': finding['id'],
            'exceeding': [{key: row[key] for key in ('source_country', 'rate_percent_display')}
                          for row in finding['comparisons'] if row['exceeds_target']],
            'delivery_receipt': receipt, 'delivery_effects': 1, 'fault_cases': cases,
            'checks': ['fresh PostgreSQL collection', 'full saved-workflow result parity', 'specialist independent original-record check',
                'independent source SQL', 'explicit mappings and complete effective dates', 'read-only grant cannot deliver',
                'durable receipt after lost acknowledgement and receiver restart', 'same-result replay has one effect',
                'conflicting delivery identity rejected', 'unavailable target source', 'revoked source/destination', 'authenticated API'],
            'model_calls': 0, 'provider_cost_usd': 0, 'local_compute_usd': None}
        if resume:
            result['completed_collection_and_workflow_evidence'] = str(resume)
        (output/'cross-system-cases.json').write_text(json.dumps(result, indent=2))
        return result
    finally:
        if process is not None:
            process.terminate(); process.wait(timeout=10)
