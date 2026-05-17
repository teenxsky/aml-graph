from typing import NewType

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
)
from sqlalchemy.orm import DeclarativeBase

__all__ = [
    'BaseDatabaseModel',
    'AmlDBEngine',
    'AmlDBSession',
    'AmlDBSessionMaker',
]


class BaseDatabaseModel(DeclarativeBase):
    """Базовая ORM-модель базы данных."""


# NewTypes для различия компонентов для подключения баз данных в DI
AmlDBEngine = NewType('AmlDBEngine', AsyncEngine)
AmlDBSession = NewType('AmlDBSession', AsyncSession)
AmlDBSessionMaker = NewType(
    'AmlDBSessionMaker',
    async_sessionmaker[AmlDBSession],
)
