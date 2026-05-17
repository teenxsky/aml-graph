import math

import pandas as pd

from src.modules.graph.parsing.ibm import normalize_ibm_transactions
from src.modules.graph.services.builder import GraphBuilder
from src.modules.graph.services.layout import compute_graph_layout
from src.modules.graph.services.serialization import build_graph_payload


def test_layout_payload_contains_coordinates_and_edges(ibm_df: pd.DataFrame) -> None:
    builder = GraphBuilder()
    graph = builder.build_from_normalized_transactions(normalize_ibm_transactions(ibm_df))
    layout = builder.compute_layout(graph)
    payload = build_graph_payload(graph, layout)

    assert payload['nodes']
    assert payload['edges']
    for node in payload['nodes']:
        assert isinstance(node['x'], float)
        assert isinstance(node['y'], float)
        assert math.isfinite(node['x'])
        assert math.isfinite(node['y'])

    first_edge = payload['edges'][0]
    assert first_edge['source'] == 'B1:A1'
    assert first_edge['target'] == 'B2:A2'


def test_layout_fallback_does_not_collapse_missing_nodes() -> None:
    graph = GraphBuilder().build_from_normalized_transactions(
        pd.DataFrame([
            {'transaction_id': 'tx_0', 'timestamp': '2024-01-01T00:00:00', 'sender_id': 'A', 'receiver_id': 'B', 'amount': 1},
            {'transaction_id': 'tx_1', 'timestamp': '2024-01-01T00:01:00', 'sender_id': 'B', 'receiver_id': 'C', 'amount': 1},
            {'transaction_id': 'tx_2', 'timestamp': '2024-01-01T00:02:00', 'sender_id': 'C', 'receiver_id': 'D', 'amount': 1},
            {'transaction_id': 'tx_3', 'timestamp': '2024-01-01T00:03:00', 'sender_id': 'D', 'receiver_id': 'E', 'amount': 1},
        ]),
    )

    layout = compute_graph_layout(graph, max_nodes=2)

    assert set(layout) == {'A', 'B', 'C', 'D', 'E'}
    assert len(set(layout.values())) > 2
    assert any(position != (0.0, 0.0) for position in layout.values())
