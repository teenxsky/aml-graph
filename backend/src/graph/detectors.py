import math
from collections import defaultdict
from typing import Any

import networkx as nx

__all__ = ['detect_cycles', 'detect_fanout', 'detect_transit', 'detect_shared_device']


def _amount(data: dict[str, Any]) -> float:
    value = data.get('amount', data.get('amount_paid', 0.0))
    try:
        return float(value)
    except TypeError, ValueError:
        return 0.0


def _timestamp(data: dict[str, Any]) -> int:
    value = data.get('timestamp', 0)
    try:
        return int(value)
    except TypeError, ValueError:
        return 0


def _edge_id(u: object, v: object, data: dict[str, Any]) -> str:
    return str(data.get('id') or data.get('transaction_id') or f'{u}->{v}:{_timestamp(data)}')


def _clamp(value: float) -> float:
    return max(0.0, min(1.0, value))


def _edge_data_between(
    graph: nx.DiGraph | nx.MultiDiGraph,
    u: object,
    v: object,
) -> list[dict[str, Any]]:
    edge_data = graph.get_edge_data(u, v)

    if edge_data is None:
        return []

    if graph.is_multigraph():
        return [dict(data) for data in edge_data.values() if isinstance(data, dict)]

    if isinstance(edge_data, dict):
        return [dict(edge_data)]

    return []


def _iter_out_edges(
    graph: nx.DiGraph | nx.MultiDiGraph,
    node: object,
) -> list[tuple[object, object, dict[str, Any]]]:
    if graph.is_multigraph():
        return [(u, v, data) for u, v, _, data in graph.out_edges(node, keys=True, data=True)]
    return list(graph.out_edges(node, data=True))


def _iter_edges(
    graph: nx.DiGraph | nx.MultiDiGraph,
) -> list[tuple[object, object, dict[str, Any]]]:
    if graph.is_multigraph():
        return [(u, v, data) for u, v, _, data in graph.edges(keys=True, data=True)]
    return list(graph.edges(data=True))


def detect_cycles(graph: nx.DiGraph, max_delta_seconds: int = 86400) -> list[dict]:
    """Detect directed transaction cycles of length 2-6.

    Each alert includes cycle nodes, transfer edge IDs, time span, total amount,
    preservation ratio rho = min(amount) / max(amount), and optional drain rate.
    Cycles outside the configured time window are ignored.
    """
    if len(graph) == 0:
        return []

    results = []
    simple_graph = nx.DiGraph(graph)
    for index, cycle in enumerate(nx.simple_cycles(simple_graph, length_bound=6)):
        if len(cycle) < 2:
            continue

        edges = [(cycle[i], cycle[(i + 1) % len(cycle)]) for i in range(len(cycle))]
        timestamps: list[int] = []
        amounts_paid: list[float] = []
        amounts_received: list[float | None] = []
        edge_ids: list[str] = []
        for u, v in edges:
            candidates = _edge_data_between(graph, u, v)
            if not candidates:
                break
            data = sorted(candidates, key=_timestamp)[0]
            timestamps.append(_timestamp(data))
            amounts_paid.append(_amount(data))
            amounts_received.append(data.get('amount_received'))
            edge_ids.append(_edge_id(u, v, data))
        else:
            delta_t = max(timestamps) - min(timestamps) if timestamps else 0
            if delta_t > max_delta_seconds:
                continue

            total_weight = sum(amounts_paid)
            max_amount = max(amounts_paid, default=0.0)
            min_amount = min(amounts_paid, default=0.0)
            rho = min_amount / max_amount if max_amount > 0 else 0.0

            if all(a is not None for a in amounts_received):
                sum_received = sum(amounts_received)  # type: ignore[arg-type]
                drain_rate: float | None = (
                    (total_weight - sum_received) / total_weight if total_weight > 0 else None
                )
            else:
                drain_rate = None

            score = _clamp(0.35 + 0.45 * rho + 0.20 * (1.0 - min(delta_t / max_delta_seconds, 1.0)))
            results.append(
                {
                    'id': f'cycle_{index}',
                    'type': 'cycle',
                    'score': score,
                    'node_ids': [str(n) for n in cycle],
                    'edge_ids': edge_ids,
                    'metrics': {
                        'length': len(cycle),
                        'delta_t': delta_t,
                        'total_weight': total_weight,
                        'rho': rho,
                        'drain_rate': drain_rate,
                    },
                    'nodes': [str(n) for n in cycle],
                    'length': len(cycle),
                    'delta_t': delta_t,
                    'total_weight': total_weight,
                    'rho': rho,
                    'drain_rate': drain_rate,
                },
            )

    return results


def detect_fanout(
    graph: nx.DiGraph,
    min_receivers: int = 3,
    time_window_seconds: int = 86400,
    max_cv: float = 0.3,
) -> list[dict]:
    """Обнаруживает smurfing: один отправитель → N+ получателей с похожими суммами за 24 ч."""
    if len(graph) == 0:
        return []

    results = []

    for node in graph.nodes():
        out_edges = _iter_out_edges(graph, node)
        if len(out_edges) < min_receivers:
            continue

        out_edges.sort(key=lambda e: _timestamp(e[2]))

        found = False
        for i in range(len(out_edges)):
            if found:
                break

            t_start = _timestamp(out_edges[i][2])
            window = [e for e in out_edges[i:] if _timestamp(e[2]) - t_start <= time_window_seconds]

            receiver_amounts: dict[str, float] = defaultdict(float)
            edge_ids: list[str] = []
            for _, recv, data in window:
                receiver_amounts[str(recv)] += _amount(data)
                edge_ids.append(_edge_id(node, recv, data))

            if len(receiver_amounts) < min_receivers:
                continue

            amounts = list(receiver_amounts.values())
            mean = sum(amounts) / len(amounts)
            if mean == 0:
                continue

            variance = sum((a - mean) ** 2 for a in amounts) / len(amounts)
            std = math.sqrt(variance)
            cv = std / mean

            if cv <= max_cv:
                high_risk_format = any(
                    (data.get('payment_format') or data.get('transaction_type') or '').upper()
                    == 'CASH'
                    for _, _, data in window
                )
                score = _clamp(
                    0.45 + 0.35 * (1.0 - min(cv / max_cv, 1.0)) + 0.20 * high_risk_format,
                )
                results.append(
                    {
                        'id': f'fanout_{node}_{i}',
                        'type': 'fanout',
                        'score': score,
                        'node_ids': [str(node), *list(receiver_amounts.keys())],
                        'edge_ids': edge_ids,
                        'metrics': {
                            'receiver_count': len(receiver_amounts),
                            'time_window': time_window_seconds,
                            'amount_mean': mean,
                            'amount_std': std,
                            'cv': cv,
                            'high_risk_format': high_risk_format,
                        },
                        'source_node': str(node),
                        'source': str(node),
                        'receivers': list(receiver_amounts.keys()),
                        'time_window': time_window_seconds,
                        'amount_mean': mean,
                        'amount_std': std,
                        'cv': cv,
                        'high_risk_format': high_risk_format,
                    },
                )
                found = True

    return results


def detect_transit(graph: nx.DiGraph, top_k: int = 50) -> list[dict]:
    """Определяет транзитные узлы: высокая betweenness + входящий ≈ исходящий поток.

    Входящий поток вычисляется через amount_received (точный баланс при FX-конвертации),
    при отсутствии — через amount_paid.
    """
    if len(graph) == 0:
        return []

    simple_graph = nx.DiGraph(graph)
    if len(simple_graph) <= 200:
        centrality = nx.betweenness_centrality(simple_graph, normalized=True)
    else:
        centrality = nx.betweenness_centrality(
            simple_graph,
            k=min(100, len(simple_graph)),
            normalized=True,
            seed=42,
        )

    in_flow: dict[str, float] = defaultdict(float)
    out_flow: dict[str, float] = defaultdict(float)
    for u, v, data in _iter_edges(graph):
        amount_paid = _amount(data)
        amount_received = data.get('amount_received')
        in_val = amount_received if amount_received is not None else amount_paid
        out_flow[str(u)] += amount_paid
        in_flow[str(v)] += in_val

    results = []
    for node in graph.nodes():
        if graph.in_degree(node) == 0 or graph.out_degree(node) == 0:
            continue

        node_str = str(node)
        in_f = in_flow.get(node_str, 0.0)
        out_f = out_flow.get(node_str, 0.0)
        denom = max(in_f, out_f)

        if denom == 0:
            continue

        balance_deviation = abs(in_f - out_f) / denom
        balance_ratio = 1.0 - balance_deviation
        if balance_ratio >= 0.8:
            score = _clamp(0.45 + 0.35 * balance_ratio + 0.20 * centrality.get(node, 0.0))
            results.append(
                {
                    'id': f'transit_{node_str}',
                    'type': 'transit',
                    'score': score,
                    'node_ids': [node_str],
                    'edge_ids': [
                        _edge_id(u, v, data)
                        for u, v, data in _iter_edges(graph)
                        if str(u) == node_str or str(v) == node_str
                    ],
                    'metrics': {
                        'f_in': in_f,
                        'f_out': out_f,
                        'balance_ratio': balance_ratio,
                        'balance_deviation': balance_deviation,
                        'in_degree': graph.in_degree(node),
                        'out_degree': graph.out_degree(node),
                        'betweenness': centrality.get(node, 0.0),
                    },
                    'node_id': node_str,
                    'f_in': in_f,
                    'f_out': out_f,
                    'betweenness': centrality.get(node, 0.0),
                    'flow_ratio': balance_deviation,
                    'balance_ratio': balance_ratio,
                },
            )

    results.sort(key=lambda x: x['betweenness'], reverse=True)
    return results[:top_k]


def detect_shared_device(graph: nx.DiGraph) -> list[dict]:
    """Находит устройства/IP, использованные двумя и более разными отправителями."""
    if len(graph) == 0:
        return []

    identity_nodes: dict[tuple[str, str], set[str]] = defaultdict(set)

    for node, data in graph.nodes(data=True):
        node_str = str(node)
        for device_id in data.get('device_ids', set()):
            identity_nodes[('device_id', str(device_id))].add(node_str)
        for ip in data.get('ip_addresses', set()):
            identity_nodes[('ip_address', str(ip))].add(node_str)

    for u, _, data in _iter_edges(graph):
        if data.get('device_id'):
            identity_nodes[('device_id', str(data['device_id']))].add(str(u))
        if data.get('ip_address'):
            identity_nodes[('ip_address', str(data['ip_address']))].add(str(u))

    results = []
    for index, ((identity_type, identity_id), nodes) in enumerate(identity_nodes.items()):
        if len(nodes) < 2:
            continue
        node_ids = sorted(nodes)
        score = _clamp(0.5 + min(len(node_ids), 10) / 20)
        results.append(
            {
                'id': f'shared_identity_{index}',
                'type': 'shared_identity',
                'score': score,
                'node_ids': node_ids,
                'edge_ids': [],
                'metrics': {'identity_type': identity_type, 'account_count': len(node_ids)},
                'identity_id': identity_id,
                'identity_type': identity_type,
                'clients': node_ids,
                'accounts': node_ids,
                'device_id': identity_id,
                'nodes': node_ids,
            },
        )

    return results
