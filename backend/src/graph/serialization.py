import math
from collections.abc import Iterator
from typing import Any

import networkx as nx

__all__ = [
    'build_graph_payload',
    'build_session_stats',
    'collect_filters',
]


def _as_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except TypeError, ValueError:
        return default


def _as_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except TypeError, ValueError:
        return default


def _safe(value: Any) -> Any:
    if isinstance(value, set):
        return sorted(str(v) for v in value)
    if isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
        return None
    return value


def _edge_iter(graph: nx.Graph) -> Iterator[tuple[object, object, object | None, dict]]:
    if graph.is_multigraph():
        yield from graph.edges(keys=True, data=True)
        return
    for u, v, data in graph.edges(data=True):
        yield u, v, None, data


def build_graph_payload(
    graph: nx.Graph,
    layout: dict[str, tuple[float, float]],
) -> dict[str, list[dict[str, Any]]]:
    """Build frontend-friendly graph payload with coordinates and risk data."""
    nodes = []
    for node_id, attrs in graph.nodes(data=True):
        node_str = str(node_id)
        x, y = layout.get(node_str, (0.0, 0.0))
        excluded = {'id', 'type', 'entity_type', 'label', 'risk_score', 'alerts'}
        nodes.append(
            {
                'id': node_str,
                'type': attrs.get('type', attrs.get('entity_type', 'unknown')),
                'label': attrs.get('label', node_str),
                'x': float(x),
                'y': float(y),
                'risk_score': float(attrs.get('risk_score', 0.0)),
                'alerts': list(attrs.get('alerts', [])),
                'attributes': {k: _safe(v) for k, v in attrs.items() if k not in excluded},
            },
        )

    edges = []
    for u, v, key, attrs in _edge_iter(graph):
        edge_id = str(attrs.get('id') or attrs.get('transaction_id') or key or f'{u}->{v}')
        excluded = {
            'id',
            'transaction_id',
            'amount',
            'amount_paid',
            'timestamp',
            'risk_score',
            'alerts',
        }
        edges.append(
            {
                'id': edge_id,
                'source': str(u),
                'target': str(v),
                'amount': _as_float(attrs.get('amount', attrs.get('amount_paid', 0.0))),
                'timestamp': _as_int(attrs.get('timestamp')),
                'risk_score': _as_float(attrs.get('risk_score')),
                'alerts': list(attrs.get('alerts', [])),
                'attributes': {k: _safe(v) for k, v in attrs.items() if k not in excluded},
            },
        )

    return {'nodes': nodes, 'edges': edges}


def build_session_stats(
    graph: nx.Graph,
    alerts: list[dict[str, Any]],
) -> dict[str, Any]:
    """Build aggregate graph statistics for a session."""
    timestamps = [
        _as_int(d.get('timestamp'))
        for _, _, _, d in _edge_iter(graph)
        if d.get('timestamp') is not None
    ]
    amounts = [
        float(d.get('amount', d.get('amount_paid', 0.0))) for _, _, _, d in _edge_iter(graph)
    ]
    laundering = [
        _as_int(d.get('is_laundering'))
        for _, _, _, d in _edge_iter(graph)
        if d.get('is_laundering') is not None
    ]
    node_scores = [float(d.get('risk_score', 0.0)) for _, d in graph.nodes(data=True)]
    edge_scores = [float(d.get('risk_score', 0.0)) for _, _, _, d in _edge_iter(graph)]
    return {
        'node_count': graph.number_of_nodes(),
        'edge_count': graph.number_of_edges(),
        'alert_count': len(alerts),
        'max_risk_score': max([*node_scores, *edge_scores], default=0.0),
        'laundering_label_count': sum(laundering),
        'amount_sum': sum(amounts),
        'time_min': min(timestamps) if timestamps else None,
        'time_max': max(timestamps) if timestamps else None,
    }


def collect_filters(graph: nx.Graph, alerts: list[dict[str, Any]]) -> dict[str, list[Any]]:
    """Collect available filter values from graph attributes and alerts."""
    alert_types = sorted({str(a.get('type')) for a in alerts if a.get('type')})
    payment_formats = sorted(
        {
            str(d.get('payment_format') or d.get('transaction_type'))
            for _, _, _, d in _edge_iter(graph)
            if d.get('payment_format') or d.get('transaction_type')
        },
    )
    currencies = sorted(
        {
            str(c)
            for _, _, _, d in _edge_iter(graph)
            for c in (d.get('payment_currency'), d.get('receiving_currency'))
            if c
        },
    )
    return {
        'alert_types': alert_types,
        'payment_formats': payment_formats,
        'currencies': currencies,
    }
