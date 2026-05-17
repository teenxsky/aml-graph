from dishka.integrations.fastapi import DishkaRoute, FromDishka, inject
from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from src.modules.graph.use_cases.stream_graph import StreamGraphUseCase

router = APIRouter(route_class=DishkaRoute)


@router.get('/stream/{job_id}')
@inject
async def stream_graph(
    job_id: str,
    stream_graph_use_case: FromDishka[StreamGraphUseCase],
) -> StreamingResponse:
    """SSE-эндпоинт: real-time статус job + чанки графа по завершении."""
    return StreamingResponse(
        stream_graph_use_case.execute(job_id),
        media_type='text/event-stream',
        headers={'Cache-Control': 'no-cache', 'X-Accel-Buffering': 'no'},
    )
