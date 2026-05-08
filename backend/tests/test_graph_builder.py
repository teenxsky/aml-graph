import pandas as pd

from src.graph.builder import GraphBuilder
from src.graph.ibm import normalize_ibm_transactions
from src.graph.scoring import apply_alert_scores


def test_build_graph_from_normalized_transactions(ibm_df: pd.DataFrame) -> None:
    normalized = normalize_ibm_transactions(ibm_df)
    graph = GraphBuilder().build_from_normalized_transactions(normalized)

    assert graph.number_of_nodes() == 3
    assert graph.number_of_edges() == 2
    assert 'B1:A1' in graph
    assert 'B2:A2' in graph

    edge = graph.get_edge_data('B1:A1', 'B2:A2')['tx_0']
    assert edge['transaction_id'] == 'tx_0'
    assert edge['amount'] == 1000.0
    assert edge['payment_currency'] == 'USD'
    assert edge['is_laundering'] == 1


def test_is_laundering_label_does_not_create_risk_score(ibm_df: pd.DataFrame) -> None:
    normalized = normalize_ibm_transactions(ibm_df)
    graph = GraphBuilder().build_from_normalized_transactions(normalized)
    node_scores, edge_scores = apply_alert_scores(graph, [])

    assert set(node_scores.values()) == {0.0}
    assert set(edge_scores.values()) == {0.0}
