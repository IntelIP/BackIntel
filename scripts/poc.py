"""Set up approved local facts, submit the background demo, and inspect its receipt."""
from __future__ import annotations

import argparse
import json
import time
import uuid
from pathlib import Path

import psycopg
from psycopg import sql
from psycopg.conninfo import conninfo_to_dict, make_conninfo

from runtime.bootstrap import initialize
from runtime.ledger import dsn
from scripts.data.load_olist_facts import DEFAULT_DATA_DIR, PROFILE_PATH, load
from scripts.jev.run_review_batch import request

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = Path.home() / "Library/Application Support/BackIntel/Evidence/PoC"


def inspect(base: str, receipt: dict, *, wait: bool) -> dict:
    deadline = time.monotonic() + 300
    while True:
        run = request("GET", f"/threads/{receipt['thread_id']}/runs/{receipt['run_id']}", base=base)
        receipt["status"] = run["status"]
        if run["status"] in ("success", "error", "interrupted", "cancelled"):
            state = request("GET", f"/threads/{receipt['thread_id']}/state", base=base)
            receipt["output"] = run.get("output") or state.get("values")
            receipt["error"] = run.get("error")
            return receipt
        if not wait:
            return receipt
        if time.monotonic() >= deadline:
            raise TimeoutError("Run is still active; inspect the same receipt instead of resubmitting")
        time.sleep(1)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("setup", "demo", "inspect"))
    parser.add_argument("--data-dir", type=Path, default=DEFAULT_DATA_DIR)
    parser.add_argument("--create-database", action="store_true")
    parser.add_argument("--base-url", default="http://127.0.0.1:2026")
    parser.add_argument("--previous-partition")
    parser.add_argument("--partition")
    parser.add_argument("--receipt", type=Path)
    parser.add_argument("--wait", action="store_true")
    args = parser.parse_args()
    if args.action == "setup":
        database_url = dsn()
        if args.create_database:
            database = conninfo_to_dict(database_url)["dbname"]
            with psycopg.connect(make_conninfo(database_url, dbname="postgres"), autocommit=True) as conn:
                if not conn.execute("SELECT 1 FROM pg_database WHERE datname=%s", (database,)).fetchone():
                    conn.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(database)))
        initialize()
        result = load(args.data_dir, PROFILE_PATH, database_url)
        print(json.dumps({"status": result["status"], "database": conninfo_to_dict(database_url)["dbname"]}))
        return 0
    if args.action == "inspect" and args.receipt is None:
        parser.error("inspect requires the receipt from the original submission")
    path = (args.receipt or EVIDENCE / f"run-{uuid.uuid4()}.json").expanduser().resolve()
    if path.is_relative_to(ROOT):
        parser.error("Receipts and dataset-derived output must stay outside the checkout")
    if args.action == "demo":
        if not args.previous_partition or not args.partition or args.previous_partition == args.partition:
            parser.error("demo requires two different previously accepted review partitions")
        if path.exists():
            parser.error("Receipt already exists; use inspect to resume that run")
        with psycopg.connect(dsn()) as conn:
            accepted = dict(conn.execute("SELECT partition_id, disposition FROM backintel.partition_results WHERE partition_id=ANY(%s)",
                                         ([args.previous_partition, args.partition],)).fetchall())
            if any(accepted.get(p) != "accepted" for p in (args.previous_partition, args.partition)):
                parser.error("Both partitions need accepted recorded observations; no paid calls are allowed")
            ids = [r[0] for r in conn.execute("SELECT review_record_id FROM backintel.jev_observations WHERE partition_id=%s ORDER BY review_record_id",
                                            (args.partition,)).fetchall()]
        assistants = request("POST", "/assistants/search", {"graph_id": "olist_review_enrichment", "limit": 1}, base=args.base_url)
        if not assistants:
            raise RuntimeError("Updated review graph is not registered in this runtime")
        thread = request("POST", "/threads", {}, base=args.base_url)
        run = request("POST", f"/threads/{thread['thread_id']}/runs", {
            "assistant_id": assistants[0]["assistant_id"],
            "input": {"partition_id": args.partition, "previous_partition_id": args.previous_partition,
                      "review_record_ids": ids, "reuse_only": True},
        }, base=args.base_url)
        receipt = {"thread_id": thread["thread_id"], "run_id": run["run_id"], "status": run["status"],
                   "previous_partition": args.previous_partition, "partition": args.partition,
                   "mode": "recorded_observations_no_inference", "base_url": args.base_url}
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(receipt, indent=2) + "\n")
        if args.wait:
            receipt = inspect(args.base_url, receipt, wait=True)
    else:
        receipt = json.loads(path.read_text())
        receipt = inspect(receipt.get("base_url", args.base_url), receipt, wait=args.wait)
    path.write_text(json.dumps(receipt, indent=2, ensure_ascii=False) + "\n")
    print(json.dumps({"status": receipt["status"], "receipt": str(path),
                      "report": (receipt.get("output") or {}).get("report")}, indent=2))
    return 1 if receipt["status"] in ("error", "interrupted", "cancelled") else 0


if __name__ == "__main__":
    raise SystemExit(main())
