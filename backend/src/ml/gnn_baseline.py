import argparse
import json
import sys
from pathlib import Path

import pandas as pd

from src.ml.gnn_dataset import build_transaction_graph_dataset

__all__ = ['main']


def _require_torch() -> None:
    try:
        import torch  # noqa: F401
    except ImportError as e:
        raise RuntimeError(
            'GNN baseline requires optional PyTorch dependencies. '
            'Install a Python-version-compatible torch build before running training.',
        ) from e


def main() -> None:
    """Run an optional offline GNN baseline skeleton."""
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', required=True)
    parser.add_argument('--epochs', type=int, default=5)
    parser.add_argument('--fast', action='store_true')
    args = parser.parse_args()

    _require_torch()
    df = pd.read_csv(Path(args.input))
    dataset = build_transaction_graph_dataset(df)
    sys.stdout.write(
        json.dumps(
            {
                'transaction_nodes': len(dataset['nodes']),
                'transaction_edges': len(dataset['edges']),
                'epochs': args.epochs,
                'fast': args.fast,
            },
        )
        + '\n',
    )


if __name__ == '__main__':
    main()
