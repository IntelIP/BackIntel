"""Dataset-independent capability simulation. No network, provider, or generated code execution."""
from __future__ import annotations

import csv
import hashlib
import html
import io
import json
import math
import os
import re
import tempfile
from pathlib import Path

ENGINE_VERSION = "capability-simulation-v1"
SCENARIOS = Path(__file__).resolve().parents[1] / "config" / "simulation"


def encoded(value: object) -> bytes:
    return (json.dumps(value, sort_keys=True, ensure_ascii=False, indent=2, allow_nan=False) + "\n").encode()


def digest(value: object) -> str:
    return hashlib.sha256(encoded(value)).hexdigest()


def load_scenario(name: str) -> dict:
    if not isinstance(name, str) or not re.fullmatch(r"[a-z][a-z0-9-]{0,40}", name):
        raise ValueError("Scenario must be a local configuration name")
    config = json.loads((SCENARIOS / f"{name}.json").read_text())
    if config.get("id") != name:
        raise ValueError("Scenario ID must match its filename")
    return config


def normalize(config: dict) -> list[dict]:
    """Two real parsers, one mapped observation contract; extraction is a labeled rule stand-in."""
    if config.get("schema") != "backintel-simulation/v1":
        raise ValueError("Unsupported simulation schema")
    for key in ("id", "title", "signal_label", "audience"):
        if not isinstance(config.get(key), str) or not config[key].strip():
            raise ValueError(f"Missing scenario {key}")
    source = config["source"]
    if source["format"] == "csv":
        rows = list(csv.DictReader(io.StringIO(source["data"])))
    elif source["format"] == "json":
        rows = source["data"]
    else:
        raise ValueError("Supported synthetic sources are CSV and JSON")
    if not isinstance(rows, list) or not 1 <= len(rows) <= 100:
        raise ValueError("A scenario requires 1..100 source rows")
    fields, rule, policy = config["fields"], config["extractor"], config["policy"]
    if set(fields) != {"id", "entity", "period", "content"} or any(not isinstance(v, str) for v in fields.values()):
        raise ValueError("Map id, entity, period, and content source fields")
    kind = rule.get("kind")
    if kind == "keywords":
        terms = rule.get("terms")
        if not isinstance(terms, list) or not terms or any(not isinstance(t, str) or not t.strip() for t in terms):
            raise ValueError("Keyword extraction requires nonempty terms")
    elif kind == "above":
        if type(rule.get("threshold")) not in (int, float) or not math.isfinite(rule["threshold"]):
            raise ValueError("Numeric extraction requires a finite threshold")
    else:
        raise ValueError("Supported simulated extractors are keywords and above")
    if type(policy.get("attention_rate")) not in (float, int) or not 0 < policy["attention_rate"] <= 1:
        raise ValueError("Attention rate must be greater than zero and at most one")
    if type(policy.get("stale_after")) is not int or policy["stale_after"] < 1:
        raise ValueError("Staleness requires a positive simulated duration")
    result, seen = [], set()
    for position, row in enumerate(rows, 1):
        if not isinstance(row, dict) or any(field not in row for field in fields.values()):
            raise ValueError("Source row does not satisfy its field mapping")
        mapped = {key: row[value] for key, value in fields.items()}
        if any(not isinstance(mapped[key], str) or not mapped[key].strip() for key in ("id", "entity", "period")):
            raise ValueError("Source IDs, entities, and periods must be nonempty strings")
        identity = (mapped["period"], mapped["id"])
        if identity in seen:
            raise ValueError("Duplicate source identity within one period")
        seen.add(identity)
        content = mapped["content"]
        if content is None or (isinstance(content, str) and not content.strip()):
            value = None
        elif kind == "keywords":
            if not isinstance(content, str) or len(content) > 5000:
                raise ValueError("Text content must be a string of at most 5000 characters")
            value = int(any(term.casefold() in content.casefold() for term in rule["terms"]))
        else:
            if isinstance(content, bool) or not isinstance(content, (str, int, float)):
                raise ValueError("Numeric content must be finite")
            number = float(content)
            if not math.isfinite(number):
                raise ValueError("Numeric content must be finite")
            value = int(number > rule["threshold"])
        result.append({"record_id": mapped["id"], "entity": mapped["entity"], "period": mapped["period"],
                       "value": value, "mode": "simulated_rule_extraction", "source_row": position,
                       "source_format": source["format"], "source_sha256": digest(row), "source": row,
                       "definition_sha256": digest({"engine": ENGINE_VERSION, "fields": fields, "extractor": rule})})
    return result


def summarize(observations: list[dict]) -> dict:
    known = [row for row in observations if row["value"] is not None]
    flagged = sum(row["value"] for row in known)
    return {"records": len(observations), "known": len(known), "unknown": len(observations) - len(known),
            "flagged": flagged, "rate": flagged / len(known) if known else None}


def simulate(config: dict) -> dict:
    observations = normalize(config)
    events = config["events"]
    if not isinstance(events, list) or not 1 <= len(events) <= 100:
        raise ValueError("A scenario requires 1..100 events")
    batches, timeline, episodes, failed_once = {}, [], [], set()
    last_at, last_data_at, last_period = -1, None, None
    current_episode = None
    for event in events:
        at, action = event.get("at"), event.get("action")
        if type(at) is not int or at < 0 or at < last_at:
            raise ValueError("Events must have nonnegative, chronological simulated times")
        last_at = at
        entry = {"at": at, "action": action}
        if action in ("arrival", "schedule", "retry"):
            period = event.get("period")
            rows = [row for row in observations if row["period"] == period]
            if not rows:
                raise ValueError("Event references an absent source period")
            entry["period"] = period
            if period in batches:
                entry["outcome"] = "reused"
            elif event.get("fail_once", False) and period not in failed_once:
                failed_once.add(period)
                entry["outcome"] = "simulated_transient_failure"
            else:
                summary = summarize(rows)
                previous = batches[last_period]["summary"] if last_period is not None else None
                delta = (summary["rate"] - previous["rate"]
                         if previous and previous["rate"] is not None and summary["rate"] is not None else None)
                batch = {"period": period, "summary": summary, "change": delta,
                         "entities": {entity: summarize([row for row in rows if row["entity"] == entity])
                                      for entity in sorted({row["entity"] for row in rows})},
                         "observations": rows,
                         "projection": {"mode": "simulated_linear_extrapolation", "validated": False,
                                        "next_rate": min(1, max(0, summary["rate"] + delta)) if delta is not None else None}}
                batches[period] = batch
                last_period, last_data_at = period, at
                condition = ("unknown" if summary["rate"] is None else
                             "active" if summary["rate"] >= config["policy"]["attention_rate"] else "cleared")
                if condition == "active" and (current_episode is None or current_episode["condition"] == "cleared"):
                    current_episode = {"id": f"{config['id']}:{period}", "condition": "active", "acknowledged": False,
                                       "history": [], "delivery": "simulated_local_inbox"}
                    episodes.append(current_episode)
                if current_episode is not None:
                    current_episode["condition"] = condition
                    current_episode["history"].append({"at": at, "condition": condition, "period": period})
                entry.update(outcome="completed", condition=condition if current_episode else "normal")
        elif action == "acknowledge":
            if current_episode is None or current_episode["condition"] == "cleared":
                raise ValueError("Acknowledgment requires an open attention episode")
            current_episode["acknowledged"] = True
            current_episode["history"].append({"at": at, "action": "acknowledged", "condition": current_episode["condition"]})
            entry.update(outcome="acknowledged", condition=current_episode["condition"])
        elif action == "tick":
            stale = last_data_at is not None and at - last_data_at >= config["policy"]["stale_after"]
            if stale and current_episode is not None and current_episode["condition"] != "cleared":
                current_episode["condition"] = "unknown"
                current_episode["history"].append({"at": at, "condition": "unknown", "reason": "stale_data"})
            entry.update(outcome="stale" if stale else "fresh", condition=current_episode["condition"] if current_episode else "normal")
        else:
            raise ValueError("Unsupported simulation event")
        timeline.append(entry)
    if not batches:
        raise ValueError("Simulation produced no completed batch")
    if set(batches) != {row["period"] for row in observations}:
        raise ValueError("Simulation ended with unprocessed periods; retry or schedule the remaining work")
    return {"schema": "backintel-simulation-result/v1", "engine": ENGINE_VERSION, "scenario": config["id"],
            "title": config["title"], "audience": config["audience"], "signal_label": config["signal_label"],
            "mode": "synthetic_simulation", "input_sha256": digest({"engine": ENGINE_VERSION, "config": config}),
            "batches": list(batches.values()), "timeline": timeline, "inbox": episodes,
            "cost": {"provider_calls": 0, "provider_usd": 0, "local_compute_usd": None},
            "limits": ["All source records are synthetic.", "Extraction uses deterministic rules, not live model inference.",
                       "Triggers, clock, injected failure, and inbox delivery are simulated.",
                       "Linear extrapolation demonstrates a prediction output contract, not forecast quality.",
                       "Artifacts use a fixed renderer; generated-code execution is not implemented."]}


def render_html(result: dict) -> str:
    esc = lambda value: html.escape(str(value), quote=True)
    rows, evidence = [], []
    for batch in result["batches"]:
        s = batch["summary"]
        rate = "unknown" if s["rate"] is None else f"{s['rate']:.0%}"
        change = "—" if batch["change"] is None else f"{batch['change'] * 100:+.0f} pp"
        rows.append(f"<tr><th scope='row'>{esc(batch['period'])}</th><td>{s['flagged']}/{s['known']}</td>"
                    f"<td>{rate}</td><td>{change}</td><td>{s['unknown']}</td></tr>")
        for row in batch["observations"]:
            evidence.append(f"<details><summary>{esc(row['period'])} · {esc(row['record_id'])} · {esc(row['entity'])}</summary>"
                            f"<p>Signal: {esc(row['value'])}; source row {row['source_row']}; simulated extraction.</p>"
                            f"<pre>{esc(json.dumps(row['source'], ensure_ascii=False, indent=2))}</pre>"
                            f"<p>Source SHA-256: <code>{row['source_sha256']}</code></p></details>")
    events = "".join(f"<li>t={row['at']}: {esc(row['action'])} {esc(row.get('period', ''))} → {esc(row['outcome'])}"
                     f" {esc(row.get('condition', ''))}</li>" for row in result["timeline"])
    return ("<!doctype html><html lang='en'><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'>"
            f"<title>BackIntel simulation — {esc(result['title'])}</title><style>"
            "body{font:16px/1.6 system-ui,sans-serif;color:#172b4d;background:#f5f7fa;margin:0}"
            "main{max-width:960px;margin:auto;padding:24px}section{background:white;padding:20px;margin:20px 0;border-radius:8px}"
            "table{border-collapse:collapse;width:100%}th,td{text-align:left;padding:10px;border-bottom:1px solid #ddd}"
            ".scroll{overflow-x:auto}pre{white-space:pre-wrap;overflow-wrap:anywhere}code{overflow-wrap:anywhere}"
            "summary{cursor:pointer}summary:focus-visible{outline:3px solid #075985}details{margin:12px 0}"
            "</style><main><p><strong>SYNTHETIC SIMULATION · No live AI calls</strong></p>"
            f"<h1>{esc(result['title'])}</h1><p>Audience: {esc(result['audience'])}. Signal: {esc(result['signal_label'])}.</p>"
            "<section><h2>Briefing</h2><div class='scroll'><table><caption>Simulated periods and known-record denominators</caption>"
            "<tr><th scope='col'>Period</th><th scope='col'>Flagged / known</th><th scope='col'>Rate</th>"
            "<th scope='col'>Change</th><th scope='col'>Unknown</th></tr>"
            + "".join(rows) + "</table></div></section><section><h2>Background and attention timeline</h2><ol>"
            + events + "</ol></section><section><h2>Analyst source evidence</h2>" + "".join(evidence)
            + "</section><section><h2>Simulation boundaries</h2><ul>"
            + "".join(f"<li>{esc(limit)}</li>" for limit in result["limits"])
            + "</ul><p>Provider calls: 0. Provider charges: $0. Local compute cost: unpriced.</p></section></main></html>")


def publish(result: dict, directory: Path) -> dict:
    directory.mkdir(parents=True, exist_ok=True)
    stem = "simulation-" + digest(result)
    artifacts = {}
    for suffix, payload in (("json", encoded(result)), ("html", render_html(result).encode())):
        destination = directory / f"{stem}.{suffix}"
        if destination.exists():
            if destination.read_bytes() != payload:
                raise ValueError("Existing simulation artifact differs from expected content")
        else:
            fd, temporary = tempfile.mkstemp(prefix=".simulation-", dir=directory)
            try:
                with os.fdopen(fd, "wb") as handle:
                    handle.write(payload)
                os.replace(temporary, destination)
            finally:
                Path(temporary).unlink(missing_ok=True)
        artifacts[suffix] = {"path": str(destination.resolve()), "sha256": hashlib.sha256(payload).hexdigest()}
    return artifacts
