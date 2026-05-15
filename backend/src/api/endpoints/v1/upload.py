import json
from typing import Annotated

from dishka.integrations.fastapi import DishkaRoute, FromDishka
from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from src.shared.schemas import ColumnMapping, SessionResponse
from src.usecases.upload_graph import UploadGraphUseCase

router = APIRouter(route_class=DishkaRoute)


@router.post('/upload')
async def upload_csv(
    file: Annotated[UploadFile, File()],
    column_mapping: Annotated[str, Form()],
    use_case: FromDishka[UploadGraphUseCase],
) -> SessionResponse:
    """Принимает CSV с транзакциями и возвращает session_id для последующего стриминга."""
    try:
        mapping = ColumnMapping.model_validate(json.loads(column_mapping))
    except Exception as e:
        raise HTTPException(status_code=422, detail=f'Невалидный column_mapping: {e}') from e

    file_bytes = await file.read()
    if not file_bytes:
        raise HTTPException(status_code=400, detail='Файл пустой')

    try:
        session_id = use_case.execute(file_bytes, mapping)
    except Exception as e:
        raise HTTPException(status_code=422, detail=f'Ошибка обработки графа: {e}') from e

    return SessionResponse(session_id=session_id)


@router.post('/upload/ibm')
async def upload_ibm(
    file: Annotated[UploadFile, File()],
    use_case: FromDishka[UploadGraphUseCase],
) -> SessionResponse:
    """Accept IBM Transactions for AML CSV and create a graph session."""
    file_bytes = await file.read()
    if not file_bytes:
        raise HTTPException(status_code=400, detail='File is empty')

    try:
        session_id = use_case.execute_ibm(file_bytes, file.filename)
    except Exception as e:
        raise HTTPException(status_code=422, detail=f'IBM upload failed: {e}') from e

    return SessionResponse(session_id=session_id)
