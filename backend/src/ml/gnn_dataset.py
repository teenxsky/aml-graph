from typing import Any

import pandas as pd

from src.graph.ibm import normalize_ibm_transactions

__all__ = ['build_transaction_graph_dataset']


def _encode(series: pd.Series) -> tuple[list[int], dict[str, int]]:
    values = sorted(str(v) for v in series.fillna('').unique())
    mapping = {value: index for index, value in enumerate(values)}
    return [mapping[str(v)] for v in series.fillna('')], mapping


def build_transaction_graph_dataset(
    ibm_df: pd.DataFrame,
    time_window_seconds: int = 86400,
) -> dict[str, Any]:
    """Build a transaction-node graph dataset from IBM AML rows."""
    tx = normalize_ibm_transactions(ibm_df).sort_values('timestamp').reset_index(drop=True)
    payment_format_ids, payment_format_mapping = _encode(tx['payment_format'])
    payment_currency_ids, payment_currency_mapping = _encode(tx['payment_currency'])
    receiving_currency_ids, receiving_currency_mapping = _encode(tx['receiving_currency'])

    sender_out_degree = tx.groupby('sender_id')['transaction_id'].transform('count')
    receiver_in_degree = tx.groupby('receiver_id')['transaction_id'].transform('count')

    nodes = []
    for idx, row in tx.iterrows():
        timestamp = pd.Timestamp(row['timestamp'])
        nodes.append(
            {
                'id': row['transaction_id'],
                'features': {
                    'amount': float(row['amount']),
                    'amount_received': float(row['amount_received']),
                    'payment_format_id': payment_format_ids[idx],
                    'payment_currency_id': payment_currency_ids[idx],
                    'receiving_currency_id': receiving_currency_ids[idx],
                    'hour': timestamp.hour,
                    'weekday': timestamp.weekday(),
                    'sender_out_degree': int(sender_out_degree.iloc[idx]),
                    'receiver_in_degree': int(receiver_in_degree.iloc[idx]),
                },
                'label': int(row['is_laundering']),
                'sender_id': row['sender_id'],
                'receiver_id': row['receiver_id'],
                'timestamp': int(timestamp.timestamp()),
            },
        )

    edges = []
    for i, left in enumerate(nodes):
        for j, right in enumerate(nodes):
            if i == j:
                continue
            if right['timestamp'] < left['timestamp']:
                continue
            if right['timestamp'] - left['timestamp'] > time_window_seconds:
                continue
            if left['receiver_id'] == right['sender_id'] or left['sender_id'] == right['sender_id']:
                edges.append({'source': left['id'], 'target': right['id']})

    return {
        'nodes': nodes,
        'edges': edges,
        'metadata': {
            'payment_format_mapping': payment_format_mapping,
            'payment_currency_mapping': payment_currency_mapping,
            'receiving_currency_mapping': receiving_currency_mapping,
        },
    }
