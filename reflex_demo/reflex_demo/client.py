"""Thin client: both frontends use the same server-owned records and reviews."""
import json
from urllib.error import HTTPError
from urllib.parse import quote
from urllib.request import Request, urlopen

BASE = "http://127.0.0.1:2041/api"


def read_workspace():
    with urlopen(BASE + "/workspace", timeout=5) as response:
        return json.load(response)


def write_decision(case_id, decision, reason, revision, source_sha256):
    request = Request(BASE + "/cases/" + quote(case_id, safe="") + "/decision", method="PUT", data=json.dumps({"decision": decision, "reason": reason, "expected_revision": revision, "expected_source_sha256": source_sha256}).encode(), headers={"Content-Type": "application/json"})
    try:
        with urlopen(request, timeout=5) as response:
            return json.load(response)
    except HTTPError as error:
        message = json.load(error).get("error", "Save failed. Try again.")
        raise ValueError(message) from error
