"""Package scoped, source-linked local artifacts from completed background work."""

from __future__ import annotations

import hashlib
import os
from pathlib import Path

from runtime.artifacts import export_csv, get_artifact, render
from runtime.audience_server import issue_grants
from runtime.evidence import Evidence
from runtime.real_semantics import usage_for
from runtime.generated_artifacts import DEVELOPMENT_SOURCE, create_candidate, render_candidate, review_candidate
from runtime.simulation import encoded


def package(connection, task_ids: list[str], output: Path, *, mode="development") -> dict:
    if mode not in ("development","real","predictor_fixture"):
        raise ValueError("Explicit supported model packaging mode required")
    output.mkdir(parents=True, exist_ok=True)
    output.chmod(0o700)
    receipt = {"schema": "backintel-capability-package/v1", "status": "running", "tasks": [], "files": [],
               "data": "synthetic", "models": "simulated_development_only", "code_generation": "simulated",
               "local_review": "simulated_operator", "paid_provider_calls": 0, "local_compute_usd": None,
               "final_real_model_acceptance": "blocked", "exact_commit_acceptance": "blocked"}
    receipt.update(mode=mode,semantic_observations="simulated" if mode == "development" else "fixture" if mode == "predictor_fixture" else "real_jev",
                   models="simulated_development_only" if mode == "development" else "actual_local_predictors_and_native_baseline",
                   provider_usd=0,provider_fixture_requests=0,fixture_provider_usd=0)

    def save(path, value):
        path.parent.mkdir(parents=True, exist_ok=True)
        data = value.encode() if isinstance(value, str) else encoded(value)
        path.write_bytes(data)
        receipt["files"].append({"path": str(path.relative_to(output)), "sha256": hashlib.sha256(data).hexdigest(), "bytes": len(data)})

    try:
        for task_id in task_ids:
            store = Evidence(connection, task_id)
            task = max(store.list("task"), key=lambda r: r["available_at"])
            usage = usage_for(store)
            fixtures = usage["provider_fixture_requests"]
            if mode == "development":
                if task["body"]["observation_provider"]["implementation_mode"] != "simulated" or usage["provider_calls"]:
                    raise ValueError("Development packaging requires simulated semantic extraction")
            else:
                routes = {(m["body"]["route"],m["body"]["feature_set"]) for m in store.list("model") if m["body"].get("implementation_mode") == "real"}
                expected = {(r,f) for r in ("catboost","tabiclv2") for f in ("structured","semantic")}
                if task["body"]["observation_provider"]["implementation_mode"] != "real" or not expected.issubset(routes):
                    raise ValueError("Actual predictor packaging requires all four real model routes")
                if not usage["provider_calls"] or (mode == "real" and fixtures) or (mode == "predictor_fixture" and fixtures != usage["provider_calls"]):
                    raise ValueError("Semantic provider evidence does not match the explicit packaging mode")
            receipt["provider_fixture_requests"] += fixtures
            if fixtures:
                receipt["fixture_provider_usd"] += usage["provider_usd"]
            else:
                receipt["paid_provider_calls"] += usage["provider_calls"]
                receipt["provider_usd"] += usage["provider_usd"]
            semantic_note = {"development":"Text findings: simulated", "real":"Text findings: real Jev responses",
                             "predictor_fixture":"Text findings: deterministic test fixtures; no paid Jev calls"}[mode]
            records = []
            for audience in task["body"]["audiences"]:
                artifact = get_artifact(store, audience["id"])
                allowed = {"simulated","native_baseline"} if mode == "development" else {"real","native_baseline"}
                if any(r["prediction"] and r["prediction"]["body"]["implementation_mode"] not in allowed for r in artifact["body"]["rows"]):
                    raise ValueError("Packaging mode must match actual predictor execution")
                folder = output / "Reports" / task_id / audience["id"]
                save(folder / "Report.json", artifact)
                save(folder / "Report.html", render(artifact, store.list("artifact_review"), interactive=False, semantic_note=semantic_note))
                save(folder / "Export.csv", export_csv(artifact))
                for row in artifact["body"]["rows"]:
                    save(folder / "Evidence" / (row["source"] + ".json"), artifact["body"]["evidence"][row["source"]])
                records.append({"audience": audience["id"], "artifact_sha256": artifact["sha256"], "visible_entities": len(artifact["body"]["rows"])})
            artifact = get_artifact(store, "operator")
            candidate = create_candidate(store, artifact, "operator", DEVELOPMENT_SOURCE)
            if candidate["body"]["run"]["status"] != "candidate":
                raise RuntimeError("Generated view failed its actual sandbox or source checks")
            review = review_candidate(store, candidate, "operator", "accepted",
                                      "Simulated operator accepts the fixed development generator after source-reference validation",
                                      artifact["available_at"] + 1)
            folder = output / "Reports" / task_id / "operator"
            save(folder / "GeneratedView.json", candidate)
            save(folder / "GeneratedView.html", render_candidate(candidate, [review], interactive=False, semantic_note=semantic_note))
            save(folder / "GeneratedView.py", DEVELOPMENT_SOURCE)
            save(folder / "GeneratedReview.json", review)
            counts = connection.execute("SELECT kind,count(*) FROM backintel.capability_evidence WHERE task_id=%s GROUP BY kind ORDER BY kind", (task_id,)).fetchall()
            jobs = connection.execute("SELECT payload->>'operation',state,attempts,wall_ms,error FROM backintel.capability_jobs WHERE task_id=%s ORDER BY sequence", (task_id,)).fetchall()
            receipt["tasks"].append({"task_id": task_id, "artifacts": records, "candidate_sha256": candidate["sha256"],
                                     "evidence_counts": dict(counts), "stages": [dict(zip(("stage", "state", "attempts", "wall_ms", "error"), row)) for row in jobs],
                                     "simulated_observation_attempts": len(store.list("extraction_attempt"))})
        grants = issue_grants(connection, task_ids)
        access = output / "AudienceAccess.json"
        with os.fdopen(os.open(access, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600), "wb") as handle:
            handle.write(encoded({"grants": grants}))
        receipt["private_access_file"] = str(access)
        receipt["status"] = "passed"
    except Exception as exc:
        receipt.update(status="failed", error={"type": type(exc).__name__, "message": str(exc)})
        raise
    finally:
        (output / "Package.json").write_bytes(encoded(receipt))
    return receipt
