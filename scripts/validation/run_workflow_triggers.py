"""S-20: actual local native timer, retained retail data, no provider calls.

Run with Python >=3.12 and requirements.testing.txt installed. The retained
S-32/S-39 archive is private local evidence, not a fabricated source fixture.
All created servers, credentials, crons and database containers are disposable.
"""
import argparse
from datetime import datetime, timedelta, timezone
import hashlib
import json
import os
from pathlib import Path
import secrets
import select
import signal
import socket
import subprocess
import sys
import tempfile
import threading
import time

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))


def command(args, **kwargs):
    result = subprocess.run(args, capture_output=True, **kwargs)
    if result.returncode:
        raise RuntimeError(result.stderr.decode(errors='replace')[-2000:])
    return result


def check_browser(env, base, token, source, trigger, output, goal):
    browser = subprocess.run(['node', str(ROOT/'scripts/validation/workflow_trigger_browser.cjs')], cwd=ROOT,
        env={**env,'S20_BROWSER_URL':base,'S20_BROWSER_TOKEN':token,'S20_TRIGGER':trigger['id'],
             'S20_GOAL':source['goal_id'],'S20_GOAL_QUESTION':goal['body']['question'],
             'S20_DOMAIN':goal['domain'],'S20_OUTPUT':str(output)}, capture_output=True, timeout=1100)
    (output/'browser.log').write_bytes(browser.stdout+browser.stderr)
    assert browser.returncode == 0, 'Browser or native execution failed; inspect browser.log'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--archive', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--browser-only', action='store_true', help='Check the current UI against a prior successful runtime archive')
    parser.add_argument('--updates', action='store_true', help='Exercise S-21 controlled changes with the real saved-workflow executor')
    parser.add_argument('--updates-after-repair', action='store_true', help='Continue the remaining update cases from an archive whose accepted-repair browser check already passed')
    parser.add_argument('--updates-resume', type=Path, help='Resume the forecast check using completed cases from the restored archive')
    parser.add_argument('--incremental-csv', type=Path, help='Run S-24 against a disposable real source built from the pinned retail CSV')
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True, mode=0o700)
    name = 'backintel-s20-' + secrets.token_hex(6)
    env = os.environ.copy()
    env['POSTGRES_PASSWORD'] = secrets.token_urlsafe(24)
    env.pop('OPENROUTER_API_KEY', None)
    server = None
    database_ready = False
    summary = {'status': 'failed', 'scope': 'local working tree; historical retail data', 'model_calls': None}
    with tempfile.TemporaryDirectory(prefix='BackIntelS20Credentials') as secret_dir:
        try:
            since = str(int(time.time()) - 1)
            command(['docker', 'run', '-d', '--rm', '--name', name, '-p', '127.0.0.1::5432',
                     '-e', 'POSTGRES_PASSWORD', '-e', 'POSTGRES_DB=backintel_app', '--health-cmd',
                     'pg_isready -h 127.0.0.1 -U postgres -d backintel_app', '--health-interval', '1s',
                     '--health-retries', '30', 'postgres:17-alpine'], env=env)
            events = subprocess.Popen(['docker', 'events', '--since', since, '--filter', 'container=' + name,
                                       '--filter', 'event=health_status', '--format', '{{.Action}}'],
                                      stdout=subprocess.PIPE, text=True)
            try:
                assert select.select([events.stdout], [], [], 40)[0], 'PostgreSQL readiness timed out'
                assert 'healthy' in events.stdout.readline(), 'PostgreSQL was not healthy'
            finally:
                events.terminate()
                events.wait(timeout=5)
            port = command(['docker', 'port', name, '5432/tcp']).stdout.decode().strip().split(':')[-1]
            command(['docker', 'exec', '-i', name, 'pg_restore', '-U', 'postgres', '-d', 'backintel_app',
                     '--no-owner', '--no-acl'], input=args.archive.read_bytes())
            database_ready = True
            uri = f'postgresql://postgres:{env["POSTGRES_PASSWORD"]}@127.0.0.1:{port}/backintel_app'
            os.environ['BACKINTEL_APP_DATABASE_URL'] = uri
            from runtime import analysis_store as db, source_workflows as workflows, workflow_triggers as triggers
            from runtime.bootstrap import initialize
            initialize()
            actor = {'id': 'connection-demo-manager'}
            token, worker_token = secrets.token_urlsafe(32), secrets.token_urlsafe(32)
            db.write("UPDATE backintel.analysis_principals SET enabled=true,expires_at=now()+interval '1 day',token_hash=%s WHERE id=%s",
                     (hashlib.sha256(token.encode()).hexdigest(), actor['id']))
            db.write("UPDATE backintel.analysis_source_connections SET enabled=true,expires_at=now()+interval '1 day'")
            db.write("INSERT INTO backintel.analysis_principals(id,token_hash,role,domains) VALUES(%s,%s,'worker',%s) ON CONFLICT(id) DO UPDATE SET token_hash=EXCLUDED.token_hash",
                     ('s20-native-worker', hashlib.sha256(worker_token.encode()).hexdigest(), []))
            source = db.query("""SELECT * FROM backintel.analysis_runs WHERE owner=%s AND status='succeeded'
                AND body->>'operation'='answer' AND result->>'mode'<>'fixture' ORDER BY created_at DESC LIMIT 1""",
                (actor['id'],),one=True)
            assert source is not None, 'The archive has no accepted real retail answer for the selected owner'
            source_id = source['id']
            assert source['status'] == 'succeeded' and source['body']['operation'] == 'answer'
            assert source['result']['mode'] != 'fixture'
            package = workflows.save(source_id, actor)
            assert workflows.load(package, actor)['status'] == 'ready'
            baseline_requests = db.query('SELECT id,status,charge FROM backintel.analysis_requests ORDER BY id')
            source_owner_uri = None
            if args.incremental_csv:
                from scripts.validation.run_source_discovery import provision_source
                from psycopg.conninfo import make_conninfo
                with args.incremental_csv.open('rb') as original:
                    assert hashlib.file_digest(original, 'sha256').hexdigest() == 'd07aec9960083af2339975a3f9d3b26313b342dcd9f86cce0b919b1cde639a44'
                reader_uri, source_rows = provision_source(uri, args.incremental_csv)
                source_owner_uri = make_conninfo(uri, dbname='backintel_retail_source')
                policy = db.query('SELECT secret_ref FROM backintel.analysis_source_connections WHERE id=%s',
                    (db.goal(source['goal_id'])['body']['objective']['source_ref'],), one=True)
                os.environ[policy['secret_ref']] = reader_uri
                env[policy['secret_ref']] = reader_uri
            credential = Path(secret_dir) / 'access.json'
            credential.write_text(json.dumps({'worker': worker_token}))
            credential.chmod(0o600)
            with socket.socket() as reserved:
                reserved.bind(('127.0.0.1', 2028 if args.incremental_csv else 0))
                api_port = reserved.getsockname()[1]
            base = f'http://127.0.0.1:{api_port}'
            env.update(BACKINTEL_APP_DATABASE_URL=uri, DATABASE_URL=uri, AEGRA_CONFIG=str(ROOT/'aegra.analysis.json'),
                       BACKINTEL_ACCESS_CREDENTIAL_FILE=str(credential), BACKINTEL_AEGRA_URL=base,
                       REDIS_BROKER_ENABLED='false', WORKER_COUNT='1', N_JOBS_PER_WORKER='1',
                       OPENROUTER_API_KEY='', OTEL_TARGETS='', OTEL_CONSOLE_EXPORT='false')
            os.environ['BACKINTEL_ACCESS_CREDENTIAL_FILE'] = str(credential)
            os.environ['BACKINTEL_AEGRA_URL'] = base
            server_log = (args.output/'native-runtime.log').open('w')
            server = subprocess.Popen([sys.executable, '-m', 'uvicorn', 'aegra_api.main:app', '--host', '127.0.0.1',
                                       '--port', str(api_port)], cwd=ROOT, env=env, stdout=subprocess.PIPE,
                                      stderr=subprocess.STDOUT, text=True, bufsize=1, start_new_session=True)
            ready=threading.Event()
            def capture():
                for line in server.stdout:
                    server_log.write(line); server_log.flush()
                    if 'Application startup complete' in line:
                        ready.set()
            capture_thread=threading.Thread(target=capture,daemon=True)
            capture_thread.start()
            assert ready.wait(50) and server.poll() is None, 'Native runtime startup failed; inspect native-runtime.log'
            import httpx
            with httpx.Client(base_url=base, headers={'Authorization': 'Bearer '+token}, timeout=30) as client:
                client.get('/api/v1/me').raise_for_status()
                if args.incremental_csv:
                    from scripts.validation.workflow_incremental_cases import check_incremental
                    result = check_incremental(actor, source, package, client, base, token, env, args.output, source_owner_uri)
                    assert db.query('SELECT id,status,charge FROM backintel.analysis_requests ORDER BY id') == baseline_requests
                    (args.output/'incremental-cases.json').write_text(json.dumps(result, default=str, indent=2))
                    summary.update(**result, model_calls=0, provider_cost_usd=0)
                    return 0
                if args.updates:
                    from scripts.validation.workflow_update_cases import check_updates
                    result = check_updates(actor, source, package, client, base, token, env, args.output,
                    repair_checked=args.updates_after_repair,
                    completed_cases=json.loads(args.updates_resume.read_text())['completed'] if args.updates_resume else None)
                    assert db.query('SELECT id,status,charge FROM backintel.analysis_requests ORDER BY id') == baseline_requests
                    (args.output/'update-cases.json').write_text(json.dumps(result, default=str, indent=2))
                    summary.update(**result, model_calls=0, provider_cost_usd=0)
                    return 0
                if args.browser_only:
                    trigger = db.query("SELECT * FROM backintel.analysis_workflow_triggers WHERE owner=%s AND accepted_count=2 ORDER BY created_at DESC LIMIT 1", (actor['id'],), one=True)
                    assert trigger is not None, 'Browser-only checks require a previously completed trigger archive'
                    check_browser(env, base, token, source, trigger, args.output, db.goal(source['goal_id']))
                    assert db.query('SELECT id,status,charge FROM backintel.analysis_requests ORDER BY id') == baseline_requests
                    summary.update(status='passed',scope='browser only against retained successful runtime; no new timer acceptance claim',model_calls=0,provider_cost_usd=0)
                    return 0
                now = datetime.now(timezone.utc)
                spec = {'event_source': 'retail.collection.completed', 'timezone': 'America/New_York',
                        'run_at': (now+timedelta(seconds=20)).isoformat(), 'expires_at': (now+timedelta(minutes=15)).isoformat(),
                        'max_runs': 2, 'max_spend_usd': 0}
                created = client.post('/api/v1/workflows/'+package['version']+'/triggers', json=spec)
                created.raise_for_status()
                trigger = created.json()
                assert trigger['state'] == 'active' and trigger['cron_id'], trigger
                assert triggers.due(trigger['id'])['status'] == 'waiting'
                payload = {'event_id': 'retail-snapshot-accepted', 'source': spec['event_source']}
                response = client.post('/api/v1/triggers/'+trigger['id']+'/events', json=payload)
                response.raise_for_status()
                event_result = response.json()
                assert event_result['status'] == 'accepted', event_result
                duplicate = client.post('/api/v1/triggers/'+trigger['id']+'/events', json=payload).json()
                assert duplicate['status'] == 'reused' and duplicate['run_id'] == event_result['run_id']
                conflict = client.post('/api/v1/triggers/'+trigger['id']+'/events', json={**payload,'source':'other'}).json()
                assert conflict['status'] == 'denied'
                # Browser wait observes real native timer and worker progress through the product API.
                check_browser(env, base, token, source, trigger, args.output, db.goal(source['goal_id']))
                observed = triggers.inspect(trigger['id'], actor)
                assert observed['accepted_count'] == 2
                accepted = [attempt for attempt in observed['attempts'] if attempt['status']=='accepted']
                scheduled = next(attempt for attempt in accepted if attempt['occurrence'].startswith('schedule:'))
                assert scheduled['created_at'] >= datetime.fromisoformat(spec['run_at'])
                assert {attempt['run_id'] for attempt in accepted} == {event_result['run_id']}
                result = db.run(event_result['run_id'])
                assert result['status'] == 'succeeded', result.get('error')
                assert result['result']['calculation']['totals'] == source['result']['calculation']['totals']
                assert workflows.invoke(package['version'], actor)['id'] == result['id']
                assert triggers.event(trigger['id'], actor, {**payload,'event_id':'over-limit'})['status']=='denied'
                guard_spec = {**spec,'run_at':None,'max_runs':5}
                guarded = triggers.configure(package['version'],actor,guard_spec)
                triggers.set_state(guarded['id'],actor,'paused')
                assert triggers.event(guarded['id'],actor,payload)['status']=='denied'
                triggers.set_state(guarded['id'],actor,'active')
                db.write("UPDATE backintel.analysis_workflow_triggers SET expires_at=now()-interval '1 second' WHERE id=%s",(guarded['id'],))
                assert triggers.event(guarded['id'],actor,payload)['status']=='denied'
                guarded = triggers.configure(package['version'],actor,guard_spec)
                db.write('UPDATE backintel.analysis_source_connections SET enabled=false')
                assert triggers.event(guarded['id'],actor,payload)['status']=='denied'
                db.write('UPDATE backintel.analysis_source_connections SET enabled=true')
                assert client.get('/api/v1/triggers/'+trigger['id'],headers={'Authorization':'Bearer invalid'}).status_code in (401,403)
                db.write("INSERT INTO backintel.analysis_principals(id,token_hash,role,domains) VALUES(%s,%s,'manager',%s)",
                         ('s20-other-manager',hashlib.sha256(secrets.token_bytes(32)).hexdigest(),db.principal(token)['domains']))
                try:
                    triggers.inspect(trigger['id'],{'id':'s20-other-manager'})
                except PermissionError:
                    pass
                else:
                    raise AssertionError('Another manager could inspect the owner trigger')
                from unittest.mock import patch
                with patch.object(triggers,'_attempt',side_effect=RuntimeError('Interrupted before receipt commit')):
                    try:
                        triggers.event(guarded['id'],actor,{**payload,'event_id':'interrupted'})
                    except RuntimeError:
                        pass
                    else:
                        raise AssertionError('The interruption check did not interrupt admission')
                assert triggers.inspect(guarded['id'],actor)['accepted_count']==0
                recovered=triggers.event(guarded['id'],actor,{**payload,'event_id':'interrupted'})
                assert recovered['status']=='accepted' and recovered['run_id']==result['id']
                bad = client.post('/api/v1/workflows/'+package['version']+'/triggers',json={**guard_spec,'max_spend_usd':1})
                assert bad.status_code==422
                removed = client.patch('/api/v1/triggers/'+trigger['id'],json={'state':'removed'})
                removed.raise_for_status()
                assert removed.json()['state']=='removed' and removed.json()['cron_id'] is None, removed.json()
                with httpx.Client(base_url=base,headers={'Authorization':'Bearer '+worker_token},timeout=15) as worker:
                    crons=worker.post('/runs/crons/search',json={'assistant_id':'workflow_triggers','limit':1000})
                    crons.raise_for_status()
                    assert not [cron for cron in crons.json() if cron.get('metadata',{}).get('purpose')=='backintel-workflow-trigger:'+trigger['id']]
                assert db.query('SELECT id,status,charge FROM backintel.analysis_requests ORDER BY id') == baseline_requests
                summary.update(status='passed',trigger_id=trigger['id'],workflow_version=package['version'],run_id=result['id'],
                    model_calls=0,provider_cost_usd=0,event_and_schedule_share_accepted_result=True,native_schedule_removed=True,
                    accepted_attempts=2,source_totals=result['result']['calculation']['totals'],
                    checks=['not before due','native scheduled start','authenticated event','duplicate replay','conflicting identity',
                            'run cap','pause','expiration','revoked source','unauthorized caller','owner isolation',
                            'interrupted admission rollback','zero-spend schema','toolkit parity','native cleanup'])
                (args.output/'trigger-history.json').write_text(json.dumps(observed,default=str,indent=2))
                (args.output/'workflow-package.json').write_text(json.dumps(package,default=str,indent=2))
        finally:
            if server is not None:
                os.killpg(server.pid,signal.SIGTERM)
                try:
                    server.wait(timeout=20)
                except subprocess.TimeoutExpired:
                    os.killpg(server.pid,signal.SIGKILL); server.wait(timeout=5)
            if database_ready:
                dump=command(['docker','exec',name,'pg_dump','-U','postgres','-d','backintel_app','-Fc'])
                (args.output/'runtime-result.dump').write_bytes(dump.stdout)
            command(['docker','rm','-f',name])
            summary['database_removed']=True
            summary['native_server_stopped']=server is None or server.poll() is not None
            (args.output/'summary.json').write_text(json.dumps(summary,default=str,indent=2))
            print(json.dumps(summary,default=str),flush=True)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
