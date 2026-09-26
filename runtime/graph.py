"""A bounded, deterministic stand-in for an Olist partition; no model or Kaggle data."""
from __future__ import annotations

import asyncio
import hashlib
from typing import TypedDict

from langgraph.graph import END, START, StateGraph

from runtime.ledger import accept, admit


class Partition(TypedDict, total=False):
    partition_id: str
    record_count: int
    delay_seconds: int
    processed_count: int
    digest: str


async def process(state: Partition) -> Partition:
    identifier = state["partition_id"]
    count = state["record_count"]
    delay = state.get("delay_seconds", 4)
    if not isinstance(identifier, str) or not identifier or len(identifier) > 80:
        raise ValueError("partition_id must be a nonempty string of at most 80 characters")
    if type(count) is not int or not 1 <= count <= 100:
        raise ValueError("record_count must be an integer from 1 to 100")
    if type(delay) is not int or not 0 <= delay <= 20:
        raise ValueError("delay_seconds must be an integer from 0 to 20")
    digest = hashlib.sha256(f"{identifier}:{count}".encode()).hexdigest()
    await admit(identifier, count, digest)
    await asyncio.sleep(delay)  # Keep worker heartbeats responsive during the demo.
    await accept(identifier, count, digest)
    return {"processed_count": count, "digest": digest}


builder = StateGraph(Partition)
builder.add_node("process", process)
builder.add_edge(START, "process")
builder.add_edge("process", END)
graph = builder.compile()
