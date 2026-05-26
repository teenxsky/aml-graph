from taskiq_pipelines import Pipeline

from src.infrastructure.task_processing.broker import rabbitmq_broker
from src.tasks import (
    build_graph_task,
    cluster_graph_task,
    detect_patterns_task,
    hierarchical_layout_task,
    save_graph_task,
    score_and_layout_task,
    select_strategy_task,
)


class ProcessIbmGraphPipelineUseCase:
    """Запускает пайплайн обработки графа расследования.

    Этапы пайплайна:

    1. Построение графа из CSV
    2. Выбор стратегии обработки (метод кластеризации, веса скоринга)
    3. Детектирование подозрительных паттернов
    4. Расчёт риск-скоринга и базовый layout
    5. Кластеризация (AGC или Louvain - выбирается автоматически на шаге 2)
    6. Иерархический layout на основе кластеров
    7. Сохранение итогового графа

    Метод кластеризации и скоринговые веса определяются в select_strategy_task
    на основе характеристик графа. Пользователь не выбирает алгоритмы.
    """

    @staticmethod
    async def execute(job_id: str) -> None:
        """Поставить пайплайн обработки графа в очередь задач.

        :param job_id: Идентификатор задачи обработки графа.
        """
        pipeline: Pipeline = (
            Pipeline(rabbitmq_broker, build_graph_task)
            .call_next(select_strategy_task)
            .call_next(detect_patterns_task)
            .call_next(score_and_layout_task)
            .call_next(cluster_graph_task)
            .call_next(hierarchical_layout_task)
            .call_next(save_graph_task)
        )

        await pipeline.kiq(job_id)
