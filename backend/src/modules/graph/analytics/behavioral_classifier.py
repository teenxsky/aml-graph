"""Поведенческая классификация узлов графа.

Вычисляет behavioral_role для каждого узла на основе структурных
характеристик графа (степени, betweenness centrality, баланс потоков).
Это второй слой классификации поверх онтологического entity_type:
entity_type отвечает на вопрос "что узел есть в реальности",
behavioral_role — "как узел ведёт себя в графе".

Правила классификации применяются эксклюзивно в фиксированном порядке:
1. isolated  — степень ≤ 2 и общий поток мал
2. hub       — степень в top 5% по графу
3. transit   — betweenness в top 10% И сбалансированные потоки
4. regular   — всё остальное (дефолт)
"""

from __future__ import annotations

from typing import Final, Literal

import networkx as nx
import numpy as np

ISOLATED_DEGREE_THRESHOLD: Final[int] = 2
HUB_DEGREE_PERCENTILE: Final[float] = 95.0
TRANSIT_BETWEENNESS_PERCENTILE: Final[float] = 90.0
TRANSIT_FLOW_BALANCE_THRESHOLD: Final[float] = 0.2  # |in − out| / (in + out)

BehavioralRole = Literal['regular', 'transit', 'hub', 'isolated']


def classify_behavioral_roles(
    graph: nx.DiGraph,
    *,
    betweenness_scores: dict[str, float] | None = None,
) -> dict[str, BehavioralRole]:
    """Вычислить behavioral_role для каждого узла графа.

    Args:
        graph: Граф с заполненными атрибутами in_flow, out_flow на узлах.
        betweenness_scores: Предвычисленные betweenness centrality.
            Если None — вычисляется здесь через nx.betweenness_centrality.

    Returns:
        Словарь node_id → BehavioralRole.
    """
    n = graph.number_of_nodes()
    if n == 0:
        return {}

    degrees: dict[str, int] = {
        node_id: graph.in_degree(node_id) + graph.out_degree(node_id)
        for node_id in graph.nodes()
    }

    degree_values = np.array(list(degrees.values()), dtype=np.float64)
    hub_threshold = float(np.percentile(degree_values, HUB_DEGREE_PERCENTILE)) if n >= 20 else float('inf')

    if betweenness_scores is None:
        betweenness_scores = nx.betweenness_centrality(graph, normalized=True)
    bc_values = np.array(list(betweenness_scores.values()), dtype=np.float64)
    transit_bc_threshold = (
        float(np.percentile(bc_values, TRANSIT_BETWEENNESS_PERCENTILE)) if n >= 20 else float('inf')
    )

    roles: dict[str, BehavioralRole] = {}
    for node_id in graph.nodes():
        deg = degrees[node_id]
        in_flow = float(graph.nodes[node_id].get('in_flow', 0.0))
        out_flow = float(graph.nodes[node_id].get('out_flow', 0.0))
        total_flow = in_flow + out_flow
        bc = betweenness_scores.get(str(node_id), 0.0)

        if deg <= ISOLATED_DEGREE_THRESHOLD:
            roles[node_id] = 'isolated'
            continue

        if deg >= hub_threshold:
            roles[node_id] = 'hub'
            continue

        if bc >= transit_bc_threshold and total_flow > 0:
            balance = abs(in_flow - out_flow) / total_flow
            if balance < TRANSIT_FLOW_BALANCE_THRESHOLD:
                roles[node_id] = 'transit'
                continue

        roles[node_id] = 'regular'

    return roles
