from datetime import datetime

from pydantic import BaseModel

__all__ = [
    'JobCreated',
    'JobInfo',
]

from src.modules.jobs.enums import JobStatus, UploadFormat


class JobCreated(BaseModel):
    """Информация о постановке задачи в очередь на обработку данных."""

    job_id: str
    status: JobStatus
    created_at: datetime


class JobInfo(BaseModel):
    """Информация задаче на обработку данных."""

    id: str
    status: JobStatus
    format: UploadFormat
    user_ip: str
    file_path: str | None
    column_mapping: dict | None
    ladybug_ref: str | None
    detector_results: dict | None
    error_msg: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {'from_attributes': True}
