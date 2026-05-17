import asyncio
import contextlib
import json
from collections.abc import AsyncGenerator
from typing import Any

from src.modules.graph.repositories.graph import GraphStoreRepository
from src.modules.graph.schemas import (
    AnalysisResultData,
    DetectorResult,
    EdgeChunk,
    EdgeData,
    GraphMeta,
    NodeChunk,
    NodeData,
)
from src.modules.jobs.enums import JobStatus
from src.modules.jobs.models import JobModel
from src.modules.jobs.repositories.job import JobRepository

__all__ = ['StreamGraphUseCase']

_NODE_BATCH = 500
_EDGE_BATCH = 1000
_POLL_INTERVAL = 1.0


class StreamGraphUseCase:
    """Генерирует SSE-поток статуса задачи и данных графа."""

    def __init__(self, job_repository: JobRepository, graph_store: GraphStoreRepository) -> None:
        self._job_repository = job_repository
        self._graph_store = graph_store

    async def execute(
        self,
        job_id: str,
        clustering: str = 'agc',
    ) -> AsyncGenerator[str]:
        """Точка входа: немедленно обрабатывает терминальные статусы, иначе запускает long-poll.

        :param job_id: Идентификатор задачи.
        :param clustering: Метод кластеризации. Если ``"none"``, событие ``analysis_result``
                           не эмитируется даже при наличии данных.
        """
        job = await self._job_repository.get_job(job_id)
        if job is None:
            yield _event('error', {'message': 'Job not found'})
            return

        if job.status == JobStatus.FAILED:
            yield _event('error', {'message': job.error_msg or 'Unknown error'})
            return

        if job.status == JobStatus.COMPLETED:
            async for chunk in self._stream_graph(job, clustering=clustering):
                yield chunk
            return

        yield _event('status', {'status': str(job.status), 'job_id': job_id})
        async for event in self._poll_and_stream(
            job_id,
            last_status=job.status,
            clustering=clustering,
        ):
            yield event

    async def _poll_and_stream(
        self,
        job_id: str,
        last_status: JobStatus,
        clustering: str,
    ) -> AsyncGenerator[str]:
        """Опрашивает БД каждые ~1s, отдаёт status-события и стримит граф по готовности."""
        while True:
            await asyncio.sleep(_POLL_INTERVAL)
            job = await self._job_repository.get_job(job_id)
            if job is None:
                yield _event('error', {'message': 'Job disappeared'})
                return

            if job.status != last_status:
                last_status = job.status
                yield _event('status', {'status': str(job.status), 'job_id': job_id})

            if job.status == JobStatus.COMPLETED:
                async for chunk in self._stream_graph(job, clustering=clustering):
                    yield chunk
                return

            if job.status == JobStatus.FAILED:
                yield _event('error', {'message': job.error_msg or 'Unknown error'})
                return

    async def _stream_graph(self, job: JobModel, *, clustering: str) -> AsyncGenerator[str]:
        """Читает граф из LadybugDB и стримит его чанками."""
        if job.ladybug_ref is None:
            yield _event('error', {'message': 'Граф не сохранён: ladybug_ref отсутствует'})
            return

        raw_nodes = self._graph_store.load_nodes(job.ladybug_ref)
        raw_edges = self._graph_store.load_edges(job.ladybug_ref)

        node_count = len(raw_nodes)
        edge_count = len(raw_edges)

        yield _event(
            'graph_meta',
            GraphMeta(
                session_id=str(job.id),
                node_count=node_count,
                edge_count=edge_count,
            ).model_dump(),
        )

        # Эмитировать analysis_result если кластеризация была выполнена
        detector_results: dict[str, Any] = job.detector_results or {}
        analysis_raw = detector_results.get('__analysis__')
        if clustering != 'none' and analysis_raw is not None:
            with contextlib.suppress(Exception):
                analysis = AnalysisResultData.model_validate(analysis_raw)
                yield _event('analysis_result', analysis.model_dump())

        for i in range(0, node_count, _NODE_BATCH):
            batch = raw_nodes[i : i + _NODE_BATCH]
            yield _event(
                'nodes_chunk',
                NodeChunk(
                    nodes=[
                        NodeData(
                            id=row['account_id'],
                            entity_type=row['entity_type'] or 'unknown',
                            label=row['account_id'],
                            x=float(row['x'] or 0.0),
                            y=float(row['y'] or 0.0),
                            risk_score=float(row['risk_score'] or 0.0),
                            alerts=json.loads(row['alerts'] or '[]'),
                            in_flow=float(row['in_flow'] or 0.0),
                            out_flow=float(row['out_flow'] or 0.0),
                            is_laundering_node=bool(row['is_laundering_node']),
                        )
                        for row in batch
                    ],
                ).model_dump(),
            )

        for i in range(0, edge_count, _EDGE_BATCH):
            batch = raw_edges[i : i + _EDGE_BATCH]
            yield _event(
                'edges_chunk',
                EdgeChunk(
                    edges=[
                        EdgeData(
                            id=row['transaction_id'],
                            source=row['source'],
                            target=row['target'],
                            amount_paid=float(row['amount_paid'] or 0.0),
                            timestamp=int(row['timestamp'] or 0),
                            risk_score=float(row['risk_score'] or 0.0),
                            alerts=json.loads(row['alerts'] or '[]'),
                            amount_received=_opt_float(row.get('amount_received')),
                            payment_currency=row.get('payment_currency') or None,
                            receiving_currency=row.get('receiving_currency') or None,
                            payment_format=row.get('payment_format') or None,
                            is_laundering=(
                                bool(row['is_laundering'])
                                if row.get('is_laundering') is not None
                                else None
                            ),
                        )
                        for row in batch
                    ],
                ).model_dump(),
            )

        for pattern_type in ('cycles', 'fanout', 'transit', 'shared_device'):
            items = detector_results.get(pattern_type, [])
            yield _event(
                'detector_result',
                DetectorResult(
                    pattern_type=pattern_type,
                    items=items,
                ).model_dump(),
            )

        yield _event('completed', {'job_id': str(job.id)})
        yield _event('stream_done', {})


def _event(name: str, data: dict) -> str:
    return f'event: {name}\ndata: {json.dumps(data)}\n\n'


def _opt_float(val: Any) -> float | None:
    if val is None or val == '':
        return None
    try:
        return float(val)
    except TypeError, ValueError:
        return None
