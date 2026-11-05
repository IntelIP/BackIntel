"""Install and operate the declared local PostgreSQL workflow without private setup."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import secrets
import selectors
import socket
import subprocess
import sys
import time
from urllib.parse import quote
import webbrowser
import zipfile

ROOT = Path(__file__).resolve().parents[1]
SOURCE_SHA = 'd07aec9960083af2339975a3f9d3b26313b342dcd9f86cce0b919b1cde639a44'
POSTGRES_IMAGE = 'pgvector/pgvector:pg18'
PREPARATION_IMAGE = 'python:3.12-slim-bookworm'
STATE_FILE = 'platform-state.json'


def docker(*args, env=None):
    return subprocess.run(['docker', *args], check=True, capture_output=True,
                          text=True, env=env, timeout=180).stdout.strip()


def save_state(directory, state):
    path = directory / STATE_FILE
    temporary = directory / (STATE_FILE + '.tmp')
    descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(descriptor, 'w') as stream:
        json.dump(state, stream, indent=2)
    temporary.replace(path)


def read_state(directory):
    if directory.is_symlink() or (directory / STATE_FILE).is_symlink():
        raise ValueError('Installation state must not be a symbolic link')
    state = json.loads((directory / STATE_FILE).read_text())
    if state.get('format') != 'backintel.local-platform/v1':
        raise ValueError('This is not a BackIntel local installation')
    return state


def owned_container(state):
    details = json.loads(docker('inspect', state['container']))[0]
    if details['Config'].get('Labels', {}).get('backintel.installation') != state['id']:
        raise ValueError('Container does not belong to this installation')
    return details


def wait_database(state):
    if owned_container(state)['State'].get('Health', {}).get('Status') == 'healthy':
        return
    process = subprocess.Popen(
        ['docker', 'events', '--since', str(int(time.time()) - 120), '--filter',
         'container=' + state['container'], '--filter', 'event=health_status',
         '--format', '{{.Action}}'], stdout=subprocess.PIPE, text=True)
    try:
        with selectors.DefaultSelector() as selector:
            selector.register(process.stdout, selectors.EVENT_READ)
            deadline = time.monotonic() + 55
            while time.monotonic() < deadline:
                if not selector.select(max(0, deadline - time.monotonic())):
                    break
                event = process.stdout.readline().strip()
                if not event:
                    break
                if event.endswith(': healthy') and owned_container(state)['State'].get('Health', {}).get('Status') == 'healthy':
                    return
            raise RuntimeError('PostgreSQL did not become ready within 55 seconds')
    finally:
        process.terminate()
        process.wait(timeout=5)


def database_ready(directory, state):
    from psycopg.conninfo import make_conninfo
    if not owned_container(state)['State']['Running']:
        docker('start', state['container'])
    wait_database(state)
    port = docker('port', state['container'], '5432/tcp').rsplit(':', 1)[-1]
    state['database_url'] = make_conninfo(state['database_url'], port=port)
    if state.get('source_url'):
        state['source_url'] = make_conninfo(state['source_url'], port=port)
    save_state(directory, state)


def native_database_url(value):
    """Aegra needs a URL; psycopg also accepts the private libpq connection form."""
    if value.startswith(('postgresql://', 'postgres://')):
        return value
    from psycopg.conninfo import conninfo_to_dict
    settings = conninfo_to_dict(value)
    auth = quote(settings['user'], safe='') + ':' + quote(settings['password'], safe='')
    return ('postgresql://' + auth + '@' + settings['host'] + ':' + settings['port']
            + '/' + quote(settings['dbname'], safe=''))


def runtime_environment(directory, state, *, allow_models=False, budget_usd=None):
    if allow_models:
        if budget_usd is None or not math.isfinite(budget_usd) or not 0 < budget_usd <= 0.5:
            raise ValueError('Live models require an explicit cumulative allowance of at most US$0.50')
        if not os.environ.get('OPENROUTER_API_KEY'):
            raise ValueError('Inject OPENROUTER_API_KEY through your local credential store first')
    elif budget_usd is not None:
        raise ValueError('A model allowance also requires --allow-models')
    env = dict(os.environ)
    # The installation must never inherit another checkout's database or source authority.
    for name in tuple(env):
        if name.startswith(('BACKINTEL_', 'AEGRA_', 'POSTGRES_', 'PG')) or name in (
                'DATABASE_URL', 'REDIS_URL', 'OPENAI_API_KEY', 'OPENROUTER_API_KEY',
                'PYTHONPATH', 'PYTHONHOME', 'LANGSMITH_API_KEY', 'LANGCHAIN_API_KEY'):
            env.pop(name)
    env.update(
        BACKINTEL_APP_DATABASE_URL=state['database_url'], DATABASE_URL=native_database_url(state['database_url']),
        BACKINTEL_SOURCE_RETAIL=state.get('source_url', ''),
        BACKINTEL_ACCESS_CREDENTIAL_FILE=str(directory / 'access.json'),
        BACKINTEL_AEGRA_URL='http://127.0.0.1:2028',
        BACKINTEL_PREPARATION_IMAGE=state['preparation_image'],
        BACKINTEL_DATASET_DIR=str(directory / 'datasets'),
        BACKINTEL_MODEL_DIR=str(directory / 'models'),
        AEGRA_CONFIG=str(ROOT / 'aegra.analysis.json'), REDIS_BROKER_ENABLED='false',
        WORKER_COUNT='1', N_JOBS_PER_WORKER='1', HF_HUB_OFFLINE='1',
        OPENROUTER_API_KEY=os.environ['OPENROUTER_API_KEY'] if allow_models else '',
        OTEL_TARGETS='', OTEL_CONSOLE_EXPORT='false', LANGSMITH_TRACING='false',
        LANGCHAIN_TRACING_V2='false')
    return env


def initialize(directory, csv_path, acknowledge_terms):
    if not acknowledge_terms:
        raise ValueError('Read the dataset attribution and acknowledge its terms with --acknowledge-terms')
    if directory.exists():
        raise ValueError('Choose a new state directory; setup never overwrites an installation')
    with csv_path.open('rb') as stream:
        if hashlib.file_digest(stream, 'sha256').hexdigest() != SOURCE_SHA:
            raise ValueError('The supplied CSV differs from the documented Online Retail snapshot')
    if not (ROOT / 'apps/web/dist/index.html').is_file():
        raise ValueError('Build the web interface using the documented npm commands first')
    from psycopg.conninfo import make_conninfo
    for image in (POSTGRES_IMAGE, PREPARATION_IMAGE):
        try:
            docker('image', 'inspect', image)
        except subprocess.CalledProcessError:
            print('Downloading public runtime image: ' + image, flush=True)
            docker('pull', image)
    directory.mkdir(parents=True, mode=0o700)
    identity = secrets.token_hex(8)
    password = secrets.token_urlsafe(32)
    state = {
        'format': 'backintel.local-platform/v1', 'id': identity,
        'container': 'backintel-platform-' + identity, 'ready': False,
        'database_url': make_conninfo(host='127.0.0.1', port=5432, dbname='backintel_app',
                                     user='postgres', password=password),
        'preparation_image': docker('image', 'inspect', PREPARATION_IMAGE, '--format', '{{.Id}}'),
        'postgres_image': docker('image', 'inspect', POSTGRES_IMAGE, '--format', '{{.Id}}'),
        'source_sha256': SOURCE_SHA, 'model_allowance_usd': 0}
    save_state(directory, state)
    (directory / 'postgres-data').mkdir(mode=0o700)
    docker('run', '-d', '--name', state['container'], '--label', 'backintel.installation=' + identity,
           '-p', '127.0.0.1::5432', '-e', 'POSTGRES_PASSWORD', '-e', 'POSTGRES_DB=backintel_app',
           '--mount', 'type=bind,src=' + str(directory / 'postgres-data') + ',dst=/var/lib/postgresql',
           '--health-cmd', 'pg_isready -U postgres -d backintel_app', '--health-interval', '2s',
           '--health-retries', '25', state['postgres_image'],
           env={**os.environ, 'POSTGRES_PASSWORD': password})
    database_ready(directory, state)
    env = runtime_environment(directory, state)
    os.environ.clear()
    os.environ.update(env)
    from runtime.bootstrap import initialize as initialize_database
    from scripts.analysis_demo import seed
    from scripts.validation.run_source_discovery import provision_source
    from runtime import analysis_store as db
    initialize_database()
    seed(administrator=True, budget_usd=0)
    db.write("UPDATE backintel.analysis_principals SET domains=ARRAY['commerce'] WHERE role <> 'worker'")
    state['source_url'], state['source_rows'] = provision_source(state['database_url'], csv_path)
    db.write('''INSERT INTO backintel.analysis_source_connections
                (id,domain,secret_ref,schemas,principals)
                VALUES('online-retail-postgres','commerce','BACKINTEL_SOURCE_RETAIL',
                       ARRAY['retail_raw'],ARRAY['manager'])''')
    state['ready'] = True
    save_state(directory, state)
    print(json.dumps({'status': 'ready', 'source_rows': state['source_rows'],
                      'source_ref': 'online-retail-postgres', 'model_allowance_usd': 0,
                      'state_directory': str(directory)}))


def start(directory, state, allow_models, budget_usd):
    if not state['ready']:
        raise ValueError('Setup is incomplete; inspect this installation before starting')
    with socket.socket() as probe:
        probe.bind(('127.0.0.1', 2028))
    env = runtime_environment(directory, state, allow_models=allow_models, budget_usd=budget_usd)
    database_ready(directory, state)
    env.update(BACKINTEL_APP_DATABASE_URL=state['database_url'], DATABASE_URL=native_database_url(state['database_url']),
               BACKINTEL_SOURCE_RETAIL=state['source_url'])
    os.environ.clear()
    os.environ.update(env)
    from scripts.analysis_demo import seed
    seed(administrator=True, budget_usd=budget_usd if allow_models else 0)
    state['model_allowance_usd'] = budget_usd if allow_models else 0
    save_state(directory, state)
    print('Starting local BackIntel at http://127.0.0.1:2028; press Ctrl-C to stop the API.', flush=True)
    os.chdir(ROOT)
    os.execvpe(sys.executable, [sys.executable, '-m', 'uvicorn', 'aegra_api.main:app',
                              '--host', '127.0.0.1', '--port', '2028'], env)


def package(output):
    if output.exists():
        raise ValueError('Choose a new candidate filename')
    files = subprocess.check_output(['git', 'ls-files', '-z', '--cached', '--others',
                                     '--exclude-standard'], cwd=ROOT).decode().split('\0')
    allowed = ('runtime/', 'scripts/', 'config/', 'migrations/', 'apps/web/', 'tests/',
               'data/profiles/', 'docs/')
    files = [name for name in files if name and
             (name.startswith(allowed) or name.startswith(('requirements', 'aegra.')) or
              name in ('README.md', 'LICENSE', 'AGENTS.md'))]
    files.extend(str(path.relative_to(ROOT)) for path in (ROOT / 'apps/web/dist').rglob('*') if path.is_file())
    if not (ROOT / 'apps/web/dist/index.html').is_file():
        raise ValueError('Build the web interface before packaging')
    manifest = {'format': 'backintel.local-candidate/v1',
                'base_commit': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
                'working_tree': True, 'files': {}}
    output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output, 'x', compression=zipfile.ZIP_DEFLATED) as archive:
        for name in sorted(set(files)):
            path = ROOT / name
            if path.is_symlink() or not path.is_file():
                raise ValueError('Candidate entries must be ordinary source files: ' + name)
            payload = path.read_bytes()
            manifest['files'][name] = hashlib.sha256(payload).hexdigest()
            archive.writestr('BackIntel/' + name, payload)
        archive.writestr('BackIntel/local-candidate.json', json.dumps(manifest, indent=2))
    print(json.dumps({'candidate': str(output), 'files': len(manifest['files']),
                      'sha256': hashlib.sha256(output.read_bytes()).hexdigest(),
                      'base_commit': manifest['base_commit'], 'working_tree': True}))


def demo_update(directory, state):
    """Explicit owner action on this installation's disposable retail source."""
    import psycopg
    from psycopg.conninfo import make_conninfo
    database_ready(directory, state)
    with psycopg.connect(make_conninfo(state['database_url'], dbname='backintel_retail_source')) as connection:
        connection.execute('LOCK TABLE retail_raw.invoice_lines IN EXCLUSIVE MODE')
        identity = connection.execute('SELECT max(source_row_id)+1 FROM retail_raw.invoice_lines').fetchone()[0]
        connection.execute('''INSERT INTO retail_raw.invoice_lines VALUES
            (%s,%s,'S35-DEMO','Explicitly synthetic independent-installation check','1',
             '12/9/2011 12:00','10.00','99999','United Kingdom')''',
                           (identity, 'S35DEMO' + str(identity)))
    print(json.dumps({'synthetic_record_added': identity, 'quantity': 1, 'unit_price_gbp': 10,
                      'expected_net_invoice_value_change_gbp': 10}))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--state', type=Path, help='Private state directory, outside the source package')
    actions = parser.add_subparsers(dest='command', required=True)
    setup = actions.add_parser('setup')
    setup.add_argument('--csv', type=Path, required=True)
    setup.add_argument('--acknowledge-terms', action='store_true')
    launch = actions.add_parser('start')
    launch.add_argument('--allow-models', action='store_true')
    launch.add_argument('--budget-usd', type=float)
    for name in ('status', 'open', 'stop', 'demo-update'):
        actions.add_parser(name)
    bundle = actions.add_parser('package')
    bundle.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.command == 'package':
        package(args.output.expanduser().absolute())
        return
    if args.state is None:
        parser.error('--state is required for installation commands')
    if args.state.expanduser().is_symlink():
        parser.error('Installation state must not be a symbolic link')
    directory = args.state.expanduser().resolve()
    if directory == ROOT or ROOT in directory.parents:
        parser.error('Keep installation state outside the source package')
    if args.command == 'setup':
        initialize(directory, args.csv.expanduser().resolve(), args.acknowledge_terms)
        return
    state = read_state(directory)
    if args.command == 'start':
        start(directory, state, args.allow_models, args.budget_usd)
    elif args.command == 'stop':
        owned_container(state)
        docker('stop', state['container'])
        print('Installation database stopped. Saved data and access grants are retained.')
    elif args.command == 'status':
        details = owned_container(state)
        print(json.dumps({'ready': state['ready'], 'database_running': details['State']['Running'],
                          'source_rows_at_setup': state.get('source_rows'),
                          'model_allowance_usd': state['model_allowance_usd'],
                          'url': 'http://127.0.0.1:2028'}))
    elif args.command == 'demo-update':
        demo_update(directory, state)
    elif args.command == 'open':
        token = json.loads((directory / 'access.json').read_text())['manager']
        if not webbrowser.open('http://127.0.0.1:2028/#access=' + token):
            raise RuntimeError('The browser could not open; retry from an interactive desktop')


if __name__ == '__main__':
    main()
