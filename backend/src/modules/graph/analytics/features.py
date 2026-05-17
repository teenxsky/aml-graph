"""Извлечение матрицы признаков узлов из графа для алгоритмов кластеризации.

Признаки строятся из агрегатов транзакций (рёбер) и атрибутов узлов.
Намеренно НЕ включает risk_score и is_laundering_node — это downstream-сигналы,
их использование привело бы к циклическому рассуждению при кластеризации.
"""

import logging
from collections import Counter
from dataclasses import dataclass

import networkx as nx
import numpy as np

__all__ = ['FeatureMatrix', 'build_node_features']

logger = logging.getLogger(__name__)


@dataclass(slots=True, frozen=True)
class FeatureMatrix:
    """Матрица признаков узлов и сопутствующие метаданные.

    :param X: Матрица признаков shape (n, d), float32, z-score нормализованная.
    :param feature_names: Имена признаков длины d для отладки и абляции.
    :param node_id_to_index: Маппинг id узла → индекс строки в X.
    """

    X: np.ndarray
    feature_names: list[str]
    node_id_to_index: dict[str, int]


def build_node_features(
    graph: nx.MultiDiGraph,
    *,
    top_k_entity_types: int = 8,
    top_k_alerts: int = 16,
) -> FeatureMatrix:
    """Построить матрицу признаков узлов из графа.

    Группы признаков:

    - A: in_flow, out_flow, total_volume, flow_balance, alerts_count
    - B: out_degree, in_degree, unique_out_counterparties, unique_in_counterparties
    - C: mean/std/max сумм исходящих и входящих транзакций
    - D: распределение по 6-часовым бинам, weekend_fraction, burstiness
    - E: one-hot entity_type (top-K), multi-hot alerts (top-K)

    Числовые признаки A+B+C логарифмируются (log1p) и z-score нормализуются.
    Категориальные E оставляются как 0/1.

    :param graph: NetworkX MultiDiGraph с атрибутами узлов и рёбер из GraphBuilder.
    :param top_k_entity_types: Сколько самых частых entity_type кодировать one-hot.
    :param top_k_alerts: Сколько самых частых типов alerts кодировать multi-hot.
    :returns: FeatureMatrix с матрицей X shape (n_nodes, d).
    :raises ValueError: Если граф пустой.
    """
    nodes = list(graph.nodes())
    n = len(nodes)

    if n == 0:
        raise ValueError('Граф пустой: нет узлов для построения матрицы признаков')

    node_id_to_index: dict[str, int] = {str(node): i for i, node in enumerate(nodes)}

    # Агрегированные данные рёбер по узлам
    out_amounts: list[list[float]] = [[] for _ in range(n)]
    in_amounts: list[list[float]] = [[] for _ in range(n)]
    out_timestamps: list[list[int]] = [[] for _ in range(n)]
    in_timestamps: list[list[int]] = [[] for _ in range(n)]
    edge_alerts_per_node: list[set[str]] = [set() for _ in range(n)]

    for u, v, edge_data in graph.edges(data=True):
        u_str, v_str = str(u), str(v)
        amount = float(edge_data.get('amount_paid', 0.0))
        ts = int(edge_data.get('timestamp', 0))
        edge_alerts: set[str] = set(edge_data.get('alerts', []))

        if u_str in node_id_to_index:
            idx_u = node_id_to_index[u_str]
            out_amounts[idx_u].append(amount)
            out_timestamps[idx_u].append(ts)
            edge_alerts_per_node[idx_u] |= edge_alerts

        if v_str in node_id_to_index:
            idx_v = node_id_to_index[v_str]
            in_amounts[idx_v].append(amount)
            in_timestamps[idx_v].append(ts)
            edge_alerts_per_node[idx_v] |= edge_alerts

    feature_names: list[str] = []
    columns: list[np.ndarray] = []

    # --- A: потоки и алерты ---

    in_flow_arr = np.array([sum(in_amounts[i]) for i in range(n)], dtype=np.float32)
    out_flow_arr = np.array([sum(out_amounts[i]) for i in range(n)], dtype=np.float32)
    total_volume = in_flow_arr + out_flow_arr
    flow_balance = out_flow_arr - in_flow_arr

    alerts_count = np.zeros(n, dtype=np.float32)
    for i, node in enumerate(nodes):
        node_attrs = graph.nodes[node]
        node_alerts: set[str] = set(node_attrs.get('alerts', []))
        alerts_count[i] = float(len(node_alerts | edge_alerts_per_node[i]))

    columns += [in_flow_arr, out_flow_arr, total_volume, flow_balance, alerts_count]
    feature_names += ['in_flow', 'out_flow', 'total_volume', 'flow_balance', 'alerts_count']

    # --- B: степени и уникальные контрагенты ---

    out_deg = np.array([graph.out_degree(node) for node in nodes], dtype=np.float32)
    in_deg = np.array([graph.in_degree(node) for node in nodes], dtype=np.float32)
    unique_out = np.array(
        [len({str(v) for _, v in graph.out_edges(node)}) for node in nodes],
        dtype=np.float32,
    )
    unique_in = np.array(
        [len({str(u) for u, _ in graph.in_edges(node)}) for node in nodes],
        dtype=np.float32,
    )

    columns += [out_deg, in_deg, unique_out, unique_in]
    feature_names += [
        'out_degree',
        'in_degree',
        'unique_out_counterparties',
        'unique_in_counterparties',
    ]

    # --- C: статистики сумм транзакций ---

    def _stats(
        amounts_list: list[list[float]],
    ) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        means = np.zeros(n, dtype=np.float32)
        stds = np.zeros(n, dtype=np.float32)
        maxs = np.zeros(n, dtype=np.float32)
        for i, amounts in enumerate(amounts_list):
            if amounts:
                arr = np.array(amounts, dtype=np.float32)
                means[i] = arr.mean()
                stds[i] = arr.std()
                maxs[i] = arr.max()
        return means, stds, maxs

    out_mean, out_std, out_max = _stats(out_amounts)
    in_mean, in_std, in_max = _stats(in_amounts)

    columns += [out_mean, out_std, out_max, in_mean, in_std, in_max]
    feature_names += [
        'out_amount_mean',
        'out_amount_std',
        'out_amount_max',
        'in_amount_mean',
        'in_amount_std',
        'in_amount_max',
    ]

    # --- D: временные признаки ---

    bin_fractions = np.zeros((n, 4), dtype=np.float32)
    weekend_fraction = np.zeros(n, dtype=np.float32)
    burstiness = np.zeros(n, dtype=np.float32)

    for i in range(n):
        all_ts = out_timestamps[i] + in_timestamps[i]
        if not all_ts:
            continue

        ts_arr = np.array(all_ts, dtype=np.int64)
        total = len(ts_arr)

        # Бины по 6 часов (4 бина на сутки)
        hours = (ts_arr // 3600) % 24
        bins = hours // 6
        for b in range(4):
            bin_fractions[i, b] = float(np.sum(bins == b)) / total

        # Доля выходных (1970-01-01 — четверг, +4 смещение к понедельнику)
        weekdays = (ts_arr // 86400 + 4) % 7
        weekend_fraction[i] = float(np.sum(weekdays >= 5)) / total

        # Burstiness по межприбывным временам (нужно ≥3 транзакций)
        if len(ts_arr) >= 3:
            sorted_ts = np.sort(ts_arr)
            inter = np.diff(sorted_ts).astype(np.float64)
            m = inter.mean()
            s = inter.std()
            denom = s + m
            burstiness[i] = float((s - m) / denom) if denom > 1e-12 else 0.0

    for b in range(4):
        columns.append(bin_fractions[:, b])
        feature_names.append(f'hour_bin_{b}')
    columns.append(weekend_fraction)
    feature_names.append('weekend_fraction')
    columns.append(burstiness)
    feature_names.append('burstiness')

    # --- E: категориальные признаки ---

    entity_counter: Counter[str] = Counter()
    for node in nodes:
        et = str(graph.nodes[node].get('entity_type', 'unknown'))
        entity_counter[et] += 1

    top_entity_types = [et for et, _ in entity_counter.most_common(top_k_entity_types)]
    for et in top_entity_types:
        col = np.array(
            [
                1.0 if str(graph.nodes[node].get('entity_type', 'unknown')) == et else 0.0
                for node in nodes
            ],
            dtype=np.float32,
        )
        columns.append(col)
        feature_names.append(f'entity_type_{et}')

    all_alert_types: Counter[str] = Counter()
    for i, node in enumerate(nodes):
        node_attrs = graph.nodes[node]
        node_alerts_set: set[str] = set(node_attrs.get('alerts', []))
        for alert in node_alerts_set | edge_alerts_per_node[i]:
            all_alert_types[alert] += 1

    top_alerts_list = [a for a, _ in all_alert_types.most_common(top_k_alerts)]
    for alert_type in top_alerts_list:
        col = np.zeros(n, dtype=np.float32)
        for i, node in enumerate(nodes):
            node_attrs = graph.nodes[node]
            node_alerts_set = set(node_attrs.get('alerts', []))
            if alert_type in (node_alerts_set | edge_alerts_per_node[i]):
                col[i] = 1.0
        columns.append(col)
        feature_names.append(f'alert_{alert_type}')

    # --- Сборка матрицы ---

    X_raw = np.column_stack(columns).astype(np.float32)

    # Log1p к объёмным признакам группы A+B+C (первые 15 колонок)
    # flow_balance (индекс 3) может быть отрицательным — знаковый log1p
    for col_idx in range(15):
        if col_idx == 3:
            X_raw[:, col_idx] = np.sign(X_raw[:, col_idx]) * np.log1p(np.abs(X_raw[:, col_idx]))
        else:
            X_raw[:, col_idx] = np.log1p(np.clip(X_raw[:, col_idx], 0.0, None))

    # Z-score нормализация всех числовых признаков (A+B+C+D, первые 21 колонок)
    n_numeric = 21
    numeric_slice = X_raw[:, :n_numeric]
    col_means = numeric_slice.mean(axis=0)
    col_stds = numeric_slice.std(axis=0)
    col_stds[col_stds < 1e-8] = 1.0
    X_raw[:, :n_numeric] = (numeric_slice - col_means) / col_stds

    logger.info(
        'Матрица признаков построена: %d узлов, %d признаков',
        n,
        X_raw.shape[1],
    )

    return FeatureMatrix(
        X=X_raw,
        feature_names=feature_names,
        node_id_to_index=node_id_to_index,
    )
