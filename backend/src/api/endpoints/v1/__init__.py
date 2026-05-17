from fastapi import APIRouter

from src.api.endpoints.v1 import processing_info, stream, upload

__all__ = ['get_router']

V1_PREFIX = '/v1'


def get_router() -> APIRouter:
    """
    Возвращает маршрутизатор API v1 со всеми обработчиками сообщений v1.
    Все маршруты в этом маршрутизаторе будут иметь префикс 'v1.'.

    :return: APIRouter с '/v1' префиксом
    """
    router = APIRouter(prefix=V1_PREFIX)

    router.include_router(stream.router, tags=['Graph'])

    router.include_router(upload.router, tags=['Jobs'])
    router.include_router(processing_info.router, tags=['Jobs'])
    return router
