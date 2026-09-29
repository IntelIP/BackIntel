"""Run the same simulation through the existing LangGraph/application ledger."""
from __future__ import annotations

import asyncio
import os
import time
from pathlib import Path
from typing import TypedDict

from langgraph.graph import END, START, StateGraph

from runtime.costs import record_usage
from runtime.ledger import accept, admit
from runtime.simulation import ENGINE_VERSION, digest, load_scenario, normalize, publish, simulate


class Simulation(TypedDict, total=False):
    scenario: str
    partition_id: str
    result: dict
    report: dict


async def process(state: Simulation) -> Simulation:
    config = load_scenario(state["scenario"])
    identifier = state["partition_id"]
    if not isinstance(identifier, str) or not identifier.startswith("simulation-") or len(identifier) > 80:
        raise ValueError("Simulation partition must start with simulation- and contain at most 80 characters")
    count = len(normalize(config))
    fingerprint = digest({"engine": ENGINE_VERSION, "config": config})
    started, outcome = time.monotonic(), "error"
    try:
        await admit(identifier, count, fingerprint)
        result = await asyncio.to_thread(simulate, config)
        await accept(identifier, count, fingerprint, digest(result))
        output = Path(os.environ.get("BACKINTEL_REPORT_DIR", "/reports")) / "Simulation"
        report = await asyncio.to_thread(publish, result, output)
        outcome = "success"
        return {"result": result, "report": report}
    except asyncio.CancelledError:
        outcome = "cancelled"
        raise
    finally:
        await record_usage(partition_id=identifier, stage="runtime", provider="local", outcome=outcome,
                           record_count=count, wall_ms=round((time.monotonic() - started) * 1000),
                           charge_status="not_applicable")


builder = StateGraph(Simulation)
builder.add_node("simulate_capabilities", process)
builder.add_edge(START, "simulate_capabilities")
builder.add_edge("simulate_capabilities", END)
graph = builder.compile()
