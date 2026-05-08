from collections import defaultdict
from collections.abc import Iterator
from typing import Any

import networkx as nx

__all__ = ['apply_alert_scores', 'compute_scores', 'flatten_alerts']


def _clamp_score(value: Any) -> float:
    try:
        score = float(value)
    except (TypeError, ValueError):
        return 0.0
    return max(0.0, min(1.0, score))


def _combine(scores: list[float]) -> float:
    remaining = 1.0
    for score in scores:
        remaining *= 1.0 - _clamp_score(score)
    return 1.0 - remaining


def _iter_edges(graph: nx.Graph) -> Iterator[tuple[object, object, object | None, dict]]:
    if graph.is_multigraph():
        yield from graph.edges(keys=True, data=True)
        return
    for u, v, data in graph.edges(data=True):
        yield u, v, None, data


def flatten_alerts(*groups: list[dict]) -> list[dict]:
    """Flatten detector alert groups into one alert list."""
    alerts = []
    for group in groups:
        alerts.extend(group)
    return alerts


def apply_alert_scores(
    graph: nx.Graph,
    alerts: list[dict],
) -> tuple[dict[str, float], dict[str, float]]:
    """Apply alert-based risk scores to graph nodes and edges."""
    node_alert_scores: dict[str, list[float]] = defaultdict(list)
    edge_alert_scores: dict[str, list[float]] = defaultdict(list)
    node_alert_ids: dict[str, list[str]] = defaultdict(list)
    edge_alert_ids: dict[str, list[str]] = defaultdict(list)

    for index, alert in enumerate(alerts):
        alert_id = str(alert.get('id') or f'alert_{index}')
        score = _clamp_score(alert.get('score', 0.0))
        node_ids = alert.get('node_ids') or alert.get('nodes') or []
        edge_ids = alert.get('edge_ids') or []

        for node_id in node_ids:
            node_str = str(node_id)
            node_alert_scores[node_str].append(score)
            node_alert_ids[node_str].append(alert_id)

        for edge_id in edge_ids:
            edge_str = str(edge_id)
            edge_alert_scores[edge_str].append(score)
            edge_alert_ids[edge_str].append(alert_id)

    node_scores = {
        str(node): _combine(node_alert_scores.get(str(node), []))
        for node in graph.nodes()
    }
    edge_scores: dict[str, float] = {}

    for node, attrs in graph.nodes(data=True):
        node_str = str(node)
        attrs['risk_score'] = node_scores[node_str]
        attrs['alerts'] = node_alert_ids.get(node_str, [])

    for u, v, key, attrs in _iter_edges(graph):
        edge_id = str(attrs.get('id') or attrs.get('transaction_id') or key or f'{u}->{v}')
        score = _combine(edge_alert_scores.get(edge_id, []))
        attrs['risk_score'] = score
        attrs['alerts'] = edge_alert_ids.get(edge_id, [])
        edge_scores[edge_id] = score

    return node_scores, edge_scores


def compute_scores(
    graph: nx.DiGraph,
    cycles: list[dict],
    fanout_nodes: list[dict],
    transit_nodes: list[dict],
    shared_device_nodes: list[dict],
) -> dict[str, float]:
    """Compute node risk scores from detector outputs."""
    if len(graph) == 0:
        return {}
    node_scores, _ = apply_alert_scores(
        graph,
        flatten_alerts(cycles, fanout_nodes, transit_nodes, shared_device_nodes),
    )
    return node_scores
