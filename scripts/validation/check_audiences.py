"""Exercise actual scoped HTTP reports and human actions on synthetic fixtures."""

from __future__ import annotations

import json
import os
from pathlib import Path
import threading
import time
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, urlopen
import uuid

import psycopg

from runtime.artifacts import create_artifacts, get_artifact
from runtime.audience_server import AudienceServer, issue_grants
from runtime.bootstrap import initialize
from runtime.capability_pipeline import bootstrap
from runtime.contracts import register_task
from runtime.evidence import Evidence
from runtime.generated_artifacts import create_candidate, review_candidate
from runtime.ledger import dsn
from runtime.simulation import encoded
from runtime.synthetic import history

OUTPUT = Path(__file__).resolve().parents[2] / "artifacts/validation/Audiences"


def request(server, path, token=None, form=None, origin=None):
    headers = {"Authorization": "Bearer " + token} if token else {}
    data = None
    if form is not None:
        data = urlencode(form).encode()
        headers["Content-Type"] = "application/x-www-form-urlencoded"
    if origin:
        headers["Origin"] = origin
    try:
        with urlopen(Request(server.origin + path, headers=headers, data=data), timeout=10) as response:
            return response.status, response.read()
    except HTTPError as exc:
        return exc.code, exc.read()


def main():
    OUTPUT.mkdir(parents=True, exist_ok=True)
    run_id = uuid.uuid4().hex[:12]
    receipt = {"schema": "backintel-audience-check/v1", "candidate": "uncommitted-working-tree",
               "model_execution": "simulated", "http_execution": "real", "paid_provider_calls": 0,
               "status": "running", "checks": [], "tasks": []}
    receipt_path = OUTPUT / (run_id + ".json")
    server = None

    def check(name, predicate):
        receipt["checks"].append({"name": name, "passed": bool(predicate)})
        receipt_path.write_bytes(encoded(receipt))
        if not predicate:
            raise AssertionError(name)

    try:
        if not os.environ.get("BACKINTEL_TEST_DATABASE_URL") or os.environ["BACKINTEL_TEST_DATABASE_URL"] != dsn():
            raise PermissionError("Audience checks require an isolated test database")
        initialize()
        with psycopg.connect(dsn(), autocommit=True) as connection:
            for scenario in ("support", "equipment"):
                task, _, _ = history(scenario)
                task["id"] = scenario + "-views-" + run_id
                task["audiences"].append({"id": "empty", "view": "briefing", "entities": ["NoRecords"], "can_correct": False})
                store = Evidence(connection, task["id"])
                task_record = register_task(store, task)
                result = bootstrap(store, task_record, scenario)
                before = len(store.list("artifact"))
                create_artifacts(store, task_record, result)
                check(scenario + ":replay_deduplicates_artifacts", before == len(store.list("artifact")) == 4)
                receipt["tasks"].append(task["id"])
            grants = issue_grants(connection, receipt["tasks"])
            server = AudienceServer(dsn(), grants, 0)
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            check("unauthenticated_access_denied", request(server, "/")[0] == 403)
            check("invalid_token_denied", request(server, "/artifact.json", "invalid")[0] == 403)
            for task_id in receipt["tasks"]:
                tokens = {g["audience"]: g["token"] for g in grants if g["task_id"] == task_id}
                store = Evidence(connection, task_id)
                manager = get_artifact(store, "manager")
                operator = get_artifact(store, "operator")
                check(task_id + ":manager_scoped_to_one_entity", len(manager["body"]["rows"]) == 1)
                check(task_id + ":operator_sees_two_entities", len(operator["body"]["rows"]) == 2)
                status, raw = request(server, "/artifact.json", tokens["manager"])
                check(task_id + ":manager_http_projection", status == 200 and json.loads(raw) == manager)
                other = next(r for r in operator["body"]["rows"] if r["entity"] != manager["body"]["rows"][0]["entity"])
                check(task_id + ":other_entity_not_in_json", other["entity"].encode() not in raw)
                check(task_id + ":evidence_scope_enforced", request(server, "/evidence/" + other["source"], tokens["manager"])[0] == 403)
                check(task_id + ":artifact_scope_enforced", request(server, "/versions/" + operator["sha256"], tokens["manager"])[0] == 403)
                csv_status, csv_body = request(server, "/export.csv", tokens["manager"])
                check(task_id + ":csv_scope_enforced", csv_status == 200 and other["entity"].encode() not in csv_body)
                check(task_id + ":empty_state", b"No visible records" in request(server, "/", tokens["empty"])[1])
                form = {"artifact": manager["sha256"], "decision": "accepted", "reason": "fixture"}
                check(task_id + ":manager_review_denied", request(server, "/review", tokens["manager"], form)[0] == 403)
                form["artifact"] = operator["sha256"]
                check(task_id + ":cross_origin_change_denied", request(server, "/review", tokens["operator"], form, "https://outside.invalid")[0] == 403)
                check(task_id + ":operator_review_saved", request(server, "/review", tokens["operator"], form)[0] == 200)
                count = len(store.list("artifact_review"))
                check(task_id + ":review_replay", request(server, "/review", tokens["operator"], form)[0] == 200 and len(store.list("artifact_review")) == count)
                observation = operator["body"]["rows"][0]["observations"][0]
                form = {"artifact": operator["sha256"], "observation": observation["sha256"], "supersedes": "", "value": "unknown", "reason": "Source needs human clarification"}
                check(task_id + ":manager_correction_denied", request(server, "/correct", tokens["manager"], {**form, "artifact": manager["sha256"]})[0] == 403)
                old_sources = [r["sha256"] for r in store.list("source")]
                check(task_id + ":operator_correction_refreshes", request(server, "/correct", tokens["operator"], form)[0] == 200)
                updated = get_artifact(store, "operator")
                check(task_id + ":new_report_version", updated["sha256"] != operator["sha256"])
                check(task_id + ":correction_visible", any(o["response"]["status"] == "unknown" and o["correction"] for r in updated["body"]["rows"] for o in r["observations"]))
                check(task_id + ":sources_preserved", old_sources == [r["sha256"] for r in store.list("source")])
                check(task_id + ":old_report_retained", request(server, "/versions/" + operator["sha256"], tokens["operator"])[0] == 200)
                old_prediction = operator["body"]["rows"][0]["prediction"]["sha256"]
                check(task_id + ":old_evidence_retained", request(server, "/evidence/" + old_prediction + "?artifact=" + operator["sha256"], tokens["operator"])[0] == 200)
                check(task_id + ":stale_form_denied", request(server, "/correct", tokens["operator"], form)[0] == 400)
                source = '''import json
s=json.load(open("/input/snapshot.json"))
rows=sorted(s["rows"],key=lambda row: row["prediction"] if row["prediction"] is not None else -1,reverse=True)
print(json.dumps({"schema":"backintel-generated-layout/v1","title":"Predicted outcomes in descending order","columns":["entity","prediction","target_at","attention"],"sources":[r["source"] for r in rows]}))
'''
                candidate = create_candidate(store, updated, "operator", source)
                check(task_id + ":generated_code_really_executed", candidate["body"]["run"]["status"] == "candidate" and candidate["body"]["run"]["cleanup_confirmed"])
                check(task_id + ":candidate_replay", create_candidate(store, updated, "operator", source) == candidate)
                check(task_id + ":candidate_preview", request(server, "/candidate/" + candidate["sha256"], tokens["operator"])[0] == 200)
                check(task_id + ":candidate_audience_boundary", request(server, "/candidate/" + candidate["sha256"], tokens["manager"])[0] == 403)
                candidate_form = {"artifact": updated["sha256"], "candidate": candidate["sha256"], "decision": "accepted", "reason": "Simulated operator checked the layout against its source rows"}
                check(task_id + ":candidate_review_persisted", request(server, "/candidate-review", tokens["operator"], candidate_form)[0] == 200)
                bad_source = 'import json\nprint(json.dumps({"schema":"backintel-generated-layout/v1","title":"Bad references","columns":["entity"],"sources":["unapproved"]}))'
                rejected = create_candidate(store, updated, "operator", bad_source)
                check(task_id + ":invented_source_rejected", rejected["body"]["run"]["status"] == "rejected")
                denied = False
                try:
                    review_candidate(store, rejected, "operator", "accepted", "fixture", updated["available_at"] + 1)
                except ValueError:
                    denied = True
                check(task_id + ":failed_candidate_cannot_be_accepted", denied)
                (OUTPUT / (task_id + ".html")).write_bytes(request(server, "/", tokens["operator"])[1])
            expired = issue_grants(connection, receipt["tasks"][:1], lifetime=-1)
            from hashlib import sha256
            server.grants[sha256(expired[0]["token"].encode()).hexdigest()] = expired[0]
            check("expired_token_denied", request(server, "/", expired[0]["token"])[0] == 403)
            # Private local browser fixture, excluded from Git along with other validation artifacts.
            private = OUTPUT / (run_id + "-access.json")
            with os.fdopen(os.open(private, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600), "wb") as output:
                output.write(encoded({"grants": grants, "database": dsn(), "tasks": receipt["tasks"]}))
            receipt["browser_fixture"] = str(private)
            receipt["status"] = "passed"
    except Exception as exc:
        receipt.update(status="blocked" if isinstance(exc, PermissionError) else "failed", error={"type": type(exc).__name__, "message": str(exc)})
        raise
    finally:
        if server:
            server.shutdown()
            server.server_close()
        receipt_path.write_bytes(encoded(receipt))
        print(json.dumps({"status": receipt["status"], "checks": len(receipt["checks"]), "receipt": str(receipt_path)}))


if __name__ == "__main__":
    main()
