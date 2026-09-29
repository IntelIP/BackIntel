"""Audience projections of accepted evidence. Never expose a whole training lineage."""

from __future__ import annotations

import csv
import html
import io
import json

from runtime.simulation import digest


def audience_for(task: dict, actor: str) -> dict:
    audience = next((a for a in task["audiences"] if a["id"] == actor), None)
    if audience is None:
        raise PermissionError("Audience is not configured for this task")
    return audience


def create_artifacts(store, task_record: dict, result: dict) -> list[dict]:
    task, at = task_record["body"], result["body"]["at"]
    if result["kind"] != "result" or result["body"]["task"] != task_record["sha256"]:
        raise ValueError("Artifacts require a matching accepted result bundle")
    predictions = [store.get(sha) for sha in result["body"]["predictions"]]
    episodes = [store.get(sha) for sha in result["body"]["episodes"]]
    labels = [r for r in store.list("outcome", at) if r["body"]["task"] == task_record["sha256"]]
    analysis = store.get(result["body"]["analysis"])["body"] if result["body"].get("analysis") else None
    artifacts = []
    for audience in task["audiences"]:
        rows, evidence = [], {}
        for sha in result["body"]["features"]:
            feature = store.get(sha)
            entity = feature["body"]["entity"]
            if audience["entities"] and entity not in audience["entities"]:
                continue
            source = store.get(feature["body"]["source"])
            observed = []
            for parent in feature["parents"]:
                record = store.get(parent)
                if record["kind"] not in ("observation", "correction"):
                    continue
                original = store.get(record["body"]["observation"]) if record["kind"] == "correction" else record
                evidence[record["sha256"]] = record
                evidence[original["sha256"]] = original
                observed.append({"sha256": original["sha256"], "correction": record["sha256"] if record["kind"] == "correction" else None,
                                 "question": original["body"]["question"], "response": record["body"]["response"],
                                 "provider": original["body"]["provider"], "request_id": original["body"].get("request_id")})
            prediction = next((r for r in predictions if r["body"]["feature"] == sha), None)
            episode = next((r for r in episodes if r["body"]["entity"] == entity), None)
            actual = max((r for r in labels if r["body"]["entity"] == entity),
                         key=lambda r: (r["body"]["event_at"], r["body"]["revision"]), default=None)
            for record in (feature, source, prediction, episode, actual):
                if record:
                    evidence[record["sha256"]] = record
            rows.append({"entity": entity, "source": source["sha256"], "source_id": source["body"]["id"],
                         "source_available_at": source["available_at"],
                         "stale": at - source["available_at"] >= task["policy"]["stale_after"],
                         "facts": {k: v for k, v in feature["body"]["values"].items() if k.startswith("structured:")},
                         "observations": observed, "expected_observations": len(task["questions"]),
                         "prediction": prediction, "actual": actual, "attention": episode})
            rows[-1]["analysis"] = next((r for r in analysis["rows"] if r["entity"] == entity), None) if analysis else None
        body = {"schema": "backintel-audience-artifact/v1", "task": task_record["sha256"],
                "result": result["sha256"], "at": at, "audience": audience, "entity_kind": task["entity"],
                "target": task["target"], "rows": rows, "evidence": evidence,
                "data": "synthetic", "clock": "synthetic event time", "hypotheses": [],
                "limits": ["Synthetic examples do not establish real-world accuracy or business value.",
                           "Attention uses a fictional demo policy: known interpretation plus scaled forecast; missing interpretation stays unknown.",
                           "Predictions are estimates; no calibrated prediction interval is available.",
                           "Latest recorded outcomes and future predictions concern different time windows.",
                           "Local compute cost is unpriced. Provider cost is separate from prediction value."]}
        artifacts.append(store.put("artifact", digest([result["sha256"], audience]), body, at,
                                   [task_record["sha256"], result["sha256"]]))
    return artifacts


def get_artifact(store, actor: str, sha: str | None = None) -> dict:
    if sha:
        artifact = store.get(sha)
        if artifact["kind"] != "artifact" or artifact["body"]["audience"]["id"] != actor:
            raise PermissionError("Artifact is outside this audience")
        return artifact
    eligible = [r for r in store.list("artifact") if r["body"]["audience"]["id"] == actor]
    if not eligible:
        raise LookupError("No accepted report is available for this audience")
    return max(eligible, key=lambda r: (r["available_at"], r["sha256"]))


def visible_evidence(artifact: dict, sha: str) -> dict:
    record = artifact["body"]["evidence"].get(sha)
    if record is None:
        raise PermissionError("Evidence is outside this audience's report")
    # Parent hashes preserve traceability; the reader must authorize every dereference.
    return record


def review_artifact(store, artifact: dict, actor: str, decision: str, reason: str, at: int) -> dict:
    task = store.get(artifact["body"]["task"])["body"]
    audience = audience_for(task, actor)
    if not audience["can_correct"] or audience["view"] != "analysis" or artifact["body"]["audience"]["id"] != actor:
        raise PermissionError("This audience cannot review this artifact")
    if decision not in ("accepted", "rejected") or not isinstance(reason, str) or not reason.strip() or len(reason) > 1000:
        raise ValueError("Review requires a decision and a bounded reason")
    body = {"artifact": artifact["sha256"], "actor": actor, "decision": decision, "reason": reason}
    with store.connection.transaction():
        store.lock()
        return store.find("artifact_review", digest(body)) or store.put("artifact_review", digest(body), body, at, [artifact["sha256"]])


def export_csv(artifact: dict) -> str:
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["entity", "source_id", "source_available_at", "stale", "latest_actual", "actual_event_at",
                     "prediction", "prediction_target_at", "predictor_mode", "attention", "source_sha256"])
    for row in artifact["body"]["rows"]:
        prediction, actual, attention = (row[k]["body"] if row[k] else {} for k in ("prediction", "actual", "attention"))
        values = [row["entity"], row["source_id"], row["source_available_at"], row["stale"], actual.get("value"),
                  actual.get("event_at"), prediction.get("value"), prediction.get("target_at"),
                  prediction.get("implementation_mode"), attention.get("condition"), row["source"]]
        writer.writerow(["'" + v if isinstance(v, str) and v.lstrip().startswith(("=", "+", "-", "@")) else v for v in values])
    return output.getvalue()


STYLE = """body{font:16px/1.6 system-ui,sans-serif;color:#172b4d;background:#f5f7fa;margin:0}
main{max-width:1060px;margin:auto;padding:24px}section{background:white;padding:20px;margin:20px 0;border-radius:8px}
h1{font-size:2rem;line-height:1.2}h2{font-size:1.3rem}a{color:#075985}nav{display:flex;gap:18px;flex-wrap:wrap}
table{border-collapse:collapse;width:100%}th,td{text-align:left;padding:10px;border-bottom:1px solid #ddd;vertical-align:top}
.scroll{overflow-x:auto}.scroll>table{min-width:600px}.scroll-note{font-size:.9rem}pre{white-space:pre-wrap;overflow-wrap:anywhere}code,.wrap{overflow-wrap:anywhere}
summary{cursor:pointer}details{margin:12px 0}a:focus-visible,summary:focus-visible,input:focus-visible,textarea:focus-visible,button:focus-visible,select:focus-visible{outline:3px solid #075985;outline-offset:3px}
label{display:block;margin:10px 0 4px}input,textarea,select,button{font:inherit;max-width:100%;box-sizing:border-box}textarea{width:100%}
button{background:#075985;color:white;border:0;border-radius:4px;padding:9px 14px;cursor:pointer}small{display:block;color:#45566c}
.notice{border-left:4px solid #b45309;padding-left:12px}.tag{font-size:.85rem;font-weight:650}form{margin:12px 0}
@media(max-width:600px){main{padding:14px}section{padding:14px}h1{font-size:1.65rem}}
"""


def page(title: str, content: str) -> str:
    return ("<!doctype html><html lang='en'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'>"
            f"<title>{html.escape(title)} · BackIntel</title><style>{STYLE}</style></head><body><main>{content}</main></body></html>")


def render(artifact: dict, reviews=(), interactive=True, semantic_note=None) -> str:
    body, esc = artifact["body"], html.escape
    audience, rows = body["audience"], body["rows"]
    versions = {r["prediction"]["body"]["implementation_mode"] for r in rows if r["prediction"]}
    model_note = "Predictors: " + (", ".join(sorted(versions)) if versions else "no predictions available")
    if semantic_note:
        model_note += " · "+semantic_note
    known = sum(o["response"]["status"] == "known" for r in rows for o in r["observations"])
    expected = sum(r["expected_observations"] for r in rows)
    flagged = [r["entity"] for r in rows if r["attention"] and r["attention"]["body"]["condition"] != "cleared"]
    headline = "Review: " + ", ".join(flagged) if flagged else "No active attention condition in this report."
    navigation = (f"<nav aria-label='Report downloads'><a href='/'>Latest report</a><a href='/export.csv?artifact={artifact['sha256']}'>Download CSV</a><a href='/artifact.json?artifact={artifact['sha256']}'>View report data</a></nav>" if interactive else
                  "<nav aria-label='Report downloads'><a href='Export.csv' download>Download CSV</a><a href='Report.json'>View report data</a></nav><p>Read-only export. Use the local viewer to correct observations or record a review.</p>")
    content = (f"<p class='tag'>SYNTHETIC DATA · {esc(model_note)}</p><h1>{esc(audience['view'].title())}: {esc(body['entity_kind'])}</h1>"
               f"<p>Audience: <strong>{esc(audience['id'])}</strong>. Report at t={body['at']} ({esc(body['clock'])}).</p>"
               f"{navigation}"
               f"<section><h2>What needs attention</h2><p>{esc(headline)}</p><p>{len(rows)} visible entities; {known}/{expected} observations known; "
               f"{sum(r['stale'] for r in rows)} inputs stale.</p><p class='notice'>Predictions estimate a future outcome. Latest recorded outcomes describe earlier events.</p></section>")
    if not rows:
        content += "<section><h2>No visible records</h2><p>There are no accepted records within this audience's scope yet.</p></section>"
    else:
        ranked = sorted((r for r in rows if r["prediction"]), key=lambda r: r["prediction"]["body"]["value"], reverse=True)
        content += "<section><h2>Facts and predictions</h2>"
        if ranked:
            content += f"<p>Highest predicted outcome among visible entities: <strong>{esc(ranked[0]['entity'])}</strong>. This ranking does not establish a cause.</p>"
        content += "<p class='scroll-note'>On a narrow screen, swipe the table or focus it and use the arrow keys to see every column.</p><div class='scroll' role='region' aria-label='Outcome comparison' tabindex='0'><table><caption>Visible entities and their distinct outcome windows</caption><thead><tr><th scope='col'>Entity</th><th scope='col'>Current facts</th><th scope='col'>Latest recorded outcome</th><th scope='col'>Future prediction</th><th scope='col'>Attention</th><th scope='col'>Input freshness</th></tr></thead><tbody>"
        for row in rows:
            prediction, actual, attention = (row[k]["body"] if row[k] else {} for k in ("prediction", "actual", "attention"))
            actual_text = f"{actual['value']:.3g} at t={actual['event_at']}" if actual else "Not yet observed"
            prediction_text = f"{prediction['value']:.3g} {body['target']['unit']} for t={prediction['target_at']}" if prediction else "Unavailable"
            finding = row.get("analysis")
            risk = ""
            if finding:
                show = lambda value: "unknown" if value is None else f"{value:.3g}"
                risk = f"<small>Demo risk: {show(finding['semantic_risk'])} from text; {show(finding['prediction_risk'])} from forecast.</small>"
            facts = ", ".join(f"{k.removeprefix('structured:')}: {v}" for k, v in row["facts"].items())
            content += (f"<tr><th scope='row'>{esc(row['entity'])}</th><td>{esc(facts)}</td><td>{esc(actual_text)}</td><td>{esc(prediction_text)}"
                        f"<small>{esc(prediction.get('implementation_mode', 'unknown'))}</small></td><td>{esc(attention.get('condition','none'))}"
                        f"<small>{esc(attention.get('response',''))}</small>{risk}</td><td>{'Stale' if row['stale'] else 'Current'} · t={row['source_available_at']}</td></tr>")
        content += "</tbody></table></div></section><section><h2>Source evidence and observations</h2>"
        for row in rows:
            source = visible_evidence(artifact, row["source"])
            source_url = f"/evidence/{row['source']}?artifact={artifact['sha256']}" if interactive else f"Evidence/{row['source']}.json"
            content += (f"<details><summary>{esc(row['entity'])} · {esc(row['source_id'])}</summary><p class='wrap'>"
                        f"<a href='{source_url}'>Open source record</a> · SHA-256: <code>{row['source']}</code></p>"
                        f"<pre>{esc(json.dumps(source['body'], indent=2))}</pre>")
            for observation in row["observations"]:
                answer = observation["response"]
                content += (f"<h3>{esc(observation['question']['prompt'])}</h3><p>{esc(answer['status'])}: {esc(str(answer['value']))}. "
                            f"{esc(answer['reason'])}</p><small>Interpretation: {esc(observation['provider']['implementation_mode'])}"
                            f"{' · human correction' if observation['correction'] else ''}</small><pre>{esc(json.dumps(answer['distribution']))}</pre>")
                if interactive and audience["can_correct"]:
                    selected = str(answer["value"]).lower() if answer["status"] == "known" else "unknown"
                    value_input = (f"<select name='value' id='value-{observation['sha256']}'>" + "".join(f"<option value='{v}'{' selected' if v == selected else ''}>{v.title()}</option>" for v in ("true", "false", "unknown")) + "</select>"
                                   if observation["question"]["type"] == "boolean" else f"<input id='value-{observation['sha256']}' name='value' value='{esc(selected)}' placeholder='Number or unknown' required>")
                    content += (f"<form method='post' action='/correct'><input type='hidden' name='artifact' value='{artifact['sha256']}'>"
                                f"<input type='hidden' name='observation' value='{observation['sha256']}'><input type='hidden' name='supersedes' value='{observation['correction'] or ''}'>"
                                f"<label for='value-{observation['sha256']}'>Corrected answer</label>{value_input}"
                                f"<label for='reason-{observation['sha256']}'>Reason for correction</label><textarea id='reason-{observation['sha256']}' name='reason' maxlength='1000' required></textarea>"
                                "<button>Save correction and refresh report</button></form>")
            content += "</details>"
        content += "</section>"
    content += "<section><h2>Uncertainty and limits</h2><p>No causal hypotheses have been established.</p><ul>" + "".join(f"<li>{esc(v)}</li>" for v in body["limits"]) + "</ul></section>"
    content += "<section><h2>Report review</h2>"
    relevant = [r for r in reviews if r["body"]["artifact"] == artifact["sha256"]]
    content += "".join(f"<p>{esc(r['body']['decision'])}: {esc(r['body']['reason'])}</p>" for r in relevant) or "<p>Not reviewed.</p>"
    if interactive and audience["can_correct"] and audience["view"] == "analysis":
        content += (f"<form method='post' action='/review'><input type='hidden' name='artifact' value='{artifact['sha256']}'>"
                    "<label for='decision'>Review decision</label><select id='decision' name='decision'><option value='accepted'>Accept</option><option value='rejected'>Reject</option></select>"
                    "<label for='review-reason'>Review reason</label><textarea id='review-reason' name='reason' maxlength='1000' required></textarea><button>Save review</button></form>")
    content += f"</section><p class='wrap'>Report version: <code>{artifact['sha256']}</code></p>"
    return page("Audience report", content)
