"""Approved S-36 local workload: actual source updates, native workers, no inference."""
from datetime import datetime, timedelta, timezone
from decimal import Decimal
import hashlib
import json
import os
from pathlib import Path
import secrets
import signal
import subprocess
import sys
import time

import psycopg
from psycopg import sql


ROOT = Path(__file__).resolve().parents[2]
DURATION = 1800
INTERVAL = 300
STORAGE_LIMIT = 4_000_000_000


def command(*args):
    return subprocess.check_output(args, text=True, stderr=subprocess.PIPE, timeout=30).strip()


def evidence_bytes(output):
    size = 0
    for directory, children, files in os.walk(output):
        if Path(directory) == output:
            children[:] = [name for name in children if name != 'postgres-data']
        for name in files:
            try:
                size += (Path(directory)/name).stat().st_size
            except FileNotFoundError:
                pass
    return size


def prior_trial_bytes(output):
    size = 0
    for path in output.parent.glob('S36*'):
        if path.is_dir() and path != output:
            size += evidence_bytes(path)
            if (path/'postgres-data').exists():
                size += int(command('du', '-sk', str(path/'postgres-data')).split()[0])*1024
    return size


def processes(roots):
    """Numeric process measurements only; never collect environment or credentials."""
    rows = [line.split() for line in command('ps', '-axo', 'pid=,ppid=,%cpu=,rss=').splitlines()]
    owned = set(roots)
    while True:
        children = {int(row[0]) for row in rows if int(row[1]) in owned}
        if children <= owned:
            break
        owned |= children
    selected = [row for row in rows if int(row[0]) in owned]
    return owned, {'cpu_percent': sum(float(row[2]) for row in selected),
                   'rss_bytes': sum(int(row[3]) * 1024 for row in selected)}


def container_resources(database, scratch):
    """Identify trial calculation containers by their owned, read-only bind mounts."""
    owned = [database]
    candidates = command('docker', 'ps', '--filter', 'name=backintel-sandbox-', '--format', '{{.ID}}').splitlines()
    for identity in candidates:
        try:
            inspected = json.loads(command('docker', 'inspect', identity))[0]
            if any(Path(mount['Source']).is_relative_to(scratch) for mount in inspected['Mounts']):
                owned.append(identity)
        except subprocess.CalledProcessError:
            continue  # A completed --rm calculation can vanish between listing and inspection.
    measurements = []
    for identity in owned:
        try:
            lines = command('docker', 'exec', identity, 'sh', '-c',
                'cat /sys/fs/cgroup/cpu.stat; cat /sys/fs/cgroup/memory.current; cat /sys/fs/cgroup/memory.peak').splitlines()
            measurements.append({'container': identity,
                'cpu_microseconds': int(next(line.split()[1] for line in lines if line.startswith('usage_usec '))),
                'memory_bytes': int(lines[-2]), 'peak_memory_bytes': int(lines[-1])})
        except subprocess.CalledProcessError:
            if identity == database:
                raise
    return measurements


def reference(connection):
    """Independent exact SQL totals and every recorded country/product category."""
    rows = connection.execute('''SELECT "Country",count(*),sum("Quantity"::numeric*"UnitPrice"::numeric),
        COALESCE(sum("Quantity"::numeric*"UnitPrice"::numeric) FILTER (WHERE "InvoiceNo" ILIKE 'c%%'),0)
        FROM retail_raw.invoice_lines GROUP BY "Country"''').fetchall()
    net, cancelled = sum(row[2] for row in rows), sum(row[3] for row in rows)
    products = connection.execute('''SELECT "StockCode",count(*),sum("Quantity"::numeric*"UnitPrice"::numeric),
        COALESCE(sum("Quantity"::numeric*"UnitPrice"::numeric) FILTER (WHERE "InvoiceNo" ILIKE 'c%%'),0)
        FROM retail_raw.invoice_lines GROUP BY "StockCode"''').fetchall()
    return {'rows': sum(row[1] for row in rows), 'totals': {
        'net_invoice_value': str(net), 'signed_cancellation_value': str(cancelled),
        'cancellation_reduction': str(-cancelled), 'value_without_cancellations': str(net-cancelled)},
        'groups': {field: {row[0]: {'row_count': row[1], 'net_value': str(row[2]),
                                  'signed_cancellation_value': str(row[3])} for row in records}
                   for field, records in (('Country', rows), ('StockCode', products))}}


def check_answer(run, expected):
    result = run['result']['calculation']
    coverage = result['coverage']
    assert coverage['expected_rows'] == coverage['processed_rows'] == expected['rows'], coverage
    assert all(coverage[key] == 0 for key in ('failed_rows', 'pending_rows', 'excluded_rows')), coverage
    assert result['currency'] == 'GBP', result['currency']
    for key, value in expected['totals'].items():
        assert Decimal(result['totals'][key]) == Decimal(value), (key, result['totals'][key], value)
    assert {part['field'] for part in result['dimensions']} == set(expected['groups'])
    for dimension in result['dimensions']:
        expected_groups = expected['groups'][dimension['field']]
        assert {group['value'] for group in dimension['groups']} == set(expected_groups)
        for group in dimension['groups']:
            for key, value in expected_groups[group['value']].items():
                assert Decimal(str(group[key])) == Decimal(str(value)), (group['value'], key)


def check_sustained(actor, source, package, client, output, source_uri, database, server_pid):
    from runtime import analysis_store as db, analysis_service as service, workflow_triggers as triggers
    from scripts.validation.workflow_multiuser_cases import import_reference

    started_setup = time.monotonic()
    scratch = (output/'scratch').resolve()
    scratch.mkdir(mode=0o700)
    retained_bytes = prior_trial_bytes(output)
    os.environ['BACKINTEL_PREPARATION_IMAGE'] = package['body']['dependencies']['image']
    info = json.loads(command('docker', 'info', '--format', '{{json .}}'))
    assert info['NCPU'] == 4 and info['MemTotal'] <= 8322945024, 'Docker allocation differs from approved trial'
    # Only this disposable archive is reset; older retained work is not part of the load.
    db.write("UPDATE backintel.capability_jobs SET state='cancelled' WHERE state IN ('queued','running','retry')")
    db.write("UPDATE backintel.analysis_workflow_triggers SET state='paused'")
    policy = db.query('SELECT * FROM backintel.analysis_source_connections WHERE id=%s',
                      (package['body']['connection']['source_ref'],), one=True)
    contexts = {}
    for name in ('a', 'b'):
        identity, token, source_ref = 's36-owner-' + name, secrets.token_urlsafe(32), 's36-retail-' + name
        db.write('''INSERT INTO backintel.analysis_principals(id,token_hash,role,domains,budget_usd)
            VALUES(%s,%s,'manager',%s,0)''', (identity, hashlib.sha256(token.encode()).hexdigest(), [policy['domain']]))
        db.write('''INSERT INTO backintel.analysis_source_connections(id,domain,secret_ref,schemas,principals)
            VALUES(%s,%s,%s,%s,%s)''', (source_ref, policy['domain'], policy['secret_ref'], policy['schemas'], [identity]))
        owner = {'id': identity}
        imported = import_reference(actor, source, package, owner, source_ref,
                                    'S-36 owner ' + name.upper() + ': ' + package['body']['question'])
        trigger = triggers.configure(imported['version'], owner, {
            'event_source': 's36-source-updates', 'timezone': 'UTC',
            'expires_at': (datetime.now(timezone.utc) + timedelta(hours=2)).isoformat(),
            'max_runs': 6, 'refresh_source': True})
        contexts[name] = {'actor': owner, 'token': token, 'package': imported, 'trigger': trigger}
        print('S-36: private retained method ready for owner ' + name.upper(), flush=True)

    def request(name, path, expected=200):
        response = client.get('/api/v1' + path, headers={'Authorization': 'Bearer ' + contexts[name]['token']})
        assert response.status_code == expected, (path, response.status_code)
        return response.json()

    for name, other in (('a', 'b'), ('b', 'a')):
        request(name, '/workflows/' + contexts[other]['package']['version'], 403)
        assert {item['id'] for item in request(name, '/goals')} == {contexts[name]['package']['body']['goal_id']}

    baseline_calls = db.query('SELECT id,status,charge FROM backintel.analysis_requests ORDER BY id')
    report = {'status': 'running', 'scope': 'local working tree; retained method, fresh PostgreSQL updates and native workers',
        'targets': {'duration_seconds': DURATION, 'owners': 2, 'active_jobs': 2, 'waiting_jobs': 6,
                    'records_per_update': 100, 'interval_seconds': INTERVAL, 'freshness_seconds': INTERVAL,
                    'additional_storage_bytes': STORAGE_LIMIT, 'docker_cpus': info['NCPU'],
                    'docker_memory_bytes': info['MemTotal'], 'paid_model_calls': 0},
        'queue_policy': 'Six outstanding jobs, including active retry reservations; two active at most.',
        'database_storage': 'Trial-owned host bind mount; existing Docker allocation unchanged.',
        'prior_trial_storage_bytes': retained_bytes,
        'measurement_scope': 'PostgreSQL plus calculation containers selected by trial-owned mounts; host process tree separately. Temporary calculation files are included in storage. Memory peaks are kernel-reported for observed containers and sampled for the combined workload.',
        'setup_seconds': time.monotonic()-started_setup, 'updates': [], 'answers': [], 'samples': [],
        'interruption': None, 'model_calls': 0, 'provider_cost_usd': 0, 'local_compute_usd': None,
        'cost_limit': 'No paid model calls. Local hardware and electricity are unpriced.',
        'overload_evidence': 'Separate disposable-database concurrent admission test; not a throughput fixture.'}
    report_path = output/'sustained-report.json'
    dispatcher = None
    logs = (output/'sustained-dispatch.log').open('a')
    started = time.monotonic()
    next_update, next_sample, next_progress = 0, 0, 0
    pending, completed, expected_versions = [], set(), {}
    interrupted_run = None

    def save():
        report['observed_seconds'] = time.monotonic()-started
        report_path.write_text(json.dumps(report, indent=2, default=str))

    try:
        while time.monotonic()-started < DURATION:
            elapsed = time.monotonic()-started
            if next_update < 6 and elapsed >= next_update * INTERVAL:
                with psycopg.connect(source_uri) as connection:
                    offset = 541909 + next_update * 100
                    columns = ['StockCode', 'Description', 'Quantity', 'InvoiceDate', 'UnitPrice', 'CustomerID', 'Country']
                    query = sql.SQL('''INSERT INTO retail_raw.invoice_lines
                        SELECT source_row_id+%s,'S36-' || %s || '-' || "InvoiceNo",{} FROM retail_raw.invoice_lines
                        WHERE source_row_id<=100 ORDER BY source_row_id''').format(sql.SQL(',').join(map(sql.Identifier, columns)))
                    assert connection.execute(query, (offset, str(next_update))).rowcount == 100
                observed = time.monotonic()-started
                with psycopg.connect(source_uri) as connection:
                    expected = reference(connection)
                expected_versions[expected['rows']] = expected
                report['updates'].append({'number': next_update, 'committed_seconds': observed,
                    'lateness_seconds': observed-next_update*INTERVAL, 'expected_rows': expected['rows'],
                    'data': '100 explicitly synthetic demonstration invoice lines'})
                for name, context in contexts.items():
                    event = {'event_id': 'update-' + str(next_update), 'source': 's36-source-updates'}
                    receipt = triggers.event(context['trigger']['id'], context['actor'], event)
                    assert receipt['status'] == 'accepted', receipt
                    replay = triggers.event(context['trigger']['id'], context['actor'], event)
                    assert replay['run_id'] == receipt['run_id'], replay
                    pending.append({'owner': name, 'update': next_update, 'refresh_run': receipt['run_id'],
                                    'source_commit_seconds': observed, 'expected_rows': expected['rows']})
                next_update += 1
                print(f'S-36: update {next_update}/6 committed; {expected["rows"]} source records; both owners admitted.', flush=True)

            if len(completed) < len(pending) and (dispatcher is None or dispatcher.poll() is not None):
                if dispatcher is not None:
                    assert dispatcher.returncode == 0, 'Dispatcher failed; inspect sustained-dispatch.log'
                dispatcher = subprocess.Popen([sys.executable, '-c',
                    'from runtime.analysis_service import dispatch; dispatch()'], cwd=ROOT,
                    env={**os.environ, 'TMPDIR': str(scratch)},
                    stdout=logs, stderr=subprocess.STDOUT, start_new_session=True)

            queues = {name: request(name, '/queue') for name in contexts}
            counts = queues['a']['shared_capacity']
            assert counts['active'] <= 2 and counts['waiting'] <= 6, counts
            for name, queue in queues.items():
                assert all(job['owner'] == contexts[name]['actor']['id'] for job in queue['jobs']), 'Private queue leaked'
                assert queue['your_usage']['provider_calls'] == 0, queue['your_usage']

            # Kill only a proven descendant supervisor of this trial's dispatcher.
            if report['interruption'] is None and counts['active'] and elapsed >= 15:
                descendants, _ = processes([dispatcher.pid])
                for pid in sorted(descendants - {dispatcher.pid}):
                    try:
                        argv = command('ps', '-p', str(pid), '-o', 'command=')
                        if ' -m runtime.job_worker ' in argv and '--run' not in argv and os.getpgid(pid) == pid:
                            running = db.query("SELECT r.id FROM backintel.analysis_runs r JOIN backintel.capability_jobs j ON j.job_id=r.job_id WHERE j.state='running' AND r.owner LIKE 's36-owner-%%'")
                            os.killpg(pid, signal.SIGKILL)
                            report['interruption'] = {'seconds': elapsed, 'owned_worker_pid': pid,
                                'running_candidates': [row['id'] for row in running], 'signal': 'SIGKILL'}
                            break
                    except (ProcessLookupError, subprocess.CalledProcessError):
                        continue

            for item in pending:
                if item['refresh_run'] in completed:
                    continue
                continuation = db.step(item['refresh_run'], 'refresh-workflow')
                if not continuation:
                    continue
                run = db.run(continuation['run_id'])
                if run['status'] != 'succeeded':
                    continue
                actual_rows = run['result']['calculation']['coverage']['expected_rows']
                assert actual_rows >= item['expected_rows'], 'Completed answer predates its source update'
                check_answer(run, expected_versions[actual_rows])
                finished = time.monotonic()-started
                attempts = db.query('SELECT attempts FROM backintel.capability_jobs WHERE job_id=%s',
                                    (db.run(item['refresh_run'])['job_id'],), one=True)['attempts']
                report['answers'].append({**item, 'workflow_run': run['id'], 'complete_seconds': finished,
                    'freshness_seconds': finished-item['source_commit_seconds'], 'processed_rows': actual_rows,
                    'refresh_attempts': attempts, 'all_totals_and_country_and_product_groups_match': True})
                completed.add(item['refresh_run'])
                if attempts > 1:
                    interrupted_run = item['refresh_run']
                print(f'S-36: owner {item["owner"].upper()} update {item["update"]+1} correct; freshness {finished-item["source_commit_seconds"]:.1f}s.', flush=True)

            if elapsed >= next_sample:
                _, host = processes([os.getpid(), server_pid, dispatcher.pid])
                containers = container_resources(database, scratch)
                database_bytes = int(command('docker', 'exec', database, 'du', '-sk', '/var/lib/postgresql/data').split()[0])*1024
                storage_bytes = database_bytes + evidence_bytes(output) + retained_bytes
                report['samples'].append({'seconds': elapsed, **counts, 'host': host,
                    'containers': containers, 'container_memory_bytes': sum(row['memory_bytes'] for row in containers),
                    'additional_storage_bytes': storage_bytes,
                    'waiting_seconds': max((float(job['waiting_seconds']) for queue in queues.values() for job in queue['jobs']), default=0)})
                assert storage_bytes <= STORAGE_LIMIT, 'Additional storage exceeds approved 4 GB limit'
                next_sample = elapsed + 10
                save()
            if elapsed >= next_progress:
                print(f'S-36: {elapsed/60:.1f}/30 minutes; {len(completed)}/12 answers complete; {counts["active"]} active, {counts["waiting"]} waiting.', flush=True)
                next_progress = elapsed + 50
            time.sleep(1)

        report['checks'] = {'six_source_updates': len(report['updates']) == 6,
            'twelve_correct_complete_answers': len(completed) == 12,
            'all_answers_within_five_minutes': len(completed) == 12 and all(item['freshness_seconds'] <= INTERVAL for item in report['answers']),
            'source_arrival_cadence': all(item['lateness_seconds'] < 10 for item in report['updates']),
            'forced_interruption_recovered': report['interruption'] is not None and interrupted_run is not None,
            'zero_new_model_calls': db.query('SELECT id,status,charge FROM backintel.analysis_requests ORDER BY id') == baseline_calls}
        report['recovered_run'] = interrupted_run
        report['status'] = 'passed' if all(report['checks'].values()) else 'failed'
        report['throughput_answers_per_minute'] = len(completed)/30
        report['unfinished'] = [item for item in pending if item['refresh_run'] not in completed]
    except (Exception, KeyboardInterrupt) as error:
        report.update(status='failed', error=str(error) or type(error).__name__)
        raise
    finally:
        if dispatcher is not None and dispatcher.poll() is None:
            os.killpg(dispatcher.pid, signal.SIGTERM)
            try:
                dispatcher.wait(timeout=10)
            except subprocess.TimeoutExpired:
                os.killpg(dispatcher.pid, signal.SIGKILL)
                dispatcher.wait(timeout=5)
        logs.close()
        report['model_call_ledger_unchanged'] = db.query('SELECT id,status,charge FROM backintel.analysis_requests ORDER BY id') == baseline_calls
        if not report['model_call_ledger_unchanged']:
            report.update(status='failed', error='Model request ledger changed during the zero-call trial')
        samples = report['samples']
        if samples:
            report['measured'] = {
                'peak_active_jobs': max(row['active'] for row in samples),
                'peak_waiting_jobs': max(row['waiting'] for row in samples),
                'max_observed_waiting_seconds': max(row['waiting_seconds'] for row in samples),
                'peak_sampled_container_memory_bytes': max(row['container_memory_bytes'] for row in samples),
                'peak_sampled_host_rss_bytes': max(row['host']['rss_bytes'] for row in samples),
                'peak_sampled_host_cpu_percent': max(row['host']['cpu_percent'] for row in samples),
                'max_observed_additional_storage_bytes': max(row['additional_storage_bytes'] for row in samples),
                'max_observed_freshness_seconds': max((row['freshness_seconds'] for row in report['answers']), default=None),
                'sample_interval_seconds': 10, 'host_cpu_percent_per_core': 100}
            observed_cpu = {}
            for sample in samples:
                for container in sample['containers']:
                    observed_cpu[container['container']] = container['cpu_microseconds']
            initial_database_cpu = next(row['cpu_microseconds'] for row in samples[0]['containers'] if row['container'] == database)
            report['measured']['observed_container_cpu_seconds'] = (sum(observed_cpu.values())-initial_database_cpu)/1_000_000
            report['measured']['cpu_scope'] = 'Database counter delta plus last observed calculation-container counters. Short-lived or post-sample work can be missed.'
        save()
    return {key: value for key, value in report.items() if key not in ('samples', 'answers', 'updates')}
