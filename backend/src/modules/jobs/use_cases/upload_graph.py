import contextlib
import uuid

from src.infrastructure.storage.csv_store import CsvStore
from src.modules.jobs.enums import UploadFormat
from src.modules.jobs.models import JobModel
from src.modules.jobs.repositories.job import JobRepository
from src.shared.schemas import ColumnMapping

__all__ = ['UploadGraphUseCase']


class UploadGraphUseCase:
    """Сохраняет загруженный файл и создаёт запись Job в БД."""

    def __init__(self, job_repository: JobRepository, csv_store: CsvStore) -> None:
        self._job_repository = job_repository
        self._csv_store = csv_store

    async def execute(
        self,
        file_bytes: bytes,
        user_ip: str,
        column_mapping: ColumnMapping | None = None,
    ) -> JobModel | None:
        """Сохраняет файл и создаёт Job в БД."""
        with contextlib.suppress(Exception):
            job_id = str(uuid.uuid4())
            file_path = self._csv_store.save(job_id, file_bytes)

            column_mapping_json = None
            data_format = UploadFormat.IBM

            if column_mapping:
                column_mapping_json = column_mapping.model_dump(exclude_none=True)
                data_format = UploadFormat.CUSTOM

            await self._job_repository.create_job(
                job_id=job_id,
                user_ip=user_ip,
                file_path=file_path,
                format=data_format,
                column_mapping=column_mapping_json,
            )

            return await self._job_repository.get_job(job_id)

        return None
