"""Generated layouts may select approved evidence; they cannot invent its values."""

import html

from runtime.artifacts import audience_for, page
from runtime.sandbox import resolve_image, run_candidate
from runtime.simulation import digest

COLUMNS = {"entity": "Entity", "prediction": "Predicted outcome", "target_at": "Prediction time",
           "attention": "Attention", "source": "Source evidence"}

# Development generator response. Execution and evidence validation remain real.
DEVELOPMENT_SOURCE = '''import json
snapshot = json.load(open("/input/snapshot.json"))
rows = sorted(snapshot["rows"], key=lambda row: row["prediction"] if row["prediction"] is not None else -1, reverse=True)
print(json.dumps({"schema": "backintel-generated-layout/v1", "title": "Predicted outcomes in descending order",
                  "columns": ["entity", "prediction", "target_at", "attention"], "sources": [row["source"] for row in rows]}))
'''


def snapshot_for(artifact):
    return {"schema": "backintel-generated-input/v1", "artifact": artifact["sha256"], "data": "synthetic",
            "rows": [{"entity": row["entity"], "source": row["source"],
                      "prediction": row["prediction"]["body"]["value"] if row["prediction"] else None,
                      "target_at": row["prediction"]["body"]["target_at"] if row["prediction"] else None,
                      "implementation_mode": row["prediction"]["body"]["implementation_mode"] if row["prediction"] else "unavailable",
                      "attention": row["attention"]["body"]["condition"] if row["attention"] else "none"}
                     for row in artifact["body"]["rows"]]}


def validate_layout(layout, snapshot):
    if not isinstance(layout, dict) or set(layout) != {"schema", "title", "columns", "sources"} or layout["schema"] != "backintel-generated-layout/v1":
        raise ValueError("Generated view must use the supported layout contract")
    if not isinstance(layout["title"], str) or not 1 <= len(layout["title"]) <= 120:
        raise ValueError("Generated title must be bounded")
    if not isinstance(layout["columns"], list) or not layout["columns"] or any(not isinstance(v, str) or v not in COLUMNS for v in layout["columns"]) or len(set(layout["columns"])) != len(layout["columns"]):
        raise ValueError("Generated view contains unsupported columns")
    allowed = {r["source"] for r in snapshot["rows"]}
    if not isinstance(layout["sources"], list) or any(not isinstance(v, str) or v not in allowed for v in layout["sources"]) or len(set(layout["sources"])) != len(layout["sources"]):
        raise ValueError("Generated view references unapproved or duplicate source rows")


def create_candidate(store, artifact, actor, source, image="backintel-capability-demo-runtime:latest"):
    audience = audience_for(store.get(artifact["body"]["task"])["body"], actor)
    if not audience["can_correct"] or audience["view"] != "analysis" or artifact["body"]["audience"]["id"] != actor:
        raise PermissionError("This audience cannot generate a candidate view")
    snapshot = snapshot_for(artifact)
    image = resolve_image(image)
    key = digest([artifact["sha256"], source, image, snapshot])
    previous = store.find("artifact_candidate", key)
    if previous:
        return previous
    run = run_candidate(source, snapshot, image)
    if run["status"] == "candidate":
        try:
            validate_layout(run["result"], snapshot)
        except ValueError as exc:
            run.update(status="rejected", stop_reason=str(exc))
    body = {"artifact": artifact["sha256"], "actor": actor, "snapshot": snapshot, "run": run,
            "code_generation": "simulated", "review": "pending", "external_publications": 0}
    return store.put("artifact_candidate", key, body, artifact["available_at"], [artifact["sha256"]])


def scoped_candidate(store, artifact, sha):
    candidate = store.get(sha)
    if candidate["kind"] != "artifact_candidate" or candidate["body"]["artifact"] != artifact["sha256"]:
        raise PermissionError("Generated candidate is outside this report")
    return candidate


def review_candidate(store, candidate, actor, decision, reason, at):
    artifact = store.get(candidate["body"]["artifact"])
    audience = audience_for(store.get(artifact["body"]["task"])["body"], actor)
    if candidate["body"]["actor"] != actor or not audience["can_correct"] or audience["view"] != "analysis":
        raise PermissionError("This audience cannot review this candidate")
    if decision not in ("accepted", "rejected") or not isinstance(reason, str) or not reason.strip() or len(reason) > 1000:
        raise ValueError("Candidate review needs a decision and a bounded reason")
    if decision == "accepted":
        if candidate["body"]["run"]["status"] != "candidate":
            raise ValueError("A failed sandbox candidate cannot be accepted")
        validate_layout(candidate["body"]["run"]["result"], candidate["body"]["snapshot"])
    body = {"candidate": candidate["sha256"], "actor": actor, "decision": decision, "reason": reason}
    with store.connection.transaction():
        store.lock()
        return store.find("artifact_candidate_review", digest(body)) or store.put("artifact_candidate_review", digest(body), body, at, [candidate["sha256"]])


def render_candidate(candidate, reviews=(), interactive=True, semantic_note=None):
    body, esc = candidate["body"], html.escape
    modes = ", ".join(sorted({r.get("implementation_mode", "unverified") for r in body["snapshot"]["rows"]})) or "unavailable"
    if semantic_note:
        modes += " · "+semantic_note
    destination = "/" if interactive else "Report.html"
    content = f"<p class='tag'>SYNTHETIC DATA · GENERATED VIEW CANDIDATE<br>Predictors: {esc(modes)}</p><h1>Inspect a generated view</h1><p><a href='{destination}'>Return to report</a></p>"
    matching = [r for r in reviews if r["body"]["candidate"] == candidate["sha256"]]
    content += "<section><h2>Review status</h2>" + ("".join(f"<p>{esc(r['body']['decision'])}: {esc(r['body']['reason'])}</p>" for r in matching) or "<p>Pending local review. No external publication.</p>") + "</section>"
    if body["run"]["status"] == "candidate":
        layout = body["run"]["result"]
        validate_layout(layout, body["snapshot"])
        rows = {r["source"]: r for r in body["snapshot"]["rows"]}
        content += f"<section><h2>{esc(layout['title'])}</h2><p>Generated title and row selection require human review. Displayed values come directly from approved evidence.</p><p class='scroll-note'>On a narrow screen, swipe the table or focus it and use the arrow keys to see every column.</p><div class='scroll' role='region' aria-label='Generated view table' tabindex='0'><table><caption>Generated selection of accepted report rows</caption><thead><tr>"
        content += "".join(f"<th scope='col'>{esc(COLUMNS[c])}</th>" for c in layout["columns"]) + "</tr></thead><tbody>"
        for source in layout["sources"]:
            content += "<tr>"
            for column in layout["columns"]:
                value = rows[source][column]
                shown = f"{value:.3g}" if isinstance(value, float) else str(value)
                content += f"<td{' class=wrap' if column == 'source' else ''}>{esc(shown)}</td>"
            content += "</tr>"
        content += "</tbody></table></div></section>"
    else:
        content += f"<section><h2>Candidate rejected</h2><p>{esc(body['run']['stop_reason'] or 'Sandbox failed')}</p></section>"
    content += f"<section><h2>Source and execution</h2><details><summary>Inspect generated Python and bounded logs</summary><pre>{esc(body['run']['source'])}</pre><pre>{esc(body['run']['stdout'])}</pre><pre>{esc(body['run']['stderr'])}</pre></details></section>"
    if not interactive:
        return page("Generated view export", content + "<p>Read-only export. Local review records are retained above.</p>")
    content += (f"<section><h2>Review this candidate</h2><form method='post' action='/candidate-review'><input type='hidden' name='candidate' value='{candidate['sha256']}'>"
                f"<input type='hidden' name='artifact' value='{body['artifact']}'>"
                "<label for='decision'>Decision</label><select id='decision' name='decision'><option value='rejected'>Reject</option>"
                + ("<option value='accepted'>Accept for local use</option>" if body["run"]["status"] == "candidate" else "")
                + "</select><label for='reason'>Review reason</label><textarea id='reason' name='reason' required maxlength='1000'></textarea><button>Save candidate review</button></form></section>")
    return page("Generated view review", content)
