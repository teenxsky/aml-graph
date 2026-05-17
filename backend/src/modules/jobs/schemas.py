from datetime import datetime

from pydantic import BaseModel

__all__ = [
    'JobInfo',
]

from src.modules.jobs.enums import JobStatus


class JobInfo(BaseModel):
    """Информация о задаче обработки датасета."""

    job_id: str
    status: JobStatus
    created_at: datetime
