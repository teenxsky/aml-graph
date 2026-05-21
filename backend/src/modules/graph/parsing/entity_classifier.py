"""Классификация и нормализация типов сущностей для построения графа.

Содержит две функции:
- normalize_entity_type: преобразование пользовательских строк
  в канонические коды entity_type с поддержкой синонимов (рус/eng).
- classify_ibm_entity_type: правило для IBM-парсера на основе
  ToBank == FromBank.
"""

from __future__ import annotations

from typing import Final

ALLOWED_ENTITY_TYPES: Final[frozenset[str]] = frozenset({
    'account', 'individual', 'business', 'payment_institution',
})

_ENTITY_TYPE_SYNONYMS: Final[dict[str, str]] = {
    # account
    'account': 'account',
    'acc': 'account',
    'счёт': 'account',
    'счет': 'account',

    # individual
    'individual': 'individual',
    'person': 'individual',
    'private': 'individual',
    'фл': 'individual',
    'физлицо': 'individual',
    'физическое лицо': 'individual',

    # business
    'business': 'business',
    'corporate': 'business',
    'company': 'business',
    'ooo': 'business',
    'ооо': 'business',
    'юл': 'business',
    'юрлицо': 'business',
    'юридическое лицо': 'business',

    # payment_institution
    'payment_institution': 'payment_institution',
    'payment institution': 'payment_institution',
    'psp': 'payment_institution',
    'gateway': 'payment_institution',
    'exchange': 'payment_institution',
    'обменник': 'payment_institution',
    'платёжный институт': 'payment_institution',
    'платежный институт': 'payment_institution',
}


class InvalidEntityTypeError(ValueError):
    """Бросается когда значение entity_type не входит в допустимые.

    Содержит сам некорректный value и подсказку о допустимых вариантах —
    эту информацию фронтенд показывает пользователю при ошибке загрузки CSV.
    """

    def __init__(self, value: str, row: int | None = None) -> None:
        self.invalid_value = value
        self.row = row
        message = (
            f'Недопустимое значение типа сущности: "{value}". '
            f'Допустимые значения: {", ".join(sorted(ALLOWED_ENTITY_TYPES))}. '
            f'Поддерживаются также русскоязычные синонимы '
            f'(физлицо, юрлицо, счёт, платёжный институт).'
        )
        if row is not None:
            message = f'Строка {row}: {message}'
        super().__init__(message)


def normalize_entity_type(value: object, *, row: int | None = None) -> str:
    """Нормализовать пользовательскую строку в канонический код entity_type.

    Применяет: strip, lower, lookup в _ENTITY_TYPE_SYNONYMS.

    Args:
        value: Строка из CSV (например, "Физлицо" или "BUSINESS").
        row: Номер строки CSV для сообщения об ошибке (опционально).

    Returns:
        Канонический код entity_type из ALLOWED_ENTITY_TYPES.

    Raises:
        InvalidEntityTypeError: Если value не маппится ни на один канонический код.
    """
    if value is None or (isinstance(value, float) and value != value):  # NaN check
        raise InvalidEntityTypeError('(пусто)', row=row)

    normalized = str(value).strip().lower()
    if not normalized:
        raise InvalidEntityTypeError('(пусто)', row=row)

    if normalized not in _ENTITY_TYPE_SYNONYMS:
        raise InvalidEntityTypeError(str(value), row=row)

    return _ENTITY_TYPE_SYNONYMS[normalized]


def classify_ibm_entity_type(from_bank: str | None, to_bank: str | None) -> str:
    """Определить entity_type для узлов IBM AML датасета.

    Правило: если перевод происходит внутри одного банка (from_bank == to_bank),
    оба узла классифицируются как individual. Если межбанковский — как account.

    Args:
        from_bank: Идентификатор банка отправителя из IBM CSV.
        to_bank: Идентификатор банка получателя из IBM CSV.

    Returns:
        'individual' если from_bank == to_bank (оба не None), иначе 'account'.
    """
    if from_bank is None or to_bank is None:
        return 'account'
    return 'individual' if from_bank == to_bank else 'account'
