from datetime import datetime

from sqlalchemy import DateTime, String, Text, text
from sqlalchemy.dialects.postgresql import ENUM, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from src.infrastructure.database.postgres.types import BaseDatabaseModel
from src.modules.jobs.enums import JobStatus, UploadFormat

__all__ = [
    'JobModel',
    'PGSQL_JOB_STATUS_ENUM',
    'PGSQL_UPLOAD_FORMAT_ENUM',
]


PGSQL_JOB_STATUS_ENUM = ENUM(
    JobStatus,
    name='job_status',
    create_type=False,
)

PGSQL_UPLOAD_FORMAT_ENUM = ENUM(
    UploadFormat,
    name='upload_format',
    create_type=False,
)


class JobModel(BaseDatabaseModel):
    """ORM-модель задачи обработки графа."""

    __tablename__ = 'jobs'

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        primary_key=True,
        server_default=text('gen_random_uuid()'),
    )

    status: Mapped[JobStatus] = mapped_column(
        PGSQL_JOB_STATUS_ENUM,
        nullable=False,
        default=JobStatus.PENDING,
        server_default=JobStatus.PENDING,
    )

    format: Mapped[UploadFormat] = mapped_column(
        PGSQL_UPLOAD_FORMAT_ENUM,
        nullable=False,
        default=UploadFormat.IBM,
        server_default=UploadFormat.IBM,
    )

    user_ip: Mapped[str] = mapped_column(String(45), nullable=False)

    file_path: Mapped[str | None] = mapped_column(Text, nullable=True)

    column_mapping: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    ladybug_ref: Mapped[str | None] = mapped_column(Text, nullable=True)

    detector_results: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    error_msg: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
