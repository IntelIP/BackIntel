"""Thin client: both frontends use the same server-owned records and reviews."""
import json
import os
from urllib.error import HTTPError
from urllib.parse import quote, urlsplit
from urllib.request import Request, urlopen

def api_origin(value):
    parsed = urlsplit(value)
    if (parsed.scheme != "http" or parsed.hostname not in ("127.0.0.1", "localhost")
            or parsed.username or parsed.password or parsed.path not in ("", "/")
            or parsed.query or parsed.fragment or not parsed.port or not 1 <= parsed.port <= 65535):
        raise ValueError("The demonstration API must be an HTTP loopback origin with a port")
    return value.rstrip("/")


BASE = api_origin(os.environ.get("BACKINTEL_WORKSPACE_API_ORIGIN", "http://127.0.0.1:2041")) + "/api"


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
