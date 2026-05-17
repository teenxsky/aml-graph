from taskiq_pipelines import Pipeline

from src.infrastructure.task_queue.broker import rabbitmq_broker
from src.tasks import (
    build_graph_task,
    detect_patterns_task,
    save_graph_task,
    score_and_layout_task,
)


class ProcessIbmGraphPipelineUseCase:
    """
    Запускает пайплайн обработки графа расследования.

    Этапы пайплайна:
    1. Построение графа
    2. Детектирование подозрительных паттернов
    3. Расчёт риск-скоринга и layout-координат
    4. Сохранение итогового графа
    """

    @staticmethod
    async def execute(job_id: str) -> None:
        """
        Ставит пайплайн обработки графа в очередь задач.

        :param job_id: Идентификатор задачи обработки графа
        """
        pipeline: Pipeline = (
            Pipeline(rabbitmq_broker, build_graph_task)
            .call_next(detect_patterns_task)
            .call_next(score_and_layout_task)
            .call_next(save_graph_task)
        )

        await pipeline.kiq(job_id)
