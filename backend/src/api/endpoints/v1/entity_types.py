"""Эндпоинт получения описаний категорий entity_type и behavioral_role.

Используется фронтендом для:
- Отображения подсказок в форме маппинга колонок CSV.
- Tooltip-ов на легенде графа.
"""

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()


class CategoryDescription(BaseModel):
    """Описание категории сущности или поведенческой роли."""

    code: str
    label_ru: str
    short_description: str
    color_hint: str  # hex без #


ENTITY_TYPES: list[CategoryDescription] = [
    CategoryDescription(
        code='account',
        label_ru='Счёт',
        short_description='Банковский счёт без явного владельца.',
        color_hint='66bb6a',
    ),
    CategoryDescription(
        code='individual',
        label_ru='Физлицо',
        short_description='Физическое лицо — частный клиент банка.',
        color_hint='4fc3f7',
    ),
    CategoryDescription(
        code='business',
        label_ru='Юрлицо',
        short_description='Юридическое лицо — компания, ИП, ООО.',
        color_hint='ffa726',
    ),
    CategoryDescription(
        code='payment_institution',
        label_ru='Платёжный институт',
        short_description='Платёжный сервис, обменник, эквайер, агрегатор.',
        color_hint='ab47bc',
    ),
]

BEHAVIORAL_ROLES: list[CategoryDescription] = [
    CategoryDescription(
        code='regular',
        label_ru='Обычный',
        short_description='Поведение в графе не выделяется по структурным метрикам.',
        color_hint='6b7280',
    ),
    CategoryDescription(
        code='hub',
        label_ru='Концентратор',
        short_description=(
            'Узел с очень высокой степенью связности (top 5%). '
            'Через него проходит существенная часть транзакций.'
        ),
        color_hint='ff453a',
    ),
    CategoryDescription(
        code='transit',
        label_ru='Транзитный',
        short_description=(
            'Высокий betweenness centrality (top 10%) при сбалансированных '
            'входящих и исходящих потоках. Типичная роль в схемах layering.'
        ),
        color_hint='ff9f0a',
    ),
    CategoryDescription(
        code='isolated',
        label_ru='Одиночный',
        short_description='Минимальная связность — 1-2 транзакции за период.',
        color_hint='9ca3af',
    ),
]


@router.get('/entity-types')
async def list_entity_types() -> list[CategoryDescription]:
    """Список онтологических типов сущностей с описаниями."""
    return ENTITY_TYPES


@router.get('/behavioral-roles')
async def list_behavioral_roles() -> list[CategoryDescription]:
    """Список поведенческих ролей с описаниями и правилами классификации."""
    return BEHAVIORAL_ROLES
