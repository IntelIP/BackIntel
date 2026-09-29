"""Run approved local predictors on synthetic, structured-only histories."""

from __future__ import annotations

import json
import os
from pathlib import Path
import time
import uuid

import psycopg

from runtime.bootstrap import initialize
from runtime.contracts import admit_source, register_task
from runtime.evidence import Evidence
from runtime.ledger import dsn
from runtime.prediction import cases, chronological_split, evaluate, features, outcome, prepare
from runtime.real_models import _allow_model_use
from runtime.simulation import encoded
from runtime.synthetic import history

OUTPUT = Path(__file__).resolve().parents[2] / "artifacts/validation/RealPredictors"


def main() -> int:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    run_id = uuid.uuid4().hex
    receipt = {
        "schema": "backintel-real-predictor-check/v1", "run_id": run_id,
        "status": "running", "candidate": "uncommitted-working-tree",
        "data": "synthetic", "feature_set": "structured", "paid_provider_calls": 0,
        "provider_usd": 0, "local_compute_usd": None, "checks": [],
        "limits": ["Synthetic results do not establish real-world quality.",
                   "Real Jev and four-way comparison remain separate acceptance requirements."],
    }
    path = OUTPUT / (run_id + ".json")
    started = time.perf_counter()
    try:
        test_dsn = os.environ.get("BACKINTEL_TEST_DATABASE_URL")
        if not test_dsn or test_dsn != dsn() or not psycopg.conninfo.conninfo_to_dict(test_dsn)["dbname"].startswith("test_"):
            raise PermissionError("Actual predictor checks require the isolated test database")
        for route in ("catboost", "tabiclv2"):
            _allow_model_use(route)
        initialize()
        with psycopg.connect(dsn(), autocommit=True) as connection:
            for scenario in ("support", "equipment"):
                task, rows, labels = history(scenario)
                task["id"] = scenario + "-real-" + run_id[:12]
                store = Evidence(connection, task["id"])
                task_record = register_task(store, task)
                snapshots = []
                for row, label in zip(rows, labels):
                    at = label["event_at"]
                    admit_source(store, task_record, {"format": "json", "data": [row]}, at)
                    snapshots.extend(r for r in features(store, task_record, at)
                                     if r["body"]["source_id"] == label["source_id"])
                    outcome(store, task_record, label)
                at = max(r["available_at"] for r in labels)
                training, holdout, prepared_at = chronological_split(task, cases(store, task_record, snapshots, at))
                for route in ("catboost", "tabiclv2"):
                    print(json.dumps({"scenario": scenario, "route": route, "state": "preparing",
                                      "training_rows": len(training), "holdout_rows": len(holdout)}), flush=True)
                    model = prepare(store, task_record, training, route, "structured", prepared_at, "real")
                    evaluation = evaluate(store, model, holdout, at)
                    assert model["body"]["implementation_mode"] == "real"
                    assert len(evaluation["body"]["predictions"]) == len(holdout) > 0
                    receipt["checks"].append({"scenario": scenario, "task_id": task["id"],
                                             "route": route, "model": model, "evaluation": evaluation})
                    path.write_bytes(encoded(receipt))
                    print(json.dumps({"scenario": scenario, "route": route, "state": "passed",
                                      "wall_ms": evaluation["body"]["wall_ms"],
                                      "metrics": evaluation["body"]["metrics"]}), flush=True)
        receipt["status"] = "passed"
    except Exception as exc:
        receipt.update(status="blocked" if isinstance(exc, (PermissionError, FileNotFoundError)) else "failed",
                       error={"type": type(exc).__name__, "message": str(exc)})
        raise
    finally:
        receipt["wall_seconds"] = time.perf_counter() - started
        path.write_bytes(encoded(receipt))
        print(json.dumps({"status": receipt["status"], "receipt": str(path)}), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
