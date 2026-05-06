from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import uvicorn
from dishka.integrations.fastapi import setup_dishka
from fastapi import FastAPI

from src.api import get_middlewares, get_root_router
from src.di.container import create_container
from src.logging import get_logging_config
from src.settings import settings

__all__ = ['app']

ROOT_PATH = '/api'


def create_app() -> FastAPI:
    """
    Управление жизненным циклом приложения.
    Запускает и останавливает все необходимые сервисы.

    :return: Настроенное приложение FastAPI
    """
    container = create_container()

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        """
        Lifespan-контекст FastAPI, управляющий ресурсами приложения.

        Вызывается один раз при старте приложения и один раз при его остановке.
        """
        yield
        await container.close()

    fastapi_app: FastAPI = FastAPI(
        title=settings.app.name,
        debug=settings.app.debug,
        root_router=get_root_router(),
        middleware=get_middlewares(),
        docs_url=settings.http.docs_path,
        redoc_url=None,
        include_in_schema=True,
        lifespan=lifespan,
        root_path=ROOT_PATH,
    )

    setup_dishka(container=container, app=fastapi_app)

    return fastapi_app


app: FastAPI = create_app()

if __name__ == '__main__':
    """Запуск приложения."""
    uvicorn.run(
        app='src.main:app',
        host=settings.app.host,
        port=settings.app.port,
        reload=settings.app.debug,
        log_config=get_logging_config(),
    )
