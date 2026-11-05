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
    parser.add_argument('--langchain', action='store_true', help='Test an external LangChain agent with scripted model responses and the real saved workflow; no paid calls')
    parser.add_argument('--framework', choices=('agno', 'mastra'), help='Test another external agent with scripted responses and the real saved workflow; no paid calls')
    parser.add_argument('--multi-user', choices=('checks', 'retail'), help='Check S-30 user isolation and the agreed local concurrent workload')
    parser.add_argument('--documents', type=Path, help='Exercise S-27 with a retained UTF-8 HTML field guide and simulated model replies; no paid calls')
    parser.add_argument('--documents-resume', type=Path, help='Resume document acceptance from completed interpretation artifacts in the restored archive')
    parser.add_argument('--documents-live', action='store_true', help='Use at most two real document interpretation calls within US$0.25; requires a separate explicit allowance')
    parser.add_argument('--cross-systems', action='store_true', help='S-34: actual retail PostgreSQL plus a separate local demonstration target/inbox service; no model calls')
    parser.add_argument('--cross-systems-resume', type=Path, help='Reuse completed S-34 collection and workflow evidence from the restored archive')
    parser.add_argument('--updates-after-repair', action='store_true', help='Continue the remaining update cases from an archive whose accepted-repair browser check already passed')
    parser.add_argument('--updates-resume', type=Path, help='Resume the forecast check using completed cases from the restored archive')
    parser.add_argument('--incremental-csv', type=Path, help='Run S-24 against a disposable real source built from the pinned retail CSV')
    parser.add_argument('--coordination', choices=('fixture', 'live'), help='Exercise S-33 against the pinned source; live requires a separately approved provider allowance')
    parser.add_argument('--coordination-resume', type=Path, help='Prior interrupted-progress.json for a completed coordination run retained in the archive')
    parser.add_argument('--coordination-max-spend-usd', type=float, default=0.5,
                        help='Approved allowance for this coordination run, excluding retained earlier charges')
    parser.add_argument('--sustained', action='store_true', help='S-36: approved 30-minute, two-owner local trial; no model calls')
    args = parser.parse_args()
    if args.sustained and (not args.incremental_csv or args.cross_systems or args.documents or args.multi_user
            or args.framework or args.langchain or args.coordination or args.updates or args.browser_only):
        parser.error('--sustained requires --incremental-csv and must run separately from other scenarios')
    if args.cross_systems_resume and not args.cross_systems:
        parser.error('--cross-systems-resume requires --cross-systems')
    if args.cross_systems and (not args.incremental_csv or args.documents or args.multi_user or args.framework
            or args.langchain or args.coordination or args.coordination_resume or args.updates or args.updates_after_repair
            or args.updates_resume or args.browser_only):
        parser.error('--cross-systems requires --incremental-csv and must run separately from other scenarios')
    if args.documents_resume and not args.documents:
        parser.error('--documents-resume requires --documents')
    if args.documents_live and not (args.documents and args.documents_resume):
        parser.error('--documents-live requires a retained pre-calculation document trial and --documents-resume')
    if args.documents and (args.multi_user or args.framework or args.langchain or args.coordination or args.coordination_resume
                           or args.incremental_csv or args.updates or args.updates_after_repair or args.updates_resume or args.browser_only):
        parser.error('The document trial must run separately from other scenarios')
    if args.multi_user and (args.framework or args.langchain or args.coordination or args.coordination_resume
                           or args.incremental_csv or args.updates or args.updates_after_repair or args.updates_resume or args.browser_only):
        parser.error('The multi-user trial must run separately from other scenarios')
    if (args.langchain or args.framework) and (
            args.coordination or args.coordination_resume or args.incremental_csv or args.updates
            or args.browser_only or args.updates_after_repair or args.updates_resume
            or (args.langchain and args.framework)):
        parser.error('Framework trials must run separately from other scenarios')
    if args.coordination and not args.incremental_csv:
        parser.error('--coordination requires --incremental-csv')
    args.output.mkdir(parents=True, exist_ok=True, mode=0o700)
    name = 'backintel-s20-' + secrets.token_hex(6)
    env = os.environ.copy()
    env['POSTGRES_PASSWORD'] = secrets.token_urlsafe(24)
    env.pop('OPENROUTER_API_KEY', None)
    server = None
    database_ready = False
    database_started = False
    database_mount = []
    if args.sustained:
        storage = (args.output/'postgres-data').resolve()
        storage.mkdir(mode=0o700)
        database_mount = ['--mount', f'type=bind,source={storage},target=/var/lib/postgresql/data']
    summary = {'status': 'failed', 'scope': 'local working tree; historical retail data', 'model_calls': None}
    with tempfile.TemporaryDirectory(prefix='BackIntelS20Credentials') as secret_dir:
        try:
            since = str(int(time.time()) - 1)
            command(['docker', 'run', '-d', '--rm', '--name', name, '-p', '127.0.0.1::5432',
                     '-e', 'POSTGRES_PASSWORD', '-e', 'POSTGRES_DB=backintel_app', '--health-cmd',
                     'pg_isready -h 127.0.0.1 -U postgres -d backintel_app', '--health-interval', '1s',
                     '--health-retries', '30', *database_mount, 'postgres:17-alpine'], env=env)
            database_started = True
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
            # Restored reference archives predate private objectives. Explicitly share
            # only this disposable demonstration objective with its retained run owner.
            db.write('''INSERT INTO backintel.analysis_goal_access(goal_id,principal_id,permission)
                VALUES(%s,%s,'manage') ON CONFLICT(goal_id,principal_id) DO UPDATE SET permission='manage' ''',
                (source['goal_id'], actor['id']))
            assert source['status'] == 'succeeded' and source['body']['operation'] == 'answer'
            assert source['result']['mode'] != 'fixture'
            if args.coordination_resume:
                source = db.run(json.loads(args.coordination_resume.read_text())['run_id'])
                assert source['owner'] == actor['id'] and source['body']['operation'] == 'coordination'
                source_id = source['id']
                package = {'body': {
                    'interpretation': db.step(source_id, 'coord-agent-data')['contribution'],
                    'method': db.step(source_id, 'coord-agent-analysis')['contribution']}}
            elif args.coordination:
                prepared = db.run(source['result']['calculation']['preparation_run_id'])
                interpreted = db.run(prepared['result']['interpretation_run_id'])
                package = {'body': {'interpretation': interpreted['result']['interpretation'],
                                    'method': source['result']['calculation']['method']}}
            else:
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
                if args.sustained:
                    from scripts.validation.workflow_sustained_cases import check_sustained
                    result = check_sustained(actor, source, package, client, args.output, source_owner_uri, name, server.pid)
                    assert db.query('SELECT id,status,charge FROM backintel.analysis_requests ORDER BY id') == baseline_requests
                    summary.update(**result)
                    return 0 if result['status'] == 'passed' else 1
                if args.cross_systems:
                    from scripts.validation.workflow_cross_system_cases import check_cross_systems
                    result = check_cross_systems(actor, source, package, client, args.output, source_owner_uri,
                                                 resume=args.cross_systems_resume)
                    assert db.query('SELECT id,status,charge FROM backintel.analysis_requests ORDER BY id') == baseline_requests
                    summary.update(**result)
                    return 0
                if args.documents:
                    from scripts.validation.workflow_document_cases import check_documents
                    result = check_documents(actor, source, package, client, args.output, args.documents,
                                             resume=args.documents_resume, live=args.documents_live)
                    if not args.documents_live:
                        assert db.query('SELECT id,status,charge FROM backintel.analysis_requests ORDER BY id') == baseline_requests
                    summary.update(**result)
                    return 0
                if args.multi_user:
                    from scripts.validation.workflow_multiuser_cases import check_multiuser
                    result = check_multiuser(actor, source, package, client, args.output, checks_only=args.multi_user == 'checks')
                    assert db.query('SELECT id,status,charge FROM backintel.analysis_requests ORDER BY id') == baseline_requests
                    (args.output/'multiuser-cases.json').write_text(json.dumps(result, default=str, indent=2))
                    summary.update(**result)
                    return 0
                if args.framework:
                    if args.framework == 'agno':
                        from scripts.validation.agno_trial import check_agno
                        result = check_agno(actor, source, package, client, args.output)
                    else:
                        from scripts.validation.mastra_trial import check_mastra
                        result = check_mastra(actor, source, package, client, args.output)
                    assert db.query('SELECT id,status,charge FROM backintel.analysis_requests ORDER BY id') == baseline_requests
                    (args.output/f'{args.framework}-cases.json').write_text(json.dumps(result, indent=2))
                    summary.update(**result)
                    return 0
                if args.langchain:
                    from scripts.validation.langchain_trial import check_langchain
                    result = check_langchain(actor, source, package, client, args.output)
                    assert db.query('SELECT id,status,charge FROM backintel.analysis_requests ORDER BY id') == baseline_requests
                    (args.output/'langchain-cases.json').write_text(json.dumps(result, indent=2))
                    summary.update(**result)
                    return 0
                if args.coordination:
                    from scripts.validation.workflow_coordination_cases import check_coordination
                    result = check_coordination(actor, source, package, client, args.output,
                                                live=args.coordination == 'live', resume=args.coordination_resume,
                                                max_spend_usd=args.coordination_max_spend_usd)
                    retained = db.query('SELECT id,status,charge FROM backintel.analysis_requests ORDER BY id')
                    assert all(row in retained for row in baseline_requests), 'Earlier request accounting changed'
                    (args.output/'coordination-cases.json').write_text(json.dumps(result, default=str, indent=2))
                    summary.update(**result)
                    return 0
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
        except Exception as error:
            summary['error'] = str(error)
            raise
        finally:
            if server is not None:
                os.killpg(server.pid,signal.SIGTERM)
                try:
                    server.wait(timeout=20)
                except subprocess.TimeoutExpired:
                    os.killpg(server.pid,signal.SIGKILL); server.wait(timeout=5)
            if database_ready:
                try:
                    if not args.coordination or (args.output/'run.json').exists():
                        dump=command(['docker','exec',name,'pg_dump','-U','postgres','-d','backintel_app','-Fc'])
                        archive_allowed = True
                        if args.sustained:
                            database_bytes = int(command(['docker','exec',name,'du','-sk','/var/lib/postgresql/data']).stdout.split()[0])*1024
                            from scripts.validation.workflow_sustained_cases import evidence_bytes, prior_trial_bytes
                            output_bytes = evidence_bytes(args.output) + prior_trial_bytes(args.output)
                            peak_with_archive = database_bytes + output_bytes + len(dump.stdout)
                            archive_allowed = peak_with_archive <= 4_000_000_000
                            summary['storage_bytes_including_archive'] = peak_with_archive
                            summary['archive_retained'] = archive_allowed
                            if not archive_allowed:
                                summary.update(status='failed', archive_storage_limit_exceeded=True,
                                               error='The retained database archive would exceed the approved 4 GB storage limit')
                            report_path = args.output/'sustained-report.json'
                            if report_path.exists():
                                report = json.loads(report_path.read_text())
                                report.update(storage_bytes_including_archive=peak_with_archive, archive_retained=archive_allowed)
                                if not archive_allowed:
                                    report.update(status='failed', error=summary['error'])
                                report_path.write_text(json.dumps(report, default=str, indent=2))
                        if archive_allowed:
                            (args.output/'runtime-result.dump').write_bytes(dump.stdout)
                finally:
                    command(['docker','rm','-f',name])
                    summary['database_removed']=True
            elif database_started:
                command(['docker','rm','-f',name])
                summary['database_removed']=True
            summary['native_server_stopped']=server is None or server.poll() is not None
            (args.output/'summary.json').write_text(json.dumps(summary,default=str,indent=2))
            print(json.dumps(summary,default=str),flush=True)
            if summary.get('archive_storage_limit_exceeded'):
                raise RuntimeError(summary['error'])
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
