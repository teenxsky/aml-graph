import io
import logging

import networkx as nx
import pandas as pd

from src.modules.graph.parsing.entity_classifier import (
    classify_ibm_entity_type,
    normalize_entity_type,
)
from src.modules.graph.services.layout import compute_graph_layout
from src.shared.schemas import ColumnMapping

__all__ = ['GraphBuilder']

logger = logging.getLogger(__name__)


def _apply_entity_type(
    graph: nx.Graph,
    node_id: str,
    entity_type: str,
    row_idx: int,
) -> None:
    """Обновить entity_type существующего узла с разрешением конфликтов (first-seen-wins)."""
    existing = graph.nodes[node_id].get('entity_type')
    if existing is None:
        graph.nodes[node_id]['entity_type'] = entity_type
    elif existing != entity_type:
        logger.warning(
            'Конфликт entity_type для узла %s (строка %d): уже задан %r, найден %r — оставляем %r.',
            node_id, row_idx, existing, entity_type, existing,
        )


def _extract_optional_col(
    row: pd.Series,
    col: str | None,
    columns: pd.Index,
) -> str | None:
    if col and col in columns and pd.notna(row[col]):
        return str(row[col])
    return None


def _build_node_id(row: pd.Series, id_col: str, bank_col: str | None) -> str:
    if bank_col and pd.notna(row.get(bank_col)):
        return f'{row[bank_col]}_{row[id_col]}'
    return str(row[id_col])


def _parse_is_laundering(value: str | None) -> bool | None:
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

    @staticmethod
    def build_from_csv(
        file_bytes: bytes,
        column_mapping: ColumnMapping,
    ) -> nx.DiGraph:
        """Строит ориентированный граф из CSV-файла с заданным маппингом столбцов.

        Поля sender_entity_type и receiver_entity_type в маппинге указывают
        на колонки CSV с онтологическим типом каждой стороны транзакции.
        Значения нормализуются через normalize_entity_type — при невалидном
        значении бросается InvalidEntityTypeError.
        """
        df = pd.read_csv(io.BytesIO(file_bytes))
        graph = nx.DiGraph()

        for idx, row in df.iterrows():
            row_num = int(idx) + 2  # CSV row number: +1 for 1-index, +1 for header

            sender = _build_node_id(row, column_mapping.sender_id, column_mapping.sender_bank)
            receiver = _build_node_id(row, column_mapping.receiver_id, column_mapping.receiver_bank)

            sender_entity_type = normalize_entity_type(
                row[column_mapping.sender_entity_type], row=row_num,
            )
            receiver_entity_type = normalize_entity_type(
                row[column_mapping.receiver_entity_type], row=row_num,
            )

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

            for node_id, entity_type in (
                (sender, sender_entity_type),
                (receiver, receiver_entity_type),
            ):
                if node_id not in graph:
                    graph.add_node(
                        node_id,
                        entity_type=entity_type,
                        device_ids=set(),
                        ip_addresses=set(),
                        in_flow=0.0,
                        out_flow=0.0,
                        is_laundering_node=False,
                    )
                else:
                    _apply_entity_type(graph, node_id, entity_type, row_num)

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

    @staticmethod
    def build_from_normalized_transactions(df: pd.DataFrame) -> nx.MultiDiGraph:
        """Строит мультиграф транзакций из нормализованных записей транзакций.

        Entity-тип узлов IBM AML датасета определяется правилом:
        если from_bank == to_bank — оба узла 'individual' (внутрибанковский перевод),
        иначе — 'account' (межбанковский, владелец неоднозначен).
        """
        required = {'transaction_id', 'timestamp', 'sender_id', 'receiver_id', 'amount'}
        missing = required - set(df.columns)
        if missing:
            raise ValueError(f'Missing normalized columns: {", ".join(sorted(missing))}')

        graph = nx.MultiDiGraph()

        for idx, row in df.iterrows():
            sender = str(row['sender_id'])
            receiver = str(row['receiver_id'])
            transaction_id = str(row['transaction_id'])
            amount = float(row['amount'])
            timestamp_raw = pd.to_datetime(row['timestamp'], errors='coerce')
            if pd.isna(timestamp_raw):
                raise ValueError(f'Invalid normalized timestamp: {row["timestamp"]}')
            timestamp = int(timestamp_raw.timestamp())

            from_bank = sender.split(':', 1)[0] if ':' in sender else None
            to_bank = receiver.split(':', 1)[0] if ':' in receiver else None
            entity_type = classify_ibm_entity_type(from_bank, to_bank)

            for node_id in (sender, receiver):
                if node_id not in graph:
                    graph.add_node(
                        node_id,
                        id=node_id,
                        type=entity_type,
                        entity_type=entity_type,
                        label=node_id,
                        risk_score=0.0,
                        alerts=[],
                        device_ids=set(),
                        ip_addresses=set(),
                        in_flow=0.0,
                        out_flow=0.0,
                        is_laundering_node=False,
                    )
                else:
                    _apply_entity_type(graph, node_id, entity_type, int(idx) + 2)

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

    @staticmethod
    def compute_layout(
        graph: nx.DiGraph,
        max_nodes: int = 2000,
    ) -> dict[str, tuple[float, float]]:
        """Вычисляет координаты двумерного графа."""
        return compute_graph_layout(graph, max_nodes=max_nodes)
