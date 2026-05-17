from src.di.container import create_container
from src.infrastructure.task_queue.broker import rabbitmq_broker
from src.infrastructure.task_queue.setup import setup_taskiq
from src.tasks import *  # noqa: F401, F403

broker = rabbitmq_broker
container = create_container()

setup_taskiq(taskiq_broker=broker, container=container)
