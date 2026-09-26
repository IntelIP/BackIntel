"""Bounded real-review graph; never fabricates Jev results when credentials are absent."""
from __future__ import annotations

import asyncio
from typing import TypedDict

from langgraph.graph import END, START, StateGraph

from runtime.jev import process_review_ids


class ReviewBatch(TypedDict, total=False):
    partition_id: str
    review_record_ids: list[int]
    result: dict
    previous_partition_id: str
    signal_snapshot: dict
    comparison: dict
    reuse_only: bool
    report: dict


async def enrich(state: ReviewBatch) -> ReviewBatch:
    result = await process_review_ids(
        partition_id=state["partition_id"],
        review_record_ids=state["review_record_ids"],
        reuse_only=state.get("reuse_only", True),
    )
    from runtime.signals import build_signal_snapshot, compare_signal_snapshots
    snapshot = await build_signal_snapshot(state["partition_id"])
    comparison = None
    previous = state.get("previous_partition_id")
    if previous:
        await build_signal_snapshot(previous)
        comparison = await compare_signal_snapshots(previous, state["partition_id"])
    report = None
    if comparison:
        from runtime.report import publish_review
        report = await asyncio.to_thread(publish_review, comparison, reuse_only=state.get("reuse_only", True))
    return {"result": result, "signal_snapshot": snapshot, "comparison": comparison, "report": report}


builder = StateGraph(ReviewBatch)
builder.add_node("enrich_reviews", enrich)
builder.add_edge(START, "enrich_reviews")
builder.add_edge("enrich_reviews", END)
graph = builder.compile()
