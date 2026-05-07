import math
from collections import defaultdict

import networkx as nx

__all__ = ['detect_cycles', 'detect_fanout', 'detect_transit', 'detect_shared_device']


def detect_cycles(graph: nx.DiGraph) -> list[dict]:
    """Находит транзакционные циклы длиной 2–6 (паттерн layering).

    Для каждого цикла вычисляет временной диапазон delta_t, суммарный объём
    транзакций total_weight и плотность потока rho = total_weight / delta_t.
    """
    results = []
    for cycle in nx.simple_cycles(graph, length_bound=6):
        if len(cycle) < 2:
            continue

        edges = [(cycle[i], cycle[(i + 1) % len(cycle)]) for i in range(len(cycle))]
        timestamps: list[int] = []
        amounts: list[float] = []
        for u, v in edges:
            data = graph[u][v]
            timestamps.append(data.get('timestamp', 0))
            amounts.append(data.get('amount', 0.0))

        delta_t = max(timestamps) - min(timestamps)
        total_weight = sum(amounts)
        rho: float | None = total_weight / delta_t if delta_t > 0 else None

        results.append(
            {
                'nodes': cycle,
                'length': len(cycle),
                'delta_t': delta_t,
                'total_weight': total_weight,
                'rho': rho,
            },
        )

    return results


def detect_fanout(
    graph: nx.DiGraph,
    min_receivers: int = 3,
    time_window_seconds: int = 86400,
) -> list[dict]:
    """Обнаруживает smurfing: один отправитель → N+ получателей с похожими суммами за 24 ч."""
    results = []

    for node in graph.nodes():
        out_edges = list(graph.out_edges(node, data=True))
        if len(out_edges) < min_receivers:
            continue

        out_edges.sort(key=lambda e: e[2].get('timestamp', 0))

        found = False
        for i in range(len(out_edges)):
            if found:
                break

            t_start = out_edges[i][2].get('timestamp', 0)
            window = [
                e
                for e in out_edges[i:]
                if e[2].get('timestamp', 0) - t_start <= time_window_seconds
            ]

            receiver_amounts: dict[str, float] = defaultdict(float)
            for _, recv, data in window:
                receiver_amounts[recv] += data.get('amount', 0.0)

            if len(receiver_amounts) < min_receivers:
                continue

            amounts = list(receiver_amounts.values())
            mean = sum(amounts) / len(amounts)
            if mean == 0:
                continue

            variance = sum((a - mean) ** 2 for a in amounts) / len(amounts)
            std = math.sqrt(variance)

            if std / mean < 0.3:
                results.append(
                    {
                        'source_node': str(node),
                        'receivers': list(receiver_amounts.keys()),
                        'time_window': time_window_seconds,
                        'amount_mean': mean,
                        'amount_std': std,
                    },
                )
                found = True

    return results


def detect_transit(graph: nx.DiGraph, top_k: int = 50) -> list[dict]:
    """Определяет транзитные узлы: высокая betweenness + входящий ≈ исходящий поток."""
    if len(graph) == 0:
        return []

    k = min(500, len(graph))
    centrality = nx.betweenness_centrality(graph, k=k, normalized=True)

    in_flow: dict[str, float] = defaultdict(float)
    out_flow: dict[str, float] = defaultdict(float)
    for u, v, data in graph.edges(data=True):
        amount = data.get('amount', 0.0)
        out_flow[str(u)] += amount
        in_flow[str(v)] += amount

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

        flow_ratio = abs(in_f - out_f) / denom
        if flow_ratio < 0.1:
            results.append(
                {
                    'node_id': node_str,
                    'betweenness': centrality.get(node, 0.0),
                    'flow_ratio': flow_ratio,
                },
            )

    results.sort(key=lambda x: x['betweenness'], reverse=True)
    return results[:top_k]


def detect_shared_device(graph: nx.DiGraph) -> list[dict]:
    """Находит устройства/IP, использованные двумя и более разными отправителями."""
    device_nodes: dict[str, set[str]] = defaultdict(set)

    for node, data in graph.nodes(data=True):
        node_str = str(node)
        for device_id in data.get('device_ids', set()):
            device_nodes[device_id].add(node_str)
        for ip in data.get('ip_addresses', set()):
            device_nodes[ip].add(node_str)

    return [
        {'device_id': identifier, 'nodes': list(nodes)}
        for identifier, nodes in device_nodes.items()
        if len(nodes) >= 2
    ]
