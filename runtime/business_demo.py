"""Business presentation for the existing real-model pipeline; never pays a provider."""
from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timedelta, timezone
import json
import math
from pathlib import Path

from runtime.capability_pipeline import followup_events
from runtime.simulation import digest
from runtime.synthetic import history

SPEC = Path(__file__).resolve().parents[1] / "docs/demo/SupportScenario.json"


def description(message, entity):
    if "failed" in message.lower() or "blocked" in message.lower():
        return (f"{message}. A customer in the {entity} queue reports that they cannot access their paid account. "
                "They tried again after resetting their password and still received an error. "
                "They need someone to investigate before they can finish their work. "
                "This is an illustrative synthetic customer report.")
    return (f"{message}. A customer in the {entity} queue asked where to update their contact details. "
            "They confirmed that they can sign in and save changes. They are requesting information, "
            "rather than reporting a current outage. This is an illustrative synthetic customer report.")


def dataset(scenario):
    task, rows, outcomes = history(scenario)
    events = deepcopy(list(followup_events(scenario)))
    if scenario == "support":
        field = task["fields"]["content"]
        entity = task["fields"]["entity"]
        for row in rows:
            row[field] = description(row[field], row[entity])
        for _, _, event in events:
            if event["operation"] == "arrival":
                row = event["row"]
                row[field] = description(row[field], row[entity])
    return (task, rows, outcomes), events


def capacity_value(assumptions):
    required = {"cases_per_week", "manual_minutes_per_case", "assisted_minutes_per_case", "labour_usd_per_hour"}
    if set(assumptions) != required or any(type(value) not in (int, float) or not math.isfinite(value) or value < 0
                                         for value in assumptions.values()):
        raise ValueError("Capacity assumptions require finite nonnegative numbers and the four declared fields")
    hours = assumptions["cases_per_week"] * (assumptions["manual_minutes_per_case"] - assumptions["assisted_minutes_per_case"]) / 60
    return {"basis": "illustrative assumptions", "assumptions": assumptions, "capacity_hours_per_week": hours,
            "capacity_value_usd_per_week": hours * assumptions["labour_usd_per_hour"],
            "cash_savings_usd": None, "revenue_gain_usd": None, "compute_usd": None, "net_benefit_usd": None,
            "explanation": "Capacity value is an assumption, not measured savings. Unpriced compute prevents a net benefit claim."}


def simulation_date(at):
    return (datetime(2026, 9, 30, tzinfo=timezone.utc) + timedelta(minutes=at)).isoformat()


def attach_local_predictions(packet, report, demo_id):
    """Expose a separate synthetic model test without completing workflow stages."""
    if (report.get("schema") != "backintel-local-prediction-rehearsal/v1"
            or report.get("demo_id") != demo_id
            or report.get("dataset_sha256") != digest(dataset("support")[0])
            or report.get("source_mode") != "synthetic"
            or report.get("status") != "completed"
            or report.get("feature_set") != "structured"
            or report.get("provider_calls") != 0):
        raise ValueError("Local prediction rehearsal does not match the approved synthetic demonstration")
    expected = {"baseline": "computed_baseline", "catboost": "actual_local_model", "tabiclv2": "actual_local_model"}
    methods = report.get("methods", [])
    if len(methods) != len(expected) or {method["route"] for method in methods} != set(expected):
        raise ValueError("Local prediction rehearsal must contain the baseline and both approved models")
    for method in methods:
        error = method["metrics"]["brier"]
        if (method.get("execution") != expected[method["route"]]
                or method.get("feature_set") != "structured"
                or not isinstance(error, (int, float)) or not math.isfinite(error) or not 0 <= error <= 1):
            raise ValueError("Local prediction rehearsal has an invalid execution label or probability error")
    demo = packet["demo"]
    demo["local_rehearsal"] = {**report, "scope_boundary": "This local rehearsal used checked fields and no Jev interpretation. Its predictions are separate from the live provider journey."}
    if not demo["comparisons"]:
        demo["comparisons"] = [{"route": method["route"], "feature_set": "structured", "metrics": method["metrics"],
                                "selected": method["route"] == report["selected_route"],
                                "train_count": report["train_count"], "holdout_count": report["holdout_count"]}
                               for method in methods]
        demo["comparison_basis"] = (f"Facts-only results are from a separate actual local model rehearsal: "
                                    f"{report['train_count']} earlier training records and {report['holdout_count']} later test records. "
                                    "Jev-enhanced methods and the autonomous provider journey remain pending.")
    return packet


def attach_live_attempt(packet, report, demo_id):
    """Show retained attempt billing without completing any workflow stage."""
    if (report.get("schema") != "backintel-live-jev-attempt/v1"
            or Path(report.get("receipt_path", "")).parent.parent.name != demo_id):
        raise ValueError("Live attempt does not match this demonstration")
    attempts, missing = report["request_attempts"], report["unknown_request_cost_count"]
    total = report["total_provider_charge_usd"]
    if (type(attempts) is not int or type(missing) is not int or not 0 <= missing <= attempts
            or (total is not None and (type(total) not in (int, float) or not math.isfinite(total) or total < 0))
            or (missing and total is not None)):
        raise ValueError("Live attempt has inconsistent cost evidence")
    demo = packet["demo"]
    demo["live_attempt"] = {"request_attempts": attempts, "unknown_request_cost_count": missing,
                            "total_provider_charge_usd": total}
    if report["status"] == "blocked" and demo["status"] != "completed":
        demo["status"] = "blocked"
        demo["error"] = f"The live attempt stopped after {attempts} request attempts. Returned answers and recorded charges are retained; the integrated workflow is unfinished."
    if missing:
        demo["value"]["explanation"] += f" Billing is missing for {missing} request attempts, so the total live attempt charge is unknown."


def attach_workflow_rehearsal(packet, report, demo_id):
    """Show native scheduled execution separately from the live provider journey."""
    submission, integration = report["submission"], report["integration"]
    rehearsal_id = submission["demo_id"]
    replay = integration["replay"]
    if (report.get("schema") != "backintel-workflow-rehearsal/v1"
            or report.get("demo_id") != demo_id
            or submission.get("mode") != "synthetic_sources_simulated_models"
            or submission.get("scheduler") != "aegra_native_cron"
            or integration.get("status") != "passed"
            or integration.get("model_execution") != "simulated_development_only"
            or integration.get("final_real_model_acceptance") != "blocked"
            or integration.get("errors") != [] or integration.get("pending_triggers") != 0
            or replay.get("status") != "passed"
            or not replay.get("before_sha256") or replay.get("before_sha256") != replay.get("after_sha256")):
        raise ValueError("Scheduled rehearsal must retain its simulated intelligence and separate acceptance boundary")
    scopes = {f"{scenario}-{rehearsal_id}": scenario for scenario in ("support", "equipment")}
    jobs, counts = integration["jobs"], integration["counts"]
    if ({job["scenario"] for job in jobs} != set(scopes)
            or any(job["state"] != "completed" or type(job["count"]) is not int or job["count"] < 1 for job in jobs)
            or any(row["scenario"] not in scopes or type(row["count"]) is not int or row["count"] < 0 for row in counts)
            or any(response["demo_id"] != rehearsal_id for response in replay["responses"])):
        raise ValueError("Scheduled rehearsal contains incomplete jobs or evidence from another run")
    scenarios = []
    for scope, name in scopes.items():
        totals = {row["kind"]: row["count"] for row in counts if row["scenario"] == scope}
        scenarios.append({"name": "Support queues" if name == "support" else "Equipment watch",
                          "completed_jobs": sum(job["count"] for job in jobs if job["scenario"] == scope),
                          "simulated_predictions": totals.get("prediction", 0),
                          "delivery_records": totals.get("delivery", 0),
                          "simulated_model_updates": totals.get("model_update", 0)})
    packet["demo"]["workflow_rehearsal"] = {
        "status": "completed with simulated intelligence", "rehearsal_id": rehearsal_id,
        "scope_boundary": "The native scheduled worker ran. Interpretation and prediction responses were simulated. "
                          "This separate rehearsal does not complete the live Jev journey or the stages above.",
        "technology": "Aegra native scheduling / LangGraph workflow / PostgreSQL evidence",
        "scenarios": scenarios, "pending_triggers": integration["pending_triggers"],
        "replay_unchanged": True, "evidence_records": replay["evidence_records"],
        "source_sha256": digest(report), "source_directory": report["source_directory"]}
    return packet


def snapshot(store, jobs, requests, triggers=()):
    """Read one exact task's committed evidence without executing or authorizing it."""
    spec = json.loads(SPEC.read_text())
    plan = store.find("real_plan", "history-v1")
    if plan is None:
        raise ValueError("Prepare the scoped business dataset before opening the demonstration")
    task = store.get(plan["body"]["task"])
    measure_units = {measure["id"]: measure["unit"] for measure in task["body"]["measures"]}
    stages = store.list("real_stage_result")
    at = max([plan["body"]["at"], *[record["available_at"] for record in stages]])
    from runtime.contracts import current_sources
    sources = current_sources(store, at, task["sha256"])
    observations = store.list("observation", at)
    models = store.list("model", at)
    comparisons = store.list("comparison", at)
    comparison_rows = []
    if comparisons:
        comparison = comparisons[-1]["body"]
        for sha in comparison["evaluations"]:
            evaluation = store.get(sha)["body"]
            model = store.get(evaluation["model"])["body"]
            comparison_rows.append({"route": model["route"], "feature_set": model["feature_set"],
                                    "metrics": evaluation["metrics"], "selected": evaluation["model"] == comparison["selected"],
                                    "train_count": comparison["train_count"], "holdout_count": comparison["holdout_count"]})
    predictions = store.list("prediction", at)
    analyses = store.list("analysis", at)
    completed = [request for request in requests if request["state"] == "completed"]
    fixture = any(request.get("metadata", {}).get("test_fixture") for request in completed)
    actual_answers = any(not request.get("metadata", {}).get("test_fixture") for request in completed)
    actual = [request for request in requests if not request.get("metadata", {}).get("test_fixture")]
    unknown_cost = any(request["state"] != "completed" or request.get("metadata", {}).get("cost_usd") is None for request in actual)
    provider_usd = None if unknown_cost else sum(float(request["metadata"]["cost_usd"]) for request in actual)
    mode = "mixed actual and simulated Jev answers" if fixture and actual_answers else "simulated Jev answers" if fixture else "actual Jev responses" if actual_answers else "Jev has not run"
    cases = []
    for entity in sorted({source["body"]["entity"] for source in sources}):
        group = [source for source in sources if source["body"]["entity"] == entity]
        latest = max(group, key=lambda source: (source["available_at"], source["identity"]))
        latest_findings = [record for record in observations if record["body"]["source"] == latest["sha256"]]
        lineage = sorted(source["sha256"] for source in group)
        text = "\n\n".join(f"{source['body']['id']} · simulation window {source['available_at']}\n{source['body']['content']}" for source in group[-3:])
        estimates = {}
        for prediction in predictions:
            body = prediction["body"]
            if body["entity"] != entity:
                continue
            feature = store.get(body["feature"])
            # A queue estimate is displayed only with its actual source lineage.
            if feature["body"]["source"] not in lineage:
                continue
            model = store.get(body["model"])["body"]
            estimates[f"{model['route']} · {model['feature_set']}"] = body["value"]
        if latest_findings:
            values = "; ".join(f"{record['body']['question_id']}: {record['body']['response']['value']}" for record in latest_findings)
            finding = {"status": mode, "text": f"Typed interpretation of this original report: {values}. Check the source before choosing an action."}
        else:
            finding = {"status": "Awaiting Jev interpretation", "text": "The original report is admitted. No Jev answer has been attached to it yet."}
        cases.append({"id": f"SUPPORT-{entity.upper()}", "workflow": "issues", "title": f"{entity} service queue",
                      "summary": latest["body"]["content"], "created_at": simulation_date(latest["available_at"]),
                      "source_kind": "Synthetic support scenario", "simulated": True,
                      "facts": [{"label": "Source reports", "value": str(len(group))},
                                {"label": "Received (simulation)", "value": simulation_date(latest["available_at"])[11:16] + " UTC"},
                                {"label": "Interpretation", "value": mode},
                                *[{"label": f"Recorded {name}", "value": f"{value:g} {measure_units[name]}" if value is not None else "Not provided"} for name, value in sorted(latest["body"]["measures"].items())]], "finding": finding,
                      "prediction": {"status": "experimental", "explanation": "Actual model estimates are shown only after execution. Performance on synthetic data does not establish customer performance.", "estimates": estimates},
                      "evidence": {"text": text, "url": None, "sha256": digest(lineage), "collected_at": simulation_date(latest["available_at"])},
                      "review": None, "outcome": None})
    stage_rows = [
        ("admission", "Collect and check reports", "Python / PostgreSQL", len(sources), "Original messages and measurements are admitted with source identities and availability times."),
        ("interpretation", "Interpret the report", "Jev / TypeSafe / OpenRouter", len(observations), mode),
        ("comparison", "Compare prediction methods", "CatBoost / TabICLv2 / baseline", len(comparisons), "Compare facts alone with facts plus interpretation on the same time-separated evaluation."),
        ("prediction", "Estimate what may happen next", "Pinned local prediction models", len(predictions), "Keep predictions attached to their actual feature and source records."),
        ("analysis", "Prepare the review packet", "LangGraph / analysis and attention", len(analyses), "Prepare evidence for a human decision; model output does not authorize business action."),
        ("refresh", "Refresh after new information", "Aegra / durable scheduled jobs", max(0, len(stages) - 1), "Arrivals and corrections create later packets and invalidate superseded predictions.")]
    value = capacity_value(spec["value_assumptions"])
    value["provider_usd"] = provider_usd
    pending = sum(job["state"] in ("queued", "running", "retry") for job in jobs) + sum(trigger["state"] == "pending" for trigger in triggers)
    blocked = any(request["state"] in ("blocked", "uncertain") for request in requests) or any(job["state"] in ("failed", "blocked") for job in jobs)
    followups = store.find("real_plan", "followups-v1")
    expected_stages = 1 + len(followups["body"]["arrival_plans"]) if followups else 1
    status = "blocked" if blocked else "running" if pending else "completed" if len(stages) >= expected_stages else "awaiting follow-up execution" if stages else "prepared"
    demo = {"schema": "backintel-business-demo/v1", "title": spec["title"], "persona": spec["persona"],
            "problem": spec["problem"], "today": spec["today"], "task_id": store.task_id, "status": status,
            "source_mode": "synthetic", "jev_mode": mode, "provider_requests": len(requests),
            "actual_provider_calls": None if unknown_cost else len(actual),
            "stages": [{"id": key, "title": title, "technology": technology, "count": count,
                        "status": "observed" if count else "pending", "explanation": explanation}
                       for key, title, technology, count, explanation in stage_rows],
            "model_records": [{"sha256": record["sha256"], "body": {key: record["body"].get(key) for key in ("route", "feature_set", "implementation_mode", "prepared_at")}} for record in models],
            "comparisons": comparison_rows, "jobs": jobs, "value": value, "stack": spec["stack"],
            "boundaries": ["Business inputs and future outcomes are synthetic.", "Financial values are assumptions; cash savings and revenue gain are unmeasured.",
                           "Prepared source versions are not proof that interpretation or prediction ran."]}
    return {"schema": "backintel-decision-workspace/v1", "source_mode": "synthetic-business-demonstration", "cases": cases, "demo": demo}
