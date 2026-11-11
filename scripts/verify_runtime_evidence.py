"""Smoke-test runtime finalization against existing stores, without model calls or data loads.

Run with ``uv run python scripts/verify_runtime_evidence.py``. Only existing service
containers are started; containers already running are preserved. Raw-file evidence runs
in the normal read-only Docker Python sandbox. Results contain no connection credentials.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
import time
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path

from pydantic import ValidationError

from backintel.answer_validation import answer_schema
from backintel.sandbox import PythonSandbox
from backintel.settings import Settings, repo_root
from backintel.stores import open_store

SERVICES = {
    "sqlite": (),
    "postgres": ("backintel-postgres",),
    "clickhouse": ("backintel-clickhouse",),
    "ferretdb": ("backintel-v2-documentdb-1", "backintel-ferretdb"),
    "lake-iceberg": ("backintel-garage",),
    "files": (),
}
COUNT_SQL = "SELECT COUNT(*) AS n FROM orders"
COUNT_QUERY = '{"collection":"orders","pipeline":[{"$count":"n"}]}'
COUNT_PYTHON = """import csv, os
from pathlib import Path
with (Path(os.environ['BACKINTEL_FILES_DIR']) / 'orders.csv').open() as handle:
    print(sum(1 for _ in csv.DictReader(handle)))
"""


def docker(*args: str) -> str:
    return subprocess.run(
        ["docker", *args], check=True, capture_output=True, text=True, timeout=60
    ).stdout.strip()


@contextmanager
def existing_services(names: tuple[str, ...], record: dict):
    """Never create/rebuild a service and always restore services this invocation starts."""
    started = []
    record["started_containers"] = started
    record["stopped_containers"] = []
    try:
        for name in names:
            running = docker("inspect", "-f", "{{.State.Running}}", name) == "true"
            if not running:
                # Record before starting so cleanup covers a successful start with a lost reply.
                started.append(name)
                docker("start", name)
        yield
    finally:
        cleanup_errors = []
        for name in reversed(started):
            try:
                docker("stop", name)
                record["stopped_containers"].append(name)
            except subprocess.SubprocessError as error:
                cleanup_errors.append(type(error).__name__)
        if cleanup_errors:
            raise RuntimeError("Could not restore every started container")


def open_ready(store_id: str, settings: Settings):
    deadline = time.monotonic() + 45
    while True:
        store = None
        try:
            store = open_store(store_id, settings)
            if store.kind != "files":
                store.query(COUNT_QUERY if store.kind == "ferretdb" else COUNT_SQL)
            return store
        except Exception:
            if store is not None:
                store.close()
            if time.monotonic() >= deadline:
                raise
            time.sleep(1)


def verify_case(store, sandbox: PythonSandbox) -> dict:
    if store.kind == "files":
        kind, good = "python", COUNT_PYTHON
        bad = """import os
from pathlib import Path
(Path(os.environ['BACKINTEL_FILES_DIR']) / '__missing_runtime_validation_file__').read_text()
"""
        result = sandbox.run(
            good,
            env=store.python_environment(),
            mounts=store.python_mounts(),
            network=store.sandbox_network(),
        )
        if result.exit_code != 0:
            raise RuntimeError("Docker Python count failed")
        count = int(result.stdout.strip())
    else:
        kind, good = ("query", COUNT_QUERY) if store.kind == "ferretdb" else ("sql", COUNT_SQL)
        bad = (
            '{"collection":"orders","pipeline":[{"$project":{"n":{"$doesNotExist":"$order_id"}}}]}'
            if store.kind == "ferretdb"
            else "SELECT missing_runtime_validation_column FROM orders"
        )
        result = store.query(good)
        count = int(result.rows[0][result.columns.index("n")])
    payload = {
        "status": "answered",
        "answer_type": "number",
        "value": count,
        "unit": "orders",
        "method": "Count the existing loaded orders table without filtering.",
        "evidence": [{"kind": kind, "code": good}],
    }
    schema = answer_schema(store, sandbox)
    schema.model_validate(payload)
    payload["evidence"].append({"kind": kind, "code": bad})
    try:
        schema.model_validate(payload)
    except ValidationError as error:
        # Distinguish an actual second-program rejection from a shape or first-item failure.
        if not any("Evidence 2:" in item["msg"] for item in error.errors()):
            raise RuntimeError("Invalid evidence rejected for the wrong reason") from None
    else:
        raise RuntimeError("Broken second evidence item was accepted")
    return {
        "count": count,
        "evidence_kind": kind,
        "valid_answer_accepted": True,
        "broken_second_evidence_rejected": True,
        "sandbox": sandbox.label if kind == "python" else None,
    }


def main() -> int:
    settings = Settings.from_env()
    sandbox = PythonSandbox("docker", timeout_s=30)
    report = {
        "created_at": datetime.now(UTC).isoformat(),
        "scope": "Runtime evidence execution smoke; not a model quality or full data parity evaluation",
        "dataset": "olist",
        "model_calls": 0,
        "data_reloads": 0,
        "validator_sha256": hashlib.sha256(
            (repo_root() / "src/backintel/answer_validation.py").read_bytes()
        ).hexdigest(),
        "initial_running_containers": sorted(docker("ps", "--format", "{{.Names}}").splitlines()),
        "checks": [],
    }
    for kind, names in SERVICES.items():
        record = {"store": f"{kind}:olist", "passed": False}
        report["checks"].append(record)
        try:
            with existing_services(names, record):
                store = open_ready(record["store"], settings)
                try:
                    if kind == "ferretdb":
                        frozen = docker(
                            "exec",
                            "backintel-v2-documentdb-1",
                            "psql",
                            "-U",
                            "loader",
                            "-d",
                            "postgres",
                            "-tA",
                            "-c",
                            "SHOW default_transaction_read_only",
                        )
                        record["backend_readonly"] = frozen == "on"
                        if not record["backend_readonly"]:
                            raise RuntimeError("FerretDB backend must remain frozen")
                    record.update(verify_case(store, sandbox))
                    record["passed"] = True
                finally:
                    store.close()
        except Exception as error:
            # Backend exceptions can include credentials; report the class, not the raw message.
            record["passed"] = False
            record["error_type"] = type(error).__name__
        print(f"{record['store']}: {'passed' if record['passed'] else 'FAILED'}", flush=True)
    report["final_running_containers"] = sorted(docker("ps", "--format", "{{.Names}}").splitlines())
    report["service_state_preserved"] = (
        report["initial_running_containers"] == report["final_running_containers"]
    )
    report["passed"] = report["service_state_preserved"] and all(row["passed"] for row in report["checks"])
    output = Path("results/runtime-validation-smoke.json")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2) + "\n")
    print(f"Saved {output}", flush=True)
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
