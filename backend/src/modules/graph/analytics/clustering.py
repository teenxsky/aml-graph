import logging
from dataclasses import dataclass
from typing import Literal

import networkx as nx
import numpy as np
import scipy.sparse as sp
import scipy.sparse.linalg as spla
from scipy.linalg import eigh
from scipy.spatial.distance import pdist
from sklearn.cluster import KMeans

from src.modules.graph.analytics.features import FeatureMatrix, build_node_features

__all__ = ['ClusteringResult', 'cluster_graph']

logger = logging.getLogger(__name__)


@dataclass(slots=True, frozen=True)
class ClusteringResult:
    """Результат кластеризации графа.

    :param labels: Метки кластеров для каждого узла, shape (n,), int32.
    :param n_clusters: Количество кластеров.
    :param method: Метод кластеризации.
    :param node_id_to_index: Маппинг id узла → индекс в labels.
    :param metadata: Метаданные метода. Для AGC: {"k": int, "intra_distance": float}.
                     Для Louvain: {"modularity": float}.
    """

    labels: np.ndarray
    n_clusters: int
    method: Literal['agc', 'louvain']
    node_id_to_index: dict[str, int]
    metadata: dict


def cluster_graph(
    graph: nx.MultiDiGraph,
    *,
    method: Literal['agc', 'louvain'] = 'agc',
    n_clusters: int | None = None,
    max_k: int = 60,
    random_state: int = 42,
) -> ClusteringResult:
    """Кластеризовать узлы графа выбранным методом.

    :param graph: Транзакционный мультиграф из GraphBuilder.
    :param method: ``"agc"`` (требует признаки узлов) или ``"louvain"`` (только структура).
    :param n_clusters: Желаемое число кластеров для AGC. Игнорируется Louvain.
                       Если None для AGC - оценивается через eigengap-эвристику.
    :param max_k: Максимальный порядок фильтра для AGC.
    :param random_state: Seed для воспроизводимости.
    :returns: ClusteringResult с метками и метаданными.
    """
    nodes = list(graph.nodes())
    n = len(nodes)

    if n == 0:
        raise ValueError('Граф пустой: нет узлов для кластеризации')

    if method == 'louvain':
        return _cluster_louvain(graph, random_state)

    # AGC требует минимум 3 узла для осмысленной кластеризации
    if n < 3:
        labels = np.zeros(n, dtype=np.int32)
        node_id_to_index = {str(node): i for i, node in enumerate(nodes)}
        return ClusteringResult(
            labels=labels,
            n_clusters=1,
            method='agc',
            node_id_to_index=node_id_to_index,
            metadata={'k': 0, 'intra_distance': 0.0},
        )

    features = build_node_features(graph)
    return _cluster_agc(
        graph,
        features,
        n_clusters=n_clusters,
        max_k=max_k,
        random_state=random_state,
    )


def _build_symmetric_adjacency(
    graph: nx.MultiDiGraph,
    node_id_to_index: dict[str, int],
    n: int,
) -> sp.csr_matrix:
    """Построить симметризованную разрежённую матрицу смежности."""
    rows: list[int] = []
    cols: list[int] = []
    data: list[float] = []

    for u, v, edge_data in graph.edges(data=True):
        u_str, v_str = str(u), str(v)
        if u_str not in node_id_to_index or v_str not in node_id_to_index:
            continue
        i = node_id_to_index[u_str]
        j = node_id_to_index[v_str]
        weight = float(edge_data.get('amount_paid', 1.0)) or 1.0
        rows.append(i)
        cols.append(j)
        data.append(weight)

    A_dir = sp.csr_matrix((data, (rows, cols)), shape=(n, n))
    # Симметризация без удвоения весов
    return (A_dir + A_dir.T) * 0.5


def _compute_normalized_adjacency(A: sp.csr_matrix) -> sp.csr_matrix:
    """Вычислить симметрично нормализованную матрицу S = D^(-1/2) A D^(-1/2)."""
    degrees = np.asarray(A.sum(axis=1)).ravel()
    # Защита от нулевых степеней (изолированные узлы)
    with np.errstate(divide='ignore'):
        d_inv_sqrt = np.where(degrees > 0, 1.0 / np.sqrt(degrees), 0.0)
    D_inv_sqrt = sp.diags(d_inv_sqrt, format='csr')
    return D_inv_sqrt @ A @ D_inv_sqrt


def _estimate_n_clusters(L_sym: sp.csr_matrix, n: int) -> int:
    """Оценить число кластеров через eigengap эвристику на нормализованном лапласиане."""
    k = min(20, n - 1)
    try:
        eigenvalues = spla.eigsh(
            L_sym,
            k=k,
            which='SM',
            return_eigenvectors=False,
            tol=1e-4,
        )
        eigenvalues = np.sort(eigenvalues)
        gaps = np.diff(eigenvalues)
        gap_idx = int(np.argmax(gaps))
        return max(2, min(gap_idx + 1, 20))
    except Exception:
        logger.warning('Eigengap оценка не удалась, используем n_clusters=5 по умолчанию')
        return 5


def _top_eigenvectors(W: np.ndarray, k: int, random_state: int) -> np.ndarray:
    """Извлечь top-k собственных векторов симметричной матрицы W.

    :returns: Матрица eigenvectors shape (n, k).
    """
    n = W.shape[0]
    k = min(k, n)
    # eigh возвращает значения в возрастающем порядке, берём последние k
    _, eigenvectors = eigh(W, subset_by_index=[n - k, n - 1])
    return eigenvectors  # shape (n, k)


def _compute_intra_distance(X_bar: np.ndarray, labels: np.ndarray) -> float:
    """Среднее внутрикластерное попарное расстояние."""
    unique_labels = np.unique(labels)
    n_clusters = len(unique_labels)
    total = 0.0
    count = 0

    for label in unique_labels:
        members = X_bar[labels == label]
        if len(members) < 2:
            continue
        total += float(pdist(members).mean())
        count += 1

    if count == 0:
        return 0.0
    return total / n_clusters


def _cluster_agc(
    graph: nx.MultiDiGraph,
    features: FeatureMatrix,
    *,
    n_clusters: int | None,
    max_k: int,
    random_state: int,
) -> ClusteringResult:
    """Реализация AGC."""
    node_id_to_index = features.node_id_to_index
    n = len(node_id_to_index)
    X = features.X.astype(np.float64)

    # Построить нормализованную матрицу смежности S
    A = _build_symmetric_adjacency(graph, node_id_to_index, n)
    S = _compute_normalized_adjacency(A)

    # Нормализованный лапласиан для eigengap
    L_sym = sp.eye(n, format='csr') - S

    if n_clusters is None:
        n_clusters = _estimate_n_clusters(L_sym, n)
        logger.info('AGC: eigengap оценил n_clusters=%d', n_clusters)

    if n > 8_000:
        logger.warning(
            'Граф содержит %d узлов. K = X_bar @ X_bar.T требует O(n²) памяти (~%.0f МБ). '
            'Рекомендуется метод Louvain для больших графов.',
            n,
            n * n * 8 / 1e6,
        )

    # Итеративное сглаживание и адаптивный выбор k (Algorithm 1)
    X_bar = X.copy()
    C_prev: np.ndarray | None = None
    intra_prev = np.inf
    best_k = 0

    for t in range(1, max_k + 1):
        # Один шаг low-pass фильтра
        X_bar = 0.5 * (X_bar + S @ X_bar)

        # Линейное ядро → симметрично-неотрицательная матрица
        K = X_bar @ X_bar.T
        W = 0.5 * (np.abs(K) + np.abs(K.T))

        # Спектральная кластеризация: top-m собственных векторов W
        try:
            U = _top_eigenvectors(W, n_clusters, random_state)
        except Exception:
            logger.warning('AGC: eigenvector extraction не удалась на шаге k=%d', t)
            break

        kmeans = KMeans(n_clusters=n_clusters, n_init=10, random_state=random_state)
        labels = kmeans.fit_predict(U).astype(np.int32)

        intra_curr = _compute_intra_distance(X_bar, labels)
        logger.debug('AGC k=%d: intra_distance=%.4f', t, intra_curr)

        if intra_curr > intra_prev:
            # Внутрикластерное расстояние выросло - предыдущий шаг был лучше
            logger.info('AGC остановился на k=%d (intra %.4f > %.4f)', t, intra_curr, intra_prev)
            break

        C_prev = labels
        intra_prev = intra_curr
        best_k = t

    final_labels = C_prev if C_prev is not None else np.zeros(n, dtype=np.int32)

    return ClusteringResult(
        labels=final_labels,
        n_clusters=n_clusters,
        method='agc',
        node_id_to_index=node_id_to_index,
        metadata={
            'k': best_k,
            'intra_distance': float(intra_prev) if np.isfinite(intra_prev) else 0.0,
        },
    )


def _cluster_louvain(graph: nx.MultiDiGraph, random_state: int) -> ClusteringResult:
    """Кластеризация Louvain через networkx.

    Игнорирует признаки узлов, использует только структуру графа с весами
    рёбер (суммарный amount_paid на паре узлов).
    """
    nodes = list(graph.nodes())
    n = len(nodes)
    node_id_to_index = {str(node): i for i, node in enumerate(nodes)}

    undirected = nx.Graph()
    undirected.add_nodes_from(nodes)

    for u, v, edge_data in graph.edges(data=True):
        weight = float(edge_data.get('amount_paid', 1.0)) or 1.0
        if undirected.has_edge(u, v):
            undirected[u][v]['weight'] += weight
        else:
            undirected.add_edge(u, v, weight=weight)

    communities = nx.algorithms.community.louvain_communities(
        undirected,
        weight='weight',
        seed=random_state,
    )

    labels = np.zeros(n, dtype=np.int32)
    for community_idx, community in enumerate(communities):
        for node in community:
            node_str = str(node)
            if node_str in node_id_to_index:
                labels[node_id_to_index[node_str]] = community_idx

    try:
        modularity = nx.algorithms.community.modularity(
            undirected,
            communities,
            weight='weight',
        )
    except Exception:
        modularity = 0.0

    logger.info(
        'Louvain: %d кластеров, modularity=%.4f',
        len(communities),
        modularity,
    )

    return ClusteringResult(
        labels=labels,
        n_clusters=len(communities),
        method='louvain',
        node_id_to_index=node_id_to_index,
        metadata={'modularity': float(modularity)},
    )
