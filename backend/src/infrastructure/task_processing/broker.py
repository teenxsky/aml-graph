from taskiq import AsyncBroker
from taskiq_aio_pika import AioPikaBroker
from taskiq_pipelines.middleware import PipelineMiddleware
from taskiq_redis import RedisAsyncResultBackend

from src.settings import settings

__all__ = ['rabbitmq_broker']


rabbitmq_broker: AsyncBroker = AioPikaBroker(
    url=f'{settings.rabbitmq.dsn}',
).with_result_backend(
    RedisAsyncResultBackend(
        redis_url=str(settings.redis.dsn),
    ),
)

rabbitmq_broker.add_middlewares(PipelineMiddleware())
