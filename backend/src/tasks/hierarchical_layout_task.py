import logging
import traceback

import networkx as nx
from dishka.integrations.taskiq import FromDishka, inject

from src.infrastructure.storage.graph_artifacts import GraphArtifactStore
from src.infrastructure.task_queue.broker import rabbitmq_broker
from src.modules.graph.analytics.clustering import ClusteringResult
from src.modules.graph.services.hierarchical_layout import compute_hierarchical_layout
from src.modules.jobs.enums import JobStatus
from src.modules.jobs.repositories.job import JobRepository
from src.settings import settings

__all__ = ['hierarchical_layout_task']

logger = logging.getLogger(__name__)


@rabbitmq_broker.task
@inject
async def hierarchical_layout_task(
    job_id: str,
    job_repository: FromDishka[JobRepository],
    graph_artifact_store: FromDishka[GraphArtifactStore],
) -> str:
    """Посчитать иерархический layout с учётом кластеризации.

    Координаты сохраняются в ``data['layout']`` (заменяют предыдущий layout)
    в нормализованном диапазоне [-1, 1]. Также сохраняет ``data['analysis_result']``
    для последующей отправки через SSE.

    :param job_id: Идентификатор задачи.
    """
    try:
        await job_repository.update_status(job_id, JobStatus.HIERARCHICAL_LAYOUT)

        data = graph_artifact_store.load(job_id)
        graph: nx.MultiDiGraph = data['graph']
        clustering_result: ClusteringResult = data['clustering_result']

        layout_result = compute_hierarchical_layout(
            graph,
            clustering_result,
            cluster_radius_factor=settings.clustering.cluster_radius_factor,
            random_state=settings.clustering.random_state,
        )

        layout: dict[str, tuple[float, float]] = {
            node_id: (
                float(layout_result.positions[idx, 0]),
                float(layout_result.positions[idx, 1]),
            )
            for node_id, idx in layout_result.node_id_to_index.items()
        }

        node_ids_ordered = list(layout_result.node_id_to_index.keys())
        labels_ordered = [
            int(clustering_result.labels[clustering_result.node_id_to_index[nid]])
            if nid in clustering_result.node_id_to_index
            else -1
            for nid in node_ids_ordered
        ]
        centroids_serializable = [
            [
                float(layout_result.cluster_centroids[c, 0]),
                float(layout_result.cluster_centroids[c, 1]),
            ]
            for c in range(clustering_result.n_clusters)
        ]

        analysis_result: dict = {
            'labels': labels_ordered,
            'node_ids': node_ids_ordered,
            'cluster_centroids_2d': centroids_serializable,
            'n_clusters': clustering_result.n_clusters,
            'method': clustering_result.method,
            'metadata': clustering_result.metadata,
        }

        data['layout'] = layout
        data['analysis_result'] = analysis_result
        graph_artifact_store.save(job_id, data)

        logger.info(
            'hierarchical_layout_task завершён для job %s: %d узлов, %d кластеров',
            job_id,
            len(node_ids_ordered),
            clustering_result.n_clusters,
        )
        return job_id

    except Exception:
        logger.exception('hierarchical_layout_task failed for job %s', job_id)
        await job_repository.update_status(
            job_id,
            JobStatus.FAILED,
            error_msg=traceback.format_exc(limit=10),
        )
        raise
