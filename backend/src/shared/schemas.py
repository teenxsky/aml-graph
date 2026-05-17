from pydantic import BaseModel

__all__ = [
    'ColumnMapping',
]


class ColumnMapping(BaseModel):
    """DTO для задания соответствий полей входного датасета с полями датасета IBM AMLSlim."""

    sender_id: str
    receiver_id: str
    amount_paid: str
    timestamp: str
    sender_bank: str | None = None
    receiver_bank: str | None = None
    amount_received: str | None = None
    payment_currency: str | None = None
    receiving_currency: str | None = None
    transaction_type: str | None = None
    device_id: str | None = None
    ip_address: str | None = None
    is_laundering: str | None = None
