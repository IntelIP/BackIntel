"""Time-safe features, evaluation and explicitly real or simulated predictors.

Real routes load the approved CatBoost/TabICLv2 adapters. Simulated routes remain
development fixtures and cannot satisfy real-model acceptance.
"""
from __future__ import annotations

import math
import statistics
import time
from pathlib import Path

from runtime.contracts import current_sources, number
from runtime.observations import effective_observation
from runtime.simulation import digest, encoded

ROUTES = (("baseline", "structured"), ("catboost", "structured"),
          ("catboost", "semantic"), ("tabiclv2", "structured"), ("tabiclv2", "semantic"))


def features(store, task_record: dict, cutoff: int) -> list[dict]:
    """Latest entity-grain facts/observations actually available at this cutoff."""
    task = task_record["body"]
    latest, grains = {}, set()
    for source in current_sources(store, cutoff, task_record["sha256"]):
        row = source["body"]
        grain = (row["entity"], row["event_at"])
        if grain in grains:
            raise ValueError("Multiple source identities at the same entity/event grain")
        grains.add(grain)
        latest[row["entity"]] = source
    available = store.list("observation", cutoff)
    result = []
    for entity, source in sorted(latest.items()):
        values = {"structured:" + key: value for key, value in source["body"]["measures"].items()}
        parents = [task_record["sha256"], source["sha256"]]
        for question in task["questions"]:
            matches = [r for r in available if r["body"]["source"] == source["sha256"]
                       and r["body"]["question_id"] == question["id"] and r["body"]["task"] == task_record["sha256"]]
            if len(matches) > 1:
                raise ValueError("Ambiguous observation provider; choose one task version/provider")
            observation = effective_observation(store, matches[0]["sha256"], cutoff) if matches else None
            value = observation["body"]["response"]["value"] if observation else None
            values["semantic:" + question["id"]] = int(value) if type(value) is bool else value
            if observation:
                parents.append(observation["sha256"])
        body = {"task": task_record["sha256"], "entity": entity, "source_id": source["body"]["id"],
                "source": source["sha256"], "event_at": source["body"]["event_at"], "cutoff": cutoff,
                "target_at": cutoff + task["target"]["horizon"], "values": values,
                "nulls": [key for key, value in values.items() if value is None]}
        result.append(store.put("feature", digest(body), body, cutoff, parents))
    return result


def outcome(store, task_record: dict, label: dict) -> dict:
    if set(label) != {"source_id", "entity", "event_at", "available_at", "revision", "value"}:
        raise ValueError("Invalid observed outcome contract")
    task = task_record["body"]
    if any(type(label[k]) is not int or label[k] < 0 for k in ("event_at", "available_at", "revision")) or label["revision"] < 1:
        raise ValueError("Invalid outcome revision/time")
    if any(not isinstance(label[k], str) or not label[k] for k in ("source_id", "entity")):
        raise ValueError("Outcome requires entity/source identity")
    if label["available_at"] < label["event_at"] + task["target"]["horizon"]:
        raise ValueError("Outcome cannot be available before target horizon")
    if not number(label["value"]) or (task["target"]["kind"] == "classification" and label["value"] not in (0, 1)):
        raise ValueError("Outcome violates target contract")
    body = {**label, "task": task_record["sha256"], "target": task["target"]["id"]}
    identity = digest([task_record["sha256"], label["source_id"], label["event_at"], label["revision"]])
    with store.connection.transaction():
        store.lock()
        history = [r for r in store.list("outcome") if r["body"]["source_id"] == label["source_id"]
                   and r["body"]["task"] == task_record["sha256"] and r["body"]["event_at"] == label["event_at"]]
        if any(r["body"]["entity"] != label["entity"] for r in history):
            raise ValueError("Outcome revision cannot change entity")
        previous = store.find("outcome", identity)
        if previous:
            if previous["body"] != body:
                raise ValueError("Conflicting outcome revision")
            return previous
        return store.put("outcome", identity, body, label["available_at"], [task_record["sha256"]] + [r["sha256"] for r in history])


def cases(store, task_record: dict, snapshots: list[dict], cutoff: int) -> list[dict]:
    labels = {}
    for label in store.list("outcome", cutoff):
        row = label["body"]
        if row["task"] != task_record["sha256"]:
            continue
        key = (row["source_id"], row["entity"], row["event_at"])
        if key not in labels or row["revision"] > labels[key]["body"]["revision"]:
            labels[key] = label
    result, seen = [], set()
    for feature in sorted(snapshots, key=lambda r: (r["body"]["cutoff"], r["body"]["entity"])):
        row = feature["body"]
        if row["task"] != task_record["sha256"] or feature["available_at"] > cutoff:
            raise ValueError("Incompatible or future feature snapshot")
        grain = (row["entity"], row["cutoff"])
        if grain in seen:
            raise ValueError("Duplicate feature grain in evaluation cases")
        seen.add(grain)
        # A stale source carried into a later snapshot has no matching future label.
        label = labels.get((row["source_id"], row["entity"], row["cutoff"]))
        if label and label["available_at"] >= row["target_at"]:
            result.append({"feature": feature, "outcome": label})
    return result


def chronological_split(task: dict, records: list[dict]) -> tuple[list[dict], list[dict], int]:
    times = sorted({r["feature"]["body"]["cutoff"] for r in records})
    if len(times) < 2:
        raise ValueError("Insufficient chronological cases")
    split = max(1, min(len(times) - 1, int(len(times) * (1 - task["target"]["holdout_fraction"]))))
    prepared_at = times[split]
    training = [r for r in records if r["feature"]["body"]["cutoff"] < prepared_at and r["outcome"]["available_at"] <= prepared_at]
    holdout = [r for r in records if r["feature"]["body"]["cutoff"] >= prepared_at]
    if len(training) < task["target"]["minimum_train"] or not holdout:
        raise ValueError("Insufficient eligible train/context or holdout cases")
    return training, holdout, prepared_at


def validate_case(record: dict) -> None:
    feature, label = record["feature"], record["outcome"]
    f, y = feature["body"], label["body"]
    if (f["task"], f["source_id"], f["entity"], f["cutoff"]) != (y["task"], y["source_id"], y["entity"], y["event_at"]) or label["available_at"] < f["target_at"]:
        raise ValueError("Outcome does not match feature grain/horizon")


def prepare(store, task_record: dict, training: list[dict], route: str, feature_set: str, at: int, implementation_mode="simulated") -> dict:
    if (route, feature_set) not in ROUTES:
        raise ValueError("Unsupported predictor route")
    if len(training) < task_record["body"]["target"]["minimum_train"]:
        raise ValueError("Insufficient preparation cases")
    for record in training:
        validate_case(record)
        f, label = record["feature"], record["outcome"]
        if f["body"]["task"] != task_record["sha256"] or label["body"]["task"] != task_record["sha256"]:
            raise ValueError("Incompatible preparation contract")
        if f["body"]["cutoff"] >= at or label["available_at"] > at:
            raise ValueError("Future feature or unavailable label in preparation")
    if implementation_mode not in ("simulated","real"):
        raise ValueError("Predictor execution mode must be explicit")
    if implementation_mode == "real" and route != "baseline":
        from runtime.real_models import prepare_real
        return prepare_real(store,task_record,training,route,feature_set,at)
    columns = sorted(k for k in training[0]["feature"]["body"]["values"] if feature_set == "semantic" or k.startswith("structured:"))
    key = digest({"task": task_record["sha256"], "training": [[r["feature"]["sha256"], r["outcome"]["sha256"]] for r in training],
                  "route": route, "feature_set": feature_set, "at": at, "adapter_version": "1"})
    with store.connection.transaction():
        store.lock()
        existing = store.find("model", key)
        if existing:
            return existing
        started = time.perf_counter()
        scales = {}
        for column in columns:
            values = [r["feature"]["body"]["values"][column] for r in training if r["feature"]["body"]["values"][column] is not None]
            scales[column] = {"mean": statistics.mean(values) if values else 0., "std": statistics.pstdev(values) if values else 0.,
                              "min": min(values) if values else 0., "max": max(values) if values else 0.}
        labels = [r["outcome"]["body"]["value"] for r in training]
        context = training[-12:] if route == "tabiclv2" else []
        body = {"task": task_record["sha256"], "route": route, "feature_set": feature_set, "adapter_version": "1",
                "implementation_mode": "native_baseline" if route == "baseline" else "simulated",
                "preparation": "empirical_mean" if route == "baseline" else "training_style" if route == "catboost" else "context_style",
                "columns": columns, "scales": scales, "target": task_record["body"]["target"], "baseline": statistics.mean(labels),
                "label_min": min(labels), "label_max": max(labels), "training_count": len(training),
                "training_matrix_sha256": digest([[r["feature"]["body"]["values"], r["outcome"]["body"]["value"]] for r in training]),
                "context": [{"values": {c: r["feature"]["body"]["values"][c] for c in columns}, "label": r["outcome"]["body"]["value"]} for r in context],
                "prepared_at": at, "wall_ms": (time.perf_counter() - started) * 1000,
                "provider_calls": 0, "measured_provider_usd": 0, "local_compute_usd": None}
        body["prepared_bytes"] = len(encoded(body))
        return store.put("model", key, body, at, [task_record["sha256"], *[r[k]["sha256"] for r in training for k in ("feature", "outcome")]])


def predict(model: dict, feature: dict) -> float:
    body, row = model["body"], feature["body"]
    if body["task"] != row["task"] or any(c not in row["values"] for c in body["columns"]):
        raise ValueError("Model/feature contract mismatch")
    if body["implementation_mode"] == "real":
        from runtime.real_models import predict_real
        return predict_real(model,feature)
    if body["route"] == "baseline":
        return body["baseline"]
    def normalize(values, column):
        scale = body["scales"][column]
        value = values[column] if values[column] is not None else scale["mean"]
        return (value - scale["min"]) / (scale["max"] - scale["min"] or 1.)
    if body["route"] == "catboost":
        # Synthetic provider response, not tree fitting or CatBoost inference.
        value = statistics.mean(normalize(row["values"], c) for c in body["columns"])
        if body["target"]["kind"] == "classification":
            return 1 / (1 + math.exp(-max(-30, min(30, (value - .5) * 4))))
        return body["label_min"] + value * (body["label_max"] - body["label_min"])
    # Synthetic context lookup, not TabICLv2 inference or an installed model.
    nearest = sorted(body["context"], key=lambda r: sum((normalize(row["values"], c) - normalize(r["values"], c)) ** 2 for c in body["columns"]))[:3]
    return statistics.mean(r["label"] for r in nearest)


def metrics(kind: str, labels: list[float], predictions: list[float]) -> dict:
    if not labels or len(labels) != len(predictions) or any(not number(v) for v in labels + predictions):
        raise ValueError("Metrics require paired finite observations and predictions")
    mse = statistics.mean((p - y) ** 2 for y, p in zip(labels, predictions))
    if kind == "regression":
        mean = statistics.mean(labels)
        total = sum((y - mean) ** 2 for y in labels)
        return {"count":len(labels), "mae":statistics.mean(abs(p-y) for y,p in zip(labels,predictions)), "rmse":math.sqrt(mse),
                "r2":1 - mse * len(labels) / total if total else None}
    if kind != "classification" or any(y not in (0,1) for y in labels) or any(not 0 <= p <= 1 for p in predictions):
        raise ValueError("Classification requires binary labels and probabilities")
    decisions = [int(p >= .5) for p in predictions]
    tp = sum(y == 1 and p == 1 for y,p in zip(labels, decisions))
    fp = sum(y == 0 and p == 1 for y,p in zip(labels, decisions))
    fn = sum(y == 1 and p == 0 for y,p in zip(labels, decisions))
    precision, recall = tp / (tp + fp) if tp + fp else 0., tp / (tp + fn) if tp + fn else 0.
    bins = []
    for index in range(5):
        pairs = [(y,p) for y,p in zip(labels,predictions) if min(4,int(p * 5)) == index]
        if pairs:
            bins.append({"lower":index/5, "upper":(index+1)/5, "count":len(pairs),
                         "mean_probability":statistics.mean(p for _,p in pairs), "observed_rate":statistics.mean(y for y,_ in pairs)})
    positive = [p for y,p in zip(labels,predictions) if y == 1]
    negative = [p for y,p in zip(labels,predictions) if y == 0]
    auc = statistics.mean(float(p > n) + .5 * (p == n) for p in positive for n in negative) if positive and negative else None
    return {"count":len(labels), "accuracy":statistics.mean(y == p for y,p in zip(labels,decisions)),
            "precision":precision, "recall":recall, "f1":2*precision*recall/(precision+recall) if precision+recall else 0.,
            "brier":mse, "log_loss":-statistics.mean(y*math.log(max(1e-12,p))+(1-y)*math.log(max(1e-12,1-p)) for y,p in zip(labels,predictions)),
            "roc_auc":auc, "calibration_bins":bins,
            "ece":sum(b["count"] * abs(b["mean_probability"]-b["observed_rate"]) for b in bins)/len(labels)}


def evaluate(store, model: dict, holdout: list[dict], at: int) -> dict:
    with store.connection.transaction():
        store.lock()
        return _evaluate(store,model,holdout,at)


def _evaluate(store, model: dict, holdout: list[dict], at: int) -> dict:
    implementation = digest({name:Path(__file__).with_name(name).read_text() for name in ('prediction.py','real_models.py','simulation.py')})
    key = digest([model["sha256"], [[r["feature"]["sha256"],r["outcome"]["sha256"]] for r in holdout], implementation])
    existing = store.find("evaluation", key)
    if existing:
        return existing
    started = time.perf_counter()
    for case in holdout:
        validate_case(case)
        if case["feature"]["body"]["cutoff"] < model["body"]["prepared_at"] or case["outcome"]["available_at"] > at:
            raise ValueError("Evaluation leakage or unavailable outcome")
        if case["outcome"]["body"]["task"] != model["body"]["task"]:
            raise ValueError("Evaluation target contract mismatch")
    predictions = [predict(model,r["feature"]) for r in holdout]
    scores = metrics(model["body"]["target"]["kind"], [r["outcome"]["body"]["value"] for r in holdout], predictions)
    body = {"model":model["sha256"], "status":"passed", "metrics":scores, "predictions":predictions, "implementation_sha256":implementation,
            "cases":[[r["feature"]["sha256"],r["outcome"]["sha256"]] for r in holdout],
            "cutoffs":[r["feature"]["body"]["cutoff"] for r in holdout],
            "wall_ms":(time.perf_counter()-started)*1000, "prediction_bytes":len(encoded(predictions)),
            "provider_calls":0, "simulated_provider_calls":len(holdout) if model["body"]["implementation_mode"] == "simulated" else 0,
            "measured_provider_usd":0, "local_compute_usd":None,
            "quality_claim":("Actual predictor ran on synthetic data; this does not establish real-world quality."
                             if model["body"]["implementation_mode"] == "real" else
                             "Development fixture exercises machinery; no actual CatBoost/TabICLv2 execution claim.")}
    return store.put("evaluation", key, body, at, [model["sha256"], *[r[k]["sha256"] for r in holdout for k in ("feature","outcome")]])


def compare(store, task_record: dict, snapshots: list[dict], at: int, implementation_mode="simulated") -> dict:
    with store.connection.transaction():
        store.lock()
        return _compare(store,task_record,snapshots,at,implementation_mode)


def _compare(store, task_record: dict, snapshots: list[dict], at: int, implementation_mode="simulated") -> dict:
    training, holdout, prepared_at = chronological_split(task_record["body"], cases(store,task_record,snapshots,at))
    models = [prepare(store,task_record,training,route,feature_set,prepared_at,implementation_mode) for route,feature_set in ROUTES]
    evaluations = [evaluate(store,model,holdout,at) for model in models]
    primary = "brier" if task_record["body"]["target"]["kind"] == "classification" else "rmse"
    selected = min(evaluations, key=lambda e:e["body"]["metrics"][primary])
    body = {"task":task_record["sha256"], "models":[m["sha256"] for m in models],
            "evaluations":[e["sha256"] for e in evaluations], "selected":selected["body"]["model"],
            "primary_metric":primary, "selection_rule":"Lowest synthetic holdout loss; baseline wins ties by stable order.",
            "holdout_cases":evaluations[0]["body"]["cases"], "train_count":len(training), "holdout_count":len(holdout)}
    return store.find("comparison",digest(body)) or store.put("comparison", digest(body), body, at, [e["sha256"] for e in evaluations])


def registry(store, cutoff: int | None = None) -> dict:
    states, active = {}, None
    for model in store.list("model",cutoff):
        states[model["sha256"]] = "prepared"
    for evaluation in store.list("evaluation",cutoff):
        if evaluation["body"]["status"] == "passed":
            states[evaluation["body"]["model"]] = "evaluated"
    for event in sorted(store.list("model_transition",cutoff), key=lambda r:r["body"]["sequence"]):
        body = event["body"]
        if body["action"] == "approve":
            states[body["model"]] = "approved"
        else:
            if active:
                states[active] = "retired"
            active = body["model"]
            states[active] = "active"
    return {"active":active, "states":states}


def transition(store, task_record: dict, model_sha: str, action: str, at: int, request_id: str) -> dict:
    if action not in ("approve", "activate", "rollback"):
        raise ValueError("Unsupported model lifecycle transition")
    with store.connection.transaction():
        store.lock()
        previous = store.find("model_transition", request_id)
        if previous:
            if previous["body"]["model"] != model_sha or previous["body"]["action"] != action:
                raise ValueError("Conflicting model transition request")
            return previous
        model = store.get(model_sha)
        if model["kind"] != "model" or model["body"]["task"] != task_record["sha256"]:
            raise ValueError("Incompatible model/task version")
        evaluations = [r for r in store.list("evaluation",at) if r["body"]["model"] == model_sha]
        if not evaluations or any(e["body"]["status"] != "passed" for e in evaluations):
            raise ValueError("Failed or blocked evidence prevents model approval/activation")
        history = store.list("model_transition")
        if history and at < max(r["available_at"] for r in history):
            raise ValueError("Cannot backdate a registry transition")
        status = registry(store,at)
        state = status["states"][model_sha]
        if (action == "approve" and state != "evaluated") or (action == "activate" and state != "approved") or (action == "rollback" and state != "retired"):
            raise ValueError("Invalid model lifecycle state")
        body = {"model":model_sha, "action":action, "previous_active":status["active"],
                "sequence":len(store.list("model_transition"))+1, "actor":"simulated-operator", "approval_mode":"simulated"}
        return store.put("model_transition", request_id, body, at, [task_record["sha256"], model_sha, *[e["sha256"] for e in evaluations],
                                                                  *[r["sha256"] for r in history[-1:]]])


def score(store, task_record: dict, feature: dict, at: int, fallback: str | None = None, shadow: str | None = None) -> dict:
    if feature["body"]["task"] != task_record["sha256"] or not feature["available_at"] <= at < feature["body"]["target_at"]:
        raise ValueError("Scoring requires compatible features before target horizon")
    with store.connection.transaction():
        store.lock()
        active = registry(store,at)["active"]
        selected, mode = (shadow,"shadow") if shadow else (active,"active")
        if not selected or store.get(selected)["body"]["task"] != task_record["sha256"]:
            selected, mode = fallback, "fallback"
        if selected is None:
            raise ValueError("No compatible active model or explicit baseline fallback")
        model = store.get(selected)
        if model["kind"] != "model" or model["body"]["prepared_at"] > feature["body"]["cutoff"]:
            raise ValueError("Model unavailable at feature cutoff")
        if mode == "fallback" and model["body"]["route"] != "baseline":
            raise ValueError("Fallback must use the explicit baseline")
        key = digest([feature["sha256"], selected, mode, task_record["sha256"]])
        previous = store.find("prediction", key)
        if previous:
            return previous
        body = {"task":task_record["sha256"], "feature":feature["sha256"], "model":selected, "mode":mode,
                "entity":feature["body"]["entity"], "cutoff":feature["body"]["cutoff"], "target_at":feature["body"]["target_at"],
                "value":predict(model,feature), "implementation_mode":model["body"]["implementation_mode"],
                "policy_sha256":digest(task_record["body"]["policy"])}
        transitions = store.list("model_transition",at) if mode == "active" else []
        return store.put("prediction", key, body, at, [task_record["sha256"], feature["sha256"], selected,
                                                       *[r["sha256"] for r in transitions[-1:]]])


def update_plan(store, model: dict, fresh: list[dict], reason_record: dict, at: int, prepare_requested=False) -> dict:
    if not fresh or any(f["body"]["task"] != model["body"]["task"] for f in fresh):
        raise ValueError("Update requires compatible feature rows")
    drift = {}
    for column, scale in model["body"]["scales"].items():
        values = [f["body"]["values"][column] for f in fresh if f["body"]["values"][column] is not None]
        drift[column] = {"mean_shift_std":abs(statistics.mean(values)-scale["mean"])/(scale["std"] or 1) if values else None,
                         "missing_rate":1-len(values)/len(fresh)}
    with store.connection.transaction():
        store.lock()
        key = digest([model["sha256"], [f["sha256"] for f in fresh], reason_record["sha256"], prepare_requested])
        replay = store.find("update_plan",key)
        if replay:
            return replay
        prior_preparations = [r for r in store.list("update_plan") if "model_preparation" in r["body"]["actions"]]
        if prepare_requested and prior_preparations:
            raise ValueError("Synthetic model-update budget exhausted")
        actions = ["feature_refresh","scoring","artifact_refresh"] + (["model_preparation"] if prepare_requested else [])
        body = {"model":model["sha256"], "drift":drift, "actions":actions, "notify":False,
                "reason":reason_record["sha256"], "preparation_requires_evaluation_and_approval":True}
        return store.put("update_plan",key,body,at,[model["sha256"],reason_record["sha256"],*[f["sha256"] for f in fresh]])


def invalidate_predictions(store, source_sha: str, reason_record: dict, at: int) -> list[dict]:
    affected = []
    for prediction in store.list("prediction",at):
        if source_sha in {r["sha256"] for r in store.lineage(prediction["body"]["feature"])}:
            body = {"prediction":prediction["sha256"], "reason":reason_record["sha256"], "disposition":"superseded_after_correction"}
            key = digest(body)
            affected.append(store.find("invalidation",key) or store.put("invalidation",key,body,at,[prediction["sha256"],reason_record["sha256"]]))
    return affected
