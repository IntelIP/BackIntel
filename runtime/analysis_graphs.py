"""Aegra supplies the checkpoint store; application tools persist their own receipts."""
import asyncio
from typing import TypedDict

from langgraph.graph import StateGraph, START, END
from runtime import analysis_service as service
from runtime import analysis_store as db


class GoalState(TypedDict, total=False):
    goal_id: str
    result: dict


class RunState(TypedDict, total=False):
    run_id: str
    result: dict


async def resolve(state: GoalState):
    g = db.goal(state['goal_id'])
    db.authorize({'id':g['owner']}, g['domain'], ('manager',))
    return {'result': {'goal':g['id'],'definitions':g['body']['definitions'],'needs_confirmation':not g['confirmed']}}


async def analysis(state: RunState):
    return {'result': await asyncio.to_thread(service.dispatch, state['run_id'])}


async def refresh_sources(state: RunState):
    return {'result': await asyncio.to_thread(service.refresh)}


def workflow(state, name, function):
    graph = StateGraph(state)
    graph.add_node(name, function)
    graph.add_edge(START, name)
    graph.add_edge(name, END)
    return graph.compile()


goal_graph = workflow(GoalState, 'resolve_and_propose', resolve)
analysis_graph = workflow(RunState, 'bounded_analysis', analysis)
refresh_graph = workflow(RunState, 'refresh_and_dispatch', refresh_sources)
