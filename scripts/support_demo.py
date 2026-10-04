"""Prepare and display a scoped business demonstration without spending money."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import shutil
import threading

import psycopg
from runtime.business_demo import attach_live_attempt, attach_local_predictions, attach_workflow_rehearsal, dataset, snapshot
from runtime.decision_workspace import DecisionStore, WorkspaceServer
from runtime.evidence import Evidence
from runtime.evidence import digest
from runtime.prediction import cases, chronological_split, evaluate, features, predict, prepare as prepare_model
from runtime.real_pipeline import prepare_history, prepare_followups
from scripts.capability_demo import DEMO_DSN, ROOT


def prepare(demo_id):
    """Freeze inputs through the same admission functions as the native workflow."""
    with psycopg.connect(DEMO_DSN, autocommit=True) as connection:
        for scenario in ("support", "equipment"):
            store = Evidence(connection, f"{scenario}-real-{demo_id}")
            data, events = dataset(scenario)
            plan = prepare_history(store, scenario, history_data=data)
            prepare_followups(store, plan, event_data=events)


def capture(demo_id):
    with psycopg.connect(DEMO_DSN, autocommit=True) as connection:
        store = Evidence(connection, f"support-real-{demo_id}")
        jobs = [{"state": state, "operation": payload["operation"]} for state, payload in connection.execute(
            "SELECT state,payload FROM backintel.capability_jobs WHERE task_id=%s", (store.task_id,)).fetchall()]
        requests = [{"state": state, "metadata": metadata or {}} for state, metadata in connection.execute(
            "SELECT state,metadata FROM backintel.capability_model_requests WHERE task_id=%s", (store.task_id,)).fetchall()]
        triggers = [{"state": state} for state, in connection.execute(
            "SELECT state FROM backintel.capability_triggers WHERE task_id=%s", (store.task_id,)).fetchall()]
        packet = snapshot(store, jobs, requests, triggers)
        packet["demo"]["captured_at"] = datetime.now(timezone.utc).isoformat()
        packet["demo"]["demo_id"] = demo_id
        local_path = ROOT / "artifacts/validation/BusinessDemo" / demo_id / "LocalPredictions.json"
        if local_path.is_file():
            attach_local_predictions(packet, json.loads(local_path.read_text()), demo_id)
        workflow_path = local_path.with_name("WorkflowRehearsal.json")
    if workflow_path.is_file():
        attach_workflow_rehearsal(packet, json.loads(workflow_path.read_text()), demo_id)
    live_path = local_path.with_name("LiveJevAttempt.json")
    if live_path.is_file():
        attach_live_attempt(packet, json.loads(live_path.read_text()), demo_id)
    return packet

def record_workflow_rehearsal(demo_id, source, output):
    report = {"schema": "backintel-workflow-rehearsal/v1", "demo_id": demo_id,
              "source_directory": str(source.resolve()),
              "submission": json.loads((source / "Submission.json").read_text()),
              "integration": json.loads((source / "Integration.json").read_text())}
    attach_workflow_rehearsal({"demo": {}}, report, demo_id)
    output.mkdir(parents=True, exist_ok=True)
    path = output / "WorkflowRehearsal.json"
    path.write_text(json.dumps(report, indent=2) + "\n")
    return path

def local_predictions(demo_id, output):
    """Run approved predictors on synthetic facts; never extract Jev observations."""
    with psycopg.connect(DEMO_DSN, autocommit=True) as connection:
        store = Evidence(connection, f"support-local-{demo_id}")
        data, _ = dataset("support")
        plan = prepare_history(store, "support", history_data=data)
        task = store.get(plan["body"]["task"])
        at = plan["body"]["at"]
        snapshots = []
        for source_sha in plan["body"]["sources"]:
            source = store.get(source_sha)
            snapshots.extend(record for record in features(store, task, source["body"]["event_at"])
                             if record["body"]["source"] == source_sha)
        training, holdout, prepared_at = chronological_split(task["body"], cases(store, task, snapshots, at))
        current = features(store, task, at)
        methods = []
        for route in ("baseline", "catboost", "tabiclv2"):
            model = prepare_model(store, task, training, route, "structured", prepared_at,
                                  implementation_mode="real")
            evaluation = evaluate(store, model, holdout, at)
            methods.append({
                "route": route, "feature_set": "structured",
                "execution": "computed_baseline" if route == "baseline" else "actual_local_model",
                "model_sha256": model["sha256"], "evaluation_sha256": evaluation["sha256"],
                "metrics": evaluation["body"]["metrics"],
                "preparation_wall_ms": model["body"]["wall_ms"],
                "estimates": [{"entity": record["body"]["entity"],
                               "source_sha256": record["body"]["source"],
                               "feature_sha256": record["sha256"],
                               "cutoff": record["body"]["cutoff"],
                               "target_at": record["body"]["target_at"],
                               "value": predict(model, record)} for record in current],
            })
        requests = connection.execute(
            "SELECT count(*) FROM backintel.capability_model_requests WHERE task_id=%s",
            (store.task_id,)).fetchone()[0]
        if requests or store.list("observation"):
            raise ValueError("Facts-only rehearsal scope must contain no Jev requests or observations")
        report = {
            "schema": "backintel-local-prediction-rehearsal/v1", "demo_id": demo_id,
            "status": "completed", "task_id": store.task_id, "source_mode": "synthetic",
            "dataset_sha256": digest(data), "task_sha256": task["sha256"],
            "feature_set": "structured", "target": task["body"]["target"],
            "train_count": len(training), "holdout_count": len(holdout), "prepared_at": prepared_at,
            "training_features": [record["feature"]["sha256"] for record in training],
            "holdout_features": [record["feature"]["sha256"] for record in holdout],
            "methods": methods, "selected_route": min(methods, key=lambda method: method["metrics"]["brier"])["route"],
            "selection_rule": "Lowest probability error on the shared chronological holdout; baseline wins ties.",
            "provider_calls": requests, "provider_usd": 0, "compute_usd": None,
            "scope_boundary": "Actual local predictions on synthetic measured fields. Jev interpretation and Jev-enhanced predictions have not run. This is separate from the autonomous provider journey.",
        }
    write_packet(output / "LocalPredictions.json", report)
    return report


def write_packet(path, packet):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(packet, ensure_ascii=False, indent=2, allow_nan=False) + "\n")
    temporary.replace(path)


def prepare_frontends(output):
    """Copy only the Python presentation into its owned recording directory."""
    owned = output / "ReflexApp"
    owned.mkdir(parents=True, exist_ok=True)
    for name in ("reflex_demo", "assets"):
        source = ROOT / "reflex_demo" / name
        if name == 'assets' and not source.exists():
            (owned / name).mkdir(exist_ok=True)
        else:
            shutil.copytree(source, owned / name, dirs_exist_ok=True, ignore=shutil.ignore_patterns("__pycache__"))
    css = (ROOT / "frontend/src/styles.css").read_text()
    asset = owned / "assets/workspace.css"
    prior = asset.read_text() if asset.exists() else css
    asset.write_text(prior.split(".demo-content", 1)[0] + css[css.index(".demo-content"):])
    (owned / "rxconfig.py").write_text('import reflex as rx\nconfig = rx.Config(app_name="reflex_demo", frontend_port=3002, backend_port=3002, api_url="http://127.0.0.1:3002", backend_host="127.0.0.1", show_built_with_reflex=False)\n')
    return owned


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--demo-id", default="business-v1")
    parser.add_argument("--prepare", action="store_true")
    parser.add_argument("--local-predictions", action="store_true", help="Run approved local models on synthetic measured fields only")
    parser.add_argument("--prepare-frontends", action="store_true")
    parser.add_argument("--workflow-rehearsal", type=Path, help="Attach a separate simulated native workflow evidence directory")
    parser.add_argument("--serve", action="store_true")
    parser.add_argument("--port", type=int, default=2043)
    args = parser.parse_args()
    if not re.fullmatch(r"[a-z][a-z0-9-]{0,24}", args.demo_id):
        parser.error("Use a bounded demonstration identity")
    if args.prepare:
        prepare(args.demo_id)
    output = ROOT / "artifacts/validation/BusinessDemo" / args.demo_id
    if args.workflow_rehearsal:
        path = record_workflow_rehearsal(args.demo_id, args.workflow_rehearsal, output)
        print(json.dumps({"workflow_rehearsal": str(path), "mode": "simulated intelligence; native scheduled worker"}), flush=True)
    if args.local_predictions:
        report = local_predictions(args.demo_id, output)
        print(json.dumps({"local_predictions": str(output / "LocalPredictions.json"),
                          "selected_route": report["selected_route"], "provider_calls": report["provider_calls"]}))
    if args.prepare_frontends:
        prepare_frontends(output)
    packet_path = output / "Workspace.json"
    packet = capture(args.demo_id)
    write_packet(packet_path, packet)
    print(json.dumps({"packet": str(packet_path), "status": packet["demo"]["status"], "provider_calls": packet["demo"]["actual_provider_calls"]}), flush=True)
    if not args.serve:
        return
    store = DecisionStore(output / "Reviews.sqlite3", packet["cases"], packet_path)
    server = WorkspaceServer(store, "synthetic-business-demonstration", port=args.port,
                             additional_origins={"http://127.0.0.1:5174", "http://localhost:5174", "http://127.0.0.1:3002", "http://localhost:3002"})
    stop = threading.Event()

    def watch():
        while not stop.wait(1):
            try:
                write_packet(packet_path, capture(args.demo_id))
            except (psycopg.Error, ValueError, OSError, KeyError) as error:
                # A stale packet cannot become a live-progress claim.
                current = json.loads(packet_path.read_text())
                current["demo"]["status"] = "unavailable"
                current["demo"]["error"] = f"Could not refresh scoped evidence ({type(error).__name__})."
                write_packet(packet_path, current)

    watcher = threading.Thread(target=watch, daemon=True)
    watcher.start()
    print(f"Business demo API: http://127.0.0.1:{server.server_port}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        stop.set()
        server.server_close()
        watcher.join(timeout=5)


if __name__ == "__main__":
    main()
