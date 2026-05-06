from typing import Any, TypeVar

from pydantic import BaseModel, Field

T = TypeVar('T')


class PaginationMetaDTO(BaseModel):
    """Метаданные пагинации."""

    total: int = Field(description='Общее количество записей')
    limit: int = Field(description='Лимит на страницу')
    offset: int = Field(description='Смещение')


class ResponseDTO[T](BaseModel):
    """Схема стандартного ответа сервера."""

    data: T = Field(..., description='Данные полученные в ходе выполнения запроса')
    meta: dict[str, Any] = Field(
        default_factory=dict,
        description='Метаданные выполнения запроса',
    )


class PaginatedResponseDTO[T](ResponseDTO[T]):
    """Схема пагинированного ответа сервера."""

    meta: PaginationMetaDTO = Field(description='Метаданные пагинации')
