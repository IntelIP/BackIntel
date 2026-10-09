"""Restore actual predictor packages and checkpoints, then reproduce recorded predictions."""

from __future__ import annotations

import argparse
from contextlib import contextmanager
import json
import math
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import uuid

import psycopg
from psycopg import sql

from runtime.evidence import Evidence
from runtime.ledger import dsn
from runtime.jobs import execute
from runtime.real_models import _load, checkpoint, file_sha, model_root, predict_real
from runtime.simulation import digest, encoded
from scripts.capability_demo import domain_snapshot


@contextmanager
def restored_database(source_dsn, task_ids, output, receipt, enabled):
    if not enabled:
        yield source_dsn
        return
    config = psycopg.conninfo.conninfo_to_dict(source_dsn)
    servers = {
        ("55436", "capability_test"): "backintel-capability-test",
        ("55437", "capability_demo"): "backintel-capability-demo-postgres-1",
    }
    container = servers.get((config.get("port"), config.get("user")))
    if config.get("host") != "127.0.0.1" or not container:
        raise PermissionError("Combined recovery requires a known isolated local database")

    def snapshot(connection):
        rows = {}
        for table in ("capability_evidence", "capability_jobs", "capability_triggers", "capability_model_requests"):
            rows[table] = [r[0] for r in connection.execute(sql.SQL(
                "SELECT to_jsonb(r) FROM backintel.{} r WHERE task_id=ANY(%s) ORDER BY to_jsonb(r)::text"
            ).format(sql.Identifier(table)), (task_ids,))]
        return digest(rows)

    target = "test_model_restore_" + uuid.uuid4().hex[:12]
    clone_dsn = f"postgresql://capability_test@127.0.0.1:55436/{target}"
    created = False
    environment = {name: os.environ.get(name) for name in ("BACKINTEL_APP_DATABASE_URL", "BACKINTEL_TEST_DATABASE_URL")}
    try:
        with psycopg.connect(source_dsn) as source:
            pending = source.execute("""SELECT
                (SELECT count(*) FROM backintel.capability_jobs WHERE task_id=ANY(%s) AND state!='completed') +
                (SELECT count(*) FROM backintel.capability_triggers WHERE task_id=ANY(%s) AND state='pending')""",
                (task_ids, task_ids)).fetchone()[0]
            if pending:
                raise RuntimeError("Combined recovery requires completed, quiescent task streams")
            before = snapshot(source)
            backup = output / "Database.dump"
            with backup.open("wb") as data, (output / "DatabaseBackup.log").open("w") as log:
                subprocess.run(["docker", "exec", container, "pg_dump", "-U", config["user"], "-d", config["dbname"],
                                "--format=custom", "--no-owner", "--no-privileges"],
                               stdout=data, stderr=log, check=True, timeout=60)
            if snapshot(source) != before:
                raise RuntimeError("Source changed during backup; retry from a quiescent stream")
        receipt["database_backup"] = {"file": str(backup), "bytes": backup.stat().st_size, "sha256": file_sha(backup)}
        with psycopg.connect("postgresql://capability_test@127.0.0.1:55436/postgres", autocommit=True) as admin:
            admin.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(target)))
            created = True
        with backup.open("rb") as data, (output / "DatabaseRestore.log").open("w") as log:
            subprocess.run(["docker", "exec", "-i", "backintel-capability-test", "pg_restore", "-U", "capability_test",
                            "-d", target, "--no-owner", "--no-privileges", "--exit-on-error"],
                           stdin=data, stdout=log, stderr=subprocess.STDOUT, check=True, timeout=60)
        with psycopg.connect(clone_dsn, autocommit=True) as clone:
            if snapshot(clone) != before:
                raise AssertionError("Restored evidence, jobs, triggers or provider ledger differ")
            os.environ.update(BACKINTEL_APP_DATABASE_URL=clone_dsn, BACKINTEL_TEST_DATABASE_URL=clone_dsn)
            yield clone_dsn
            completed = domain_snapshot(clone, task_ids)["jobs"]
            for row in completed:
                result = execute(row[0])
                if not result.get("reused") or result["state"] != "completed":
                    raise AssertionError("Restored completed job did not replay safely")
            if snapshot(clone) != before:
                raise AssertionError("Restored scoring or replay changed accepted state or provider requests")
            receipt["combined_database_recovery"] = {"status": "passed", "source_and_restored_sha256": before,
                "replayed_jobs": len(completed), "provider_requests_unchanged": True}
    finally:
        for name, value in environment.items():
            if value is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = value
        if created:
            with psycopg.connect("postgresql://capability_test@127.0.0.1:55436/postgres", autocommit=True) as admin:
                admin.execute(sql.SQL("DROP DATABASE {} WITH (FORCE)").format(sql.Identifier(target)))
            receipt["temporary_database_removed"] = True


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--predictor-receipt", type=Path, required=True)
    parser.add_argument("--restore-database", action="store_true", help="Restore the isolated database and model files together")
    parser.add_argument("--predictor-image", help="Use the existing pinned Linux image that prepared the models")
    args = parser.parse_args()
    prior = json.loads(args.predictor_receipt.read_text())
    if prior["status"] != "passed" or prior["data"] != "synthetic":
        raise PermissionError("Recovery requires a passed synthetic predictor receipt")
    test_dsn = os.environ.get("BACKINTEL_TEST_DATABASE_URL")
    if not test_dsn or test_dsn != dsn() or not psycopg.conninfo.conninfo_to_dict(test_dsn)["dbname"].startswith("test_"):
        raise PermissionError("Recovery requires the explicitly isolated test database")
    output = Path(__file__).resolve().parents[2] / "artifacts/validation/RealModelRecovery" / ("Attempt"+uuid.uuid4().hex[:12])
    backup = output / "BackupModels"
    output.mkdir(parents=True)
    receipt = {"schema":"backintel-real-model-restore/v1", "status":"running", "candidate":"uncommitted-working-tree",
               "paid_provider_calls":0, "provider_usd":0, "local_compute_usd":None, "checks":[],
               "limits":["Model files and checkpoints restored; this check uses the existing isolated evidence database.",
                         "Real Jev and the complete combined database/model recovery remain separate acceptance."]}
    if args.restore_database:
        receipt["limits"] = ["Synthetic evidence only; actual Jev, live scheduler/broker restore and exact-commit acceptance remain separate."]
    receipt["semantic_provider"] = prior.get("semantic_provider", "structured-only predictor check")
    original = model_root()
    try:
        task_ids = sorted({check["task_id"] for check in prior["checks"]})
        if not task_ids:
            raise ValueError("Recovery requires at least one recorded predictor")
        if args.predictor_image:
            if not args.restore_database or not args.predictor_image.startswith("sha256:"):
                raise ValueError("A pinned predictor image requires combined database recovery")
            root = Path(__file__).resolve().parents[2]
            inputs = output / "Predictors.json"
            inputs.write_bytes(encoded(prior))
            with restored_database(test_dsn, task_ids, output, receipt, True) as restore_dsn:
                container_dsn = restore_dsn.replace("127.0.0.1", "host.docker.internal")
                command = ["docker", "run", "--rm", "--cpus", "2", "--entrypoint", "python",
                    "-v", f"{root / 'artifacts'}:/app/artifacts", "-v", f"{original}:/models:ro",
                    "-e", f"BACKINTEL_APP_DATABASE_URL={container_dsn}", "-e", f"BACKINTEL_TEST_DATABASE_URL={container_dsn}",
                    "-e", "BACKINTEL_MODEL_DIR=/models", "-e", "OMP_NUM_THREADS=2", "-e", "OPENBLAS_NUM_THREADS=2",
                    "-e", "MKL_NUM_THREADS=2", "-e", "HF_HUB_OFFLINE=1", args.predictor_image,
                    "-m", "scripts.validation.check_real_model_restore", "--predictor-receipt",
                    str(Path('/app') / inputs.relative_to(root))]
                with (output / "PredictorRestore.log").open("w+") as log:
                    subprocess.run(command, stdout=log, stderr=subprocess.STDOUT, check=True, timeout=600)
                    log.seek(0)
                    result = json.loads(log.read().strip().splitlines()[-1])
                model_receipt = root / Path(result["receipt"]).relative_to("/app")
                recovered = json.loads(model_receipt.read_text())
                if recovered["status"] != "passed" or not recovered.get("temporary_restore_removed"):
                    raise AssertionError("Container model recovery did not complete and clean up")
                receipt.update(checks=recovered["checks"], model_recovery_receipt=str(model_receipt),
                               predictor_image=args.predictor_image, temporary_restore_removed=True)
            receipt["status"] = "passed"
            return 0
        backup.mkdir()
        relative = {Path("model-use-approval.json")}
        for check in prior["checks"]:
            body = check["model"]["body"]
            relative.update((Path(body["artifact"]["package"])/body["artifact"]["file"],
                             Path(body["artifact"]["package"])/"manifest.json"))
            if body["checkpoint"]:
                path, spec = checkpoint(body["target"]["kind"])
                if spec != body["checkpoint"]:
                    raise ValueError("Predictor receipt has a different checkpoint identity")
                relative.add(path.relative_to(original))
        identities = {}
        for path in sorted(relative):
            source = original / path
            if not source.resolve().is_relative_to(original):
                raise ValueError("Model receipt references an out-of-scope file")
            target = backup / path
            target.parent.mkdir(parents=True,exist_ok=True)
            shutil.copyfile(source,target)
            identities[str(path)] = {"sha256":file_sha(target),"bytes":target.stat().st_size}
        receipt["backup_files"] = identities
        with restored_database(test_dsn, task_ids, output, receipt, args.restore_database) as restore_dsn, \
                tempfile.TemporaryDirectory(prefix="BackIntelModelRestore") as directory:
            restored = Path(directory)/"Models"
            shutil.copytree(backup,restored)
            for path, identity in identities.items():
                if file_sha(restored/path) != identity["sha256"]:
                    raise AssertionError("Restored model bytes differ")
            os.environ["BACKINTEL_MODEL_DIR"] = str(restored)
            _load.cache_clear()
            with psycopg.connect(restore_dsn) as connection:
                for check in prior["checks"]:
                    store = Evidence(connection,check["task_id"])
                    model = store.get(check["model"]["sha256"])
                    verified = 0
                    evaluation = store.get(check["evaluation"]["sha256"])["body"]
                    for case, expected in zip(evaluation["cases"],evaluation["predictions"],strict=True):
                        feature = store.get(case[0])
                        value = predict_real(model,feature)
                        if not math.isclose(value,expected,rel_tol=1e-6,abs_tol=1e-7):
                            raise AssertionError("Restored model prediction differs")
                        verified += 1
                    if not verified:
                        raise AssertionError("Recovery receipt has no predictions")
                    receipt["checks"].append({"scenario":check["scenario"],"route":check["route"],
                                              "model":model["sha256"],"predictions_reproduced":verified})
            _load.cache_clear()
        receipt.update(status="passed",temporary_restore_removed=not Path(directory).exists())
    except Exception as exc:
        receipt.update(status="failed",error={"type":type(exc).__name__,"message":str(exc)})
        raise
    finally:
        _load.cache_clear()
        os.environ["BACKINTEL_MODEL_DIR"] = str(original)
        path = output/"Restore.json"
        path.write_bytes(encoded(receipt))
        print(json.dumps({"status":receipt["status"],"receipt":str(path)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
