import logging
from datetime import datetime, timezone

from dishka.integrations.taskiq import FromDishka, inject

from src.infrastructure.storage.graph_artifacts import GraphArtifactStore
from src.infrastructure.task_queue.broker import rabbitmq_broker
from src.modules.graph.analytics.detectors import (
    detect_cycles,
    detect_fanout,
    detect_shared_device,
    detect_transit,
)
from src.modules.graph.analytics.scoring import flatten_alerts
from src.modules.jobs.enums import JobStatus
from src.modules.jobs.repositories.job import JobRepository

__all__ = ['detect_patterns_task']

logger = logging.getLogger(__name__)


@rabbitmq_broker.task
@inject
async def detect_patterns_task(
    job_id: str,
    job_repository: FromDishka[JobRepository],
    graph_artifact_store: FromDishka[GraphArtifactStore],
) -> str:
    """Запускает детекторы AML-паттернов (циклы, fanout, транзит, общие устройства)."""
    started = datetime.now(timezone.utc)
    try:
        await job_repository.update_status(job_id, JobStatus.DETECTING)

        data = graph_artifact_store.load(job_id)
        graph = data['graph']

        cycles = detect_cycles(graph)
        fanout = detect_fanout(graph)
        transit = detect_transit(graph)
        shared_device = detect_shared_device(graph)

        finished = datetime.now(timezone.utc)
        duration_ms = int((finished - started).total_seconds() * 1000)

        data['detector_results'] = {
            'cycles': cycles,
            'fanout': fanout,
            'transit': transit,
            'shared_device': shared_device,
        }
        data['alerts'] = flatten_alerts(cycles, fanout, transit, shared_device)

        step_timings: list[dict] = data.get('step_timings', [])
        step_timings.append({
            'step': 'detect_patterns',
            'duration_ms': duration_ms,
            'started_at': started.isoformat(),
            'finished_at': finished.isoformat(),
        })
        data['step_timings'] = step_timings

        graph_artifact_store.save(job_id, data)
        return job_id

    except Exception as e:
        logger.exception('detect_patterns_task failed for job %s', job_id)
        await job_repository.update_status(
            job_id,
            JobStatus.FAILED,
            error_msg=str(e),
        )
        raise
