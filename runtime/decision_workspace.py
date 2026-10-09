"""Loopback demo API for shared decision records and durable human reviews.

Public issue text is read from retained evidence outside Git. Equipment records
are explicitly simulated. No model, network collection, or paid inference runs.
"""

import argparse
from copy import deepcopy
from contextlib import closing
from datetime import datetime, timezone
import hashlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import math
import re
from pathlib import Path
import sqlite3
from threading import RLock
from urllib.parse import unquote, urlsplit

SCHEMA = "backintel-decision-workspace/v1"
DECISIONS = {"follow_up", "no_action", "need_more_information"}
DEFAULT_SOURCE = Path.home() / "Library/Application Support/BackIntel/Evidence/IssuePredictionTest"


class Conflict(ValueError):
    """A newer decision exists; the caller must reload it."""


def fingerprint(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def decision_context(case):
    # Bind review to everything shown before the decision, not a later outcome.
    return fingerprint({key: value for key, value in case.items()
                        if key not in ('review', 'history', 'outcome', 'context_sha256')})


def preview(text):
    """Readable excerpt only; original source text stays intact in evidence."""
    text = re.sub(r"<!--.*?-->", "", text, flags=re.DOTALL)
    text = re.sub(r"!\[[^\]]*\]\([^)]*\)", "[Image attached]", text)
    text = re.sub(r"</?(?:b|strong|p|br|div)\b[^>]*>", " ", text)
    return " ".join(text.split())[:240] or "Read the original source record."


def simulated_cases():
    """Small portable fixtures for demonstrating a second workflow."""
    cases = []
    for index, (title, reading, text) in enumerate([
        ("Vibration changed on pump P-17", "6.4 mm/s", "Pump P-17 vibration increased from 3.1 to 6.4 mm/s. Inspection has not been recorded."),
        ("Temperature drift on compressor C-04", "82 °C", "Compressor C-04 temperature rose from 71 to 82 °C over three simulated readings."),
        ("Repeated pressure drop on line L-08", "2.6 bar", "Line L-08 pressure fell below its simulated 3.0 bar reference twice."),
    ]):
        created = f"2024-02-01T0{index + 1}:00:00Z"
        cases.append({
            "id": f"EQ-{17 + index}", "workflow": "equipment", "title": title,
            "summary": text, "created_at": created, "source_kind": "Sensor replay",
            "simulated": True,
            "facts": [{"label": "Observed value", "value": reading}, {"label": "Data", "value": "Simulated"}, {"label": "Recorded", "value": "Feb 1, 2024"}],
            "finding": {"status": "Simulated interpretation", "text": "Check the original reading and ask the equipment owner whether an inspection is needed. This is an illustrative review suggestion."},
            "prediction": {"status": "simulated", "explanation": "No equipment prediction model ran. This workflow demonstrates the shared review template.", "estimates": {}},
            "evidence": {"text": text, "url": None, "sha256": fingerprint(text), "collected_at": created},
            "review": None, "outcome": {"text": "Simulated later outcome: the owner inspected the equipment and recorded a maintenance decision.", "available_at": "2024-02-08T12:00:00Z"},
        })
    return cases


def issue_cases(source):
    cohort_bytes = (source / "cohort.json").read_bytes()
    cohort = json.loads(cohort_bytes)
    predictions = json.loads((source / "predictions.json").read_text())
    if predictions.get("cohort_sha256") != hashlib.sha256(cohort_bytes).hexdigest():
        raise ValueError("Predictions do not belong to this retained issue cohort")
    rows = cohort["holdout"]
    scores = predictions.get("cases", [])
    if [score["number"] for score in scores] != [row["number"] for row in rows]:
        raise ValueError("Prediction case identities or order do not match the retained issues")
    cases = []
    probabilities = predictions["probabilities"]
    if not probabilities or any(len(values) != len(rows) for values in probabilities.values()):
        raise ValueError("Each prediction method must score every retained issue")
    for index, row in enumerate(rows):
        original = row["original"]
        text = original.get("body") or "No opening text was recorded."
        title = original["title"]
        estimates = {name: float(values[index]) for name, values in probabilities.items()}
        if any(not math.isfinite(value) or not 0 <= value <= 1 for value in estimates.values()):
            raise ValueError("Issue prediction probabilities must be finite values from zero to one")
        if estimates != scores[index]["probabilities"]:
            raise ValueError("Prediction vectors disagree with their issue records")
        url = row["url"]
        if not url.startswith("https://github.com/"):
            raise ValueError("Issue evidence must reference the retained public GitHub source")
        cases.append({
            "id": f"GH-{row['number']}", "workflow": "issues", "title": title,
            "summary": preview(text), "created_at": row["created_at"],
            "source_kind": "GitHub issue", "simulated": False,
            "facts": [{"label": "Opened", "value": row["created_at"][:10]}, {"label": "Opening text", "value": f"{len(text)} characters"}, {"label": "Source", "value": "Archived public record"}],
            "finding": {"status": "Rule-based review suggestion", "text": "Review the opening report and confirm whether follow-up is needed. Text interpretation by a language model has not run for this case."},
            "prediction": {"status": "experimental", "explanation": "Real local models estimated whether the issue would remain open without a qualifying maintainer reply after seven days. Neither beat the simple baseline on seven test cases; these estimates do not drive decisions.", "estimates": estimates},
            "evidence": {"text": text, "url": url, "sha256": row["original_sha256"], "collected_at": row["created_at"]},
            "review": None,
            "outcome": {"text": f"At the seven-day deadline, the archived issue was {row['state_at_deadline']}. Qualifying maintainer comments recorded: {len(row['qualifying_comments'])}. This does not prove what happened outside the archive.", "available_at": row["outcome_available_at"]},
        })
    return cases


def load_cases(source):
    equipment = simulated_cases()
    if source is not None:
        return sorted(issue_cases(source) + equipment, key=lambda item: item["created_at"]), "retained-public-issue-evidence"
    # Portable simulation used by unit checks or hosts without the retained data.
    titles = ["Payment failure at checkout", "Account export did not finish", "Duplicate notification received"]
    issues = []
    for index, title in enumerate(titles):
        item = deepcopy(equipment[index])
        item.update(id=f"DEMO-{284 + index}", workflow="issues", title=title, source_kind="Simulated issue")
        item["summary"] = f"Simulated opening report: {title.lower()}."
        item["evidence"].update(text=item["summary"], sha256=fingerprint(item["summary"]))
        item["facts"] = [{"label": "Data", "value": "Simulated"}, {"label": "Opened", "value": "Feb 1, 2024"}]
        item["finding"] = {"status": "Simulated interpretation", "text": "Check the source report and confirm whether a follow-up is needed. This is a simulated finding."}
        item["prediction"] = {"status": "simulated", "explanation": "No model ran on this simulated case.", "estimates": {}}
        item["outcome"]["text"] = "Simulated later outcome: the owner reviewed the report and resolved the case."
        issues.append(item)
    return issues + equipment, "simulated-template-data"


class DecisionStore:
    def __init__(self, database, cases, packet_path=None):
        self._lock = RLock()
        self.database = Path(database)
        self.packet_path = Path(packet_path) if packet_path is not None else None
        self.demo = None
        self.database.parent.mkdir(parents=True, exist_ok=True)
        self.cases = {case["id"]: deepcopy(case) for case in cases}
        with closing(self.connect()) as connection, connection:
            connection.execute("PRAGMA journal_mode=WAL")
            connection.execute("""CREATE TABLE IF NOT EXISTS reviews (
                case_id TEXT NOT NULL, revision INTEGER NOT NULL,
                decision TEXT NOT NULL, reason TEXT NOT NULL, recorded_at TEXT NOT NULL,
                PRIMARY KEY (case_id, revision))""")
            if "source_sha256" not in {row["name"] for row in connection.execute("PRAGMA table_info(reviews)")}:
                connection.execute("ALTER TABLE reviews ADD COLUMN source_sha256 TEXT")
            if "context_sha256" not in {row["name"] for row in connection.execute("PRAGMA table_info(reviews)")}:
                connection.execute("ALTER TABLE reviews ADD COLUMN context_sha256 TEXT")

    def connect(self):
        connection = sqlite3.connect(self.database, timeout=5)
        connection.row_factory = sqlite3.Row
        return connection

    def case(self, case_id):
        with self._lock:
            if case_id not in self.cases:
                raise KeyError("Case not found")
            item = deepcopy(self.cases[case_id])
            item["context_sha256"] = decision_context(item)
            with closing(self.connect()) as connection, connection:
                rows = connection.execute("SELECT decision,reason,revision,recorded_at FROM reviews WHERE case_id=? AND context_sha256=? ORDER BY revision DESC", (case_id, item["context_sha256"])).fetchall()
            item["history"] = [dict(row) for row in rows]
            item["review"] = item["history"][0] if rows else None
            if not rows:
                item["outcome"] = None
            return item

    def refresh_packet(self):
        with self._lock:
            if self.packet_path is None:
                return
            packet = json.loads(self.packet_path.read_text())
            if packet.get("schema") != SCHEMA or not isinstance(packet.get("cases"), list):
                raise ValueError("Invalid demonstration packet")
            cases = {}
            for case in packet["cases"]:
                if case["id"] in cases or not re.fullmatch(r"[a-f0-9]{64}", case["evidence"]["sha256"]):
                    raise ValueError("Demonstration source identities must be unique and fingerprinted")
                if any(type(value) not in (int, float) or not math.isfinite(value) or not 0 <= value <= 1
                       for value in case["prediction"]["estimates"].values()):
                    raise ValueError("Demonstration estimates must be finite probabilities")
                cases[case["id"]] = deepcopy(case)
            self.cases, self.demo = cases, packet.get("demo")

    def workspace(self, source_mode):
        with self._lock:
            self.refresh_packet()
            packet = {"schema": SCHEMA, "cases": [self.case(case_id) for case_id in self.cases], "source_mode": source_mode}
            if self.demo is not None:
                packet["demo"] = self.demo
            return packet

    def decide(self, case_id, body):
        with self._lock:
            try:
                self.refresh_packet()
            except (OSError, ValueError, KeyError) as error:
                raise OSError("Source evidence unavailable. Refresh before saving.") from error
            if self.demo and self.demo.get("status") == "unavailable":
                raise OSError("Source evidence unavailable. Refresh before saving.")
            if case_id not in self.cases:
                raise KeyError("Case not found")
            if not isinstance(body, dict) or set(body) != {"decision", "reason", "expected_revision", "expected_context_sha256"}:
                raise ValueError("Decision must include decision, reason, expected_revision, and expected_context_sha256 only")
            if not isinstance(body["decision"], str) or body["decision"] not in DECISIONS:
                raise ValueError("Choose a supported decision")
            if not isinstance(body["reason"], str) or not body["reason"].strip() or len(body["reason"]) > 2000:
                raise ValueError("A reason of 1–2000 characters is required")
            if type(body["expected_revision"]) is not int or body["expected_revision"] < 0:
                raise ValueError("Expected revision must be a nonnegative integer")
            source_sha256 = self.cases[case_id]["evidence"]["sha256"]
            context_sha256 = decision_context(self.cases[case_id])
            if body["expected_context_sha256"] != context_sha256:
                raise Conflict("This case or its analysis changed. Refresh before saving.")
            with closing(self.connect()) as connection, connection:
                connection.execute("BEGIN IMMEDIATE")
                revision = connection.execute("SELECT COALESCE(MAX(revision),0) FROM reviews WHERE case_id=? AND context_sha256=?", (case_id, context_sha256)).fetchone()[0]
                if body["expected_revision"] != revision:
                    raise Conflict("This case changed in another view. Refresh before saving.")
                next_revision = connection.execute("SELECT COALESCE(MAX(revision),0)+1 FROM reviews WHERE case_id=?", (case_id,)).fetchone()[0]
                connection.execute("INSERT INTO reviews (case_id,revision,decision,reason,recorded_at,source_sha256,context_sha256) VALUES (?,?,?,?,?,?,?)", (case_id, next_revision, body["decision"], body["reason"].strip(), datetime.now(timezone.utc).isoformat(), source_sha256, context_sha256))
            return self.case(case_id)


class WorkspaceServer(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self, store, source_mode, port=2041, additional_origins=()):
        self.store, self.source_mode = store, source_mode
        super().__init__(("127.0.0.1", port), WorkspaceHandler)
        self.origins = {f"http://127.0.0.1:{self.server_port}", "http://127.0.0.1:5173", "http://localhost:5173", "http://127.0.0.1:3001", "http://localhost:3001"}
        self.origins.update(additional_origins)


class WorkspaceHandler(BaseHTTPRequestHandler):
    def log_message(self, *_):
        pass

    def send_json(self, status, body):
        encoded = json.dumps(body).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(encoded)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Vary", "Origin")
        origin = self.headers.get("Origin")
        if origin in self.server.origins:
            self.send_header("Access-Control-Allow-Origin", origin)
        self.end_headers()
        self.wfile.write(encoded)

    def allowed(self):
        host = self.headers.get("Host", "").split(":")[0]
        origin = self.headers.get("Origin")
        if host not in {"127.0.0.1", "localhost"} or (origin is not None and origin not in self.server.origins):
            self.send_json(403, {"error": "Only the local demo frontends may access this service"})
            return False
        return True

    def do_GET(self):
        if not self.allowed():
            return
        if urlsplit(self.path).path != "/api/workspace":
            self.send_json(404, {"error": "Not found"})
            return
        try:
            packet = self.server.store.workspace(self.server.source_mode)
        except (OSError, ValueError, KeyError, sqlite3.Error):
            self.send_json(503, {"error": "Workspace evidence unavailable. Try again."})
        else:
            self.send_json(200, packet)

    def do_OPTIONS(self):
        if not self.allowed():
            return
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", self.headers.get("Origin", ""))
        self.send_header("Access-Control-Allow-Methods", "GET, PUT, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Content-Length", "0")
        self.end_headers()

    def do_PUT(self):
        if not self.allowed():
            return
        parts = urlsplit(self.path).path.split("/")
        if len(parts) != 5 or parts[1:3] != ["api", "cases"] or parts[4] != "decision":
            self.send_json(404, {"error": "Not found"})
            return
        try:
            if self.headers.get_content_type() != "application/json":
                raise ValueError("Content-Type must be application/json")
            length = int(self.headers.get("Content-Length", "0"))
            if not 0 < length <= 16384:
                raise ValueError("Invalid request size")
            self.connection.settimeout(5)
            body = json.loads(self.rfile.read(length))
            case = self.server.store.decide(unquote(parts[3]), body)
        except Conflict as error:
            self.send_json(409, {"error": str(error)})
        except KeyError:
            self.send_json(404, {"error": "Case not found"})
        except (ValueError, UnicodeDecodeError) as error:
            self.send_json(400, {"error": str(error)})
        except sqlite3.Error:
            self.send_json(503, {"error": "Review storage is unavailable. Try again."})
        except OSError:
            self.send_json(503, {"error": "Source evidence unavailable. Refresh before saving."})
        else:
            self.send_json(200, case)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--simulation-only", action="store_true")
    parser.add_argument("--database", type=Path, default=Path.home() / "Library/Application Support/BackIntel/DecisionWorkspace/Reviews.sqlite3")
    parser.add_argument("--port", type=int, default=2041)
    args = parser.parse_args()
    source = None if args.simulation_only else args.source
    if source is not None and not (source / "cohort.json").exists():
        parser.error("Retained evidence not found. Supply --source or explicitly choose --simulation-only.")
    cases, mode = load_cases(source)
    server = WorkspaceServer(DecisionStore(args.database, cases), mode, args.port)
    print(f"Decision API: http://127.0.0.1:{server.server_port} · {mode}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
