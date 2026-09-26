#!/usr/bin/env python3
"""Submit or inspect a bounded Jev review batch through the local Aegra API."""
from __future__ import annotations

import argparse
import json
import time
import urllib.request
from pathlib import Path

BASE = "http://127.0.0.1:2026"


def request(method: str, path: str, body: dict | None = None, *, base: str = BASE) -> dict:
    req = urllib.request.Request(
        base.rstrip("/") + path,
        data=json.dumps(body).encode("utf-8") if body is not None else None,
        method=method,
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=15) as response:
        return json.load(response)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("submit", "inspect"))
    parser.add_argument("--evidence", type=Path, required=True)
    parser.add_argument("--sample", type=Path, help="unlabeled reference sample JSON; submit uses its IDs only")
    parser.add_argument("--partition", default="olist-jev-review-demo-v1")
    parser.add_argument("--limit", type=int, default=5)
    parser.add_argument("--previous-partition", help="optional accepted partition to compare against")
    args = parser.parse_args()
    if args.action == "submit":
        if args.sample is None or not 1 <= args.limit <= 20:
            parser.error("submit requires --sample and --limit between 1 and 20")
        sample = json.loads(args.sample.read_text(encoding="utf-8"))
        ids = [row["review_record_id"] for row in sample["records"][:args.limit]]
        assistants = request("POST", "/assistants/search", {"graph_id": "olist_review_enrichment", "limit": 5})
        if not assistants:
            raise RuntimeError("Aegra does not expose the olist_review_enrichment graph")
        assistant_id = assistants[0]["assistant_id"]
        thread = request("POST", "/threads", {})
        run_input = {"partition_id": args.partition, "review_record_ids": ids}
        if args.previous_partition:
            run_input["previous_partition_id"] = args.previous_partition
        run = request("POST", f"/threads/{thread['thread_id']}/runs", {
            "assistant_id": assistant_id,
            "input": run_input,
        })
        if run.get("status") not in ("pending", "running"):
            raise RuntimeError(f"Aegra did not admit background work: {run}")
        result = {"thread_id": thread["thread_id"], "run_id": run["run_id"],
                  "status": run["status"], "assistant_id": assistant_id, "partition_id": args.partition,
                  "review_record_ids": ids, "sample_sha256": sample["sample_sha256"],
                  "previous_partition_id": args.previous_partition}
        args.evidence.parent.mkdir(parents=True, exist_ok=True)
        args.evidence.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(result, indent=2))
        return 0

    record = json.loads(args.evidence.read_text(encoding="utf-8"))
    route = f"/threads/{record['thread_id']}/runs/{record['run_id']}"
    for _ in range(180):
        run = request("GET", route)
        if run.get("status") in ("success", "error", "interrupted", "cancelled"):
            break
        time.sleep(1)
    else:
        raise TimeoutError("Jev review batch did not reach a terminal state within 180 seconds")
    record["final_status"] = run.get("status")
    record["output"] = run.get("output")
    record["error"] = run.get("error")
    args.evidence.write_text(json.dumps(record, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"run_id": record["run_id"], "status": record["final_status"],
                      "output": record.get("output"), "error": record.get("error")}, indent=2, ensure_ascii=False))
    return 0 if record["final_status"] == "success" else 1


if __name__ == "__main__":
    raise SystemExit(main())
