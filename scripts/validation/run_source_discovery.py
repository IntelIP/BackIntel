"""Discover the real retail source through the runtime and platform API.

The source owner loads the pinned public CSV into isolated local PostgreSQL.
BackIntel then uses a separate read-only identity to discover its structure.
No provider calls occur. Dumps preserve both databases before container cleanup.
"""
import argparse
import csv
import hashlib
import json
import os
from pathlib import Path
import secrets
import subprocess
import sys
import tempfile
import time

import psycopg
from psycopg import sql
from psycopg.conninfo import make_conninfo

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
COLUMNS = ['InvoiceNo', 'StockCode', 'Description', 'Quantity', 'InvoiceDate', 'UnitPrice', 'CustomerID', 'Country']


def provision_source(uri, csv_path):
    """Owner bootstrap only; this is not the agent's collection workflow."""
    password = secrets.token_urlsafe(32)
    with psycopg.connect(uri, autocommit=True) as owner:
        owner.execute('CREATE DATABASE backintel_retail_source')
        owner.execute(sql.SQL('CREATE ROLE retail_reader LOGIN PASSWORD {}').format(sql.Literal(password)))
        owner.execute('REVOKE ALL ON DATABASE backintel_retail_source FROM PUBLIC')
        owner.execute('GRANT CONNECT ON DATABASE backintel_retail_source TO retail_reader')
    source_uri = make_conninfo(uri, dbname='backintel_retail_source')
    with psycopg.connect(source_uri) as owner:
        owner.execute('CREATE SCHEMA retail_raw')
        owner.execute(sql.SQL('CREATE TABLE retail_raw.invoice_lines (source_row_id bigint PRIMARY KEY, {})').format(
            sql.SQL(', ').join(sql.SQL('{} text NOT NULL').format(sql.Identifier(column)) for column in COLUMNS)))
        count = 0
        with csv_path.open(encoding='iso-8859-1', newline='') as source, owner.cursor().copy('COPY retail_raw.invoice_lines FROM STDIN') as target:
            reader = csv.reader(source)
            if next(reader) != COLUMNS:
                raise ValueError('The pinned source columns changed')
            for count, row in enumerate(reader, 1):
                if len(row) != len(COLUMNS):
                    raise ValueError('Malformed CSV row')
                target.write_row((count, *row))
        observed = owner.execute('SELECT count(*),min(source_row_id),max(source_row_id) FROM retail_raw.invoice_lines').fetchone()
        if observed != (541909, 1, 541909) or count != 541909:
            raise ValueError('The source bootstrap did not preserve the full pinned workload')
        owner.execute('GRANT USAGE ON SCHEMA retail_raw TO retail_reader')
        owner.execute('GRANT SELECT ON retail_raw.invoice_lines TO retail_reader')
    return make_conninfo(source_uri, user='retail_reader', password=password), count


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--csv', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--planning-dump', type=Path, help='Continue the saved live-planning objective without another model call')
    parser.add_argument('--collect', action='store_true', help='Collect every source row and independently compare it with the original CSV')
    args = parser.parse_args()
    csv_path = args.csv.expanduser().resolve()
    scenario = json.loads((ROOT / 'config/reference_scenarios/online_retail.json').read_text())
    expected = scenario['request']['objective']['expected_source_sha256']
    with csv_path.open('rb') as source:
        fingerprint = hashlib.file_digest(source, 'sha256').hexdigest()
    if fingerprint != expected:
        parser.error('The CSV fingerprint differs from the agreed historical snapshot')
    output = args.output.expanduser().resolve()
    if output.is_relative_to(ROOT):
        parser.error('Keep source data and demonstration artifacts outside Git')
    output.mkdir(mode=0o700, parents=True, exist_ok=False)
    environment = os.environ.copy()
    environment.pop('OPENROUTER_API_KEY', None)
    environment['BACKINTEL_CHECK_PASSWORD'] = secrets.token_hex(24)
    started = time.monotonic()
    receipt = {'status': 'incomplete', 'source_file_sha256': fingerprint, 'source_file_bytes': csv_path.stat().st_size,
               'mode': 'real-local-postgresql', 'provider_calls': 0, 'provider_usd': 0,
               'local_compute_usd': None, 'source_bootstrap': 'Owner-loaded public CSV; agent collection has not run.'}
    project = 'backintel-discovery-' + secrets.token_hex(4)
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
        loaded = False
        try:
            subprocess.run(compose + ['up', '-d', '--wait', '--wait-timeout', '45'], env=environment, check=True, stdout=subprocess.DEVNULL)
            ready = True
            port = subprocess.check_output(compose + ['port', 'db', '5432'], env=environment, text=True).strip().rsplit(':', 1)[1]
            uri = make_conninfo(host='127.0.0.1', port=port, dbname='backintel_objective_test', user='postgres', password=environment['BACKINTEL_CHECK_PASSWORD'])
            if args.planning_dump:
                with args.planning_dump.open('rb') as archive:
                    subprocess.run(compose + ['exec', '-T', 'db', 'pg_restore', '--exit-on-error', '-U', 'postgres', '-d', 'backintel_objective_test'],
                                   env=environment, check=True, stdin=archive)
            os.environ['BACKINTEL_APP_DATABASE_URL'] = uri
            os.environ['BACKINTEL_TEST_DATABASE_URL'] = uri
            from fastapi.testclient import TestClient
            from runtime import analysis_api as api, analysis_service as service, analysis_store as db
            from runtime.bootstrap import initialize
            initialize()
            db.catalog()
            os.environ['BACKINTEL_SOURCE_RETAIL'], receipt['source_rows'] = provision_source(uri, csv_path)
            loaded = True
            token = secrets.token_urlsafe(32)
            actor = 'connection-demo-manager'
            db.write('INSERT INTO backintel.analysis_principals(id,token_hash,role,domains) VALUES(%s,%s,%s,%s)',
                     (actor, hashlib.sha256(token.encode()).hexdigest(), 'manager', ['commerce']))
            db.write('''INSERT INTO backintel.analysis_source_connections(id,domain,secret_ref,schemas,principals)
                VALUES('online-retail-postgres','commerce','BACKINTEL_SOURCE_RETAIL',ARRAY['retail_raw'],%s)''', ([actor],))
            client = TestClient(api.app, headers={'Authorization': 'Bearer ' + token})
            if args.planning_dump:
                goal = db.query("SELECT * FROM backintel.analysis_goals WHERE body->'objective'->>'source_ref'='online-retail-postgres' ORDER BY created_at DESC LIMIT 1", one=True)
                if not goal or goal['body']['objective'] != scenario['request']['objective']:
                    raise ValueError('The retained planning goal differs from the agreed scenario')
            else:
                response = client.post('/api/v1/goals', json=scenario['request'])
                response.raise_for_status()
                goal = response.json()
            before = db.query('SELECT count(*) AS count FROM backintel.analysis_requests', one=True)['count']
            response = client.patch('/api/v1/goals/' + goal['id'], json={'confirmed': True})
            response.raise_for_status()
            path = '/api/v1/goals/' + goal['id'] + '/runs'
            response = client.post(path, json={'operation': 'discovery'})
            response.raise_for_status()
            run = response.json()
            service.dispatch(run['id'])
            completed = client.get('/api/v1/runs/' + run['id'])
            completed.raise_for_status()
            receipt['run'] = completed.json()
            if receipt['run']['status'] != 'succeeded':
                raise RuntimeError('Real source discovery failed; inspect retained evidence')
            again = client.post(path, json={'operation': 'discovery'})
            again.raise_for_status()
            if again.json()['id'] != run['id']:
                raise RuntimeError('Repeated discovery did not reuse its identity')
            shown = client.get('/api/v1/goals')
            shown.raise_for_status()
            receipt['goal'] = next(g for g in shown.json() if g['id'] == goal['id'])
            fields = receipt['goal']['discovery']['fields']
            if {(f['schema'], f['table']) for f in fields} != {('retail_raw', 'invoice_lines')} or {f['column'] for f in fields} != set(COLUMNS + ['source_row_id']):
                raise RuntimeError('Discovery did not expose exactly the permitted source structure')
            if args.planning_dump and not receipt['goal']['plan']:
                raise RuntimeError('The saved live plan was not preserved')
            if args.collect:
                from runtime.source_inputs import retained_input
                response = client.post(path, json={'operation': 'collection'})
                response.raise_for_status()
                collection_run = response.json()
                service.dispatch(collection_run['id'])
                response = client.get('/api/v1/runs/' + collection_run['id'])
                response.raise_for_status()
                receipt['collection_run'] = response.json()
                if receipt['collection_run']['status'] != 'succeeded':
                    raise RuntimeError('Whole-source collection failed; inspect retained evidence')
                checked = 0
                with csv_path.open(encoding='iso-8859-1', newline='') as original_csv:
                    expected_rows = csv.reader(original_csv)
                    next(expected_rows)
                    for page in receipt['collection_run']['result']['inputs']:
                        raw = retained_input(page['raw_input_id'], {'id': actor})
                        envelope = json.loads(raw['payload'])
                        if envelope['columns'] != ['source_row_id', *COLUMNS]:
                            raise RuntimeError('Collected fields differ from the independent CSV contract')
                        for observed_row in envelope['rows']:
                            checked += 1
                            expected_row = next(expected_rows, None)
                            if expected_row is None or observed_row != [checked, *expected_row]:
                                raise RuntimeError('A collected record differs from its independent original')
                    if next(expected_rows, None) is not None or checked != 541909:
                        raise RuntimeError('The collected workload omitted original records')
                receipt['independent_check'] = {'status': 'passed', 'compared_rows': checked,
                                                'method': 'Every retained field and stable row identity equals the unchanged original CSV.'}
                again = client.post(path, json={'operation': 'collection'})
                again.raise_for_status()
                if again.json()['id'] != collection_run['id']:
                    raise RuntimeError('Repeated collection did not reuse its accepted result')
                shown = client.get('/api/v1/goals')
                shown.raise_for_status()
                receipt['goal'] = next(g for g in shown.json() if g['id'] == goal['id'])
                if receipt['goal']['collection']['coverage']['collected_rows'] != checked:
                    raise RuntimeError('The platform did not display complete collection coverage')
            if db.query('SELECT count(*) AS count FROM backintel.analysis_requests', one=True)['count'] != before:
                raise RuntimeError('Discovery unexpectedly created a provider request')
            receipt.update({'status': 'succeeded', 'repeated_request_reused': True,
                            'limitations': [('Original data collected and checked; preparation and analytical answers are unfinished.' if args.collect else 'Metadata discovery only; agent collection and analytical answers are unfinished.'),
                                            'Local compute cost is unmeasured. The disposable service is stopped after retaining database dumps.']})
        finally:
            receipt['elapsed_seconds'] = round(time.monotonic() - started, 3)
            try:
                if ready:
                    databases = ['backintel_objective_test'] + (['backintel_retail_source'] if loaded else [])
                    for database in databases:
                        archive = output / (database + '.dump')
                        with archive.open('wb') as handle:
                            archive.chmod(0o600)
                            subprocess.run(compose + ['exec', '-T', 'db', 'pg_dump', '-U', 'postgres', '-Fc', database],
                                           env=environment, check=True, stdout=handle)
                evidence = output / ('collection-evidence.json' if args.collect else 'discovery-evidence.json')
                evidence.write_text(json.dumps(receipt, indent=2, default=str) + '\n')
                evidence.chmod(0o600)
            finally:
                subprocess.run(compose + ['down', '--volumes', '--remove-orphans'], env=environment, check=True, stdout=subprocess.DEVNULL)
    print(json.dumps({'status': receipt['status'], 'source_rows': receipt['source_rows'], 'provider_calls': receipt['provider_calls'], 'evidence': str(evidence)}))


if __name__ == '__main__':
    main()
