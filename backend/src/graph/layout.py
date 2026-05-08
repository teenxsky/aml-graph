import math
from typing import Literal

import networkx as nx

__all__ = ['compute_graph_layout']

LayoutAlgorithm = Literal['forceatlas2', 'spring']


def _layout_core(
    graph: nx.Graph,
    algorithm: LayoutAlgorithm,
) -> dict[object, tuple[float, float]]:
    if algorithm == 'forceatlas2' and hasattr(nx, 'forceatlas2_layout'):
        positions = nx.forceatlas2_layout(
            graph,
            max_iter=300,
            scaling_ratio=2.0,
            gravity=1.0,
            seed=42,
        )
    else:
        positions = nx.spring_layout(graph, seed=42)
    return {node: (float(x), float(y)) for node, (x, y) in positions.items()}


def _placed_neighbors(
    graph: nx.Graph,
    node: object,
    result: dict[str, tuple[float, float]],
) -> list[tuple[float, float]]:
    if graph.is_directed():
        neighbors = set(graph.predecessors(node)) | set(graph.successors(node))
    else:
        neighbors = set(graph.neighbors(node))
    return [result[str(neighbor)] for neighbor in neighbors if str(neighbor) in result]


def _fill_missing_positions(
    graph: nx.Graph,
    result: dict[str, tuple[float, float]],
) -> dict[str, tuple[float, float]]:
    spread = max((max(abs(x), abs(y)) for x, y in result.values()), default=1.0) or 1.0
    missing_nodes = [node for node in graph.nodes() if str(node) not in result]

    for index, node in enumerate(sorted(missing_nodes, key=str)):
        neighbors = _placed_neighbors(graph, node, result)
        angle = index * math.pi * (3.0 - math.sqrt(5.0))
        if neighbors:
            x = sum(pos[0] for pos in neighbors) / len(neighbors)
            y = sum(pos[1] for pos in neighbors) / len(neighbors)
            radius = 0.05 * spread
        else:
            x = 0.0
            y = 0.0
            radius = 1.5 * spread
        result[str(node)] = (
            float(x + math.cos(angle) * radius),
            float(y + math.sin(angle) * radius),
        )

    return result


def compute_graph_layout(
    graph: nx.Graph,
    max_nodes: int = 2000,
    algorithm: LayoutAlgorithm = 'forceatlas2',
) -> dict[str, tuple[float, float]]:
    """Compute graph coordinates with ForceAtlas2 and a spring-layout fallback."""
    if len(graph) == 0:
        return {}
    if len(graph) == 1:
        return {str(next(iter(graph.nodes()))): (0.0, 0.0)}

    layout_graph = graph
    if len(graph) > max_nodes:
        top_nodes = sorted(
            graph.nodes(),
            key=lambda n: graph.degree(n),
            reverse=True,
        )[:max_nodes]
        layout_graph = graph.subgraph(top_nodes)

    try:
        positions = _layout_core(layout_graph, algorithm)
    except Exception:
        positions = _layout_core(layout_graph, 'spring')

    result = {str(node): position for node, position in positions.items()}
    return _fill_missing_positions(graph, result)
