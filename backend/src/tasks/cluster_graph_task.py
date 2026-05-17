import logging
import traceback
from typing import Literal

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
    method: Literal['agc', 'louvain'] = 'agc',
    n_clusters: int | None = None,
) -> str:
    """Кластеризовать граф и сохранить ClusteringResult в artifact store.

    Выполняется после score_and_layout_task. Результат используется
    hierarchical_layout_task.

    :param job_id: Идентификатор задачи.
    :param method: Метод кластеризации.
    :param n_clusters: Желаемое число кластеров (None — автодетект через eigengap).
    """
    try:
        await job_repository.update_status(job_id, JobStatus.CLUSTERING)

        data = graph_artifact_store.load(job_id)
        graph = data['graph']

        clustering_result = cluster_graph(
            graph,
            method=method,
            n_clusters=n_clusters,
            max_k=settings.clustering.agc_max_k,
            random_state=settings.clustering.random_state,
        )

        data['clustering_result'] = clustering_result
        graph_artifact_store.save(job_id, data)

        logger.info(
            'cluster_graph_task завершён для job %s: метод=%s, кластеров=%d',
            job_id,
            method,
            clustering_result.n_clusters,
        )
        return job_id

    except Exception:
        logger.exception('cluster_graph_task failed for job %s', job_id)
        await job_repository.update_status(
            job_id,
            JobStatus.FAILED,
            error_msg=traceback.format_exc(limit=10),
        )
        raise
