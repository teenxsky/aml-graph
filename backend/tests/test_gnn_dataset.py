import pandas as pd

from src.ml.gnn_dataset import build_transaction_graph_dataset


def test_gnn_dataset_construction_without_training(ibm_df: pd.DataFrame) -> None:
    dataset = build_transaction_graph_dataset(ibm_df)

    assert len(dataset['nodes']) == 2
    assert dataset['nodes'][0]['id'] == 'tx_0'
    assert dataset['nodes'][0]['label'] == 1
    assert dataset['edges'] == [{'source': 'tx_0', 'target': 'tx_1'}]
    assert 'payment_format_mapping' in dataset['metadata']
