"""Run every Python unit module with its own disposable test database."""
import json
import os
from pathlib import Path
import subprocess
import sys
import uuid

import psycopg
from psycopg import sql
from psycopg.conninfo import conninfo_to_dict, make_conninfo

ROOT = Path(__file__).resolve().parents[2]


def main():
    base = os.environ.get("BACKINTEL_TEST_DATABASE_URL", "")
    if not base or not conninfo_to_dict(base).get("dbname", "").startswith("test_"):
        raise RuntimeError("All-unit checks require an explicitly isolated test_ database server")
    output = Path(os.environ.get("BACKINTEL_UNIT_OUTPUT", ROOT / "artifacts/validation/DecisionWorkspace/PythonUnits"))
    output.mkdir(parents=True, exist_ok=True)
    results = []
    with psycopg.connect(make_conninfo(base, dbname="postgres"), autocommit=True) as admin:
        for file in sorted((ROOT / "tests").glob("test_*.py")):
            name = "test_unit_" + uuid.uuid4().hex[:12]
            if file.name == "test_olist_facts.py":
                name = "backintel_unit_" + uuid.uuid4().hex[:12] + "_test"
            admin.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(name)))
            env = dict(os.environ, BACKINTEL_TEST_DATABASE_URL=make_conninfo(base, dbname=name), BACKINTEL_APP_DATABASE_URL=make_conninfo(base, dbname=name), PYTHONDONTWRITEBYTECODE="1")
            try:
                if file.name != "test_olist_facts.py":
                    subprocess.run([sys.executable, "-m", "runtime.bootstrap"], cwd=ROOT, env=env, check=True, capture_output=True)
                run = subprocess.run([sys.executable, "-m", "unittest", "discover", "-s", "tests", "-p", file.name, "-v"], cwd=ROOT, env=env, capture_output=True, text=True, timeout=180)
                (output / (file.stem + ".log")).write_text(run.stdout + run.stderr)
                results.append({"module": file.name, "status": "passed" if run.returncode == 0 else "failed"})
                print(file.name + ": " + results[-1]["status"], flush=True)
                if run.returncode:
                    print(run.stderr[-6000:], flush=True)
            finally:
                admin.execute(sql.SQL("DROP DATABASE {} WITH (FORCE)").format(sql.Identifier(name)))
    (output / "results.json").write_text(json.dumps(results, indent=2) + "\n")
    return int(any(result["status"] != "passed" for result in results))


if __name__ == "__main__":
    raise SystemExit(main())
