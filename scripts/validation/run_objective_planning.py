"""Bounded S-12 demonstration. Default mode performs no provider call.

Use Python 3.12 with requirements.testing.txt. --execute requires prior human
authorization and OPENROUTER_API_KEY injected into this process, never a file.
The output preserves the objective, plan receipts and restorable database.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import secrets
import subprocess
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--execute', action='store_true', help='Make at most two approved provider calls, capped at $0.50 combined')
    args = parser.parse_args()
    if args.execute and not os.getenv('OPENROUTER_API_KEY'):
        parser.error('Inject the existing provider credential only after authorization')
    output = args.output.expanduser().resolve()
    if output.is_relative_to(ROOT):
        parser.error('Keep local demonstration artifacts outside the repository')
    output.mkdir(mode=0o700, parents=True, exist_ok=False)
    started = time.monotonic()
    project = 'backintel-objective-' + secrets.token_hex(4)
    environment = os.environ.copy()
    environment['BACKINTEL_CHECK_PASSWORD'] = secrets.token_hex(24)
    receipt = {'mode': 'live' if args.execute else 'check-only', 'status': 'incomplete',
               'max_provider_requests': 2, 'max_total_provider_usd': .50, 'runs': []}
    with tempfile.TemporaryDirectory(prefix=project) as temporary:
        config = Path(temporary) / 'compose.yml'
        config.write_text('''services:
  db:
    image: pgvector/pgvector:pg18
    environment:
      POSTGRES_PASSWORD: ${BACKINTEL_CHECK_PASSWORD}
      POSTGRES_DB: backintel_objective_test
    ports:
      - "127.0.0.1::5432"
    tmpfs:
      - /var/lib/postgresql
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres -d backintel_objective_test"]
      interval: 1s
      timeout: 3s
      retries: 30
''')
        compose = ['docker', 'compose', '-p', project, '-f', str(config)]
        ready = False
        try:
            subprocess.run(compose + ['up', '-d', '--wait', '--wait-timeout', '45'], env=environment,
                           check=True, stdout=subprocess.DEVNULL)
            ready = True
            port = subprocess.check_output(compose + ['port', 'db', '5432'], env=environment, text=True).strip().rsplit(':', 1)[1]
            uri = 'postgresql://postgres:' + environment['BACKINTEL_CHECK_PASSWORD'] + '@127.0.0.1:' + port + '/backintel_objective_test'
            os.environ['BACKINTEL_APP_DATABASE_URL'] = uri
            os.environ['BACKINTEL_TEST_DATABASE_URL'] = uri
            from fastapi.testclient import TestClient
            from runtime import analysis_api as api, analysis_service as service, analysis_store as db
            from runtime.analysis_data import CONFIG
            from runtime.bootstrap import initialize
            initialize()
            db.catalog()
            token = secrets.token_urlsafe(32)
            db.write('INSERT INTO backintel.analysis_principals(id,token_hash,role,domains) VALUES(%s,%s,%s,%s)',
                     ('objective-demo-manager', hashlib.sha256(token.encode()).hexdigest(), 'manager', ['commerce']))
            client = TestClient(api.app, headers={'Authorization': 'Bearer ' + token})
            scenario = json.loads((ROOT / 'config/reference_scenarios/online_retail.json').read_text())
            response = client.post('/api/v1/goals', json=scenario['request'])
            response.raise_for_status()
            goal = response.json()
            receipt.update({'goal_id': goal['id'], 'objective': goal['body'], 'configured_model': CONFIG['analyst']['model']})
            denied = client.post('/api/v1/goals/' + goal['id'] + '/runs', json={'operation': 'planning'})
            if denied.status_code != 403 or 'budget' not in denied.json().get('detail', '').lower():
                raise RuntimeError('Zero-spend admission check failed')
            receipt['zero_spend_denied'] = True
            if args.execute:
                response = client.patch('/api/v1/goals/' + goal['id'], json={'budget_usd': .25})
                response.raise_for_status()
                receipt['objective'] = response.json()['body']
                questions = [None, 'Make cancellation checks explicit. Preserve every source row, including duplicate-looking lines, and keep unresolved meanings visible.']
                for question in questions:
                    response = client.post('/api/v1/goals/' + goal['id'] + '/runs', json={'operation': 'planning', 'question': question})
                    response.raise_for_status()
                    run = response.json()
                    # The application queue is driven manually here; no background scheduler is created.
                    service.dispatch(run['id'])
                    completed = db.run(run['id'])
                    receipt['runs'].append(completed)
                    if completed['status'] != 'succeeded' or completed['result'].get('mode') != 'real':
                        raise RuntimeError('Live planning did not succeed; inspect the retained run and accounting evidence')
                    again = client.post('/api/v1/goals/' + goal['id'] + '/runs', json={'operation': 'planning', 'question': question})
                    again.raise_for_status()
                    if again.json()['id'] != run['id']:
                        raise RuntimeError('A repeated request changed run identity')
                shown = client.get('/api/v1/goals')
                shown.raise_for_status()
                receipt['saved_goal'] = next(item for item in shown.json() if item['id'] == goal['id'])
                if receipt['saved_goal']['plan_run_id'] != receipt['runs'][-1]['id']:
                    raise RuntimeError('The latest plan was not readable through the platform')
            receipt['accounting'] = db.query('SELECT status,reserved,charge FROM backintel.analysis_requests ORDER BY created_at')
            if len(receipt['accounting']) > 2:
                raise RuntimeError('The demonstration exceeded its two-request boundary')
            receipt['status'] = 'succeeded' if args.execute else 'ready-for-authorized-live-run'
        finally:
            # Retain durable evidence even on provider rejection or uncertain charges; never retry automatically.
            receipt['elapsed_seconds'] = round(time.monotonic() - started, 3)
            try:
                if ready:
                    archive = output / 'planning-database.dump'
                    with archive.open('wb') as handle:
                        archive.chmod(0o600)
                        subprocess.run(compose + ['exec', '-T', 'db', 'pg_dump', '-U', 'postgres', '-Fc', 'backintel_objective_test'],
                                       env=environment, check=True, stdout=handle)
                evidence = output / 'planning-evidence.json'
                evidence.write_text(json.dumps(receipt, indent=2, default=str) + '\n')
                evidence.chmod(0o600)
            finally:
                subprocess.run(compose + ['down', '--volumes', '--remove-orphans'], env=environment,
                               check=True, stdout=subprocess.DEVNULL)
    print(json.dumps({'status': receipt['status'], 'provider_requests': len(receipt['accounting']), 'evidence': str(output / 'planning-evidence.json')}))


if __name__ == '__main__':
    main()
