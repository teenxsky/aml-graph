import pickle
from pathlib import Path
from typing import Any

__all__ = ['GraphArtifactStore']


class GraphArtifactStore:
    """
    Хранит промежуточные артефакты обработки графов между этапами конвейерной задачи.

    Каждое задание получает отдельный файл pickle,
    в котором накапливаются выходные данные по мере выполнения шагов.
    Все шаги выполняются последовательно, поэтому нет одновременных операций чтения/записи.
    """

    def __init__(self, base_path: str) -> None:
        self._base = Path(base_path)

    def save(self, job_id: str, data: dict[str, Any]) -> None:
        """Сохраняет артефакты задачи в pickle-файл."""
        with (self._base / f'{job_id}_artifacts.pkl').open('wb') as f:
            pickle.dump(data, f)

    def load(self, job_id: str) -> dict[str, Any]:
        """Загружает артефакты задачи из pickle-файла."""
        with (self._base / f'{job_id}_artifacts.pkl').open('rb') as f:
            return pickle.load(f)  # noqa: S301

    def delete(self, job_id: str) -> None:
        """Удаляет pickle-файл артефактов задачи."""
        (self._base / f'{job_id}_artifacts.pkl').unlink(missing_ok=True)
