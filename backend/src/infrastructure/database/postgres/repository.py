from typing import TypeVar

from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.database.postgres.types import BaseDatabaseModel

ModelType = TypeVar('ModelType', bound=BaseDatabaseModel)


class BaseRepository[ModelType]:
    """Базовый репозиторий для выполнения общих операций с базой данных."""

    model: type[ModelType]

    def __init__(self, session: AsyncSession) -> None:
        model = getattr(self, 'model', None)

        if model is None:
            raise ValueError(f'Модель репозитория {self.__class__.__name__} не определена')

        self._session: AsyncSession = session

    async def save(self, model: ModelType) -> None:
        """
        Сохраняет ORM модель в базу данных и обновляет переданную модель актуальными данными.

        :param model: Модель ORM
        """
        self._session.add(model)
        await self._session.flush()
        await self._session.refresh(model)
