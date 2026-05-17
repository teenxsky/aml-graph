from fastapi import APIRouter

from src.api.endpoints.v1 import stream, upload

__all__ = ['get_router']

V1_PREFIX = '/v1'


def get_router() -> APIRouter:
    """
    Возвращает маршрутизатор API v1 со всеми обработчиками сообщений v1.
    Все маршруты в этом маршрутизаторе будут иметь префикс 'v1.'.

    :return: APIRouter с '/v1' префиксом
    """
    router = APIRouter(prefix=V1_PREFIX)
    router.include_router(upload.router, tags=['upload'])
    router.include_router(stream.router, tags=['stream'])
    return router
