"""Submit explicit real-model stages to the isolated development API."""

from __future__ import annotations

import argparse
import json
import uuid

from scripts.capability_demo import BASE, ROOT
from scripts.jev.run_review_batch import request
from runtime.simulation import encoded


def submit(stage, scenario, demo_id, request_id, **fields):
    assistants = request("POST", "/assistants/search", {"graph_id":"capability_platform","limit":1}, base=BASE)
    if not assistants:
        raise RuntimeError("The isolated API has no capability platform assistant")
    thread = request("POST", "/threads", {}, base=BASE)
    return request("POST", f"/threads/{thread['thread_id']}/runs/wait", {
        "assistant_id": assistants[0]["assistant_id"],
        "input": {"operation": "real_"+stage, "scenario": scenario, "demo_id": demo_id,
                  "request_id": request_id, **fields}}, base=BASE)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stage", choices=("prepare", "prepare_followups", "interpret", "compare", "start_followups", "start"))
    parser.add_argument("--scenario", choices=("support", "equipment"), required=True)
    parser.add_argument("--demo-id", required=True)
    parser.add_argument("--request-id", required=True)
    parser.add_argument("--source-sha256")
    parser.add_argument("--plan-sha256")
    parser.add_argument("--authorization")
    args = parser.parse_args()
    fields = {}
    if args.stage == "interpret":
        if not args.source_sha256 or not args.authorization:
            parser.error("Interpretation requires a source hash and separately approved authorization")
        fields = {"source_sha256": args.source_sha256, "provider_authorization_id": args.authorization}
        if args.plan_sha256:
            fields["plan_sha256"] = args.plan_sha256
    elif args.stage in ("start_followups","start"):
        if not args.authorization or args.source_sha256 or args.plan_sha256:
            parser.error("Starting follow-ups requires only the matching approved authorization")
        fields = {"provider_authorization_id":args.authorization}
    elif args.source_sha256 or args.authorization or args.plan_sha256:
        parser.error("Source and authorization arguments apply only to interpretation")
    output = ROOT / "artifacts/validation/RealPipeline" / ("Attempt"+uuid.uuid4().hex[:12])
    output.mkdir(parents=True)
    receipt = {"schema": "backintel-real-stage/v1", "stage": args.stage, "scenario": args.scenario,
               "demo_id": args.demo_id, "request_id":args.request_id, "fields":fields,
               "candidate": "uncommitted-working-tree", "status": "running"}
    try:
        reply = submit(args.stage,args.scenario,args.demo_id,args.request_id,**fields)
        receipt.update(reply=reply, status="passed" if reply.get("result",{}).get("state") == "completed" else "blocked")
    except Exception as exc:
        receipt.update(status="blocked",error={"type":type(exc).__name__,"message":str(exc)},
                       state="Transport failure does not establish whether the durable job completed; replay this request identity.")
        raise
    finally:
        path = output / "Stage.json"
        path.write_bytes(encoded(receipt))
        print(json.dumps({"status":receipt["status"],"receipt":str(path)}))
    return 0 if receipt["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
