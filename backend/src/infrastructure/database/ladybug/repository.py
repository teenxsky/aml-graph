from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

import pandas as pd

from src.infrastructure.database.ladybug.base import LadybugBaseRepository
from src.modules.graph.repositories.graph import GraphStoreRepository

if TYPE_CHECKING:
    import networkx as nx

__all__ = ['LadybugGraphRepository']

_ACCOUNT_DDL = """
CREATE NODE TABLE Account (
    pk                  STRING  PRIMARY KEY,
    account_id          STRING,
    entity_type         STRING,
    in_flow             DOUBLE,
    out_flow            DOUBLE,
    risk_score          DOUBLE,
    is_laundering_node  BOOLEAN,
    x                   DOUBLE,
    y                   DOUBLE,
    alerts              STRING
)
"""

_TRANSFER_DDL = """
CREATE REL TABLE TRANSFER (
    FROM Account TO Account,
    transaction_id      STRING,
    amount_paid         DOUBLE,
    amount_received     DOUBLE,
    payment_currency    STRING,
    receiving_currency  STRING,
    payment_format      STRING,
    timestamp           INT64,
    is_laundering       BOOLEAN,
    risk_score          DOUBLE,
    alerts              STRING
)
"""

_LOAD_NODES_CYPHER = (
    'MATCH (a:Account) RETURN '
    'a.account_id, a.entity_type, a.in_flow, a.out_flow, '
    'a.risk_score, a.is_laundering_node, a.x, a.y, a.alerts'
)

_LOAD_EDGES_CYPHER = (
    'MATCH (a:Account)-[t:TRANSFER]->(b:Account) RETURN '
    'a.account_id AS source, b.account_id AS target, '
    't.transaction_id, t.amount_paid, t.amount_received, '
    't.payment_currency, t.receiving_currency, t.payment_format, '
    't.timestamp, t.is_laundering, t.risk_score, t.alerts'
)


class LadybugGraphRepository(LadybugBaseRepository, GraphStoreRepository):
    """Хранилище AML graph, поддерживаемое LadybugDB."""

    def save_graph(
        self,
        job_id: str,
        graph: nx.DiGraph,
        layout: dict[str, tuple[float, float]],
        scores: dict[str, float],
        edge_scores: dict[str, float],
    ) -> str:
        """Сохраняет граф в отдельный .lbug-файл и возвращает путь к нему."""
        db_file = self._db_file(job_id)
        _, conn = self._open(db_file)

        conn.execute(_ACCOUNT_DDL)
        conn.execute(_TRANSFER_DDL)

        self._bulk_import(conn, 'Account', self._build_nodes_df(job_id, graph, layout, scores))
        self._bulk_import(conn, 'TRANSFER', self._build_edges_df(job_id, graph, edge_scores))

        return db_file

    def load_nodes(self, db_ref: str) -> list[dict[str, Any]]:
        """Загружает все узлы графа из LadybugDB."""
        return self._query(db_ref, _LOAD_NODES_CYPHER)

    def load_edges(self, db_ref: str) -> list[dict[str, Any]]:
        """Загружает все рёбра графа из LadybugDB."""
        return self._query(db_ref, _LOAD_EDGES_CYPHER)

    @staticmethod
    def _build_nodes_df(
        job_id: str,
        graph: nx.DiGraph,
        layout: dict[str, tuple[float, float]],
        scores: dict[str, float],
    ) -> pd.DataFrame:
        rows: list[dict[str, Any]] = []
        for node_id, attrs in graph.nodes(data=True):
            node_str = str(node_id)
            x, y = layout.get(node_str, (0.0, 0.0))
            rows.append(
                {
                    'pk': f'{job_id}::{node_str}',
                    'account_id': node_str,
                    'entity_type': attrs.get('entity_type', 'unknown'),
                    'in_flow': float(attrs.get('in_flow', 0.0)),
                    'out_flow': float(attrs.get('out_flow', 0.0)),
                    'risk_score': float(scores.get(node_str, 0.0)),
                    'is_laundering_node': bool(attrs.get('is_laundering_node', False)),
                    'x': float(x),
                    'y': float(y),
                    'alerts': json.dumps(list(attrs.get('alerts', []))),
                },
            )
        return pd.DataFrame(rows)

    @staticmethod
    def _build_edges_df(
        job_id: str,
        graph: nx.DiGraph,
        edge_scores: dict[str, float],
    ) -> pd.DataFrame:
        rows: list[dict[str, Any]] = []
        for u, v, d in graph.edges(data=True):
            tid = str(d.get('transaction_id') or d.get('id') or f'{u}->{v}')
            rows.append(
                {
                    'from': f'{job_id}::{u}',
                    'to': f'{job_id}::{v}',
                    'transaction_id': tid,
                    'amount_paid': float(d.get('amount_paid', 0.0)),
                    'amount_received': float(d.get('amount_received') or 0.0),
                    'payment_currency': str(d.get('payment_currency') or ''),
                    'receiving_currency': str(d.get('receiving_currency') or ''),
                    'payment_format': str(d.get('payment_format') or ''),
                    'timestamp': int(d.get('timestamp', 0)),
                    'is_laundering': bool(d.get('is_laundering', False)),
                    'risk_score': float(edge_scores.get(tid, d.get('risk_score', 0.0))),
                    'alerts': json.dumps(list(d.get('alerts', []))),
                },
            )
        return pd.DataFrame(rows)
