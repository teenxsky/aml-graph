import logging
from datetime import UTC, datetime

from dishka.integrations.taskiq import FromDishka, inject

from src.infrastructure.storage.csv_store import CsvStore
from src.infrastructure.storage.redis_artifacts import RedisArtifactStore
from src.infrastructure.task_processing.broker import rabbitmq_broker
from src.modules.graph.parsing.ibm import read_ibm_transactions
from src.modules.graph.services.builder import GraphBuilder
from src.modules.jobs.enums import JobStatus, UploadFormat
from src.modules.jobs.repositories.job import JobRepository
from src.shared.schemas import ColumnMapping

__all__ = ['build_graph_task']

logger = logging.getLogger(__name__)


@rabbitmq_broker.task
@inject
async def build_graph_task(
    job_id: str,
    job_repository: FromDishka[JobRepository],
    csv_store: FromDishka[CsvStore],
    graph_builder: FromDishka[GraphBuilder],
    redis_artifact_store: FromDishka[RedisArtifactStore],
) -> str:
    """Парсит CSV и строит NetworkX-граф; результат сохраняет в Redis artifact store."""
    started = datetime.now(UTC)
    try:
        await job_repository.update_status(job_id, JobStatus.GRAPH_BUILDING)

        job = await job_repository.get_job(job_id)

        if job is None or job.file_path is None:
            raise ValueError(f'Job {job_id} not found')

        file_bytes = csv_store.load(job.file_path)

        if job.format == UploadFormat.IBM:
            normalized = read_ibm_transactions(file_bytes)
            graph = graph_builder.build_from_normalized_transactions(normalized)
        else:
            mapping = ColumnMapping.model_validate(job.column_mapping)
            graph = graph_builder.build_from_csv(file_bytes, mapping)

        finished = datetime.now(UTC)
        duration_ms = int((finished - started).total_seconds() * 1000)

        await redis_artifact_store.save(
            job_id,
            {
                'graph': graph,
                'step_timings': [
                    {
                        'step': 'build_graph',
                        'duration_ms': duration_ms,
                        'started_at': started.isoformat(),
                        'finished_at': finished.isoformat(),
                    },
                ],
            },
        )
        return job_id

    except Exception as e:
        logger.exception('build_graph_task failed for job %s', job_id)

        await job_repository.update_status(
            job_id,
            JobStatus.FAILED,
            error_msg=str(e),
        )

        raise
