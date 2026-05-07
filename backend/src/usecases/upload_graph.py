import uuid

from src.di.providers.sessions import GraphSession, SessionStore
from src.graph.builder import GraphBuilder
from src.graph.detectors import detect_cycles, detect_fanout, detect_shared_device, detect_transit
from src.graph.scoring import compute_scores
from src.shared.schemas import ColumnMapping

__all__ = ['UploadGraphUseCase']


class UploadGraphUseCase:
    """
    Оркестрирует загрузку CSV:
    - построение графа,
    - layout,
    - детекторы,
    - скоринг,
    - сохранение сессии.
    """

    def __init__(self, builder: GraphBuilder, session_store: SessionStore) -> None:
        self._builder = builder
        self._session_store = session_store

    def execute(self, file_bytes: bytes, mapping: ColumnMapping) -> str:
        """Строит граф, запускает все детекторы и возвращает идентификатор сессии."""
        graph = self._builder.build_from_csv(file_bytes, mapping)
        layout = self._builder.compute_layout(graph)

        cycles = detect_cycles(graph)
        fanout = detect_fanout(graph)
        transit = detect_transit(graph)
        shared_device = detect_shared_device(graph)
        scores = compute_scores(graph, cycles, fanout, transit, shared_device)

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
            ),
        )
        return session_id
