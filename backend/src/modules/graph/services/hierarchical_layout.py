"""
Иерархическая укладка графа с учётом кластерной структуры.

Алгоритм:

1. Строится граф кластеров (мета-граф), где супервершина = кластер, ребро = есть
   хотя бы одно ребро между узлами разных кластеров. Вес ребра = количество
   межкластерных связей.
2. Запускается spring_layout на мета-графе → координаты центров кластеров в [-1, 1].
3. Для каждого кластера запускается spring_layout на подграфе его узлов в локальном
   пространстве [-r, r], где r = sqrt(размер_кластера) * cluster_radius_factor.
4. Финальные координаты = центр_кластера + локальное_смещение_узла.
5. Всё нормализуется в [-1, 1] относительно максимального |координата|.
"""

import logging
from dataclasses import dataclass

import networkx as nx
import numpy as np

from src.modules.graph.analytics.clustering import ClusteringResult
from src.modules.graph.types import AnyGraph

__all__ = ['HierarchicalLayoutResult', 'compute_hierarchical_layout']

logger = logging.getLogger(__name__)


@dataclass(slots=True, frozen=True)
class HierarchicalLayoutResult:
    """Результат иерархической укладки.

    :param positions: Координаты узлов shape (n, 2), float32, нормализованные в [-1, 1].
    :param cluster_centroids: Координаты центров кластеров shape (n_clusters, 2),
                              float32, нормализованные в [-1, 1].
    :param node_id_to_index: Маппинг id узла → индекс строки в positions.
    """

    positions: np.ndarray
    cluster_centroids: np.ndarray
    node_id_to_index: dict[str, int]


def compute_hierarchical_layout(
    graph: AnyGraph,
    clustering: ClusteringResult,
    *,
    cluster_radius_factor: float = 0.15,
    meta_iterations: int = 200,
    intra_iterations: int = 100,
    random_state: int = 42,
) -> HierarchicalLayoutResult:
    """Посчитать иерархическую 2D-укладку графа.

    :param graph: Транзакционный граф.
    :param clustering: Результат кластеризации (метки узлов).
    :param cluster_radius_factor: Множитель радиуса локальной укладки.
                                  Радиус = sqrt(n_nodes_in_cluster) * factor.
    :param meta_iterations: Число итераций spring_layout для мета-графа.
    :param intra_iterations: Число итераций spring_layout внутри кластера.
    :param random_state: Seed для воспроизводимости.
    :returns: HierarchicalLayoutResult с финальными нормализованными координатами.
    """
    nodes = list(graph.nodes())
    n = len(nodes)
    node_id_to_index: dict[str, int] = {str(node): i for i, node in enumerate(nodes)}
    n_clusters = clustering.n_clusters

    # Сопоставить метки кластеров с нашим порядком узлов
    # (порядок в clustering.node_id_to_index может отличаться)
    node_labels = np.full(n, -1, dtype=np.int32)
    for node_id, our_idx in node_id_to_index.items():
        cluster_idx = clustering.node_id_to_index.get(node_id)
        if cluster_idx is not None:
            node_labels[our_idx] = int(clustering.labels[cluster_idx])

    # ===== Шаг 1: мета-граф кластеров =====

    meta_graph = nx.Graph()
    for c in range(n_clusters):
        meta_graph.add_node(c)

    for u, v in graph.edges():
        u_str, v_str = str(u), str(v)
        u_our = node_id_to_index.get(u_str)
        v_our = node_id_to_index.get(v_str)
        if u_our is None or v_our is None:
            continue
        cu, cv = int(node_labels[u_our]), int(node_labels[v_our])
        if cu < 0 or cv < 0 or cu == cv:
            continue
        if meta_graph.has_edge(cu, cv):
            meta_graph[cu][cv]['weight'] += 1
        else:
            meta_graph.add_edge(cu, cv, weight=1)

    # ===== Шаг 2: layout мета-графа =======─

    if n_clusters == 1:
        meta_positions: dict[int, tuple[float, float]] = {0: (0.0, 0.0)}
    else:
        meta_pos = nx.spring_layout(
            meta_graph,
            seed=random_state,
            iterations=meta_iterations,
            scale=1.0,
            weight='weight',
        )
        meta_positions = {c: (float(pos[0]), float(pos[1])) for c, pos in meta_pos.items()}

    # ===== Шаг 3: layout узлов внутри каждого кластера ==========================

    positions = np.zeros((n, 2), dtype=np.float32)
    cluster_centroids = np.zeros((n_clusters, 2), dtype=np.float32)

    for c in range(n_clusters):
        cx, cy = meta_positions.get(c, (0.0, 0.0))
        cluster_centroids[c] = (cx, cy)

        cluster_node_our_indices = [i for i in range(n) if node_labels[i] == c]
        cluster_size = len(cluster_node_our_indices)

        if cluster_size == 0:
            continue

        radius = np.sqrt(cluster_size) * cluster_radius_factor

        if cluster_size == 1:
            positions[cluster_node_our_indices[0]] = (cx, cy)

        elif cluster_size == 2:
            positions[cluster_node_our_indices[0]] = (cx, cy + radius * 0.5)
            positions[cluster_node_our_indices[1]] = (cx, cy - radius * 0.5)

        else:
            cluster_nodes = [nodes[i] for i in cluster_node_our_indices]
            subgraph = graph.subgraph(cluster_nodes)

            local_pos = nx.spring_layout(
                subgraph,
                seed=random_state,
                iterations=intra_iterations,
                scale=radius,
            )

            for node, (lx, ly) in local_pos.items():
                node_str = str(node)
                our_idx = node_id_to_index.get(node_str)
                if our_idx is not None:
                    positions[our_idx] = (cx + lx, cy + ly)

    # ===== Изолированные узлы (label == -1) ====================================─

    isolated = [i for i in range(n) if node_labels[i] == -1]
    if isolated:
        periphery_r = 1.5
        step = 2.0 * np.pi / max(len(isolated), 1)
        for j, idx in enumerate(isolated):
            angle = j * step
            positions[idx] = (
                periphery_r * np.cos(angle),
                periphery_r * np.sin(angle),
            )

    # ===== Шаг 5: нормализация в [-1, 1] ========================================

    max_abs = float(np.abs(positions).max())
    if max_abs > 0:
        positions /= max_abs
        cluster_centroids /= max_abs

    logger.info(
        'Иерархический layout завершён: %d узлов, %d кластеров',
        n,
        n_clusters,
    )

    return HierarchicalLayoutResult(
        positions=positions,
        cluster_centroids=cluster_centroids,
        node_id_to_index=node_id_to_index,
    )
