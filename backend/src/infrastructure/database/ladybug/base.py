import tempfile
from pathlib import Path
from typing import Any

import ladybug as lb
import pandas as pd

__all__ = ['LadybugBaseRepository']


class LadybugBaseRepository:
    """
    Базовый класс для репозиториев LadybugDB.

    Инкапсулирует управление подключением, DDL, bulk-импорт через CSV и Cypher-запросы.
    """

    def __init__(self, db_path: str, subdir: str = 'graphs') -> None:
        self._base = Path(db_path) / subdir
        self._base.mkdir(parents=True, exist_ok=True)

    def _db_file(self, key: str) -> str:
        return str(self._base / f'{key}.lbug')

    @staticmethod
    def _open(db_file: str) -> tuple[lb.Database, lb.Connection]:
        db = lb.Database(db_file)
        conn = lb.Connection(db)
        return db, conn

    @staticmethod
    def _bulk_import(
        conn: lb.Connection,
        table: str,
        df: pd.DataFrame,
    ) -> None:
        """Массовая загрузка фрейма данных в таблицу LadybugDB через CSV."""
        if df.empty:
            return
        with tempfile.NamedTemporaryFile(
            mode='w',
            suffix='.csv',
            delete=False,
            encoding='utf-8',
        ) as f:
            df.to_csv(f, index=False)
            tmp_path = f.name
        try:
            conn.execute(f"COPY {table} FROM '{tmp_path}' (HEADER=true)")
        finally:
            Path(tmp_path).unlink(missing_ok=True)

    def _query(self, db_file: str, cypher: str) -> list[dict[str, Any]]:
        """Выполните зашифрованный запрос и верните строки в виде dicts."""
        _, conn = self._open(db_file)
        result = conn.execute(cypher)
        rows = list(result)
        if not rows:
            return []
        headers: list[str] = [str(h) for h in rows[0]]
        return [dict(zip(headers, row, strict=False)) for row in rows[1:]]
