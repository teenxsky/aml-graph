from typing import TYPE_CHECKING, Literal

import networkx as nx
import numpy as np

from src.modules.graph.types import AnyGraph, LayoutAlgorithm

if TYPE_CHECKING:
    from src.modules.graph.analytics.clustering import ClusteringResult

__all__ = ['compute_graph_layout', 'compute_graph_layout_dispatched']


def _layout_core(
    graph: AnyGraph,
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
    graph: AnyGraph,
    node: object,
    result: dict[str, tuple[float, float]],
) -> list[tuple[float, float]]:
    neighbors: set[object]

    if isinstance(graph, (nx.DiGraph, nx.MultiDiGraph)):
        neighbors = set(graph.predecessors(node)) | set(graph.successors(node))
    else:
        neighbors = set(graph.neighbors(node))

    return [result[str(neighbor)] for neighbor in neighbors if str(neighbor) in result]


def _fill_missing_positions(
    graph: AnyGraph,
    result: dict[str, tuple[float, float]],
) -> dict[str, tuple[float, float]]:
    spread = (
        max(
            (max(abs(x), abs(y)) for x, y in result.values()),
            default=1.0,
        )
        or 1.0
    )

    missing_nodes = [node for node in graph.nodes() if str(node) not in result]

    for index, node in enumerate(sorted(missing_nodes, key=str)):
        neighbors = _placed_neighbors(graph, node, result)

        angle = index * np.pi * (3.0 - np.sqrt(5.0))

        if neighbors:
            x = sum(pos[0] for pos in neighbors) / len(neighbors)
            y = sum(pos[1] for pos in neighbors) / len(neighbors)
            radius = 0.05 * spread
        else:
            x = 0.0
            y = 0.0
            radius = 1.5 * spread

        result[str(node)] = (
            float(x + np.cos(angle) * radius),
            float(y + np.sin(angle) * radius),
        )

    return result


def compute_graph_layout_dispatched(
    graph: AnyGraph,
    *,
    method: Literal['forceatlas2', 'hierarchical', 'spring'] = 'hierarchical',
    clustering: ClusteringResult | None = None,
    **kwargs: object,
) -> dict[str, tuple[float, float]]:
    """Универсальный диспетчер для layout алгоритмов.

    Если ``method == "hierarchical"``, ``clustering`` обязателен.
    Для остальных методов вызывается :func:`compute_graph_layout`.

    :param graph: Граф для укладки.
    :param method: Алгоритм укладки.
    :param clustering: Результат кластеризации (обязателен для hierarchical).
    :raises ValueError: Если method == "hierarchical" и clustering не передан.
    """
    if method == 'hierarchical':
        if clustering is None:
            raise ValueError('clustering обязателен для метода hierarchical')
        from src.modules.graph.services.hierarchical_layout import compute_hierarchical_layout

        result = compute_hierarchical_layout(graph, clustering)
        return {
            node_id: (
                float(result.positions[idx, 0]),
                float(result.positions[idx, 1]),
            )
            for node_id, idx in result.node_id_to_index.items()
        }

    algorithm: LayoutAlgorithm = 'spring' if method == 'spring' else 'forceatlas2'
    return compute_graph_layout(graph, algorithm=algorithm)


def compute_graph_layout(
    graph: AnyGraph,
    max_nodes: int = 2000,
    algorithm: LayoutAlgorithm = 'forceatlas2',
) -> dict[str, tuple[float, float]]:
    """
    Вычисляет координаты графа с помощью ForceAtlas2 и
    резервного варианта с пружинным расположением.
    """

    if len(graph) == 0:
        return {}

    if len(graph) == 1:
        return {
            str(next(iter(graph.nodes()))): (0.0, 0.0),
        }

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
