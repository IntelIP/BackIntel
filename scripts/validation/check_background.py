"""Check cancellation, replay, and no-inference publication in an isolated runtime."""
import argparse
import json
import time
import uuid
from pathlib import Path

import psycopg
from psycopg.conninfo import conninfo_to_dict

from runtime.ledger import dsn
from scripts.jev.run_review_batch import request
from scripts.poc import inspect


def check(args) -> dict:
    database = conninfo_to_dict(dsn())["dbname"]
    if not (database.startswith("test_") or database.endswith("_test")):
        raise RuntimeError("Background probes require an isolated test database")
    original = json.loads(args.receipt.read_text())

    def submit(graph, state):
        assistants = request("POST", "/assistants/search", {"graph_id": graph, "limit": 1}, base=args.base_url)
        thread = request("POST", "/threads", {}, base=args.base_url)
        run = request("POST", f"/threads/{thread['thread_id']}/runs",
                      {"assistant_id": assistants[0]["assistant_id"], "input": state}, base=args.base_url)
        return {"thread_id": thread["thread_id"], "run_id": run["run_id"], "status": run["status"]}

    probe_id = "recovery-" + uuid.uuid4().hex
    cancelled = submit("olist_fixture", {"partition_id": probe_id, "record_count": 7, "delay_seconds": 20})
    deadline = time.monotonic() + 30
    while True:
        with psycopg.connect(dsn()) as conn:
            partial = conn.execute("SELECT disposition FROM backintel.partition_results WHERE partition_id=%s", (probe_id,)).fetchone()
        if partial == ("partial",):
            break
        if time.monotonic() >= deadline:
            raise TimeoutError("Probe did not enter domain processing")
        time.sleep(.2)
    request("POST", f"/threads/{cancelled['thread_id']}/runs/{cancelled['run_id']}/cancel?wait=1&action=cancel", base=args.base_url)
    cancelled = inspect(args.base_url, cancelled, wait=True)
    assert cancelled["status"] in ("interrupted", "cancelled"), cancelled["status"]
    with psycopg.connect(dsn()) as conn:
        assert conn.execute("SELECT disposition FROM backintel.partition_results WHERE partition_id=%s", (probe_id,)).fetchone() == ("partial",)
    retried = inspect(args.base_url, submit("olist_fixture", {"partition_id": probe_id, "record_count": 7, "delay_seconds": 0}), wait=True)
    assert retried["status"] == "success", retried

    partitions = [original["previous_partition"], original["partition"]]
    with psycopg.connect(dsn()) as conn:
        before = conn.execute("SELECT (SELECT count(*) FROM backintel.jev_observations WHERE partition_id=ANY(%s)), (SELECT count(*) FROM backintel.usage_events WHERE partition_id=ANY(%s))", (partitions, partitions)).fetchone()
        ids = [row[0] for row in conn.execute("SELECT review_record_id FROM backintel.jev_observations WHERE partition_id=%s ORDER BY review_record_id", (original["partition"],))]
    state = {"partition_id": original["partition"], "previous_partition_id": original["previous_partition"], "review_record_ids": ids, "reuse_only": True}
    runs = [submit("olist_review_enrichment", state) for _ in range(2)]
    completed = [inspect(args.base_url, run, wait=True) for run in runs]
    assert all(run["status"] == "success" for run in completed), completed
    artifacts = [run["output"]["report"]["artifacts"] for run in completed]
    assert artifacts[0] == artifacts[1] == original["output"]["report"]["artifacts"], "Replay duplicated or changed publication"
    with psycopg.connect(dsn()) as conn:
        after = conn.execute("SELECT (SELECT count(*) FROM backintel.jev_observations WHERE partition_id=ANY(%s)), (SELECT count(*) FROM backintel.usage_events WHERE partition_id=ANY(%s))", (partitions, partitions)).fetchone()
        assert conn.execute("SELECT count(*) FROM backintel.partition_results WHERE partition_id=%s AND disposition='accepted'", (probe_id,)).fetchone() == (1,)
    assert before == after, "Recorded replay created observations or provider usage"
    result = {"status": "passed", "candidate": completed[0]["output"]["report"]["candidate"],
              "cancelled_run": cancelled["run_id"], "cancellation_status": cancelled["status"],
              "retry_run": retried["run_id"], "accepted_probe_rows": 1,
              "concurrent_replay_runs": [run["run_id"] for run in completed],
              "observation_count": after[0], "usage_count": after[1], "new_provider_calls": 0,
              "artifact_reused": True}
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--receipt", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    started = time.monotonic()
    try:
        result = check(args)
    except Exception as error:
        result = {"status": "blocked" if isinstance(error, (OSError, TimeoutError)) else "failed",
                  "summary": str(error), "error_type": type(error).__name__}
    result["duration_ms"] = round((time.monotonic() - started) * 1000)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))
    return 0 if result["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
