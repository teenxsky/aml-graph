import math
from collections import defaultdict

import networkx as nx

__all__ = ['compute_scores']


def _sigmoid(x: float) -> float:
    """Сигмоид-функция активации."""
    return 1.0 / (1.0 + math.exp(-x))


def compute_scores(
    graph: nx.DiGraph,
    cycles: list[dict],
    fanout_nodes: list[dict],
    transit_nodes: list[dict],
    shared_device_nodes: list[dict],
) -> dict[str, float]:
    """Вычисляет risk score для каждого узла через взвешенную сумму признаков + sigmoid.

    risk_score = sigmoid(degree_norm*0.25 + cycle_flag*0.40
                         + balance_deviation*0.20 + shared_device_flag*0.15)
    """
    if len(graph) == 0:
        return {}

    max_degree = max((graph.degree(n) for n in graph.nodes()), default=1) or 1

    cycle_node_set: set[str] = {str(n) for c in cycles for n in c['nodes']}
    shared_device_node_set: set[str] = {str(n) for sd in shared_device_nodes for n in sd['nodes']}

    in_flow: dict[str, float] = defaultdict(float)
    out_flow: dict[str, float] = defaultdict(float)
    for u, v, data in graph.edges(data=True):
        amount = data.get('amount', 0.0)
        out_flow[str(u)] += amount
        in_flow[str(v)] += amount

    scores: dict[str, float] = {}
    for node in graph.nodes():
        node_str = str(node)

        degree_norm = graph.degree(node) / max_degree
        cycle_flag = 1.0 if node_str in cycle_node_set else 0.0
        shared_device_flag = 1.0 if node_str in shared_device_node_set else 0.0

        in_f = in_flow.get(node_str, 0.0)
        out_f = out_flow.get(node_str, 0.0)
        denom = max(in_f, out_f, 1.0)
        balance_deviation = abs(in_f - out_f) / denom

        raw = (
            degree_norm * 0.25
            + cycle_flag * 0.40
            + balance_deviation * 0.20
            + shared_device_flag * 0.15
        )
        scores[node_str] = _sigmoid(raw)

    return scores
