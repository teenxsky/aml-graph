from taskiq_pipelines import Pipeline

from src.infrastructure.task_queue.broker import rabbitmq_broker
from src.modules.graph.types import ClusteringMethod
from src.tasks import (
    build_graph_task,
    cluster_graph_task,
    detect_patterns_task,
    hierarchical_layout_task,
    save_graph_task,
    score_and_layout_task,
)


class ProcessIbmGraphPipelineUseCase:
    """Запускает пайплайн обработки графа расследования.

    Этапы пайплайна при кластеризации (по умолчанию):

    1. Построение графа
    2. Детектирование подозрительных паттернов
    3. Расчёт риск-скоринга и базовый layout
    4. Кластеризация (AGC или Louvain)
    5. Иерархический layout на основе кластеров
    6. Сохранение итогового графа

    Этапы при ``clustering=None`` (обратная совместимость):

    1. Построение графа
    2. Детектирование подозрительных паттернов
    3. Расчёт риск-скоринга и spring/ForceAtlas2 layout
    4. Сохранение итогового графа
    """

    @staticmethod
    async def execute(
        job_id: str,
        clustering: ClusteringMethod | None = 'agc',
    ) -> None:
        """Поставить пайплайн обработки графа в очередь задач.

        :param job_id: Идентификатор задачи обработки графа.
        :param clustering: Метод кластеризации. ``None`` отключает новые шаги
                           и возвращает к плоскому ForceAtlas2/spring layout.
        """
        if clustering is None:
            pipeline: Pipeline = (
                Pipeline(rabbitmq_broker, build_graph_task)
                .call_next(detect_patterns_task)
                .call_next(score_and_layout_task)
                .call_next(save_graph_task)
            )
        else:
            pipeline: Pipeline = (
                Pipeline(rabbitmq_broker, build_graph_task)
                .call_next(detect_patterns_task)
                .call_next(score_and_layout_task)
                .call_next(cluster_graph_task, method=clustering)
                .call_next(hierarchical_layout_task)
                .call_next(save_graph_task)
            )

        await pipeline.kiq(job_id)
