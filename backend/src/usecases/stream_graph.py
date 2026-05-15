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

        yield 'event: started\ndata: {}\n\n'
        yield 'event: parsed\ndata: {}\n\n'
        yield 'event: graph_built\ndata: {}\n\n'

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
                        type=attrs.get('type', attrs.get('entity_type', 'unknown')),
                        label=attrs.get('label', node_str),
                        x=x,
                        y=y,
                        risk_score=scores.get(node_str, 0.0),
                        alerts=list(attrs.get('alerts', [])),
                        in_flow=attrs.get('in_flow', 0.0),
                        out_flow=attrs.get('out_flow', 0.0),
                        is_laundering_node=attrs.get('is_laundering_node', False),
                        attributes={
                            k: list(v) if isinstance(v, set) else v
                            for k, v in attrs.items()
                            if k not in ('entity_type', 'in_flow', 'out_flow', 'is_laundering_node')
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
                    id=str(d.get('id') or d.get('transaction_id') or f'{u}->{v}'),
                    source=str(u),
                    target=str(v),
                    amount_paid=float(d.get('amount_paid', 0.0)),
                    timestamp=int(d.get('timestamp', 0)),
                    risk_score=float(d.get('risk_score', 0.0)),
                    alerts=list(d.get('alerts', [])),
                    amount_received=d.get('amount_received'),
                    payment_currency=d.get('payment_currency'),
                    receiving_currency=d.get('receiving_currency'),
                    transaction_type=d.get('transaction_type'),
                    is_laundering=d.get('is_laundering'),
                    attributes={
                        k: list(v) if isinstance(v, set) else v
                        for k, v in d.items()
                        if k
                        not in (
                            'id',
                            'transaction_id',
                            'amount_paid',
                            'timestamp',
                            'risk_score',
                            'alerts',
                            'amount_received',
                            'payment_currency',
                            'receiving_currency',
                            'transaction_type',
                            'is_laundering',
                        )
                    },
                )
                for u, v, d in batch
            ]
            chunk = EdgeChunk(edges=edge_list)
            yield f'event: edges_chunk\ndata: {chunk.model_dump_json()}\n\n'

        yield 'event: layout_done\ndata: {}\n\n'
        yield 'event: detectors_done\ndata: {}\n\n'

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

        yield 'event: scoring_done\ndata: {}\n\n'
        yield 'event: completed\ndata: {}\n\n'
        yield 'event: stream_done\ndata: {}\n\n'
