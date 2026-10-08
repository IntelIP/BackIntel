"""Check Compose authentication and actual TCP denial in an owned throwaway database."""
import json
import os
from pathlib import Path
import secrets
import subprocess
import time
import uuid

ROOT = Path(__file__).resolve().parents[2]


def main():
    password = secrets.token_hex(32)
    env = {**os.environ, 'POSTGRES_PASSWORD': password,
           'BACKINTEL_ANALYSIS_DB_PASSWORD': password, 'BACKINTEL_CAPABILITY_DB_PASSWORD': password}
    for filename in ('compose.analysis.yml', 'compose.capabilities.yml'):
        result = subprocess.run(['docker', 'compose', '-f', filename, 'config', '--format', 'json'],
                                cwd=ROOT, env=env, capture_output=True, check=True, timeout=20)
        services = json.loads(result.stdout)['services']
        database = services['postgres']
        assert database['environment'].get('POSTGRES_HOST_AUTH_METHOD') != 'trust'
        assert database['environment']['POSTGRES_PASSWORD'] == password
        assert services['runtime']['environment']['PGPASSWORD'] == password
        assert 'hba_file=/etc/postgresql/backintel-hba.conf' in database['command']
        assert any(v['target'] == '/etc/postgresql/backintel-hba.conf' and v.get('read_only')
                   and Path(v['source']).resolve() == ROOT / 'config/local-postgres-hba.conf'
                   for v in database['volumes'])
    name = 'backintel-auth-check-' + uuid.uuid4().hex[:12]
    try:
        subprocess.run(['docker', 'run', '-d', '--name', name, '-e', 'POSTGRES_PASSWORD',
                        '-v', str(ROOT / 'config/local-postgres-hba.conf') + ':/etc/postgresql/backintel-hba.conf:ro',
                        'postgres:16', 'postgres', '-c', 'hba_file=/etc/postgresql/backintel-hba.conf'],
                       env=env, capture_output=True, check=True, timeout=60)
        deadline = time.monotonic() + 30
        while subprocess.run(['docker', 'exec', name, 'pg_isready', '-h', '127.0.0.1', '-U', 'postgres'],
                             capture_output=True, timeout=5).returncode:
            if time.monotonic() >= deadline:
                raise TimeoutError('Owned database did not become ready')
            time.sleep(.25)
        for supplied, expected in (('', False), ('wrong-fixture-password', False), (password, True)):
            attempt = subprocess.run(['docker', 'exec', '-e', 'PGPASSWORD', name,
                                      'psql', '-h', '127.0.0.1', '-U', 'postgres', '-w', '-Atc', 'SELECT 1'],
                                     env={**env, 'PGPASSWORD': supplied}, capture_output=True, timeout=10)
            assert (attempt.returncode == 0) == expected, 'TCP authentication boundary failed'
    finally:
        subprocess.run(['docker', 'rm', '-fv', name], capture_output=True, check=True, timeout=20)
    print(json.dumps({'status': 'passed', 'passwordless_tcp': 'denied', 'wrong_password': 'denied',
                      'correct_password': 'accepted', 'owned_database': 'removed', 'provider_calls': 0}))


if __name__ == '__main__':
    main()
