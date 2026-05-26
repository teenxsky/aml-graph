from dishka.integrations.fastapi import DishkaRoute, FromDishka
from fastapi import APIRouter
from fastapi.sse import EventSourceResponse
from pydantic import UUID4

from src.modules.graph.use_cases.stream_graph import StreamGraphUseCase

router = APIRouter(route_class=DishkaRoute)


@router.get('/graph/{job_id}/stream')
async def stream_graph(
    job_id: UUID4,
    stream_graph_use_case: FromDishka[StreamGraphUseCase],
) -> EventSourceResponse:
    """SSE-эндпоинт: real-time статус job + чанки графа по завершении.

    Алгоритмы кластеризации и скоринга выбираются автоматически на основе
    характеристик графа. Подробности выбора доступны в метаданных анализа
    (событие analysis_result.metadata).
    """
    return EventSourceResponse(
        content=stream_graph_use_case.execute(str(job_id)),
    )
