"""One reusable synthetic pipeline for service operations and equipment monitoring."""
from __future__ import annotations

import time

from runtime.attention import attend, latest_episode
from runtime.artifacts import create_artifacts
from runtime.contracts import admit_source, current_sources, register_task
from runtime.jobs import schedule
from runtime.observations import extract
from runtime.prediction import (cases, compare, evaluate, features, invalidate_predictions, outcome,
                                prepare, registry, score, transition, update_plan)
from runtime.simulation import digest, load_scenario
from runtime.synthetic import history


def bootstrap(store, task_record: dict, name: str) -> dict:
    _, rows, labels = history(name)
    snapshots = []
    for row,label in zip(rows,labels):
        at = label["event_at"]
        admit_source(store,task_record,{"format":"json","data":[row]},at)
        source = next(r for r in current_sources(store,at,task_record["sha256"]) if r["body"]["id"] == label["source_id"])
        extract(store,task_record,source,at)
        snapshots.extend(r for r in features(store,task_record,at) if r["body"]["source_id"] == label["source_id"])
        outcome(store,task_record,label)
    comparison = compare(store,task_record,snapshots,71)
    selected = comparison["body"]["selected"]
    transition(store,task_record,selected,"approve",71,"initial-approval")
    transition(store,task_record,selected,"activate",71,"initial-activation")
    event = store.put("event","bootstrap",{"operation":"bootstrap","scenario":name},71,[comparison["sha256"]])
    result = refresh(store,task_record,event,71,observe=True)
    seed_followups(store,task_record,name)
    return result


def followup_events(name: str) -> list:
    task, rows, labels = history(name,31)
    changed = dict(rows[24],revision=2,arrived_at=75)
    changed[task["fields"]["content"]] = "Login failed" if task["questions"][0]["type"] == "boolean" else "9"
    recovered = dict(rows[30])
    recovered[task["fields"]["content"]] = "Service working" if task["questions"][0]["type"] == "boolean" else "0"
    entity = rows[24][task["fields"]["entity"]]
    return [
        (2,"event",{"operation":"arrival","at":72,"row":rows[24],"fail_once":True}),
        (4,"event",{"operation":"outcome","at":74,"label":labels[24]}),
        (6,"event",{"operation":"arrival","at":75,"row":changed}),
        (8,"deadline",{"operation":"deadline","at":76}),
        (10,"on_demand",{"operation":"acknowledge","at":77,"entity":entity}),
        (12,"on_demand",{"operation":"investigate","at":78,"entity":entity}),
        (14,"staleness",{"operation":"staleness","at":84}),
        (16,"schedule",{"operation":"model_update_prepare","at":85}),
        (18,"on_demand",{"operation":"resolve","at":86,"entity":entity}),
        (20,"event",{"operation":"arrival","at":90,"row":recovered}),
        (22,"event",{"operation":"outcome","at":92,"label":labels[30]}),
        (24,"schedule",{"operation":"model_update_complete","at":93}),
        (26,"schedule",{"operation":"artifact_refresh","at":94}),
    ]

def seed_followups(store, task_record: dict, name: str) -> None:
    now = time.time()
    for offset,kind,payload in followup_events(name):
        schedule(store,kind,{**payload,"scenario":name},now+offset,f"demo-{payload['operation']}-{payload['at']}")


def analyze(store, task_record, snapshots, predictions, event, at):
    if len(snapshots) != len(predictions) or any(p["body"]["feature"] != f["sha256"] for f, p in zip(snapshots, predictions)):
        raise ValueError("Analysis requires one matching prediction for each feature snapshot")
    policy = task_record["body"]["policy"]
    rows = []
    for feature, prediction in zip(snapshots, predictions):
        semantic = feature["body"]["values"].get("semantic:" + policy["signal_question"])
        semantic_risk = min(1, max(0, semantic / policy["signal_scale"])) if semantic is not None else None
        prediction_risk = min(1, max(0, prediction["body"]["value"] / policy["prediction_scale"])) if "prediction_scale" in policy else None
        # Fictional policy for synthetic demonstrations. Missing interpretation stays unknown.
        attention_value = max(semantic_risk, prediction_risk or 0) if semantic_risk is not None else None
        rows.append({"entity": feature["body"]["entity"], "feature": feature["sha256"], "prediction": prediction["sha256"],
                     "semantic_risk": semantic_risk, "prediction_risk": prediction_risk, "attention_value": attention_value})
    body = {"task": task_record["sha256"], "event": event["sha256"], "at": at, "rows": rows,
            "policy_sha256": digest(policy), "rule": "maximum_known_interpretation_and_scaled_forecast_else_unknown",
            "synthetic_policy": True, "prediction_scale": policy.get("prediction_scale")}
    return store.put("analysis", digest(body), body, at, [task_record["sha256"], event["sha256"], *[r["sha256"] for r in snapshots + predictions]])


def refresh(store, task_record: dict, event: dict, at: int, observe=False, entities=None) -> dict:
    snapshots = features(store,task_record,at)
    active = registry(store,at)["active"]
    predictions = [score(store,task_record,f,at) for f in snapshots]
    analysis = analyze(store, task_record, snapshots, predictions, event, at)
    episodes = []
    for feature, finding in zip(snapshots, analysis["body"]["rows"]):
        entity = feature["body"]["entity"]
        if observe and (entities is None or entity in entities):
            episodes.append(attend(store,task_record,entity,analysis,at,finding["attention_value"]))
        else:
            latest = latest_episode(store,entity,task_record['sha256'])
            if latest:
                episodes.append(latest)
    real = task_record["body"]["observation_provider"]["implementation_mode"] == "real"
    from runtime.real_semantics import usage_for
    usage = usage_for(store) if real else {"provider_calls":0,"provider_usd":0,"local_compute_usd":None}
    mode = "synthetic_sources_real_models" if real else "synthetic_simulation"
    if usage.get("provider_fixture_requests"):
        mode = "synthetic_sources_real_predictors_fixture_semantics"
    body = {"task":task_record["sha256"],"event":event["sha256"],"analysis":analysis["sha256"],"at":at,"model":active,
            "features":[r["sha256"] for r in snapshots],"predictions":[r["sha256"] for r in predictions],
            "episodes":[r["sha256"] for r in episodes],"mode":mode,
            **usage}
    result = store.put("result",digest(body),body,at,[task_record["sha256"],event["sha256"],analysis["sha256"],*[r["sha256"] for r in snapshots+predictions+episodes]])
    create_artifacts(store, task_record, result)
    return result


def handle(store, payload: dict, task_record=None) -> dict:
    name, operation = payload["scenario"], payload["operation"]
    if operation.startswith("real_"):
        from runtime.real_pipeline import handle as handle_real
        return handle_real(store, payload)
    if task_record is None:
        task = load_scenario(name)["task"]
        task["id"] = store.task_id
        task_record = register_task(store,task)
    if operation == "bootstrap":
        return bootstrap(store,task_record,name)
    at = payload["at"]
    event = store.put("event",digest(payload),payload,at,[task_record["sha256"]])
    if operation == "arrival":
        row = payload["row"]
        old = next((r for r in current_sources(store,at,task_record["sha256"])
                    if r["body"]["id"] == row[task_record["body"]["fields"]["id"]]),None)
        receipt = admit_source(store,task_record,{"format":"json","data":[row]},at)
        dispositions = receipt["body"]["dispositions"]
        if any(r["status"] == "quarantined" for r in dispositions):
            return receipt
        source = store.get(dispositions[0]["source"])
        extract(store,task_record,source,at)
        if old and old["sha256"] != source["sha256"]:
            invalidate_predictions(store,old["sha256"],receipt,at)
        result = refresh(store,task_record,event,at,observe=True,entities=[source["body"]["entity"]])
        update_plan(store,store.get(result["body"]["model"]),[store.get(s) for s in result["body"]["features"]],receipt,at)
        return result
    if operation == "outcome":
        return outcome(store,task_record,payload["label"])
    if operation in ("acknowledge","investigate","resolve","deadline","staleness"):
        entities = [payload["entity"]] if "entity" in payload else sorted({r["body"]["entity"] for r in store.list("episode")})
        for entity in entities:
            attend(store,task_record,entity,event,at,action=operation)
        return refresh(store,task_record,event,at)
    if operation == "model_update_prepare":
        active = store.get(registry(store,at)["active"])
        fresh = features(store,task_record,at)
        update_plan(store,active,fresh,event,at,prepare_requested=True)
        training = cases(store,task_record,store.list("feature",at),at)
        current = {r["sha256"] for r in current_sources(store,at,task_record["sha256"])}
        training = [r for r in training if r["feature"]["body"]["cutoff"] < at and r["feature"]["body"]["source"] in current]
        mode = "real" if task_record["body"]["observation_provider"]["implementation_mode"] == "real" else "simulated"
        prepared = prepare(store,task_record,training,active["body"]["route"],active["body"]["feature_set"],at,implementation_mode=mode)
        return store.put("model_update","bounded-update",{"model":prepared["sha256"]},at,[event["sha256"],prepared["sha256"]])
    if operation == "model_update_complete":
        model = store.get(store.find("model_update","bounded-update")["body"]["model"])
        holdout = [r for r in cases(store,task_record,store.list("feature",at),at)
                   if r["feature"]["body"]["cutoff"] >= model["body"]["prepared_at"]]
        evaluate(store,model,holdout,at)
        transition(store,task_record,model["sha256"],"approve",at,"update-approval")
        transition(store,task_record,model["sha256"],"activate",at,"update-activation")
        return refresh(store,task_record,event,at,observe=True)
    if operation == "artifact_refresh":
        return refresh(store,task_record,event,at)
    raise ValueError("Unsupported capability operation")
