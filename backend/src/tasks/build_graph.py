import logging
import traceback

from dishka.integrations.taskiq import FromDishka, inject

from src.infrastructure.storage.csv_store import CsvStore
from src.infrastructure.storage.graph_artifacts import GraphArtifactStore
from src.infrastructure.task_queue.broker import rabbitmq_broker
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
    graph_artifact_store: FromDishka[GraphArtifactStore],
) -> str:
    """Парсит CSV и строит NetworkX-граф; результат сохраняет в artifact store."""
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

        graph_artifact_store.save(job_id, {'graph': graph})
        return job_id

    except Exception:
        logger.exception('build_graph_task failed for job %s', job_id)

        await job_repository.update_status(
            job_id,
            JobStatus.FAILED,
            error_msg=traceback.format_exc(limit=10),
        )

        raise
