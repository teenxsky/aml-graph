from __future__ import annotations

from pathlib import Path

__all__ = ['CsvStore']


class CsvStore:
    """Сохраняет и загружает сырые CSV файлы на shared volume."""

    def __init__(self, base_path: str) -> None:
        self._base = Path(base_path)
        self._base.mkdir(parents=True, exist_ok=True)

    def save(self, job_id: str, data: bytes) -> str:
        """Записывает байты в файл и возвращает абсолютный путь."""
        path = self._base / f'{job_id}.csv'
        path.write_bytes(data)
        return str(path)

    @staticmethod
    def load(file_path: str) -> bytes:
        """Читает файл по пути и возвращает его содержимое."""
        return Path(file_path).read_bytes()
