from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    import networkx as nx

__all__ = ['GraphStoreRepository']


class GraphStoreRepository(ABC):
    """
    Доменный интерфейс для сохранения графов.
    Отделяет варианты использования и API от любой конкретной реализации графовой базы данных.
    """

    @abstractmethod
    def save_graph(
        self,
        job_id: str,
        graph: nx.DiGraph,
        layout: dict[str, tuple[float, float]],
        scores: dict[str, float],
        edge_scores: dict[str, float],
    ) -> str:
        """Сохраняет граф с укладкой и оценками риска. Возвращает ссылку db_ref."""

    @abstractmethod
    def load_nodes(self, db_ref: str) -> list[dict[str, Any]]:
        """Загружает все записи узлов для сохраненного графа."""

    @abstractmethod
    def load_edges(self, db_ref: str) -> list[dict[str, Any]]:
        """Загружает все записи рёбер для сохраненного графа."""
