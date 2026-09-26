#!/usr/bin/env python3
"""Submit a mock partition, then inspect it in a separate process after disconnect."""
import argparse
import hashlib
import json
import time
import urllib.error
import urllib.request
from pathlib import Path

BASE = "http://127.0.0.1:2026"


def request(method, path, body=None):
    req = urllib.request.Request(
        BASE + path,
        data=json.dumps(body).encode() if body is not None else None,
        method=method,
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=10) as response:
        return json.load(response)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["submit", "inspect"])
    parser.add_argument("--evidence", required=True, type=Path)
    parser.add_argument("--partition", default="mock-olist-partition-001")
    args = parser.parse_args()
    if args.action == "submit":
        thread = request("POST", "/threads", {})
        run = request("POST", f'/threads/{thread["thread_id"]}/runs', {
            "assistant_id": "olist_fixture",
            "input": {"partition_id": args.partition, "record_count": 7, "delay_seconds": 10},
        })
        if run["status"] not in ("pending", "running"):
            raise RuntimeError(f'Run was not admitted as background work: {run["status"]}')
        payload = {"thread_id": thread["thread_id"], "run_id": run["run_id"],
                   "submitted_status": run["status"], "partition_id": args.partition}
        args.evidence.parent.mkdir(parents=True, exist_ok=True)
        args.evidence.write_text(json.dumps(payload, indent=2) + "\n")
        print(json.dumps(payload))
        return
    record = json.loads(args.evidence.read_text())
    path = f'/threads/{record["thread_id"]}/runs/{record["run_id"]}'
    for _ in range(60):
        run = request("GET", path)
        if run["status"] in ("success", "error", "interrupted", "cancelled"):
            break
        time.sleep(1)
    else:
        raise TimeoutError("Background run did not reach a terminal state within 60 seconds")
    expected = hashlib.sha256(f'{record["partition_id"]}:7'.encode()).hexdigest()
    if run["status"] != "success" or run["output"].get("processed_count") != 7 or run["output"].get("digest") != expected:
        raise AssertionError(f"Background output was not the deterministic fixture result: {run}")
    record.update({"final_status": run["status"], "output": run["output"]})
    args.evidence.write_text(json.dumps(record, indent=2) + "\n")
    print(json.dumps(record))


if __name__ == "__main__":
    main()
