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


class ColumnMapping(BaseModel):  # noqa: D101
    sender_id: str
    receiver_id: str
    amount_paid: str
    timestamp: str
    sender_bank: str | None = None
    receiver_bank: str | None = None
    amount_received: str | None = None
    payment_currency: str | None = None
    receiving_currency: str | None = None
    transaction_type: str | None = None
    device_id: str | None = None
    ip_address: str | None = None
    is_laundering: str | None = None


class SessionResponse(BaseModel):
    """Response with created session identifier."""

    session_id: str


class GraphMeta(BaseModel):
    """Graph metadata for SSE streaming."""

    session_id: str
    node_count: int
    edge_count: int


class NodeData(BaseModel):
    """One graph node with layout and scoring data."""

    id: str
    entity_type: str
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
    """SSE node chunk."""

    nodes: list[NodeData]


class EdgeData(BaseModel):
    """One transaction edge in a graph payload."""

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
    transaction_type: str | None = None
    is_laundering: bool | None = None
    attributes: dict[str, Any] = Field(default_factory=dict)


class EdgeChunk(BaseModel):
    """SSE edge chunk."""

    edges: list[EdgeData]


class DetectorResult(BaseModel):
    """Detector result with pattern type and alert items."""

    pattern_type: str
    items: list[dict[str, Any]]
