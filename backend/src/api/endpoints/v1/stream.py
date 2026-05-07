from dishka.integrations.fastapi import DishkaRoute, FromDishka
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from src.usecases.stream_graph import StreamGraphUseCase

router = APIRouter(route_class=DishkaRoute)


@router.get('/stream/{session_id}')
async def stream_graph(
    session_id: str,
    use_case: FromDishka[StreamGraphUseCase],
) -> StreamingResponse:
    """SSE-эндпоинт: стримит метаданные, узлы, рёбра и результаты AML-детекторов."""
    session = use_case.get_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail='Сессия не найдена')

    return StreamingResponse(
        use_case.generate_events(session, session_id),
        media_type='text/event-stream',
        headers={'Cache-Control': 'no-cache', 'X-Accel-Buffering': 'no'},
    )
