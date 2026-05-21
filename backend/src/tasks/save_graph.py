import logging
import math
from datetime import datetime, timezone
from typing import Any

from dishka.integrations.taskiq import FromDishka, inject

from src.infrastructure.storage.graph_artifacts import GraphArtifactStore
from src.infrastructure.task_queue.broker import rabbitmq_broker
from src.modules.graph.repositories.graph import GraphStoreRepository
from src.modules.jobs.enums import JobStatus
from src.modules.jobs.repositories.job import JobRepository

__all__ = ['save_graph_task']

logger = logging.getLogger(__name__)


@rabbitmq_broker.task
@inject
async def save_graph_task(
    job_id: str,
    job_repository: FromDishka[JobRepository],
    graph_store_repository: FromDishka[GraphStoreRepository],
    graph_artifact_store: FromDishka[GraphArtifactStore],
) -> str:
    """Сохраняет граф в LadybugDB, обновляет статус задачи на COMPLETED и удаляет артефакты."""
    started = datetime.now(timezone.utc)
    try:
        await job_repository.update_status(job_id, JobStatus.SAVING)

        data = graph_artifact_store.load(job_id)
        db_file = graph_store_repository.save_graph(
            job_id,
            data['graph'],
            data['layout'],
            data['scores'],
            data['edge_scores'],
        )

        finished = datetime.now(timezone.utc)
        duration_ms = int((finished - started).total_seconds() * 1000)

        step_timings: list[dict] = data.get('step_timings', [])
        step_timings.append({
            'step': 'save',
            'duration_ms': duration_ms,
            'started_at': started.isoformat(),
            'finished_at': finished.isoformat(),
        })

        detector_results = {k: _sanitize(v) for k, v in data['detector_results'].items()}

        if 'analysis_result' in data:
            detector_results['__analysis__'] = data['analysis_result']

        if step_timings:
            detector_results['__step_timings__'] = step_timings

        if 'analysis_strategy' in data:
            detector_results['__analysis_strategy__'] = data['analysis_strategy']

        await job_repository.update_status(
            job_id,
            JobStatus.COMPLETED,
            ladybug_ref=db_file,
            detector_results=detector_results,
        )
        graph_artifact_store.delete(job_id)
        return job_id

    except Exception as e:
        logger.exception('save_graph_task failed for job %s', job_id)
        await job_repository.update_status(
            job_id,
            JobStatus.FAILED,
            error_msg=str(e),
        )
        raise


def _sanitize(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    result = []
    for item in items:
        clean: dict[str, Any] = {}
        for k, v in item.items():
            if isinstance(v, float) and math.isinf(v):
                clean[k] = None
            elif isinstance(v, set):
                clean[k] = list(v)
            else:
                clean[k] = v
        result.append(clean)
    return result
