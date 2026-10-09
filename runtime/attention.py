"""Durable attention episodes and a local-only, deduplicated delivery ledger."""
from runtime.simulation import digest


def latest_episode(store, entity: str, task_sha256: str) -> dict | None:
    history = [r for r in store.list("episode") if r["body"]["entity"] == entity and r["body"].get("task") == task_sha256]
    return max(history,key=lambda r:r["body"]["sequence"],default=None)


def attend(store, task_record: dict, entity: str, reason: dict, at: int, value: float | None = None,
           action="observe", actor="simulated-operator") -> dict:
    if action not in ("observe","acknowledge","investigate","resolve","staleness","deadline"):
        raise ValueError("Unsupported attention action")
    policy = task_record["body"]["policy"]
    key = digest([task_record["sha256"],entity,reason["sha256"],action])
    with store.connection.transaction():
        store.lock()
        previous = store.find("episode",key)
        if previous:
            return previous
        latest = latest_episode(store,entity,task_record['sha256'])
        old = latest["body"] if latest else {}
        if latest and at < latest["available_at"]:
            raise ValueError("Cannot backdate attention actions")
        state = {"entity":entity,"episode_id":old.get("episode_id"),"condition":old.get("condition","cleared"),
                 "response":old.get("response","open"),"last_observed_at":old.get("last_observed_at"),
                 "last_delivery_at":old.get("last_delivery_at"),"opened_at":old.get("opened_at"),
                 "sequence":old.get("sequence",0)+1,"value":old.get("value"),"action":action,"actor":actor,
                 "policy_sha256":digest(policy),"reason":reason["sha256"],"task":task_record["sha256"]}
        notify = None
        if action == "observe":
            state.update(last_observed_at=at,value=value)
            if value is None:
                state["condition"] = "unknown"
            elif value >= policy["entry"]:
                state["condition"] = "active"
                if old.get("condition","cleared") == "cleared" or not state["episode_id"]:
                    state.update(episode_id=digest([task_record['sha256'],entity,reason["sha256"]]),response="open",opened_at=at)
                    notify = "opened"
                elif old.get("condition") == "unknown" and (state["last_delivery_at"] is None or at-state["last_delivery_at"] >= policy["cooldown"]):
                    notify = "updated"
            elif value <= policy["clear"]:
                state["condition"] = "cleared"
            # Between thresholds retains the previous condition (hysteresis).
        elif action in ("acknowledge","investigate","resolve"):
            if state["condition"] == "cleared" or not state["episode_id"]:
                raise ValueError("Response action requires an open episode")
            if actor != "simulated-operator":
                audience = next((a for a in task_record["body"]["audiences"] if a["id"] == actor),None)
                if not audience or not audience["can_correct"] or (audience["entities"] and entity not in audience["entities"]):
                    raise PermissionError("Actor cannot respond to this episode")
            state["response"] = {"acknowledge":"acknowledged","investigate":"investigating","resolve":"resolved"}[action]
        elif action == "staleness":
            if state["condition"] != "cleared" and state["last_observed_at"] is not None and at-state["last_observed_at"] >= policy["stale_after"]:
                state["condition"] = "unknown"
        elif action == "deadline" and state["episode_id"] and state["condition"] != "cleared" and state["response"] == "open":
            if at-state["opened_at"] >= policy["response_deadline"] and (state["last_delivery_at"] is None or at-state["last_delivery_at"] >= policy["cooldown"]):
                notify = "response_overdue"
        if notify:
            state["last_delivery_at"] = at
        parents = [task_record["sha256"],reason["sha256"]] + ([latest["sha256"]] if latest else [])
        saved = store.put("episode",key,state,at,parents)
        if notify:
            delivery_key = digest([state["episode_id"],notify, reason["sha256"] if notify == "updated" else None])
            if not store.find("delivery",delivery_key):
                store.put("delivery",delivery_key,{"episode":saved["sha256"],"episode_id":state["episode_id"],
                          "entity":entity,"reason":notify,"channel":"local_inbox","status":"delivered", "external_messages":0},at,[saved["sha256"]])
        return saved
