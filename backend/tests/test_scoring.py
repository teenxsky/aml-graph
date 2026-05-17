import networkx as nx

from src.modules.graph.analytics.scoring import apply_alert_scores


def test_one_alert_gives_score() -> None:
    graph = nx.DiGraph()
    graph.add_edge('A', 'B', id='tx_0')

    node_scores, edge_scores = apply_alert_scores(
        graph,
        [{'id': 'a1', 'score': 0.7, 'node_ids': ['A'], 'edge_ids': ['tx_0']}],
    )

    assert node_scores['A'] == 0.7
    assert edge_scores['tx_0'] == 0.7


def test_several_alerts_increase_score() -> None:
    graph = nx.DiGraph()
    graph.add_node('A')

    node_scores, _ = apply_alert_scores(
        graph,
        [
            {'id': 'a1', 'score': 0.5, 'node_ids': ['A']},
            {'id': 'a2', 'score': 0.5, 'node_ids': ['A']},
        ],
    )

    assert node_scores['A'] == 0.75


def test_score_never_exceeds_one() -> None:
    graph = nx.DiGraph()
    graph.add_node('A')

    node_scores, _ = apply_alert_scores(
        graph,
        [
            {'id': 'a1', 'score': 2.0, 'node_ids': ['A']},
            {'id': 'a2', 'score': 1.0, 'node_ids': ['A']},
        ],
    )

    assert node_scores['A'] == 1.0


def test_nodes_and_edges_without_alerts_remain_zero() -> None:
    graph = nx.DiGraph()
    graph.add_edge('A', 'B', id='tx_0')

    node_scores, edge_scores = apply_alert_scores(graph, [])

    assert node_scores == {'A': 0.0, 'B': 0.0}
    assert edge_scores == {'tx_0': 0.0}
