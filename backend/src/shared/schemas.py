from typing import Any

from pydantic import BaseModel, Field

__all__ = [
    'ColumnMapping',
    'SessionResponse',
    'GraphMeta',
    'NodeData',
    'NodeChunk',
    'EdgeData',
    'EdgeChunk',
    'DetectorResult',
]


class ColumnMapping(BaseModel):
    """Маппинг столбцов CSV на поля схемы графа."""

    sender_id: str = Field(description='Название столбца CSV с ID отправителя')
    receiver_id: str = Field(description='Название столбца CSV с ID получателя')
    amount_paid: str = Field(description='Название столбца CSV с суммой исходящего платежа')
    timestamp: str = Field(description='Название столбца CSV с меткой времени')
    sender_bank: str | None = Field(
        default=None,
        description='Название столбца CSV с банком отправителя',
    )
    receiver_bank: str | None = Field(
        default=None,
        description='Название столбца CSV с банком получателя',
    )
    amount_received: str | None = Field(
        default=None,
        description='Название столбца CSV с суммой полученного платежа',
    )
    payment_currency: str | None = Field(
        default=None,
        description='Название столбца CSV с валютой платежа',
    )
    receiving_currency: str | None = Field(
        default=None,
        description='Название столбца CSV с валютой получения',
    )
    transaction_type: str | None = Field(
        default=None,
        description='Название столбца CSV с типом транзакции',
    )
    device_id: str | None = Field(default=None, description='Название столбца CSV с ID устройства')
    ip_address: str | None = Field(default=None, description='Название столбца CSV с IP-адресом')
    is_laundering: str | None = Field(
        default=None,
        description='Название столбца CSV с флагом отмывания',
    )


class SessionResponse(BaseModel):
    """Ответ с идентификатором созданной сессии."""

    session_id: str


class GraphMeta(BaseModel):
    """Метаданные построенного графа транзакций."""

    session_id: str
    node_count: int
    edge_count: int


class NodeData(BaseModel):
    """Данные одного узла графа с координатами и риск-скором."""

    id: str
    entity_type: str
    x: float
    y: float
    risk_score: float
    in_flow: float = 0.0
    out_flow: float = 0.0
    is_laundering_node: bool = False
    attributes: dict[str, Any] = Field(default_factory=dict)


class NodeChunk(BaseModel):
    """Батч узлов графа для SSE-стриминга."""

    nodes: list[NodeData]


class EdgeData(BaseModel):
    """Данные одного ребра (транзакции) графа."""

    source: str
    target: str
    amount_paid: float
    timestamp: int
    amount_received: float | None = None
    payment_currency: str | None = None
    receiving_currency: str | None = None
    transaction_type: str | None = None
    is_laundering: bool | None = None


class EdgeChunk(BaseModel):
    """Батч рёбер графа для SSE-стриминга."""

    edges: list[EdgeData]


class DetectorResult(BaseModel):
    """Результат одного AML-детектора с типом паттерна и списком найденных элементов."""

    pattern_type: str
    items: list[dict[str, Any]]
