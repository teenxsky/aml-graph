from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

import networkx as nx

# AGC строит dense матрицу схожести n×n float32. При n=1500 это ~9 МБ
# и eigsh работает за 2-5 секунд - приемлемо. При n>1500 переключение
# на Louvain (структурный, без матрицы признаков, O(n log n)).
AGC_NODE_LIMIT = 1500

# Точный betweenness_centrality - O(n·m). При n>500 на плотном графе
# становится медленным, используется sampling.
BETWEENNESS_EXACT_LIMIT = 500
BETWEENNESS_SAMPLE_K = 200  # ~5% погрешности при n=5000


@dataclass(frozen=True, slots=True)
class ScoringWeights:
    """Веса компонентов формулы риск-скоринга.

    Итоговый скор узла = 1 − ∏(1 − w_i · score_i),
    где каждый компонент нормализован в [0, 1].
    """

    detector_alerts: float
    betweenness: float
    pagerank: float
    flow_imbalance: float


# Малые графы (n ≤ 1500): детекторы паттернов работают надёжно
# (мало шума), структурные центральности менее дискриминирующие
# (граф плотный, диаметр маленький).
SCORING_WEIGHTS_SMALL = ScoringWeights(
    detector_alerts=0.55,
    betweenness=0.15,
    pagerank=0.15,
    flow_imbalance=0.15,
)

# Большие графы (n > 1500): на разреженной структуре betweenness
# выделяет транзитные узлы, детекторы дают больше false positives.
SCORING_WEIGHTS_LARGE = ScoringWeights(
    detector_alerts=0.35,
    betweenness=0.30,
    pagerank=0.20,
    flow_imbalance=0.15,
)


@dataclass(frozen=True, slots=True)
class AnalysisStrategy:
    """Стратегия обработки конкретного графа.

    Все поля попадают в метаданные ответа SSE для прозрачности.
    """

    clustering_method: Literal['agc', 'louvain']
    clustering_reason: str
    scoring_weights: ScoringWeights
    scoring_reason: str
    betweenness_exact: bool
    betweenness_k: int  # 0 если exact


def select_strategy(graph: nx.MultiDiGraph) -> AnalysisStrategy:
    """Выбрать стратегию обработки графа автоматически.

    Решения основаны на вычислительных ограничениях алгоритмов и
    характеристиках графа (размер, плотность). Возвращает AnalysisStrategy
    с человекочитаемыми обоснованиями для прозрачности.
    """
    n = graph.number_of_nodes()

    # Кластеризация
    if n <= AGC_NODE_LIMIT:
        clustering_method: Literal['agc', 'louvain'] = 'agc'
        clustering_reason = (
            f'Использован AGC: размер графа ({n} узлов) позволяет '
            f'применить спектральный метод с учётом признаков узлов.'
        )
    else:
        clustering_method = 'louvain'
        clustering_reason = (
            f'Использован Louvain: размер графа ({n} узлов) превышает '
            f'порог {AGC_NODE_LIMIT} для спектральных методов.'
        )

    # Веса скоринга
    if n <= AGC_NODE_LIMIT:
        scoring_weights = SCORING_WEIGHTS_SMALL
        scoring_reason = (
            'На малом графе детекторы AML-паттернов работают надёжно; '
            'они доминируют в формуле скоринга, центральности - вспомогательны.'
        )
    else:
        scoring_weights = SCORING_WEIGHTS_LARGE
        scoring_reason = (
            'На большом графе усилен вклад betweenness centrality - '
            'она хорошо выделяет транзитные узлы; вес детекторов снижен '
            'из-за повышенного уровня шума.'
        )

    # Betweenness
    betweenness_exact = n <= BETWEENNESS_EXACT_LIMIT
    betweenness_k = 0 if betweenness_exact else BETWEENNESS_SAMPLE_K

    return AnalysisStrategy(
        clustering_method=clustering_method,
        clustering_reason=clustering_reason,
        scoring_weights=scoring_weights,
        scoring_reason=scoring_reason,
        betweenness_exact=betweenness_exact,
        betweenness_k=betweenness_k,
    )
