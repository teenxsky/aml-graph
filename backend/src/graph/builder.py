import io

import networkx as nx
import pandas as pd

from src.graph.layout import compute_graph_layout
from src.shared.schemas import ColumnMapping

__all__ = ['GraphBuilder']

# Порядок важен: 'CO' проверяем раньше 'C'
_ENTITY_PREFIXES: list[tuple[str, str]] = [
    ('CO', 'company'),
    ('C', 'client'),
    ('A', 'account'),
    ('D', 'device'),
]


def _infer_entity_type(node_id: str) -> str:
    """Определяет тип сущности по префиксу идентификатора узла."""
    for prefix, entity_type in _ENTITY_PREFIXES:
        if node_id.startswith(prefix):
            return entity_type
    return 'unknown'


def _extract_optional_col(
    row: pd.Series,
    col: str | None,
    columns: pd.Index,
) -> str | None:
    """Извлекает значение необязательного столбца CSV, возвращает None если отсутствует или NaN."""
    if col and col in columns and pd.notna(row[col]):
        return str(row[col])
    return None


def _resolve_entity_type(node_id: str, row: pd.Series, has_entity_col: bool) -> str:
    """Возвращает тип сущности из столбца entity_type или по префиксу ID."""
    if has_entity_col and pd.notna(row.get('entity_type')):
        return str(row['entity_type'])
    return _infer_entity_type(node_id)


def _build_node_id(row: pd.Series, id_col: str, bank_col: str | None) -> str:
    """Строит уникальный node_id с учётом банка: «банк_id» или просто «id»."""
    if bank_col and pd.notna(row.get(bank_col)):
        return f'{row[bank_col]}_{row[id_col]}'
    return str(row[id_col])


def _parse_is_laundering(value: str | None) -> bool | None:
    """Парсит флаг отмывания из строкового значения CSV."""
    if value is None:
        return None
    val = value.strip().lower()
    if val in ('1', '1.0', 'true', 'yes'):
        return True
    if val in ('0', '0.0', 'false', 'no'):
        return False
    return None


class GraphBuilder:
    """Строит граф транзакций NetworkX из CSV или normalized DataFrame."""

    def build_from_csv(
        self,
        file_bytes: bytes,
        column_mapping: ColumnMapping,
    ) -> nx.DiGraph:
        """Строит ориентированный граф из CSV-файла с заданным маппингом столбцов."""
        df = pd.read_csv(io.BytesIO(file_bytes))
        graph = nx.DiGraph()
        has_entity_col = 'entity_type' in df.columns

        for idx, row in df.iterrows():
            sender = _build_node_id(row, column_mapping.sender_id, column_mapping.sender_bank)
            receiver = _build_node_id(row, column_mapping.receiver_id, column_mapping.receiver_bank)

            amount_paid = float(row[column_mapping.amount_paid])

            cols = df.columns
            amount_received_raw = _extract_optional_col(row, column_mapping.amount_received, cols)
            amount_received = (
                float(amount_received_raw) if amount_received_raw is not None else None
            )

            payment_currency = _extract_optional_col(row, column_mapping.payment_currency, cols)
            receiving_currency = _extract_optional_col(row, column_mapping.receiving_currency, cols)
            transaction_type = _extract_optional_col(row, column_mapping.transaction_type, cols)
            device_id = _extract_optional_col(row, column_mapping.device_id, cols)
            ip_address = _extract_optional_col(row, column_mapping.ip_address, cols)
            is_laundering = _parse_is_laundering(
                _extract_optional_col(row, column_mapping.is_laundering, cols),
            )

            raw_timestamp = pd.to_datetime(row[column_mapping.timestamp], errors='coerce')
            if pd.isna(raw_timestamp):
                raise ValueError(f'Invalid timestamp value: {row[column_mapping.timestamp]}')
            timestamp = int(raw_timestamp.timestamp())

            for node_id, raw_id in (
                (sender, str(row[column_mapping.sender_id])),
                (receiver, str(row[column_mapping.receiver_id])),
            ):
                if node_id not in graph:
                    entity_type = _resolve_entity_type(raw_id, row, has_entity_col)
                    graph.add_node(
                        node_id,
                        entity_type=entity_type,
                        device_ids=set(),
                        ip_addresses=set(),
                        in_flow=0.0,
                        out_flow=0.0,
                        is_laundering_node=False,
                    )

            if device_id:
                graph.nodes[sender]['device_ids'].add(device_id)
            if ip_address:
                graph.nodes[sender]['ip_addresses'].add(ip_address)

            in_val = amount_received if amount_received is not None else amount_paid
            graph.nodes[receiver]['in_flow'] += in_val
            graph.nodes[sender]['out_flow'] += amount_paid

            if is_laundering:
                graph.nodes[sender]['is_laundering_node'] = True
                graph.nodes[receiver]['is_laundering_node'] = True

            graph.add_edge(
                sender,
                receiver,
                id=f'tx_{idx}',
                transaction_id=f'tx_{idx}',
                amount_paid=amount_paid,
                amount=amount_paid,
                amount_received=amount_received,
                payment_currency=payment_currency,
                receiving_currency=receiving_currency,
                transaction_type=transaction_type,
                payment_format=transaction_type,
                timestamp=timestamp,
                device_id=device_id,
                ip_address=ip_address,
                is_laundering=is_laundering,
                risk_score=0.0,
                alerts=[],
            )

        return graph

    def build_from_normalized_transactions(self, df: pd.DataFrame) -> nx.MultiDiGraph:
        """Build a transaction multigraph from normalized transaction rows."""
        required = {'transaction_id', 'timestamp', 'sender_id', 'receiver_id', 'amount'}
        missing = required - set(df.columns)
        if missing:
            raise ValueError(f'Missing normalized columns: {", ".join(sorted(missing))}')

        graph = nx.MultiDiGraph()

        for _, row in df.iterrows():
            sender = str(row['sender_id'])
            receiver = str(row['receiver_id'])
            transaction_id = str(row['transaction_id'])
            amount = float(row['amount'])
            timestamp_raw = pd.to_datetime(row['timestamp'], errors='coerce')
            if pd.isna(timestamp_raw):
                raise ValueError(f'Invalid normalized timestamp: {row["timestamp"]}')
            timestamp = int(timestamp_raw.timestamp())

            for node_id in (sender, receiver):
                if node_id not in graph:
                    graph.add_node(
                        node_id,
                        id=node_id,
                        type='account',
                        entity_type='account',
                        label=node_id,
                        risk_score=0.0,
                        alerts=[],
                        device_ids=set(),
                        ip_addresses=set(),
                        in_flow=0.0,
                        out_flow=0.0,
                        is_laundering_node=False,
                    )

            amount_received = (
                float(row['amount_received'])
                if 'amount_received' in df.columns and pd.notna(row.get('amount_received'))
                else None
            )
            payment_currency = (
                str(row['payment_currency'])
                if 'payment_currency' in df.columns and pd.notna(row.get('payment_currency'))
                else None
            )
            receiving_currency = (
                str(row['receiving_currency'])
                if 'receiving_currency' in df.columns and pd.notna(row.get('receiving_currency'))
                else None
            )
            payment_format = (
                str(row['payment_format'])
                if 'payment_format' in df.columns and pd.notna(row.get('payment_format'))
                else None
            )
            device_id = (
                str(row['device_id'])
                if 'device_id' in df.columns and pd.notna(row.get('device_id'))
                else None
            )
            ip_address = (
                str(row['ip_address'])
                if 'ip_address' in df.columns and pd.notna(row.get('ip_address'))
                else None
            )
            is_laundering = (
                int(row['is_laundering'])
                if 'is_laundering' in df.columns and pd.notna(row.get('is_laundering'))
                else None
            )

            if device_id:
                graph.nodes[sender]['device_ids'].add(device_id)
            if ip_address:
                graph.nodes[sender]['ip_addresses'].add(ip_address)

            graph.nodes[sender]['out_flow'] += amount
            receiver_flow = amount_received if amount_received is not None else amount
            graph.nodes[receiver]['in_flow'] += receiver_flow
            if is_laundering:
                graph.nodes[sender]['is_laundering_node'] = True
                graph.nodes[receiver]['is_laundering_node'] = True

            graph.add_edge(
                sender,
                receiver,
                key=transaction_id,
                id=transaction_id,
                transaction_id=transaction_id,
                amount=amount,
                amount_paid=amount,
                amount_received=amount_received,
                receiving_currency=receiving_currency,
                payment_currency=payment_currency,
                payment_format=payment_format,
                transaction_type=payment_format,
                timestamp=timestamp,
                is_laundering=is_laundering,
                device_id=device_id,
                ip_address=ip_address,
                type='transfer',
                risk_score=0.0,
                alerts=[],
            )

        return graph

    def compute_layout(
        self,
        graph: nx.DiGraph,
        max_nodes: int = 2000,
    ) -> dict[str, tuple[float, float]]:
        """Compute 2D graph coordinates."""
        return compute_graph_layout(graph, max_nodes=max_nodes)
