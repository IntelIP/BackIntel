"""Portable synthetic task contracts and revision-aware CSV/JSON/text admission."""
from __future__ import annotations

import csv
import io
import json
import math
import re

from runtime.simulation import digest, encoded


def number(value) -> bool:
    return type(value) in (int, float) and math.isfinite(value)


def validate_task(task: dict) -> dict:
    required = {"schema", "id", "entity", "fields", "measures", "questions", "target", "audiences", "policy", "observation_provider"}
    if set(task) != required or task["schema"] != "backintel-task/v1":
        raise ValueError("Invalid task schema or fields")
    if not isinstance(task["id"], str) or not re.fullmatch(r"[a-z][a-z0-9-]{0,40}", task["id"]):
        raise ValueError("Invalid task ID")
    if not isinstance(task["entity"], str) or not task["entity"].strip():
        raise ValueError("Task entity is required")
    provider = task["observation_provider"]
    if set(provider) != {"name","version","implementation_mode"} or provider["implementation_mode"] not in ("simulated","real") or any(
            not isinstance(provider[k],str) or not provider[k] for k in ("name","version")):
        raise ValueError("Task requires an explicit observation provider identity and execution mode")
    fields = task["fields"]
    if set(fields) != {"id", "entity", "event_at", "available_at", "revision", "content"}:
        raise ValueError("Source mapping requires identity, event/availability times, revision and content")
    if any(not isinstance(v, str) or not v for v in fields.values()) or len(set(fields.values())) != len(fields):
        raise ValueError("Source mapping must use distinct fields")
    measures = task["measures"]
    if not measures or any(set(m) != {"id", "field", "unit", "nullable"} or type(m["nullable"]) is not bool
                           or any(not isinstance(m[k], str) or not m[k] for k in ("id", "field", "unit")) for m in measures):
        raise ValueError("Measures require IDs, source fields, units and null policies")
    if len({m["id"] for m in measures}) != len(measures):
        raise ValueError("Duplicate measure ID")
    questions = task["questions"]
    if not questions or len({q["id"] for q in questions}) != len(questions):
        raise ValueError("Questions require unique IDs")
    for question in questions:
        if set(question) != {"id", "prompt", "type", "rule"} or question["type"] not in ("boolean", "number"):
            raise ValueError("Invalid typed question")
        if any(not isinstance(question[k], str) or not question[k].strip() for k in ("id", "prompt")):
            raise ValueError("Question requires ID and prompt")
        rule = question["rule"]
        if rule.get("kind") == "keywords":
            if question["type"] != "boolean" or set(rule) != {"kind", "terms"} or not rule["terms"] or any(
                    not isinstance(term, str) or not term.strip() for term in rule["terms"]):
                raise ValueError("Keyword rule requires boolean type and terms")
        elif rule.get("kind") == "number":
            if question["type"] != "number" or set(rule) != {"kind"}:
                raise ValueError("Number rule requires number type")
        else:
            raise ValueError("Unsupported simulated extraction rule")
    target = task["target"]
    if set(target) != {"id", "kind", "unit", "horizon", "minimum_train", "holdout_fraction"} or target["kind"] not in ("classification", "regression"):
        raise ValueError("Invalid target contract")
    if any(not isinstance(target[k], str) or not target[k] for k in ("id", "unit")) or type(target["horizon"]) is not int or target["horizon"] < 1:
        raise ValueError("Target requires ID, unit and positive horizon")
    if type(target["minimum_train"]) is not int or target["minimum_train"] < 2 or not number(target["holdout_fraction"]) or not 0 < target["holdout_fraction"] < 1:
        raise ValueError("Target requires bounded chronological split")
    if not task["audiences"] or any(set(a) != {"id", "view", "entities", "can_correct"} or a["view"] not in ("briefing", "analysis", "export")
                                     or not isinstance(a["id"], str) or not re.fullmatch(r"[a-z][a-z0-9-]{0,40}", a["id"])
                                     or type(a["can_correct"]) is not bool or not isinstance(a["entities"], list)
                                     or any(not isinstance(e, str) or not e for e in a["entities"]) for a in task["audiences"]):
        raise ValueError("Invalid audience scope")
    if len({a["id"] for a in task["audiences"]}) != len(task["audiences"]):
        raise ValueError("Duplicate audience ID")
    policy = task["policy"]
    required_policy = {"max_rows", "max_attempts", "max_provider_calls", "entry", "clear", "cooldown", "stale_after", "response_deadline", "signal_question", "signal_scale"}
    if set(policy) not in (required_policy, required_policy | {"prediction_scale"}):
        raise ValueError("Invalid policy fields")
    if "prediction_scale" in policy and (not number(policy["prediction_scale"]) or policy["prediction_scale"] <= 0):
        raise ValueError("Prediction attention scale must be positive")
    if any(type(policy[k]) is not int or policy[k] < 1 for k in ("max_rows", "max_attempts", "max_provider_calls", "cooldown", "stale_after", "response_deadline")):
        raise ValueError("Policy limits must be positive integers")
    if policy["max_rows"] > 1000 or policy["max_attempts"] > 5 or policy["max_provider_calls"] > 5000:
        raise ValueError("Synthetic policy exceeds execution bounds")
    if not number(policy["entry"]) or not number(policy["clear"]) or not 0 <= policy["clear"] < policy["entry"] <= 1:
        raise ValueError("Attention requires distinct entry and clear thresholds")
    if policy["signal_question"] not in {q["id"] for q in questions} or not number(policy["signal_scale"]) or policy["signal_scale"] <= 0:
        raise ValueError("Attention requires a known question and positive normalization scale")
    return task


def register_task(store, task: dict, available_at=0) -> dict:
    validate_task(task)
    if task["id"] != store.task_id:
        raise ValueError("Task/store mismatch")
    with store.connection.transaction():
        store.lock()
        existing = store.find('task', digest(task))
        if existing:
            return existing
        previous = store.list('task')
        if previous and available_at <= max(record['available_at'] for record in previous):
            raise ValueError('Task revisions require a strictly later available_at time')
        return store.put("task", digest(task), task, available_at)


def parse_source(source: dict, max_rows: int) -> list[dict]:
    if set(source) != {"format", "data"} or len(encoded(source)) > 1_000_000:
        raise ValueError("Invalid or oversized source envelope")
    if source["format"] == "json":
        rows = json.loads(source["data"]) if isinstance(source["data"], str) else source["data"]
    elif source["format"] == "csv":
        reader = csv.DictReader(io.StringIO(source["data"]))
        if not reader.fieldnames or len(reader.fieldnames) != len(set(reader.fieldnames)):
            raise ValueError("Missing or duplicate CSV headers")
        rows = list(reader)
    elif source["format"] == "text":
        # Text batches are line-delimited JSON envelopes with untrusted free text in content.
        rows = [json.loads(line) for line in source["data"].splitlines() if line.strip()]
    else:
        raise ValueError("Supported sources are JSON, CSV and text envelopes")
    if not isinstance(rows, list) or not 1 <= len(rows) <= max_rows:
        raise ValueError("Source row budget exceeded or batch empty")
    return rows


def mapped_fact(task: dict, row: dict, source_format: str) -> dict:
    if not isinstance(row, dict):
        raise ValueError("Source row must be an object")
    try:
        fact = {key: row[value] for key, value in task["fields"].items()}
        measures = {m["id"]: row[m["field"]] for m in task["measures"]}
    except KeyError as error:
        raise ValueError("Source row missing mapped field") from error
    if any(not isinstance(fact[key], str) or not fact[key].strip() or len(fact[key]) > 200 for key in ("id", "entity")):
        raise ValueError("Source identity/entity must be nonempty strings")
    for key in ("event_at", "available_at", "revision"):
        value = fact[key]
        if source_format == "csv" and isinstance(value, str) and value.isdecimal():
            value = int(value)
        if type(value) is not int or not (0 <= value <= 2**53):
            raise ValueError("Source times and revision must be nonnegative integers")
        fact[key] = value
    if fact["revision"] < 1 or fact["available_at"] < fact["event_at"]:
        raise ValueError("Invalid source revision/availability")
    if fact["content"] is not None and (not isinstance(fact["content"], str) or len(fact["content"]) > 5000):
        raise ValueError("Content must be bounded text or null")
    for measure in task["measures"]:
        value = measures[measure["id"]]
        if source_format == "csv":
            value = None if value == "" else float(value)
        if value is None and measure["nullable"]:
            measures[measure["id"]] = None
        elif not number(value):
            raise ValueError("Measure violates finite numeric/null contract")
        else:
            measures[measure["id"]] = value
    return {**fact, "measures": measures, "source": row, "source_format": source_format}


def admit_source(store, task_record: dict, source: dict, received_at: int) -> dict:
    task = task_record["body"]
    batch_identity = digest({"task": task_record["sha256"], "source": source, "received_at": received_at})
    with store.connection.transaction():
        store.lock()
        previous = store.find("admission", batch_identity)
        if previous:
            return previous
        dispositions, parents = [], [task_record["sha256"]]
        try:
            rows = parse_source(source, task["policy"]["max_rows"])
        except (ValueError, TypeError, KeyError, csv.Error) as error:
            rows = []
            dispositions.append({"row": None, "status": "quarantined", "reason": str(error)})
        for index, raw in enumerate(rows):
            try:
                fact = mapped_fact(task, raw, source["format"])
                if fact["available_at"] > received_at:
                    raise ValueError("Source claims future availability")
                fact["available_at"] = received_at
                fact["task"] = task_record["sha256"]
                identity = digest([task_record["sha256"], fact["id"], fact["revision"]])
                previous = store.find("source", identity)
                if previous:
                    if previous["body"]["source"] != raw or previous["body"]["source_format"] != source["format"]:
                        raise ValueError("Conflicting source identity/revision")
                    disposition = {"row": index, "status": "duplicate", "source": previous["sha256"]}
                else:
                    revisions = [r for r in store.list("source") if r["body"]["id"] == fact["id"] and r["body"]["task"] == task_record["sha256"]]
                    if any(r["body"]["entity"] != fact["entity"] or r["body"]["event_at"] != fact["event_at"] for r in revisions):
                        raise ValueError("Correction cannot change entity or event grain")
                    latest = max(revisions, key=lambda r: r["body"]["revision"], default=None)
                    source_parents = [task_record["sha256"]] + ([latest["sha256"]] if latest else [])
                    saved = store.put("source", identity, fact, received_at, source_parents)
                    disposition = {"row": index, "status": "accepted", "source": saved["sha256"],
                                   "revision_kind": "correction" if latest and fact["revision"] > latest["body"]["revision"] else "late_revision" if latest else "initial",
                                   "late": received_at > fact["event_at"]}
                parents.append(disposition["source"])
                dispositions.append(disposition)
            except (ValueError, TypeError, KeyError) as error:
                dispositions.append({"row": index, "status": "quarantined", "reason": str(error), "source_sha256": digest(raw)})
        return store.put("admission", batch_identity, {"source_sha256": digest(source), "dispositions": dispositions}, received_at, parents)


def current_sources(store, cutoff: int, task_sha: str | None = None) -> list[dict]:
    current = {}
    for record in store.list("source", cutoff):
        body = record["body"]
        if task_sha is not None and body["task"] != task_sha:
            continue
        if body["event_at"] <= cutoff and (body["id"] not in current or body["revision"] > current[body["id"]]["body"]["revision"]):
            current[body["id"]] = record
    return sorted(current.values(), key=lambda r: (r["body"]["event_at"], r["body"]["entity"], r["body"]["id"]))
