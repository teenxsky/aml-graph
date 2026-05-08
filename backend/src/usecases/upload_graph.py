import uuid
from typing import Any

from src.di.providers.sessions import GraphSession, SessionStore
from src.graph.builder import GraphBuilder
from src.graph.detectors import detect_cycles, detect_fanout, detect_shared_device, detect_transit
from src.graph.ibm import read_ibm_transactions
from src.graph.layout import compute_graph_layout
from src.graph.scoring import apply_alert_scores, flatten_alerts
from src.shared.schemas import ColumnMapping

__all__ = ['UploadGraphUseCase']


class UploadGraphUseCase:
    """Build graph sessions from uploaded transaction files."""

    def __init__(self, builder: GraphBuilder, session_store: SessionStore) -> None:
        self._builder = builder
        self._session_store = session_store

    def execute(self, file_bytes: bytes, mapping: ColumnMapping) -> str:
        """Build and save a graph session from a mapped CSV file."""
        graph = self._builder.build_from_csv(file_bytes, mapping)
        return self._save_graph(graph)

    def execute_ibm(self, file_bytes: bytes, filename: str | None = None) -> str:
        """Build and save a graph session from IBM Transactions for AML input."""
        normalized = read_ibm_transactions(file_bytes, filename)
        graph = self._builder.build_from_normalized_transactions(normalized)
        return self._save_graph(graph)

    def _save_graph(self, graph: Any) -> str:
        cycles = detect_cycles(graph)
        fanout = detect_fanout(graph)
        transit = detect_transit(graph)
        shared_device = detect_shared_device(graph)
        alerts = flatten_alerts(cycles, fanout, transit, shared_device)
        scores, edge_scores = apply_alert_scores(graph, alerts)
        layout = compute_graph_layout(graph)

        session_id = str(uuid.uuid4())
        self._session_store.save(
            session_id,
            GraphSession(
                graph=graph,
                layout=layout,
                cycles=cycles,
                fanout=fanout,
                transit=transit,
                shared_device=shared_device,
                scores=scores,
                alerts=alerts,
                edge_scores=edge_scores,
            ),
        )
        return session_id
