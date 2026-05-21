import logging
from datetime import datetime, timezone

from dishka.integrations.taskiq import FromDishka, inject

from src.infrastructure.storage.graph_artifacts import GraphArtifactStore
from src.infrastructure.task_queue.broker import rabbitmq_broker
from src.modules.graph.analytics.clustering import cluster_graph
from src.modules.jobs.enums import JobStatus
from src.modules.jobs.repositories.job import JobRepository
from src.settings import settings

__all__ = ['cluster_graph_task']

logger = logging.getLogger(__name__)


@rabbitmq_broker.task
@inject
async def cluster_graph_task(
    job_id: str,
    job_repository: FromDishka[JobRepository],
    graph_artifact_store: FromDishka[GraphArtifactStore],
) -> str:
    """Кластеризовать граф методом из analysis_strategy и сохранить результат.

    Выполняется после score_and_layout_task. Метод кластеризации определяется
    автоматически в select_strategy_task. Результат используется hierarchical_layout_task.
    """
    started = datetime.now(timezone.utc)
    try:
        await job_repository.update_status(job_id, JobStatus.CLUSTERING)

        data = graph_artifact_store.load(job_id)
        graph = data['graph']

        strategy = data.get('analysis_strategy', {})
        method = strategy.get('clustering_method', 'agc')

        clustering_result = cluster_graph(
            graph,
            method=method,
            max_k=settings.clustering.agc_max_k,
            random_state=settings.clustering.random_state,
        )

        finished = datetime.now(timezone.utc)
        duration_ms = int((finished - started).total_seconds() * 1000)

        data['clustering_result'] = clustering_result

        step_timings: list[dict] = data.get('step_timings', [])
        step_timings.append({
            'step': 'cluster_graph',
            'duration_ms': duration_ms,
            'started_at': started.isoformat(),
            'finished_at': finished.isoformat(),
        })
        data['step_timings'] = step_timings

        graph_artifact_store.save(job_id, data)

        logger.info(
            'cluster_graph_task завершён для job %s: метод=%s, кластеров=%d',
            job_id,
            method,
            clustering_result.n_clusters,
        )
        return job_id

    except Exception as e:
        logger.exception('cluster_graph_task failed for job %s', job_id)
        await job_repository.update_status(
            job_id,
            JobStatus.FAILED,
            error_msg=str(e),
        )
        raise
