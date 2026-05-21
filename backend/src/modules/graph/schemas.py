from typing import Any

from pydantic import BaseModel, Field

__all__ = [
    'GraphMeta',
    'NodeData',
    'NodeChunk',
    'EdgeData',
    'EdgeChunk',
    'DetectorResult',
    'ClusteringMetadata',
    'StepTiming',
    'AnalysisMetadata',
    'AnalysisResultData',
]


class GraphMeta(BaseModel):
    """Графовые метаданные для потоковой передачи."""

    session_id: str
    node_count: int
    edge_count: int


class NodeData(BaseModel):
    """Один узел графа с макетом и оценочными данными.

    Поля ``x`` и ``y`` содержат нормализованные координаты в диапазоне ``[-1, 1]``
    при использовании иерархического layout. Frontend масштабирует их под размер canvas.

    ``entity_type`` — онтологическая категория (account / individual / business /
    payment_institution), задаётся источником данных.
    ``behavioral_role`` — поведенческая роль в графе (regular / hub / transit /
    isolated), вычисляется бэкендом после построения графа.
    """

    id: str
    entity_type: str
    behavioral_role: str = 'regular'
    type: str | None = None
    label: str | None = None
    x: float
    y: float
    risk_score: float
    alerts: list[str] = Field(default_factory=list)
    in_flow: float = 0.0
    out_flow: float = 0.0
    is_laundering_node: bool = False
    attributes: dict[str, Any] = Field(default_factory=dict)


class NodeChunk(BaseModel):
    """Chunk узлов для потоковой передачи."""

    nodes: list[NodeData]


class EdgeData(BaseModel):
    """Одно ребро транзакции в полезной нагрузке графа."""

    id: str | None = None
    source: str
    target: str
    amount_paid: float
    timestamp: int
    risk_score: float = 0.0
    alerts: list[str] = Field(default_factory=list)
    amount_received: float | None = None
    payment_currency: str | None = None
    receiving_currency: str | None = None
    payment_format: str | None = None
    is_laundering: bool | None = None
    attributes: dict[str, Any] = Field(default_factory=dict)


class EdgeChunk(BaseModel):
    """Chunk рёбер для потоковой передачи."""

    edges: list[EdgeData]


class DetectorResult(BaseModel):
    """Результат обнаружения детектором с указанием типа шаблона и элементов оповещения."""

    pattern_type: str
    items: list[dict[str, Any]]


class ClusteringMetadata(BaseModel):
    """Метаданные результата кластеризации."""

    method: str
    n_clusters: int
    extra: dict[str, Any] = Field(default_factory=dict)


class StepTiming(BaseModel):
    """Время выполнения одного шага пайплайна."""

    step: str
    duration_ms: int
    started_at: str   # ISO 8601 datetime
    finished_at: str  # ISO 8601 datetime


class AnalysisMetadata(BaseModel):
    """Структурированные метаданные процесса анализа графа.

    Содержит информацию обо всех алгоритмах применённых при обработке
    графа и обоснованиях их выбора.
    """

    n_nodes: int = 0
    n_edges: int = 0
    density: float = 0.0
    is_directed: bool = True

    clustering_method: str = ''
    clustering_reason: str = ''
    clustering_extra: dict[str, Any] = Field(default_factory=dict)

    scoring_weights: dict[str, float] = Field(default_factory=dict)
    scoring_reason: str = ''
    betweenness_exact: bool = True
    betweenness_k: int = 0

    step_timings: list[StepTiming] = Field(default_factory=list)
    total_duration_ms: int = 0

    algorithm_versions: dict[str, str] = Field(default_factory=dict)


class AnalysisResultData(BaseModel):
    """Результат аналитического этапа: кластеризация + метаданные layout.

    Эмитируется через SSE после ``graph_meta`` и до ``nodes_chunk``.
    Содержит метки кластеров для каждого узла и координаты центров кластеров.
    """

    labels: list[int]
    node_ids: list[str]
    cluster_centroids_2d: list[tuple[float, float]]
    type_centroids: dict[str, list[float]] = Field(default_factory=dict)
    n_clusters: int
    method: str
    metadata: AnalysisMetadata = Field(default_factory=AnalysisMetadata)
