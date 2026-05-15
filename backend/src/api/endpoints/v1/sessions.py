from typing import Annotated

import networkx as nx
from dishka.integrations.fastapi import DishkaRoute, FromDishka
from fastapi import APIRouter, HTTPException, Query

from src.di.providers.sessions import GraphSession, SessionStore
from src.graph.serialization import build_graph_payload, build_session_stats, collect_filters

router = APIRouter(route_class=DishkaRoute)


def _get_session(session_store: SessionStore, session_id: str) -> GraphSession:
    session = session_store.get(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail='Session not found')
    return session


@router.get('/sessions/{session_id}/stats')
async def get_session_stats(
    session_id: str,
    session_store: FromDishka[SessionStore],
) -> dict:
    """Return aggregate statistics for a graph session."""
    session = _get_session(session_store, session_id)
    return build_session_stats(session.graph, session.alerts)


@router.get('/sessions/{session_id}/graph')
async def get_session_graph(
    session_id: str,
    session_store: FromDishka[SessionStore],
) -> dict:
    """Return serialized graph payload for a session."""
    session = _get_session(session_store, session_id)
    return build_graph_payload(session.graph, session.layout)


@router.get('/sessions/{session_id}/alerts')
async def get_session_alerts(
    session_id: str,
    session_store: FromDishka[SessionStore],
) -> dict:
    """Return detector alerts for a session."""
    session = _get_session(session_store, session_id)
    return {'alerts': session.alerts}


@router.get('/sessions/{session_id}/filters')
async def get_session_filters(
    session_id: str,
    session_store: FromDishka[SessionStore],
) -> dict:
    """Return available filter values for a session."""
    session = _get_session(session_store, session_id)
    return collect_filters(session.graph, session.alerts)


@router.get('/sessions/{session_id}/subgraph')
async def get_session_subgraph(
    session_id: str,
    session_store: FromDishka[SessionStore],
    node_id: Annotated[str, Query(...)],
    k: Annotated[int, Query(ge=1, le=6)] = 2,
) -> dict:
    """Return a k-hop subgraph around a node."""
    session = _get_session(session_store, session_id)
    graph = session.graph
    if node_id not in graph:
        raise HTTPException(status_code=404, detail='Node not found')

    undirected = graph.to_undirected()
    lengths = nx.single_source_shortest_path_length(undirected, node_id, cutoff=k)
    nodes = list(lengths.keys())
    subgraph = graph.subgraph(nodes).copy()
    layout = {node: session.layout.get(node, (0.0, 0.0)) for node in nodes}
    return build_graph_payload(subgraph, layout)
