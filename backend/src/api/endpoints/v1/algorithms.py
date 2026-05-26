from http import HTTPStatus

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter()


class AlgorithmDescription(BaseModel):
    """Описание одного алгоритма для отображения пользователю."""

    id: str
    name: str
    short_description: str
    detailed_description: str
    reference: str | None
    complexity: str | None
    use_case: str


ALGORITHM_DESCRIPTIONS: dict[str, AlgorithmDescription] = {
    'agc': AlgorithmDescription(
        id='agc',
        name='Adaptive Graph Convolution',
        short_description=(
            'Спектральный метод кластеризации без обучения, '
            'использующий признаки узлов и структуру графа.'
        ),
        detailed_description=(
            'AGC применяет итеративный low-pass фильтр на основе '
            'нормализованного лапласиана графа к матрице признаков узлов. '
            'Это сглаживает признаки по структуре графа: узлы одного '
            'кластера становятся похожими по признакам, что упрощает '
            'последующую спектральную кластеризацию. Ключевая особенность - '
            'адаптивный выбор порядка фильтра k: алгоритм сам останавливается '
            'в точке первого локального минимума внутрикластерного '
            'расстояния, предотвращая over-smoothing.'
        ),
        reference='Zhang et al., IJCAI 2019 (arXiv:1906.01210)',
        complexity='O(n² · d)',
        use_case=(
            'Применяется для графов до 1500 узлов когда доступны признаки '
            'узлов (агрегаты транзакций, временные паттерны).'
        ),
    ),
    'louvain': AlgorithmDescription(
        id='louvain',
        name='Алгоритм Лувена',
        short_description=(
            'Структурная кластеризация на основе оптимизации модулярности. '
            'Работает только со связями графа, без признаков узлов.'
        ),
        detailed_description=(
            'Метод последовательно объединяет узлы в сообщества так, '
            'чтобы максимизировать модулярность - меру того, насколько '
            'плотно узлы сообщества связаны между собой по сравнению '
            'с тем, что ожидалось бы в случайном графе. Работает '
            'итеративно и масштабируется на большие графы.'
        ),
        reference='Blondel et al., 2008',
        complexity='O(n log n)',
        use_case=(
            'Применяется для графов больше 1500 узлов или когда '
            'признаки узлов недоступны / неинформативны.'
        ),
    ),
    'betweenness': AlgorithmDescription(
        id='betweenness',
        name='Betweenness Centrality',
        short_description=(
            'Мера того, насколько часто узел лежит на кратчайших '
            'путях между другими парами узлов.'
        ),
        detailed_description=(
            'Узел с высоким betweenness - это "транзитный" узел, '
            'через который проходит значительная часть потоков в сети. '
            'В контексте AML такие узлы часто служат точками отмывания '
            '(layering), где средства проходят несколько раз меняя '
            'юрисдикцию или формат. На графах больше 500 узлов '
            'используется приближённое вычисление с k=200 случайных '
            'источников.'
        ),
        reference='Brandes, 2001 (точный); Brandes & Pich, 2007 (sampling)',
        complexity='O(n · m) точно, O(k · m) с sampling',
        use_case='Один из четырёх компонентов формулы риск-скоринга узла.',
    ),
    'pagerank': AlgorithmDescription(
        id='pagerank',
        name='PageRank',
        short_description=(
            'Мера важности узла в графе, учитывающая важность узлов, '
            'которые на него ссылаются.'
        ),
        detailed_description=(
            'PageRank итеративно рассчитывает вероятность того, что '
            'случайный обход графа окажется в данном узле. В контексте '
            'AML узлы с высоким PageRank - это получатели крупных '
            'потоков от других важных узлов, что может указывать на '
            'роль конечного бенефициара схемы. Для транзакционных '
            'графов используется взвешенный вариант (веса = суммы '
            'транзакций).'
        ),
        reference='Page & Brin, 1998',
        complexity='O(k · m), k ~ 50-100 итераций',
        use_case='Один из четырёх компонентов формулы риск-скоринга узла.',
    ),
    'risk_scoring': AlgorithmDescription(
        id='risk_scoring',
        name='Композитный риск-скоринг',
        short_description=(
            'Итоговая оценка риска узла как комбинация четырёх компонентов '
            'с весами, адаптированными к размеру графа.'
        ),
        detailed_description=(
            'Риск-скор каждого узла вычисляется по формуле '
            '1 − ∏(1 − w_i · score_i), где компоненты: срабатывания '
            'AML-детекторов (cycles, fanout, transit, shared_device), '
            'betweenness centrality, PageRank, дисбаланс потоков '
            '|in − out| / (in + out). Веса w_i подбираются автоматически: '
            'на малых графах детекторы преобладают, на больших - '
            'структурные центральности.'
        ),
        reference=None,
        complexity='O(n · m) на расчёт компонентов',
        use_case='Финальный шаг агрегации сигналов в единую оценку.',
    ),
    'hierarchical_layout': AlgorithmDescription(
        id='hierarchical_layout',
        name='Иерархическая укладка',
        short_description=(
            'Трёхуровневое размещение узлов: семантические группы → '
            'кластеры → отдельные узлы.'
        ),
        detailed_description=(
            'Первый уровень группирует узлы по типу сущности '
            '(клиенты, счета, юрлица, устройства). Второй уровень - '
            'AGC/Louvain подкластеры внутри каждого типа. Третий - '
            'позиционирование узлов внутри подкластера через '
            'spring_layout. Координаты нормализуются в [-1, 1] '
            'и масштабируются на frontend под размер canvas.'
        ),
        reference='Fruchterman-Reingold, 1991 (spring_layout)',
        complexity='O(iterations · m) на каждом уровне',
        use_case='Применяется всегда; цель - снижение visual clutter.',
    ),
}


@router.get('/algorithms')
async def list_algorithms() -> list[AlgorithmDescription]:
    """Получить список описаний всех алгоритмов используемых в системе."""
    return list(ALGORITHM_DESCRIPTIONS.values())


@router.get('/algorithms/{algorithm_id}')
async def get_algorithm(algorithm_id: str) -> AlgorithmDescription:
    """Получить описание конкретного алгоритма по его id."""
    if algorithm_id not in ALGORITHM_DESCRIPTIONS:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail=f'Алгоритм {algorithm_id} неизвестен',
        )
    return ALGORITHM_DESCRIPTIONS[algorithm_id]
