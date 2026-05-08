import math
from collections import defaultdict

import networkx as nx

__all__ = ['compute_scores']

# Риск по типу транзакции (0.0–1.0)
# TODO(teenxsky): почекать IBM AML для нахождения более расширенного списка
_TRANSACTION_TYPE_RISK: dict[str, float] = {
    'Cash': 1.0,
    'Bitcoin': 0.9,
    'Cheque': 0.6,
    'Wire': 0.4,
    'ACH': 0.3,
    'Credit Card': 0.2,
    'Reinvestment': 0.1,
}
_DEFAULT_TYPE_RISK = 0.3


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

    risk_score = sigmoid(degree_norm*0.20 + cycle_flag*0.35
                         + balance_deviation*0.20 + shared_device_flag*0.10
                         + transaction_type_risk*0.15)
    """
    if len(graph) == 0:
        return {}

    max_degree = max((graph.degree(n) for n in graph.nodes()), default=1) or 1

    cycle_node_set: set[str] = {str(n) for c in cycles for n in c['nodes']}
    shared_device_node_set: set[str] = {str(n) for sd in shared_device_nodes for n in sd['nodes']}

    in_flow: dict[str, float] = defaultdict(float)
    out_flow: dict[str, float] = defaultdict(float)
    for u, v, data in graph.edges(data=True):
        amount_paid = data.get('amount_paid', 0.0)
        amount_received = data.get('amount_received')
        in_val = amount_received if amount_received is not None else amount_paid
        out_flow[str(u)] += amount_paid
        in_flow[str(v)] += in_val

    type_risk_per_node: dict[str, float] = {}
    for node in graph.nodes():
        node_str = str(node)
        risk_values: list[float] = []
        for edges_fn in (graph.out_edges, graph.in_edges):
            for _, _, data in edges_fn(node, data=True):  # type: ignore[call-arg]
                t_type = data.get('transaction_type') or ''
                risk_values.append(_TRANSACTION_TYPE_RISK.get(t_type, _DEFAULT_TYPE_RISK))
        type_risk_per_node[node_str] = max(risk_values) if risk_values else _DEFAULT_TYPE_RISK

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

        transaction_type_risk = type_risk_per_node.get(node_str, _DEFAULT_TYPE_RISK)

        raw = (
            degree_norm * 0.20
            + cycle_flag * 0.35
            + balance_deviation * 0.20
            + shared_device_flag * 0.10
            + transaction_type_risk * 0.15
        )
        scores[node_str] = _sigmoid(raw)

    return scores
