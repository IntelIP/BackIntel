"""Real-model stages with committed source admission before any paid request."""

from __future__ import annotations

import time
from runtime.contracts import admit_source, current_sources, register_task
from runtime.observations import effective_observation
from runtime.prediction import compare, features, invalidate_predictions, outcome, transition, update_plan
from runtime.real_semantics import extract_real, scope_for, usage_for
from runtime.simulation import digest
from runtime.synthetic import history


def prepare_history(store, scenario: str) -> dict:
    existing = store.find("real_plan", "history-v1")
    if existing:
        if existing["body"]["scenario"] != scenario:
            raise ValueError("Real-model preparation identity conflicts with its scenario")
        return existing
    task, rows, labels = history(scenario)
    task["id"] = store.task_id
    task["observation_provider"] = {"name": "openrouter-jev", "version": "jev-1.13", "implementation_mode": "real"}
    task_record = register_task(store, task)
    sources, outcomes = [], []
    for row, label in zip(rows, labels):
        admission = admit_source(store, task_record, {"format": "json", "data": [row]}, label["event_at"])
        disposition = admission["body"]["dispositions"][0]
        if disposition["status"] == "quarantined":
            raise ValueError("Synthetic real-model history failed source admission")
        sources.append(store.get(disposition["source"]))
        outcomes.append(outcome(store, task_record, label))
    at = max(r["available_at"] for r in outcomes)
    body = {"scenario": scenario, "task": task_record["sha256"], "sources": [r["sha256"] for r in sources],
            "outcomes": [r["sha256"] for r in outcomes], "scope": scope_for(task_record, sources),
            "at": at, "model_execution": "not_started", "provider_approval": "required", "provider_calls": 0,
            "unique_texts": len({r["body"]["content"] for r in sources}), "source_records": len(sources),
            "followup": "Separate approved interpretation jobs must finish before real comparison."}
    return store.put("real_plan", "history-v1", body, at,
                     [task_record["sha256"], *[r["sha256"] for r in sources + outcomes]])


def interpret_source(store, plan, source_sha, authorization_id, classifier_factory=None):
    if source_sha not in plan["body"]["sources"]:
        raise PermissionError("Interpretation source is outside the prepared history")
    if not isinstance(authorization_id, str) or not 1 <= len(authorization_id) <= 128:
        raise PermissionError("A named approved provider authorization is required")
    task_record, source = store.get(plan["body"]["task"]), store.get(source_sha)
    # prepare_history is a different completed job; the foreign-key parents are committed.
    observations = extract_real(store, task_record, source, source["available_at"],
                                authorization_id=authorization_id, classifier_factory=classifier_factory)
    body = {"plan": plan["sha256"], "source": source_sha, "observations": [r["sha256"] for r in observations],
            "implementation_mode": "real", "request_ids": sorted({r["body"]["request_id"] for r in observations})}
    return store.find("real_interpretation", digest(body)) or store.put("real_interpretation", digest(body), body,
        plan["available_at"], [plan["sha256"], *[r["sha256"] for r in observations]])


def require_observations(store, plan, *, historical=False):
    task_record = store.get(plan["body"]["task"])
    task, at = task_record["body"], plan["body"]["at"]
    observations = store.list("observation", at)
    for source_sha in plan["body"]["sources"]:
        source = store.get(source_sha)
        cutoff = source["body"]["event_at"] if historical else at
        for question in task["questions"]:
            matches = [r for r in observations if r["body"]["source"] == source_sha
                       and r["body"]["task"] == task_record["sha256"] and r["body"]["question_id"] == question["id"]]
            if len(matches) != 1:
                raise PermissionError("Real comparison requires an actual Jev finding for every history question")
            finding = matches[0]
            if finding["available_at"] > cutoff or finding["body"]["provider"]["implementation_mode"] != "real" or not finding["body"].get("request_id"):
                raise ValueError("Observation is simulated, untraceable or unavailable at the feature cutoff")
            effective_observation(store, finding["sha256"], cutoff)
    usage_for(store)  # Unknown actual billing or uncertain requests block acceptance.
    return task_record


def compare_history(store, plan):
    previous = store.find("real_stage_result", "history-v1")
    if previous:
        return store.get(previous["body"]["result"])
    task_record = require_observations(store, plan, historical=True)
    at = plan["body"]["at"]
    snapshots = []
    for source_sha in plan["body"]["sources"]:
        source = store.get(source_sha)
        snapshots.extend(r for r in features(store, task_record, source["body"]["event_at"])
                         if r["body"]["source"] == source_sha)
    comparison = compare(store, task_record, snapshots, at, implementation_mode="real")
    selected = comparison["body"]["selected"]
    transition(store, task_record, selected, "approve", at, "real-demo-policy-approval")
    transition(store, task_record, selected, "activate", at, "real-demo-policy-activation")
    event = store.put("event", "real-initial-comparison", {"operation": "real_compare", "scenario": plan["body"]["scenario"],
                      "operator_approval": "simulated_demo_policy"}, at, [comparison["sha256"], plan["sha256"]])
    from runtime.capability_pipeline import refresh
    result = refresh(store, task_record, event, at, observe=True)
    store.put("real_stage_result", "history-v1", {"result":result["sha256"]}, at, [result["sha256"]])
    return result


def prepare_arrival(store, task_record, scenario, payload):
    at, row = payload["at"], payload["row"]
    key = "arrival-"+digest([task_record["sha256"],row,at])
    previous = store.find("real_plan",key)
    if previous:
        return previous
    old = next((r for r in current_sources(store,at,task_record["sha256"])
                if r["body"]["id"] == row[task_record["body"]["fields"]["id"]]),None)
    admission = admit_source(store,task_record,{"format":"json","data":[row]},at)
    disposition = admission["body"]["dispositions"][0]
    if disposition["status"] == "quarantined":
        raise ValueError("Synthetic real follow-up failed source admission")
    source = store.get(disposition["source"])
    body = {"scenario":scenario,"task":task_record["sha256"],"sources":[source["sha256"]],"at":at,
            "admission":admission["sha256"],"scope":scope_for(task_record,[source]),
            "previous_source":old["sha256"] if old and old["sha256"] != source["sha256"] else None}
    return store.put("real_plan",key,body,at,[task_record["sha256"],admission["sha256"]])


def prepare_followups(store, history_plan):
    previous = store.find("real_plan","followups-v1")
    if previous:
        return previous
    from runtime.capability_pipeline import followup_events
    task_record = store.get(history_plan["body"]["task"])
    scenario = history_plan["body"]["scenario"]
    events, plans, sources = [], [], []
    for _,kind,payload in followup_events(scenario):
        if payload["operation"] == "arrival":
            plan = prepare_arrival(store,task_record,scenario,payload)
            plans.append(plan)
            sources.extend(store.get(sha) for sha in plan["body"]["sources"])
            events.append({"kind":kind,"payload":{"operation":"real_interpret","plan_sha256":plan["sha256"],
                                                    "source_sha256":plan["body"]["sources"][0]}})
            payload = {"operation":"real_arrival_apply","plan_sha256":plan["sha256"],"at":payload["at"],
                       "fail_once":payload.get("fail_once",False)}
        else:
            payload = {**payload,"operation":"real_event","action":payload["operation"]}
        events.append({"kind":kind,"payload":payload})
    at = max(p["payload"].get("at",0) for p in events)
    body = {"scenario":scenario,"task":task_record["sha256"],"sources":[r["sha256"] for r in sources],
            "scope":scope_for(task_record,sources),"at":at,"events":events,
            "arrival_plans":[r["sha256"] for r in plans],
            "mode":"synthetic_future_sources_with_cutoff_enforcement","provider_calls":0}
    return store.put("real_plan","followups-v1",body,at,[history_plan["sha256"],*[r["sha256"] for r in plans]])


def apply_arrival(store, plan):
    previous = store.find("real_stage_result",plan["sha256"])
    if previous:
        return store.get(previous["body"]["result"])
    task_record = require_observations(store,plan)
    from runtime.capability_pipeline import refresh
    at = plan["body"]["at"]
    source = store.get(plan["body"]["sources"][0])
    admission = store.get(plan["body"]["admission"])
    if plan["body"]["previous_source"]:
        invalidate_predictions(store,plan["body"]["previous_source"],admission,at)
    result = refresh(store,task_record,admission,at,observe=True,entities=[source["body"]["entity"]])
    update_plan(store,store.get(result["body"]["model"]),[store.get(s) for s in result["body"]["features"]],admission,at)
    store.put("real_stage_result",plan["sha256"],{"result":result["sha256"]},at,[result["sha256"]])
    return result


def require_approved_scope(store, task, expected, authorization_id):
    authorization = store.connection.execute("""SELECT approved,expires_at>now(),scope,scope_sha256,model
        FROM backintel.capability_provider_authorizations WHERE authorization_id=%s""",(authorization_id,)).fetchone()
    if not authorization or not all(authorization[:2]):
        raise PermissionError("Follow-up scheduling requires current explicit provider approval")
    scope, scope_sha, model = authorization[2:]
    if digest(scope) != scope_sha or model != task["body"]["observation_provider"]["version"] or any(
            scope.get(k) != expected[k] for k in ("task_sha256","questions_sha256")) or not set(
            expected["source_sha256s"]).issubset(scope.get("source_sha256s",[])):
        raise PermissionError("Follow-up sources exceed the approved scope")


def start_followups(store, plan, authorization_id):
    previous = store.find("real_schedule","followups-v1")
    if previous:
        if previous["body"]["authorization_id"] != authorization_id:
            raise ValueError("Follow-up scheduling identity conflicts with its authorization")
        return previous
    if not store.find("real_stage_result","history-v1"):
        raise ValueError("Real history comparison must complete before follow-up scheduling")
    require_approved_scope(store,store.get(plan["body"]["task"]),plan["body"]["scope"],authorization_id)
    from runtime.jobs import schedule
    triggers = []
    now = time.time()
    for index,event in enumerate(plan["body"]["events"]):
        payload = {**event["payload"],"scenario":plan["body"]["scenario"]}
        if payload["operation"] == "real_interpret":
            payload["provider_authorization_id"] = authorization_id
        triggers.append(schedule(store,event["kind"],payload,now+2*(index+1),f"real-followup-{index}"))
    return store.put("real_schedule","followups-v1",{"plan":plan["sha256"],"authorization_id":authorization_id,
                     "triggers":triggers},plan["available_at"],[plan["sha256"]])


def start_journey(store, history_plan, followups, authorization_id):
    previous = store.find("real_schedule","journey-v1")
    if previous:
        if previous["body"]["authorization_id"] != authorization_id:
            raise ValueError("Journey identity conflicts with its authorization")
        return previous
    task = store.get(history_plan["body"]["task"])
    sources = [store.get(sha) for sha in history_plan["body"]["sources"]+followups["body"]["sources"]]
    require_approved_scope(store,task,scope_for(task,sources),authorization_id)
    events = [{"operation":"real_interpret","source_sha256":sha,"provider_authorization_id":authorization_id}
              for sha in history_plan["body"]["sources"]]
    events.extend(({"operation":"real_compare"},
                   {"operation":"real_start_followups","provider_authorization_id":authorization_id}))
    from runtime.jobs import schedule
    now = time.time()
    triggers = [schedule(store,"event",{**payload,"scenario":history_plan["body"]["scenario"]},
                         now+2*(index+1),f"real-history-{index}") for index,payload in enumerate(events)]
    return store.put("real_schedule","journey-v1",{"history_plan":history_plan["sha256"],"followups":followups["sha256"],
                     "authorization_id":authorization_id,"triggers":triggers},followups["available_at"],
                     [history_plan["sha256"],followups["sha256"]])


def handle(store, payload):
    operation = payload["operation"]
    if operation == "real_prepare":
        return prepare_history(store, payload["scenario"])
    plan = store.get(payload["plan_sha256"]) if payload.get("plan_sha256") else store.find("real_plan", "history-v1")
    if plan is None or plan["body"]["scenario"] != payload["scenario"]:
        raise ValueError("A separate source-admission stage must complete first")
    if plan["kind"] != "real_plan":
        raise ValueError("An immutable real-model plan is required")
    if operation == "real_prepare_followups":
        return prepare_followups(store,plan)
    if operation == "real_interpret":
        return interpret_source(store, plan, payload["source_sha256"], payload["provider_authorization_id"])
    if operation == "real_compare":
        return compare_history(store, plan)
    if operation == "real_arrival_apply":
        return apply_arrival(store,plan)
    if operation in ("real_start_followups","real_start"):
        followups = store.find("real_plan","followups-v1")
        if followups is None:
            raise ValueError("Follow-up source preparation must complete first")
        if operation == "real_start":
            return start_journey(store,plan,followups,payload["provider_authorization_id"])
        return start_followups(store,followups,payload["provider_authorization_id"])
    if operation == "real_event":
        if payload["action"] not in ("outcome","acknowledge","investigate","resolve","deadline","staleness",
                                     "model_update_prepare","model_update_complete","artifact_refresh"):
            raise ValueError("Unsupported real follow-up action")
        from runtime.capability_pipeline import handle as handle_event
        return handle_event(store,{**payload,"operation":payload["action"]},task_record=store.get(plan["body"]["task"]))
    raise ValueError("Unsupported real-model stage")
