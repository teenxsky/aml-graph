from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from dishka.integrations.fastapi import setup_dishka as setup_fastapi
from fastapi import FastAPI

from src.api import get_middlewares, get_root_router
from src.di.container import create_container
from src.infrastructure.task_processing.broker import rabbitmq_broker
from src.infrastructure.task_processing.setup import setup_taskiq
from src.settings import settings

__all__ = ['app']

ROOT_PATH = '/api'

container = create_container()
taskiq_broker = rabbitmq_broker


def create_app() -> FastAPI:
    """
    Управление жизненным циклом приложения.
    Запускает и останавливает все необходимые сервисы.

    :return: Настроенное приложение FastAPI
    """

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        if not taskiq_broker.is_worker_process:
            await taskiq_broker.startup()

        yield

        if not taskiq_broker.is_worker_process:
            await taskiq_broker.shutdown()

        await container.close()

    fastapi = FastAPI(
        title=settings.app.name,
        debug=settings.app.debug,
        middleware=get_middlewares(),
        docs_url=settings.http.docs_path,
        redoc_url=None,
        include_in_schema=True,
        lifespan=lifespan,
        root_path=ROOT_PATH,
    )

    fastapi.include_router(get_root_router())

    setup_fastapi(app=fastapi, container=container)
    setup_taskiq(taskiq_broker=taskiq_broker, container=container)

    return fastapi


app: FastAPI = create_app()
