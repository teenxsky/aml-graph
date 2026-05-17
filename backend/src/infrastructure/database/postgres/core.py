from pydantic import PostgresDsn
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from src.settings import settings

__all__ = [
    'create_db_engine',
    'create_db_session_maker',
]


def create_db_engine(
    dsn: PostgresDsn,
    pool_size: int,
    max_pool_size: int,
) -> AsyncEngine:
    """
    Создаёт асинхронный SQLAlchemy Engine для PostgreSQL.

    Конфигурирует пул соединений, включает проверку соединений
    перед использованием (pool_pre_ping) и управляет уровнем
    логирования SQL-запросов через настройку `settings.app.debug`.

    :param dsn: DSN подключения к базе данных PostgreSQL.
    :param pool_size: Базовое количество соединений в пуле.
    :param max_pool_size: Максимальное количество дополнительных соединений сверх `pool_size`.
    :return: Сконфигурированный экземпляр SQLAlchemy Engine.
    """
    return create_async_engine(
        url=dsn.unicode_string(),
        echo=settings.app.debug,
        pool_pre_ping=True,
        pool_size=pool_size,
        max_overflow=max_pool_size,
    )


def create_db_session_maker(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    """
    Создаёт фабрику сессий (async_sessionmaker) для работы с БД.

    Сессии создаются:
    - без автоматического commit,
    - без автоматического flush,
    - без expire объектов после commit.

    :param engine: SQLAlchemy Engine, к которому будет привязана фабрика.
    :return:  Фабрика async_sessionmaker для создания экземпляров AsyncSession.
    """
    return async_sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False,
    )
