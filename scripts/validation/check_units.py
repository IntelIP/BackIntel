"""Run every Python unit module with its own disposable test database."""
import argparse
import json
import os
import re
from pathlib import Path
import subprocess
import sys
import uuid

import psycopg
from psycopg import sql
from psycopg.conninfo import conninfo_to_dict, make_conninfo

ROOT = Path(__file__).resolve().parents[2]


def main():
    files = sorted((ROOT / 'tests').glob('test_*.py'))
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--module', action='append', choices=[file.name for file in files])
    args = parser.parse_args()
    base = os.environ.get('BACKINTEL_VALIDATION_ADMIN_URL') or os.environ.get("BACKINTEL_TEST_DATABASE_URL", "")
    settings = conninfo_to_dict(base) if base else {}
    if os.environ.get('BACKINTEL_VALIDATION_ADMIN_URL'):
        if settings.get('host') not in ('localhost','127.0.0.1'):
            raise RuntimeError('Validation admin must address the local test server')
    elif not settings.get('dbname', '').startswith('test_'):
        raise RuntimeError("All-unit checks require an explicitly isolated test_ database server")
    output = Path(os.environ.get("BACKINTEL_UNIT_OUTPUT", ROOT / "artifacts/validation/DecisionWorkspace/PythonUnits"))
    output.mkdir(parents=True, exist_ok=True)
    results = []
    with psycopg.connect(make_conninfo(base, dbname="postgres"), autocommit=True) as admin:
        for file in files:
            if args.module and file.name not in args.module:
                continue
            name = "test_unit_" + uuid.uuid4().hex[:12]
            if file.name == "test_olist_facts.py" or file.name.startswith('test_analysis'):
                name = "backintel_unit_" + uuid.uuid4().hex[:12] + "_test"
            admin.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(name)))
            env = dict(os.environ, BACKINTEL_TEST_DATABASE_URL=make_conninfo(base, dbname=name), BACKINTEL_APP_DATABASE_URL=make_conninfo(base, dbname=name), PYTHONDONTWRITEBYTECODE="1")
            if file.name.startswith('test_analysis'):
                env['BACKINTEL_ANALYSIS_CHECK_DB'] = env['BACKINTEL_TEST_DATABASE_URL']
            for key in ('OPENROUTER_API_KEY','OPENAI_API_KEY','ANTHROPIC_API_KEY','GEMINI_API_KEY'):
                env[key] = ''
            env['BACKINTEL_ANALYST_CREDENTIAL_FILE'] = str(output / 'no-analyst-credential.json')
            env['BACKINTEL_PROVIDER_CREDENTIAL_FILE'] = str(output / 'no-provider-credential.json')
            try:
                if file.name != "test_olist_facts.py":
                    subprocess.run([sys.executable, "-m", "runtime.bootstrap"], cwd=ROOT, env=env, check=True, capture_output=True)
                code = '''import httpx,sys,unittest
original=httpx.Client.send
def guarded(self,request,*args,**kwargs):
    if request.url.host not in ('testserver','localhost','127.0.0.1','::1'):raise RuntimeError('External provider transport forbidden')
    return original(self,request,*args,**kwargs)
httpx.Client.send=guarded
result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.discover('tests',pattern=sys.argv[1]))
sys.exit(0 if result.wasSuccessful() else 1)
'''
                run = subprocess.run([sys.executable, '-c', code, file.name], cwd=ROOT, env=env, capture_output=True, text=True, timeout=180)
                log = run.stdout + run.stderr
                password = conninfo_to_dict(base).get('password')
                if password:
                    log = log.replace(password, '[redacted]')
                (output / (file.stem + ".log")).write_text(log)
                count = re.search(r'Ran (\d+) tests?', run.stderr)
                skipped = re.search(r'skipped=(\d+)', run.stderr)
                results.append({"module": file.name, "status": "passed" if run.returncode == 0 else "failed",
                                "tests": int(count[1]) if count else 0, "skipped": int(skipped[1]) if skipped else 0})
                print(file.name + ": " + results[-1]["status"], flush=True)
                if run.returncode:
                    print(log[-6000:], flush=True)
            finally:
                admin.execute(sql.SQL("DROP DATABASE {} WITH (FORCE)").format(sql.Identifier(name)))
    (output / "results.json").write_text(json.dumps(results, indent=2) + "\n")
    return int(any(result["status"] != "passed" for result in results))


if __name__ == "__main__":
    raise SystemExit(main())
