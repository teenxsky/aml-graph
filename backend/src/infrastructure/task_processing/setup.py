from dishka import AsyncContainer
from dishka.integrations.taskiq import setup_dishka
from taskiq import AsyncBroker

__all__ = ['setup_taskiq']


def setup_taskiq(taskiq_broker: AsyncBroker, container: AsyncContainer) -> None:
    """Подключает Dishka DI-контейнер к Taskiq-брокеру."""
    setup_dishka(
        broker=taskiq_broker,
        container=container,
    )
