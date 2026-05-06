from fastapi import APIRouter

__all__ = ['get_router']

V1_PREFIX = '/v1'


def get_router() -> APIRouter:
    """
    Возвращает маршрутизатор API v1 со всеми обработчиками сообщений v1.
    Все маршруты в этом маршрутизаторе будут иметь префикс 'v1.'.

    :return: APIRouter с '/v1' префиксом
    """
    return APIRouter(prefix=V1_PREFIX)
