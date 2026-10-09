"""Loopback-only stakeholder access. Tokens bind a task version and audience."""

from __future__ import annotations

import hashlib
from http.cookies import SimpleCookie
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import secrets
import time
from urllib.parse import parse_qs, urlsplit

import psycopg

from runtime.artifacts import audience_for, export_csv, get_artifact, page, render, review_artifact, visible_evidence
from runtime.evidence import Evidence
from runtime.observations import correct_observation
from runtime.simulation import digest, encoded


def issue_grants(connection, task_ids: list[str], lifetime=3600) -> list[dict]:
    grants = []
    for task_id in task_ids:
        store = Evidence(connection, task_id)
        tasks = store.list("task")
        if not tasks:
            raise ValueError("Task has no registered contract")
        task = max(tasks, key=lambda r: r["available_at"])
        for audience in task["body"]["audiences"]:
            grants.append({"task_id": task_id, "task_sha256": task["sha256"], "audience": audience["id"],
                           "token": secrets.token_urlsafe(32), "expires_at": time.time() + lifetime})
    return grants


class AudienceServer(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self, database: str, grants: list[dict], port=2028):
        self.database = database
        self.grants = {hashlib.sha256(g["token"].encode()).hexdigest(): {k: v for k, v in g.items() if k != "token"} for g in grants}
        super().__init__(("127.0.0.1", port), AudienceHandler)
        self.origin = f"http://127.0.0.1:{self.server_address[1]}"


class AudienceHandler(BaseHTTPRequestHandler):
    def log_message(self, *_):
        # Do not persist authorization values, URL input or source data in access logs.
        pass

    def setup(self):
        super().setup()
        self.connection.settimeout(5)

    def reply(self, status: int, body: bytes, content_type="text/html; charset=utf-8", headers=()):
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "same-origin")
        self.send_header("Content-Security-Policy", "default-src 'none'; style-src 'unsafe-inline'; form-action 'self'; frame-ancestors 'none'; base-uri 'none'")
        for key, value in headers:
            self.send_header(key, value)
        self.end_headers()
        self.wfile.write(body)

    def principal(self, token=None):
        if token is None:
            authorization = self.headers.get("Authorization", "")
            token = authorization[7:] if authorization.startswith("Bearer ") else None
            if token is None:
                cookies = SimpleCookie()
                cookies.load(self.headers.get("Cookie", ""))
                token = cookies["backintel_audience"].value if "backintel_audience" in cookies else ""
        grant = self.server.grants.get(hashlib.sha256(token.encode()).hexdigest())
        if grant is None or grant["expires_at"] <= time.time():
            raise PermissionError("A valid, unexpired audience access token is required")
        return grant

    def guard_host(self):
        if self.headers.get("Host") != self.server.origin.removeprefix("http://"):
            raise PermissionError("Only the configured loopback origin is allowed")

    def scoped_artifact(self, store, grant, sha=None):
        artifact = get_artifact(store, grant["audience"], sha, task_sha=grant["task_sha256"])
        if artifact["body"]["task"] != grant["task_sha256"]:
            raise PermissionError("Access token belongs to another task version")
        return artifact

    def do_GET(self):
        try:
            self.guard_host()
            path = urlsplit(self.path).path
            query = parse_qs(urlsplit(self.path).query, max_num_fields=1)
            if any(key != "artifact" or len(values) != 1 for key, values in query.items()):
                raise ValueError("Unsupported report query")
            if path == "/login":
                content = ("<h1>Open your report</h1><p>Use the local access token issued for your audience. It grants access to one task and audience.</p>"
                           "<form method='post' action='/session'><label for='token'>Audience access token</label>"
                           "<input type='password' id='token' name='token' required autocomplete='off'><p><button>Open report</button></p></form>")
                return self.reply(200, page("Sign in", content).encode())
            grant = self.principal()
            with psycopg.connect(self.server.database, autocommit=True) as connection:
                store = Evidence(connection, grant["task_id"])
                artifact = self.scoped_artifact(store, grant, query.get("artifact", [None])[0])
                if path == "/":
                    document = render(artifact, store.list("artifact_review"))
                    candidates = [r for r in store.list("artifact_candidate") if r["body"]["artifact"] == artifact["sha256"]]
                    if candidates:
                        links = "<section><h2>Generated view candidates</h2>" + "".join(f"<p><a href='/candidate/{r['sha256']}'>Inspect candidate {i + 1}</a></p>" for i, r in enumerate(candidates)) + "</section>"
                        document = document.replace("</main>", links + "</main>")
                    return self.reply(200, document.encode())
                if path == "/artifact.json":
                    return self.reply(200, encoded(artifact), "application/json")
                if path == "/export.csv":
                    return self.reply(200, export_csv(artifact).encode(), "text/csv; charset=utf-8",
                                      [("Content-Disposition", 'attachment; filename="backintel-report.csv"')])
                if path.startswith("/evidence/"):
                    return self.reply(200, encoded(visible_evidence(artifact, path.removeprefix("/evidence/"))), "application/json")
                if path.startswith("/versions/"):
                    version = self.scoped_artifact(store, grant, path.removeprefix("/versions/"))
                    return self.reply(200, render(version, store.list("artifact_review")).encode())
                if path.startswith("/candidate/"):
                    from runtime.generated_artifacts import render_candidate, scoped_candidate
                    record = store.get(path.removeprefix("/candidate/"))
                    if record["kind"] != "artifact_candidate":
                        raise PermissionError("Not a generated view candidate")
                    artifact = self.scoped_artifact(store, grant, record["body"]["artifact"])
                    candidate = scoped_candidate(store, artifact, path.removeprefix("/candidate/"))
                    return self.reply(200, render_candidate(candidate, store.list("artifact_candidate_review")).encode())
                raise LookupError("Page not found")
        except PermissionError as exc:
            self.error_page(403, str(exc))
        except LookupError as exc:
            self.error_page(404, str(exc))
        except ValueError:
            self.error_page(400, "Invalid report request")
        except psycopg.Error:
            self.error_page(503, "Report storage is temporarily unavailable. Retry later.")

    def do_POST(self):
        try:
            self.guard_host()
            origin = self.headers.get("Origin")
            if origin and origin != self.server.origin:
                raise PermissionError("Cross-origin changes are not allowed")
            if not origin and not self.headers.get("Authorization", "").startswith("Bearer "):
                raise PermissionError("Browser changes require the local report origin")
            size = int(self.headers.get("Content-Length", "0"))
            if not 0 < size <= 16384 or self.headers.get_content_type() != "application/x-www-form-urlencoded":
                raise ValueError("Invalid form body")
            fields = parse_qs(self.rfile.read(size).decode(), keep_blank_values=True, max_num_fields=10)
            if any(len(v) != 1 for v in fields.values()):
                raise ValueError("Duplicate fields are not allowed")
            form = {k: v[0] for k, v in fields.items()}
            path = urlsplit(self.path).path
            if path == "/session":
                if set(form) != {"token"}:
                    raise ValueError("Invalid login")
                self.principal(form["token"])
                return self.reply(303, b"", headers=[("Location", "/"), ("Set-Cookie", f"backintel_audience={form['token']}; Path=/; HttpOnly; SameSite=Strict; Max-Age=3600")])
            grant = self.principal()
            with psycopg.connect(self.server.database, autocommit=True) as connection:
                store = Evidence(connection, grant["task_id"])
                with connection.transaction():
                    store.lock()
                    artifact = self.scoped_artifact(store, grant, form.get("artifact"))
                    latest = self.scoped_artifact(store, grant)
                    if artifact["sha256"] != latest["sha256"]:
                        raise ValueError("Report changed. Reload before making a change.")
                    at = latest["available_at"] + 1
                    if path == "/review" and set(form) == {"artifact", "decision", "reason"}:
                        review_artifact(store, artifact, grant["audience"], form["decision"], form["reason"], at)
                    elif path == "/candidate-review" and set(form) == {"artifact", "candidate", "decision", "reason"}:
                        from runtime.generated_artifacts import review_candidate, scoped_candidate
                        candidate = scoped_candidate(store, artifact, form["candidate"])
                        review_candidate(store, candidate, grant["audience"], form["decision"], form["reason"], at)
                    elif path == "/correct" and set(form) == {"artifact", "observation", "supersedes", "value", "reason"}:
                        task_record = store.get(grant["task_sha256"])
                        audience = audience_for(task_record["body"], grant["audience"])
                        if not audience["can_correct"]:
                            raise PermissionError("This audience cannot correct observations")
                        observation = visible_evidence(artifact, form["observation"])
                        if observation["kind"] != "observation":
                            raise ValueError("Choose an original observation")
                        value = form["value"]
                        if value == "unknown":
                            response = {"status": "unknown", "value": None, "distribution": None, "reason": form["reason"]}
                        elif observation["body"]["question"]["type"] == "boolean":
                            if value not in ("true", "false"):
                                raise ValueError("Boolean correction requires true, false or unknown")
                            response = {"status": "known", "value": value == "true", "distribution": {"true": int(value == "true"), "false": int(value == "false")}, "reason": form["reason"]}
                        else:
                            response = {"status": "known", "value": float(value), "distribution": None, "reason": form["reason"]}
                        correction = correct_observation(store, observation["sha256"], response, grant["audience"], form["reason"], at, form["supersedes"] or None)
                        from runtime.capability_pipeline import refresh
                        from runtime.prediction import invalidate_predictions
                        invalidate_predictions(store, observation["body"]["source"], correction, at)
                        event = store.put("event", digest(["audience-correction", correction["sha256"]]),
                                          {"operation": "audience_correction", "actor": grant["audience"]}, at, [correction["sha256"]])
                        refresh(store, task_record, event, at, observe=True,
                                entities=[store.get(observation["body"]["source"])["body"]["entity"]])
                    else:
                        raise ValueError("Invalid review or correction request")
            return self.reply(303, b"", headers=[("Location", "/")])
        except PermissionError as exc:
            self.error_page(403, str(exc))
        except (ValueError, KeyError, UnicodeError) as exc:
            self.error_page(400, str(exc))
        except LookupError as exc:
            self.error_page(404, str(exc))
        except psycopg.Error:
            self.error_page(503, "Report storage is temporarily unavailable. Retry later.")

    def error_page(self, status, message):
        import html
        self.reply(status, page("Report unavailable", f"<h1>Report unavailable</h1><p>{html.escape(message)}</p><p><a href='/login'>Sign in</a> · <a href='/'>Return to report</a></p>").encode())
