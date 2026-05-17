from dishka import AsyncContainer, make_async_container

from src.di.providers.database import DatabaseProvider
from src.di.providers.repositories import RepositoriesProvider
from src.di.providers.services import ServicesProvider
from src.di.providers.use_cases import UseCasesProvider


def create_container() -> AsyncContainer:
    """Создаёт и возвращает Dishka DI-контейнер приложения."""
    return make_async_container(
        DatabaseProvider(),
        RepositoriesProvider(),
        ServicesProvider(),
        UseCasesProvider(),
    )
