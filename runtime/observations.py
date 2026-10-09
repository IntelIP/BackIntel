"""Typed Jev-style boundary with deterministic simulated responses; no real Jev execution."""
from __future__ import annotations

from runtime.contracts import number
from runtime.simulation import digest

PROVIDER = {"name": "synthetic-jev-contract", "version": "1", "implementation_mode": "simulated"}


def simulated_response(question: dict, content: str | None) -> dict:
    if content is None or not content.strip():
        return {"status": "unknown", "value": None, "distribution": None, "reason": "missing_content"}
    if content.startswith("[abstain]"):
        return {"status": "abstained", "value": None, "distribution": None, "reason": "simulated_ambiguity"}
    if question["type"] == "boolean":
        value = any(term.casefold() in content.casefold() for term in question["rule"]["terms"])
        probability = .9 if value else .1
        distribution = {"false": 1 - probability, "true": probability}
    else:
        try:
            value = float(content)
        except ValueError:
            return {"status": "abstained", "value": None, "distribution": None, "reason": "not_numeric_text"}
        distribution = None
    return {"status": "known", "value": value, "distribution": distribution, "reason": "simulated_response"}


def validate_response(question: dict, response: dict) -> None:
    if set(response) != {"status", "value", "distribution", "reason"} or response["status"] not in ("known", "unknown", "abstained"):
        raise ValueError("Provider returned invalid typed response")
    if not isinstance(response["reason"], str) or not response["reason"] or len(response["reason"]) > 1000:
        raise ValueError("Response requires bounded reason")
    value, distribution = response["value"], response["distribution"]
    if response["status"] != "known":
        if value is not None or distribution is not None:
            raise ValueError("Unknown/abstained cannot carry a value or distribution")
    elif question["type"] == "boolean":
        if type(value) is not bool or not isinstance(distribution, dict) or set(distribution) != {"true", "false"}:
            raise ValueError("Boolean response requires boolean value and binary distribution")
        if any(not number(v) or not 0 <= v <= 1 for v in distribution.values()) or abs(sum(distribution.values()) - 1) > 1e-9:
            raise ValueError("Invalid probability distribution")
        if value != (distribution["true"] >= .5):
            raise ValueError("Boolean value conflicts with its distribution")
    elif not number(value):
        raise ValueError("Numeric response requires finite value")
    elif distribution is not None:
        if not isinstance(distribution,dict) or set(distribution) != {"values","probabilities"}:
            raise ValueError("Numeric distribution requires values and probabilities")
        values, probabilities = distribution["values"], distribution["probabilities"]
        if not isinstance(values,list) or not isinstance(probabilities,list) or not values or len(values) != len(probabilities):
            raise ValueError("Numeric distribution has invalid dimensions")
        if any(not number(v) for v in values) or any(not number(p) or not 0 <= p <= 1 for p in probabilities) or abs(sum(probabilities)-1) > 1e-6:
            raise ValueError("Invalid numeric probability distribution")
        if abs(sum(v*p for v,p in zip(values,probabilities))-value) > 1e-4:
            raise ValueError("Numeric answer conflicts with its distribution")


def extract(store, task_record: dict, source: dict, at: int, response_provider=simulated_response,
            provider=None) -> list[dict]:
    provider = provider or task_record["body"]["observation_provider"]
    if provider["implementation_mode"] == "real":
        from runtime.real_semantics import extract_real
        return extract_real(store,task_record,source,at)
    if provider.get("implementation_mode") != "simulated" or set(provider) != {"name", "version", "implementation_mode"}:
        raise ValueError("Only explicitly identified simulated providers are permitted")
    task, observations = task_record["body"], []
    with store.connection.transaction():
        store.lock()
        for question in task["questions"]:
            cache_key = digest({"source": source["sha256"], "task": task_record["sha256"], "question": question, "provider": provider})
            cached = store.find("observation", cache_key)
            if cached:
                observations.append(cached)
                continue
            attempts = store.list("extraction_attempt")
            prior = [r for r in attempts if r["body"]["cache_key"] == cache_key]
            for attempt in range(len(prior) + 1, task["policy"]["max_attempts"] + 1):
                if len(attempts) >= task["policy"]["max_provider_calls"]:
                    break
                response, error = None, None
                try:
                    response = response_provider(question, source["body"]["content"])
                    validate_response(question, response)
                except (ValueError, TypeError, KeyError, TimeoutError) as failure:
                    error = str(failure)
                    response = None
                attempt_record = store.put("extraction_attempt", f"{cache_key}:{attempt}", {
                    "cache_key": cache_key, "attempt": attempt, "provider": provider,
                    "status": "failed" if error else "passed", "error": error,
                    "response": response, "provider_calls": 0, "simulated_provider_calls": 1,
                    "simulated_charge_usd": .0001, "measured_provider_usd": 0, "local_compute_usd": None,
                }, at, [source["sha256"], task_record["sha256"]])
                prior.append(attempt_record)
                attempts.append(attempt_record)
                if not error:
                    break
            success = next((r for r in reversed(prior) if r["body"]["status"] == "passed"), None)
            response = success["body"]["response"] if success else {
                "status": "unknown", "value": None, "distribution": None,
                "reason": "attempts_exhausted" if len(prior) >= task["policy"]["max_attempts"] else "provider_budget_exhausted"}
            observations.append(store.put("observation", cache_key, {
                "source": source["sha256"], "question_id": question["id"], "question": question,
                "provider": provider, "response": response, "task": task_record["sha256"],
            }, at, [source["sha256"], task_record["sha256"], *[r["sha256"] for r in prior]]))
    return observations


def correct_observation(store, observation_sha: str, response: dict, actor: str, reason: str,
                        at: int, supersedes: str | None = None) -> dict:
    original = store.get(observation_sha)
    if original["kind"] != "observation":
        raise ValueError("Correction requires original observation")
    task = store.get(original["body"]["task"])["body"]
    audience = next((a for a in task["audiences"] if a["id"] == actor), None)
    source = store.get(original["body"]["source"])["body"]
    if not audience or not audience["can_correct"] or (audience["entities"] and source["entity"] not in audience["entities"]):
        raise PermissionError("Actor cannot correct this entity")
    if not isinstance(reason, str) or not reason.strip() or len(reason) > 1000:
        raise ValueError("Correction requires bounded reason")
    validate_response(original["body"]["question"], response)
    if (original["body"]["question"]["id"] == task["policy"]["signal_question"]
            and original["body"]["question"]["type"] != "boolean" and response["status"] == "known"):
        values = [response["value"]] + (response.get("distribution") or {}).get("values", [])
        if any(not 0 <= value <= task["policy"]["signal_scale"] for value in values):
            raise ValueError("Numeric correction must remain within the task signal scale")
    body = {"observation": observation_sha, "response": response, "actor": actor, "reason": reason, "supersedes": supersedes}
    identity = digest(body)
    with store.connection.transaction():
        store.lock()
        replay = store.find("correction", identity)
        if replay:
            return replay
        history = [r for r in store.list("correction") if r["body"]["observation"] == observation_sha]
        latest = max(history, key=lambda r: (r["available_at"], r["body"]["sequence"]), default=None)
        if supersedes != (latest["sha256"] if latest else None):
            raise ValueError("Correction must supersede the current correction")
        body["sequence"] = len(history) + 1
        return store.put("correction", identity, body, at, [observation_sha] + ([supersedes] if supersedes else []))


def effective_observation(store, observation_sha: str, cutoff: int) -> dict:
    original = store.get(observation_sha)
    if original["available_at"] > cutoff:
        raise ValueError("Observation unavailable at cutoff")
    history = [r for r in store.list("correction", cutoff) if r["body"]["observation"] == observation_sha]
    return max(history, key=lambda r: (r["available_at"], r["body"]["sequence"]), default=original)
