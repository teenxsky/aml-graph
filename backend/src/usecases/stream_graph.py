import math
from collections.abc import AsyncGenerator
from typing import Any

from src.di.providers.sessions import GraphSession, SessionStore
from src.shared.schemas import (
    DetectorResult,
    EdgeChunk,
    EdgeData,
    GraphMeta,
    NodeChunk,
    NodeData,
)

__all__ = ['StreamGraphUseCase']

_NODE_BATCH = 500
_EDGE_BATCH = 1000


def _make_serializable(items: list[dict]) -> list[dict[str, Any]]:
    """Заменяет float('inf') на None и set на list для JSON-сериализации."""
    result = []
    for item in items:
        clean: dict[str, Any] = {}
        for k, v in item.items():
            if isinstance(v, float) and math.isinf(v):
                clean[k] = None
            elif isinstance(v, set):
                clean[k] = list(v)
            else:
                clean[k] = v
        result.append(clean)
    return result


class StreamGraphUseCase:
    """Предоставляет данные сессии в виде SSE-потока для фронтенда."""

    def __init__(self, session_store: SessionStore) -> None:
        self._session_store = session_store

    def get_session(self, session_id: str) -> GraphSession | None:
        """Возвращает сессию по ID или None если не найдена."""
        return self._session_store.get(session_id)

    async def generate_events(
        self,
        session: GraphSession,
        session_id: str,
    ) -> AsyncGenerator[str]:
        """Генерирует SSE-события: метаданные, узлы, рёбра, результаты детекторов."""
        graph = session.graph
        layout = session.layout
        scores = session.scores

        meta = GraphMeta(
            session_id=session_id,
            node_count=graph.number_of_nodes(),
            edge_count=graph.number_of_edges(),
        )
        yield f'event: graph_meta\ndata: {meta.model_dump_json()}\n\n'

        nodes = list(graph.nodes(data=True))
        for i in range(0, len(nodes), _NODE_BATCH):
            batch = nodes[i : i + _NODE_BATCH]
            node_list = []
            for node_id, attrs in batch:
                node_str = str(node_id)
                x, y = layout.get(node_str, (0.0, 0.0))
                node_list.append(
                    NodeData(
                        id=node_str,
                        entity_type=attrs.get('entity_type', 'unknown'),
                        x=x,
                        y=y,
                        risk_score=scores.get(node_str, 0.0),
                        attributes={
                            k: list(v) if isinstance(v, set) else v
                            for k, v in attrs.items()
                            if k != 'entity_type'
                        },
                    ),
                )
            chunk = NodeChunk(nodes=node_list)
            yield f'event: nodes_chunk\ndata: {chunk.model_dump_json()}\n\n'

        edges = list(graph.edges(data=True))
        for i in range(0, len(edges), _EDGE_BATCH):
            batch = edges[i : i + _EDGE_BATCH]
            edge_list = [
                EdgeData(
                    source=str(u),
                    target=str(v),
                    amount=float(d.get('amount', 0.0)),
                    timestamp=int(d.get('timestamp', 0)),
                )
                for u, v, d in batch
            ]
            chunk = EdgeChunk(edges=edge_list)
            yield f'event: edges_chunk\ndata: {chunk.model_dump_json()}\n\n'

        yield 'event: layout_done\ndata: {}\n\n'

        for pattern_type, items in [
            ('cycles', session.cycles),
            ('fanout', session.fanout),
            ('transit', session.transit),
            ('shared_device', session.shared_device),
        ]:
            result = DetectorResult(
                pattern_type=pattern_type,
                items=_make_serializable(items),
            )
            yield f'event: detector_result\ndata: {result.model_dump_json()}\n\n'

        yield 'event: stream_done\ndata: {}\n\n'
