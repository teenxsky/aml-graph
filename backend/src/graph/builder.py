import io

import networkx as nx
import pandas as pd

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
    """Строит граф транзакций NetworkX из CSV и вычисляет его layout."""

    def build_from_csv(
        self,
        file_bytes: bytes,
        column_mapping: ColumnMapping,
    ) -> nx.DiGraph:
        """Строит ориентированный граф из CSV-файла с заданным маппингом столбцов."""
        df = pd.read_csv(io.BytesIO(file_bytes))
        graph = nx.DiGraph()
        has_entity_col = 'entity_type' in df.columns

        for _, row in df.iterrows():
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
                amount_paid=amount_paid,
                amount_received=amount_received,
                payment_currency=payment_currency,
                receiving_currency=receiving_currency,
                transaction_type=transaction_type,
                timestamp=timestamp,
                device_id=device_id,
                ip_address=ip_address,
                is_laundering=is_laundering,
            )

        return graph

    def compute_layout(self, graph: nx.DiGraph) -> dict[str, tuple[float, float]]:
        """Вычисляет 2D-координаты узлов через nx.forceatlas2_layout, при ошибке — spring layout."""
        if len(graph) == 0:
            return {}
        if len(graph) == 1:
            return {str(next(iter(graph.nodes()))): (0.0, 0.0)}

        try:
            positions = nx.forceatlas2_layout(graph, max_iter=500, seed=42)
        except Exception:  # noqa: BLE001
            positions = nx.spring_layout(graph, seed=42)

        return {str(node): (float(x), float(y)) for node, (x, y) in positions.items()}
