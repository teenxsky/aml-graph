import pickle
from typing import Any

import redis.asyncio as aioredis

__all__ = ['RedisArtifactStore']

_KEY_PREFIX = 'artifact:'
_DEFAULT_TTL = 3600


class RedisArtifactStore:
    """Хранит промежуточные артефакты обработки графов в Redis между этапами пайплайна."""

    def __init__(self, redis_url: str, ttl: int = _DEFAULT_TTL) -> None:
        self._client: aioredis.Redis = aioredis.from_url(redis_url)
        self._ttl = ttl

    @staticmethod
    def _build_key(job_id: str) -> str:
        return f'{_KEY_PREFIX}{job_id}'

    async def save(self, job_id: str, data: dict[str, Any]) -> None:
        """Сохраняет артефакты задачи."""
        await self._client.set(self._build_key(job_id), pickle.dumps(data), ex=self._ttl)

    async def load(self, job_id: str) -> dict[str, Any]:
        """Загружает артефакты задачи."""
        raw = await self._client.get(self._build_key(job_id))

        if raw is None:
            raise KeyError(f'No artifacts for job {job_id}')

        return pickle.loads(raw)  # noqa: S301

    async def delete(self, job_id: str) -> None:
        """Удаляет артефакт задачи."""
        await self._client.delete(self._build_key(job_id))
