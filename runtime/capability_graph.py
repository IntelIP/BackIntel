"""Generic Aegra/LangGraph entry points for durable capability jobs and native cron ticks."""
import asyncio
import re
from typing import TypedDict

import psycopg
from langgraph.graph import END, START, StateGraph

from runtime.evidence import Evidence
from runtime.jobs import cancel, dispatch, enqueue, execute
from runtime.ledger import dsn
from runtime.simulation import load_scenario


class CapabilityState(TypedDict, total=False):
    operation: str
    scenario: str
    request_id: str
    job_id: str
    task_ids: list[str]
    demo_id: str
    source_sha256: str
    plan_sha256: str
    provider_authorization_id: str
    result: dict


async def process(state: CapabilityState) -> dict:
    if state.get("operation") == "dispatch":
        task_ids = state.get("task_ids")
        if task_ids is not None and (not isinstance(task_ids,list) or not 1 <= len(task_ids) <= 2 or
                any(not isinstance(t,str) or not re.fullmatch(r"(?:support|equipment)-real-[a-z][a-z0-9-]{0,24}",t) for t in task_ids)):
            raise ValueError("Scoped real dispatch requires one or two exact real task identities")
        return {"result":await asyncio.to_thread(dispatch,task_ids)}
    if state.get("operation") == "cancel":
        with psycopg.connect(dsn(),autocommit=True) as connection:
            return {"result":{"state":cancel(connection,state["job_id"])}}
    operation = state.get("operation")
    if operation not in ("bootstrap", "real_prepare", "real_interpret", "real_compare", "real_prepare_followups", "real_start_followups", "real_start"):
        raise ValueError("Unsupported generic pipeline operation")
    config = load_scenario(state["scenario"])
    demo_id = state.get("demo_id","development-v1")
    if not isinstance(demo_id,str) or not re.fullmatch(r"[a-z][a-z0-9-]{0,24}",demo_id):
        raise ValueError("Invalid demonstration identity")
    request_id = state["request_id"]
    if not isinstance(request_id,str) or not 1 <= len(request_id) <= 100:
        raise ValueError("Bounded request identity required")
    with psycopg.connect(dsn(),autocommit=True) as connection:
        payload = {"scenario": config["id"], "operation": operation}
        if operation == "real_interpret":
            if not re.fullmatch(r"[a-f0-9]{64}", state.get("source_sha256", "")) or not isinstance(state.get("provider_authorization_id"), str):
                raise ValueError("Interpretation requires a source hash and named authorization")
            payload.update(source_sha256=state["source_sha256"], provider_authorization_id=state["provider_authorization_id"])
            if state.get("plan_sha256"):
                if not re.fullmatch(r"[a-f0-9]{64}",state["plan_sha256"]):
                    raise ValueError("Interpretation plan requires an exact evidence hash")
                payload["plan_sha256"] = state["plan_sha256"]
        if operation in ("real_start_followups","real_start"):
            if not isinstance(state.get("provider_authorization_id"),str) or not 1 <= len(state["provider_authorization_id"]) <= 128:
                raise ValueError("Follow-up execution requires a named authorization")
            payload["provider_authorization_id"] = state["provider_authorization_id"]
        prefix = "-real-" if operation.startswith("real_") else "-"
        job_id = enqueue(Evidence(connection,f"{config['id']}{prefix}{demo_id}"),payload,request_id)
    try:
        return {"job_id":job_id,"result":await asyncio.to_thread(execute,job_id)}
    except asyncio.CancelledError:
        with psycopg.connect(dsn(),autocommit=True) as connection:
            cancel(connection,job_id)
        raise


builder = StateGraph(CapabilityState)
builder.add_node("durable_capabilities",process)
builder.add_edge(START,"durable_capabilities")
builder.add_edge("durable_capabilities",END)
graph = builder.compile()
