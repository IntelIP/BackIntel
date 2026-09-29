"""Run synthetic capability scenarios locally, or submit them to an installed Aegra runtime."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from urllib.parse import urlsplit

from runtime.simulation import SCENARIOS, load_scenario, publish, simulate


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scenario", default="all", help="Local scenario name, or all")
    parser.add_argument("--output", type=Path, default=Path.home() / "Library/Application Support/BackIntel/Evidence/Simulation")
    parser.add_argument("--base-url", help="Submit to an Aegra runtime containing capability_simulation")
    parser.add_argument("--receipt", type=Path, help="New receipt for background submission")
    args = parser.parse_args()
    if args.base_url:
        endpoint = urlsplit(args.base_url)
        if endpoint.scheme != "http" or endpoint.hostname not in ("127.0.0.1", "localhost", "::1"):
            parser.error("Simulation submission is restricted to a local HTTP runtime")
        if args.scenario == "all" or args.receipt is None:
            parser.error("Background submission requires one scenario and --receipt")
        if args.receipt.exists():
            parser.error("Receipt already exists; inspect it instead of overwriting")
        from scripts.jev.run_review_batch import request
        scenario = load_scenario(args.scenario)
        assistants = request("POST", "/assistants/search", {"graph_id": "capability_simulation", "limit": 1}, base=args.base_url)
        if not assistants:
            raise RuntimeError("Selected runtime does not contain capability_simulation; use offline mode or an approved runtime update")
        thread = request("POST", "/threads", {}, base=args.base_url)
        run = request("POST", f"/threads/{thread['thread_id']}/runs", {
            "assistant_id": assistants[0]["assistant_id"],
            "input": {"scenario": scenario["id"], "partition_id": f"simulation-{thread['thread_id']}"},
        }, base=args.base_url)
        receipt = {"thread_id": thread["thread_id"], "run_id": run["run_id"], "status": run["status"],
                   "base_url": args.base_url, "mode": "synthetic_simulation"}
        args.receipt.parent.mkdir(parents=True, exist_ok=True)
        with args.receipt.open("x") as handle:
            json.dump(receipt, handle, indent=2)
        print(json.dumps(receipt, indent=2))
        return 0
    if args.receipt:
        parser.error("--receipt is only used with --base-url")
    names = sorted(path.stem for path in SCENARIOS.glob("*.json")) if args.scenario == "all" else [args.scenario]
    if not names:
        parser.error("No simulation scenarios configured")
    output = []
    for name in names:
        result = simulate(load_scenario(name))
        artifacts = publish(result, args.output)
        output.append({"scenario": name, "mode": result["mode"], "batches": len(result["batches"]),
                       "episodes": len(result["inbox"]), "provider_calls": 0, "artifacts": artifacts})
    print(json.dumps(output, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
