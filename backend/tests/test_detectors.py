import pandas as pd

from src.graph.builder import GraphBuilder
from src.graph.detectors import detect_cycles, detect_fanout, detect_shared_device, detect_transit


def _graph_from_rows(rows: list[dict]):
    return GraphBuilder().build_from_normalized_transactions(pd.DataFrame(rows))


def test_cycle_detected() -> None:
    graph = _graph_from_rows([
        {'transaction_id': 'tx_0', 'timestamp': '2024-01-01T00:00:00', 'sender_id': 'A', 'receiver_id': 'B', 'amount': 100},
        {'transaction_id': 'tx_1', 'timestamp': '2024-01-01T01:00:00', 'sender_id': 'B', 'receiver_id': 'C', 'amount': 98},
        {'transaction_id': 'tx_2', 'timestamp': '2024-01-01T02:00:00', 'sender_id': 'C', 'receiver_id': 'A', 'amount': 97},
    ])

    alerts = detect_cycles(graph)

    assert alerts
    assert alerts[0]['type'] == 'cycle'
    assert set(alerts[0]['node_ids']) == {'A', 'B', 'C'}


def test_fanout_detected() -> None:
    graph = _graph_from_rows([
        {'transaction_id': 'tx_0', 'timestamp': '2024-01-01T00:00:00', 'sender_id': 'A', 'receiver_id': 'B', 'amount': 100},
        {'transaction_id': 'tx_1', 'timestamp': '2024-01-01T00:10:00', 'sender_id': 'A', 'receiver_id': 'C', 'amount': 101},
        {'transaction_id': 'tx_2', 'timestamp': '2024-01-01T00:20:00', 'sender_id': 'A', 'receiver_id': 'D', 'amount': 99},
    ])

    alerts = detect_fanout(graph, min_receivers=3)

    assert alerts
    assert alerts[0]['source'] == 'A'
    assert set(alerts[0]['receivers']) == {'B', 'C', 'D'}


def test_transit_detected() -> None:
    graph = _graph_from_rows([
        {'transaction_id': 'tx_0', 'timestamp': '2024-01-01T00:00:00', 'sender_id': 'A', 'receiver_id': 'B', 'amount': 100},
        {'transaction_id': 'tx_1', 'timestamp': '2024-01-01T00:10:00', 'sender_id': 'C', 'receiver_id': 'B', 'amount': 100},
        {'transaction_id': 'tx_2', 'timestamp': '2024-01-01T00:20:00', 'sender_id': 'B', 'receiver_id': 'D', 'amount': 100},
        {'transaction_id': 'tx_3', 'timestamp': '2024-01-01T00:30:00', 'sender_id': 'B', 'receiver_id': 'E', 'amount': 100},
    ])

    alerts = detect_transit(graph)

    assert any(alert['node_id'] == 'B' for alert in alerts)


def test_shared_identity_detected_when_fields_exist() -> None:
    graph = _graph_from_rows([
        {'transaction_id': 'tx_0', 'timestamp': '2024-01-01T00:00:00', 'sender_id': 'A', 'receiver_id': 'B', 'amount': 100, 'device_id': 'D1'},
        {'transaction_id': 'tx_1', 'timestamp': '2024-01-01T00:10:00', 'sender_id': 'C', 'receiver_id': 'D', 'amount': 100, 'device_id': 'D1'},
    ])

    alerts = detect_shared_device(graph)

    assert alerts
    assert alerts[0]['identity_id'] == 'D1'
    assert set(alerts[0]['accounts']) == {'A', 'C'}


def test_shared_identity_empty_when_fields_absent() -> None:
    graph = _graph_from_rows([
        {'transaction_id': 'tx_0', 'timestamp': '2024-01-01T00:00:00', 'sender_id': 'A', 'receiver_id': 'B', 'amount': 100},
    ])

    assert detect_shared_device(graph) == []
