import logging
from datetime import datetime, timezone

from dishka.integrations.taskiq import FromDishka, inject

from src.infrastructure.storage.graph_artifacts import GraphArtifactStore
from src.infrastructure.task_queue.broker import rabbitmq_broker
from src.modules.graph.analytics.adaptive_strategy import select_strategy
from src.modules.jobs.enums import JobStatus
from src.modules.jobs.repositories.job import JobRepository

__all__ = ['select_strategy_task']

logger = logging.getLogger(__name__)


@rabbitmq_broker.task
@inject
async def select_strategy_task(
    job_id: str,
    job_repository: FromDishka[JobRepository],
    graph_artifact_store: FromDishka[GraphArtifactStore],
) -> str:
    """Выбрать стратегию обработки графа и сохранить в artifact store.

    Запускается между build_graph и detect_patterns. Результат используется
    cluster_graph_task и score_and_layout_task. Инициализирует список step_timings.
    """
    started = datetime.now(timezone.utc)
    try:
        data = graph_artifact_store.load(job_id)
        graph = data['graph']

        strategy = select_strategy(graph)

        finished = datetime.now(timezone.utc)
        duration_ms = int((finished - started).total_seconds() * 1000)

        step_timings: list[dict] = data.get('step_timings', [])
        step_timings.append({
            'step': 'select_strategy',
            'duration_ms': duration_ms,
            'started_at': started.isoformat(),
            'finished_at': finished.isoformat(),
        })

        data['analysis_strategy'] = {
            'clustering_method': strategy.clustering_method,
            'clustering_reason': strategy.clustering_reason,
            'scoring_weights': {
                'detector_alerts': strategy.scoring_weights.detector_alerts,
                'betweenness': strategy.scoring_weights.betweenness,
                'pagerank': strategy.scoring_weights.pagerank,
                'flow_imbalance': strategy.scoring_weights.flow_imbalance,
            },
            'scoring_reason': strategy.scoring_reason,
            'betweenness_exact': strategy.betweenness_exact,
            'betweenness_k': strategy.betweenness_k,
        }
        data['step_timings'] = step_timings
        graph_artifact_store.save(job_id, data)

        logger.info(
            'select_strategy_task завершён для job %s: метод=%s, n=%d',
            job_id,
            strategy.clustering_method,
            graph.number_of_nodes(),
        )
        return job_id

    except Exception as e:
        logger.exception('select_strategy_task failed for job %s', job_id)
        await job_repository.update_status(
            job_id,
            JobStatus.FAILED,
            error_msg=str(e),
        )
        raise
