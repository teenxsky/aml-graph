from collections.abc import AsyncIterable
from typing import cast

from dishka import Provider, Scope, provide

from src.infrastructure.database.postgres.core import create_db_engine, create_db_session_maker
from src.infrastructure.database.postgres.types import (
    AmlDBEngine,
    AmlDBSession,
    AmlDBSessionMaker,
)
from src.settings import settings

__all__ = ['DatabaseProvider']


class DatabaseProvider(Provider):
    @provide(scope=Scope.APP)
    def aml_engine(self) -> AmlDBEngine:
        return cast(
            AmlDBEngine,
            create_db_engine(
                dsn=settings.aml_db.async_dsn,
                pool_size=settings.aml_db.pool_size,
                max_pool_size=settings.aml_db.max_pool_size,
            ),
        )

    @provide(scope=Scope.APP)
    def aml_session_maker(self, engine: AmlDBEngine) -> AmlDBSessionMaker:
        return cast(AmlDBSessionMaker, create_db_session_maker(engine))

    @provide(scope=Scope.REQUEST)
    async def aml_session(
        self,
        aml_session_maker: AmlDBSessionMaker,
    ) -> AsyncIterable[AmlDBSession]:
        async with aml_session_maker() as session:
            try:
                yield session
                if session.in_transaction():
                    await session.commit()
            except Exception:
                if session.in_transaction():
                    await session.rollback()
                raise
