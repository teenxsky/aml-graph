from typing import Any

from sqlalchemy import func, select, update

from src.infrastructure.database.postgres.repository import BaseRepository
from src.modules.jobs.enums import JobStatus, UploadFormat
from src.modules.jobs.models import JobModel

__all__ = ['JobRepository']


class JobRepository(BaseRepository[JobModel]):
    """Репозиторий задач обработки графа поверх SQLAlchemy ORM."""

    model = JobModel

    async def create_job(
        self,
        *,
        job_id: str,
        user_ip: str,
        file_path: str,
        format: UploadFormat,
        column_mapping: dict[str, Any] | None = None,
    ) -> None:
        """Создаёт запись задачи со статусом PENDING."""
        job = JobModel(
            id=job_id,
            status=JobStatus.PENDING,
            format=format,
            user_ip=user_ip,
            file_path=file_path,
            column_mapping=column_mapping,
        )
        await self.save(job)
        await self._session.commit()

    async def update_status(
        self,
        job_id: str,
        status: JobStatus,
        *,
        ladybug_ref: str | None = None,
        detector_results: dict[str, Any] | None = None,
        error_msg: str | None = None,
    ) -> None:
        """Обновляет статус задачи; коммитит сразу, чтобы SSE-стрим видел изменения."""
        values: dict[str, Any] = {'status': status}
        if ladybug_ref is not None:
            values['ladybug_ref'] = ladybug_ref
        if detector_results is not None:
            values['detector_results'] = detector_results
        if error_msg is not None:
            values['error_msg'] = error_msg

        await self._session.execute(
            update(JobModel).where(JobModel.id == job_id).values(**values),
        )

        await self._session.commit()

    async def get_job(self, job_id: str) -> JobModel | None:
        """Возвращает задачу по ID или None, если не найдена."""
        query = select(JobModel).where(JobModel.id == job_id)
        result = await self._session.execute(query)
        return result.scalar_one_or_none()

    async def get_latest_jobs_by_user_ip(
        self,
        user_ip: str,
        limit: int = 10,
        offset: int = 0,
    ) -> tuple[list[JobModel], int]:
        """Возвращает последние задачи пользователя и общее количество."""

        stmt = (
            select(JobModel)
            .where(JobModel.user_ip == user_ip)
            .order_by(JobModel.created_at.desc())
            .limit(limit)
            .offset(offset)
        )

        count_stmt = select(func.count()).select_from(JobModel).where(JobModel.user_ip == user_ip)

        result = await self._session.execute(stmt)
        count_result = await self._session.execute(count_stmt)

        jobs = list(result.scalars().all())
        total = count_result.scalar_one()

        return jobs, total
