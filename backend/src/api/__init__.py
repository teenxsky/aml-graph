from fastapi import APIRouter
from starlette.middleware import Middleware
from starlette.responses import JSONResponse

from src.api.endpoints import v1
from src.api.middlewares.cors import cors_middleware

__all__ = ['get_root_router', 'get_middlewares']


def get_root_router() -> APIRouter:
    """
    Возвращает корневой маршрутизатор HTTP со всеми обработчиками сообщений приложения.

    :return: APIRouter со всеми версионными маршрутами API
    """
    root_router = APIRouter(default_response_class=JSONResponse)

    root_router.include_router(v1.get_router())

    return root_router


def get_middlewares() -> list[Middleware]:
    """
    Возвращает список middleware для HTTP-транспорта.

    Пример кастомного HTTP-middleware:
    .. code-block:: python
    >>> from starlette.middleware import Middleware
    >>>
    >>> class MyMiddleware(Middleware):
    ...     pass

    :return: Список middleware для HTTP.
    """
    return [cors_middleware]
