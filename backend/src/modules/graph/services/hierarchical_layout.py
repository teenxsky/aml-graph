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
    """
    Результат иерархической укладки.

    :param positions: Координаты узлов shape (n, 2), float32, нормализованные в [-1, 1].
    :param cluster_centroids: Координаты центров AGC-кластеров shape (n_clusters, 2), float32.
    :param type_centroids: Словарь entity_type → (x, y) в нормализованном пространстве.
    :param node_id_to_index: Маппинг id узла → индекс строки в positions.
    """

    positions: np.ndarray
    cluster_centroids: np.ndarray
    type_centroids: dict[str, tuple[float, float]]
    node_id_to_index: dict[str, int]


def compute_hierarchical_layout(
    graph: AnyGraph,
    clustering: ClusteringResult,
    *,
    type_radius_factor: float = 0.25,
    cluster_radius_factor: float = 0.08,
    meta_iterations: int = 200,
    intra_iterations: int = 100,
    random_state: int = 42,
) -> HierarchicalLayoutResult:
    """
    Трёхуровневая иерархическая укладка графа.

    Уровни иерархии (от внешнего к внутреннему):
    1. entity_type - семантическая группировка (client/account/company/device).
    2. AGC-кластер внутри entity_type - структурное подразделение.
    3. Узлы внутри AGC-подкластера - финальное позиционирование.

    :param graph: Транзакционный граф с атрибутом entity_type на каждом узле.
    :param clustering: Результат AGC/Louvain кластеризации.
    :param type_radius_factor: Множитель радиуса региона entity-типа.
    :param cluster_radius_factor: Множитель радиуса AGC-подкластера внутри типа.
    :param meta_iterations: Итерации spring_layout для meta-графов.
    :param intra_iterations: Итерации spring_layout внутри подкластеров.
    :param random_state: Seed для воспроизводимости.
    :returns: HierarchicalLayoutResult с финальными координатами в [-1, 1].
    """
    nodes = list(graph.nodes())
    n = len(nodes)
    node_id_to_index: dict[str, int] = {str(node): i for i, node in enumerate(nodes)}
    n_clusters = clustering.n_clusters

    node_entity_types: list[str] = []
    for node in nodes:
        et = graph.nodes[node].get('entity_type') or 'unknown'
        node_entity_types.append(str(et))

    node_labels = np.full(n, -1, dtype=np.int32)
    for node_id, our_idx in node_id_to_index.items():
        cluster_idx = clustering.node_id_to_index.get(node_id)
        if cluster_idx is not None:
            node_labels[our_idx] = int(clustering.labels[cluster_idx])

    all_entity_types = sorted(set(node_entity_types))

    type_meta = nx.Graph()
    for et in all_entity_types:
        type_meta.add_node(et)

    for u, v in graph.edges():
        u_str, v_str = str(u), str(v)
        ui = node_id_to_index.get(u_str)
        vi = node_id_to_index.get(v_str)
        if ui is None or vi is None:
            continue
        et_u = node_entity_types[ui]
        et_v = node_entity_types[vi]
        if et_u == et_v:
            continue
        if type_meta.has_edge(et_u, et_v):
            type_meta[et_u][et_v]['weight'] += 1
        else:
            type_meta.add_edge(et_u, et_v, weight=1)

    n_types = len(all_entity_types)
    if n_types <= 1:
        type_positions: dict[str, tuple[float, float]] = dict.fromkeys(all_entity_types, (0.0, 0.0))
    else:
        raw_type = nx.spring_layout(
            type_meta,
            seed=random_state,
            iterations=meta_iterations,
            scale=1.0,
            weight='weight',
        )
        type_positions = {et: (float(p[0]), float(p[1])) for et, p in raw_type.items()}

    positions = np.zeros((n, 2), dtype=np.float32)

    for et in all_entity_types:
        et_cx, et_cy = type_positions[et]
        et_indices = [i for i in range(n) if node_entity_types[i] == et]
        et_size = len(et_indices)
        if et_size == 0:
            continue

        type_radius = np.sqrt(et_size) * type_radius_factor

        et_cluster_set = {int(node_labels[i]) for i in et_indices if node_labels[i] >= 0}
        et_clusters = sorted(et_cluster_set)

        if not et_clusters:
            agc_positions: dict[int, tuple[float, float]] = {}
        elif len(et_clusters) == 1:
            agc_positions = {et_clusters[0]: (et_cx, et_cy)}
        else:
            sub_meta = nx.Graph()
            for cid in et_clusters:
                sub_meta.add_node(cid)

            for u, v in graph.edges():
                u_str, v_str = str(u), str(v)
                ui = node_id_to_index.get(u_str)
                vi = node_id_to_index.get(v_str)
                if ui is None or vi is None:
                    continue
                if node_entity_types[ui] != et or node_entity_types[vi] != et:
                    continue
                cu = int(node_labels[ui])
                cv = int(node_labels[vi])
                if cu < 0 or cv < 0 or cu not in et_cluster_set or cv not in et_cluster_set or cu == cv:
                    continue
                if sub_meta.has_edge(cu, cv):
                    sub_meta[cu][cv]['weight'] += 1
                else:
                    sub_meta.add_edge(cu, cv, weight=1)

            raw_sub = nx.spring_layout(
                sub_meta,
                seed=random_state,
                iterations=meta_iterations,
                scale=type_radius,
                weight='weight',
            )
            agc_positions = {
                cid: (et_cx + float(p[0]), et_cy + float(p[1]))
                for cid, p in raw_sub.items()
            }

        for cid in et_clusters:
            cx, cy = agc_positions.get(cid, (et_cx, et_cy))
            sub_indices = [i for i in et_indices if int(node_labels[i]) == cid]
            sub_size = len(sub_indices)
            if sub_size == 0:
                continue

            cr = np.sqrt(sub_size) * cluster_radius_factor

            if sub_size == 1:
                positions[sub_indices[0]] = (cx, cy)
            elif sub_size == 2:
                positions[sub_indices[0]] = (cx, cy + cr * 0.5)
                positions[sub_indices[1]] = (cx, cy - cr * 0.5)
            else:
                sub_nodes = [nodes[i] for i in sub_indices]
                subgraph = graph.subgraph(sub_nodes)
                local = nx.spring_layout(
                    subgraph,
                    seed=random_state,
                    iterations=intra_iterations,
                    scale=cr,
                )
                for node, (lx, ly) in local.items():
                    idx = node_id_to_index.get(str(node))
                    if idx is not None:
                        positions[idx] = (cx + lx, cy + ly)

        unclustered = [i for i in et_indices if node_labels[i] < 0]
        if unclustered:
            peri_r = type_radius * 1.2
            angle_step = 2.0 * np.pi / max(len(unclustered), 1)
            for j, idx in enumerate(unclustered):
                angle = j * angle_step
                positions[idx] = (
                    et_cx + peri_r * np.cos(angle),
                    et_cy + peri_r * np.sin(angle),
                )

    # нормализация
    max_abs = float(np.abs(positions).max())
    if max_abs > 0:
        positions /= max_abs

    # кластеризация центроидов
    cluster_centroids = np.zeros((n_clusters, 2), dtype=np.float32)
    for c in range(n_clusters):
        c_idxs = [i for i in range(n) if int(node_labels[i]) == c]
        if c_idxs:
            cluster_centroids[c] = positions[c_idxs].mean(axis=0)

    # типизация центроидов
    type_centroids_result: dict[str, tuple[float, float]] = {}
    for et in all_entity_types:
        et_idxs = [i for i in range(n) if node_entity_types[i] == et]
        if et_idxs:
            mean_pos = positions[et_idxs].mean(axis=0)
            type_centroids_result[et] = (float(mean_pos[0]), float(mean_pos[1]))

    logger.info(
        'Трёхуровневый layout: %d узлов, %d кластеров, %d типов сущностей',
        n,
        n_clusters,
        len(all_entity_types),
    )

    return HierarchicalLayoutResult(
        positions=positions,
        cluster_centroids=cluster_centroids,
        type_centroids=type_centroids_result,
        node_id_to_index=node_id_to_index,
    )
