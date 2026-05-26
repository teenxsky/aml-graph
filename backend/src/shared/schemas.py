from typing import Any, TypeVar

from pydantic import BaseModel, Field

__all__ = [
    'ColumnMapping',
    'ResponseDTO',
    'PaginationMetaDTO',
    'PaginatedResponseDTO',
]

T = TypeVar('T')


class ColumnMapping(BaseModel):
    """DTO для задания соответствий полей входного датасета с полями датасета IBM AMLSlim.

    Поля sender_entity_type и receiver_entity_type обязательны: они указывают
    колонки CSV, из которых берётся онтологический тип каждой стороны транзакции.
    Допустимые значения в колонках: account, individual, business, payment_institution.
    """

    sender_id: str
    receiver_id: str
    amount_paid: str
    timestamp: str
    sender_entity_type: str
    receiver_entity_type: str
    sender_bank: str | None = None
    receiver_bank: str | None = None
    amount_received: str | None = None
    payment_currency: str | None = None
    receiving_currency: str | None = None
    transaction_type: str | None = None
    device_id: str | None = None
    ip_address: str | None = None
    is_laundering: str | None = None


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
