from dataclasses import dataclass, field
from typing import Any

import networkx as nx
from dishka import Provider, Scope, provide

__all__ = ['SessionStoreProvider', 'SessionStore', 'GraphSession']


@dataclass
class GraphSession:
    graph: nx.DiGraph
    layout: dict[str, tuple[float, float]]
    cycles: list[dict]
    fanout: list[dict]
    transit: list[dict]
    shared_device: list[dict]
    scores: dict[str, float]
    alerts: list[dict[str, Any]] = field(default_factory=list)
    edge_scores: dict[str, float] = field(default_factory=dict)


class SessionStore:
    def __init__(self) -> None:
        self._sessions: dict[str, GraphSession] = {}

    def save(self, session_id: str, session: GraphSession) -> None:
        self._sessions[session_id] = session

    def get(self, session_id: str) -> GraphSession | None:
        return self._sessions.get(session_id)

    def delete(self, session_id: str) -> None:
        self._sessions.pop(session_id, None)


class SessionStoreProvider(Provider):
    @provide(scope=Scope.APP)
    def get_session_store(self) -> SessionStore:
        return SessionStore()
