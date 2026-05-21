import logging
from datetime import datetime, timezone

import networkx as nx
from dishka.integrations.taskiq import FromDishka, inject

from src.infrastructure.storage.graph_artifacts import GraphArtifactStore
from src.infrastructure.task_queue.broker import rabbitmq_broker
from src.modules.graph.analytics.behavioral_classifier import classify_behavioral_roles
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
    score_started = datetime.now(timezone.utc)
    try:
        await job_repository.update_status(job_id, JobStatus.SCORING)

        data = graph_artifact_store.load(job_id)
        graph = data['graph']

        scores, edge_scores = apply_alert_scores(graph, data['alerts'])
        data['scores'] = scores
        data['edge_scores'] = edge_scores

        # Betweenness centrality для behavioral classification
        strategy = data.get('analysis_strategy', {})
        betweenness_exact = strategy.get('betweenness_exact', True)
        betweenness_k = strategy.get('betweenness_k', 0)
        n_nodes = graph.number_of_nodes()
        if betweenness_exact or n_nodes == 0:
            betweenness = nx.betweenness_centrality(graph, normalized=True)
        else:
            k = min(betweenness_k or 200, n_nodes)
            betweenness = nx.betweenness_centrality(graph, normalized=True, k=k)

        roles = classify_behavioral_roles(graph, betweenness_scores=betweenness)
        for node_id, role in roles.items():
            graph.nodes[node_id]['behavioral_role'] = role

        score_finished = datetime.now(timezone.utc)

        await job_repository.update_status(job_id, JobStatus.LAYOUT)

        layout_started = datetime.now(timezone.utc)
        data['layout'] = compute_graph_layout(graph)
        layout_finished = datetime.now(timezone.utc)

        step_timings: list[dict] = data.get('step_timings', [])
        step_timings.append({
            'step': 'score',
            'duration_ms': int((score_finished - score_started).total_seconds() * 1000),
            'started_at': score_started.isoformat(),
            'finished_at': score_finished.isoformat(),
        })
        step_timings.append({
            'step': 'layout',
            'duration_ms': int((layout_finished - layout_started).total_seconds() * 1000),
            'started_at': layout_started.isoformat(),
            'finished_at': layout_finished.isoformat(),
        })
        data['step_timings'] = step_timings

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
