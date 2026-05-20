import logging

from dishka.integrations.taskiq import FromDishka, inject

from src.infrastructure.storage.graph_artifacts import GraphArtifactStore
from src.infrastructure.task_queue.broker import rabbitmq_broker
from src.modules.graph.analytics.scoring import apply_alert_scores
from src.modules.graph.services.layout import compute_graph_layout
from src.modules.jobs.enums import JobStatus
from src.modules.jobs.repositories.job import JobRepository

__all__ = ['score_and_layout_task']

logger = logging.getLogger(__name__)


@rabbitmq_broker.task
@inject
async def score_and_layout_task(
    job_id: str,
    job_repository: FromDishka[JobRepository],
    graph_artifact_store: FromDishka[GraphArtifactStore],
) -> str:
    """Вычисляет risk-score узлов/рёбер и раскладку (layout) графа."""
    try:
        await job_repository.update_status(job_id, JobStatus.SCORING)

        data = graph_artifact_store.load(job_id)
        graph = data['graph']

        scores, edge_scores = apply_alert_scores(graph, data['alerts'])
        data['scores'] = scores
        data['edge_scores'] = edge_scores

        await job_repository.update_status(job_id, JobStatus.LAYOUT)

        data['layout'] = compute_graph_layout(graph)
        graph_artifact_store.save(job_id, data)
        return job_id

    except Exception as e:
        logger.exception('score_and_layout_task failed for job %s', job_id)
        await job_repository.update_status(
            job_id,
            JobStatus.FAILED,
            error_msg=str(e),
        )
        raise
