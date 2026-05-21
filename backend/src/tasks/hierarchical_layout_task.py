import logging
from datetime import UTC, datetime, timezone

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

_ALGORITHM_VERSIONS: dict[str, str] = {
    'agc': 'Zhang_2019_IJCAI_arXiv:1906.01210',
    'louvain': 'Blondel_2008_J.Stat.Mech.',
    'betweenness': 'Brandes_2001_exact;Brandes&Pich_2007_sampling',
    'pagerank': 'Page&Brin_1998',
    'hierarchical_layout': 'Fruchterman-Reingold_1991',
}


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
    для последующей отправки через SSE, включая структурированные метаданные.
    """
    started = datetime.now(timezone.utc)
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

        type_centroids_serializable = {
            entity_type: [float(x), float(y)]
            for entity_type, (x, y) in layout_result.type_centroids.items()
        }

        finished = datetime.now(UTC)
        duration_ms = int((finished - started).total_seconds() * 1000)

        step_timings: list[dict] = data.get('step_timings', [])
        step_timings.append(
            {
                'step': 'hierarchical_layout',
                'duration_ms': duration_ms,
                'started_at': started.isoformat(),
                'finished_at': finished.isoformat(),
            },
        )

        total_duration_ms = sum(t['duration_ms'] for t in step_timings)

        # Граф-статистика для метаданных
        n_nodes = graph.number_of_nodes()
        n_edges = graph.number_of_edges()
        density = n_edges / (n_nodes * (n_nodes - 1)) if n_nodes > 1 else 0.0

        strategy = data.get('analysis_strategy', {})

        metadata: dict = {
            'n_nodes': n_nodes,
            'n_edges': n_edges,
            'density': density,
            'is_directed': graph.is_directed(),
            'clustering_method': strategy.get('clustering_method', clustering_result.method),
            'clustering_reason': strategy.get('clustering_reason', ''),
            'clustering_extra': clustering_result.metadata,
            'scoring_weights': strategy.get('scoring_weights', {}),
            'scoring_reason': strategy.get('scoring_reason', ''),
            'betweenness_exact': strategy.get('betweenness_exact', True),
            'betweenness_k': strategy.get('betweenness_k', 0),
            'step_timings': step_timings,
            'total_duration_ms': total_duration_ms,
            'algorithm_versions': _ALGORITHM_VERSIONS,
        }

        analysis_result: dict = {
            'labels': labels_ordered,
            'node_ids': node_ids_ordered,
            'cluster_centroids_2d': centroids_serializable,
            'type_centroids': type_centroids_serializable,
            'n_clusters': clustering_result.n_clusters,
            'method': clustering_result.method,
            'metadata': metadata,
        }

        data['layout'] = layout
        data['analysis_result'] = analysis_result
        data['step_timings'] = step_timings
        graph_artifact_store.save(job_id, data)

        logger.info(
            'hierarchical_layout_task завершён для job %s: %d узлов, %d кластеров',
            job_id,
            len(node_ids_ordered),
            clustering_result.n_clusters,
        )
        return job_id

    except Exception as e:
        logger.exception('hierarchical_layout_task failed for job %s', job_id)
        await job_repository.update_status(
            job_id,
            JobStatus.FAILED,
            error_msg=str(e),
        )
        raise
