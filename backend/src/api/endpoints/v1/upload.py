import json
from http import HTTPStatus
from typing import Annotated

from dishka.integrations.fastapi import DishkaRoute, FromDishka
from fastapi import APIRouter, File, Form, HTTPException, Request, UploadFile

from src.modules.graph.use_cases.process_ibm_graph_pipeline import ProcessIbmGraphPipelineUseCase
from src.modules.jobs.schemas import JobCreated
from src.modules.jobs.use_cases.upload_graph import UploadGraphUseCase
from src.shared.helpers import get_client_ip
from src.shared.schemas import ColumnMapping, ResponseDTO

router = APIRouter(route_class=DishkaRoute)


@router.post('/graph/processing/ibm')
async def upload_ibm(
    request: Request,
    file: Annotated[UploadFile, File()],
    upload_graph_use_case: FromDishka[UploadGraphUseCase],
    process_ibm_graph_pipeline_use_case: FromDishka[ProcessIbmGraphPipelineUseCase],
) -> ResponseDTO[JobCreated]:
    """Принять IBM AML CSV, поставить в очередь обработки, вернуть job_id.

    Алгоритм кластеризации выбирается автоматически на основе размера графа.
    """
    file_bytes = await file.read()

    if not file_bytes:
        raise HTTPException(status_code=HTTPStatus.BAD_REQUEST, detail='File is empty')

    user_ip = get_client_ip(request)

    if not user_ip:
        raise HTTPException(
            status_code=HTTPStatus.FORBIDDEN,
            detail='Не удалось определить IP клиента',
        )

    job_model = await upload_graph_use_case.execute(
        file_bytes=file_bytes,
        user_ip=user_ip,
    )

    if job_model is None:
        raise HTTPException(
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
            detail='Не удалось загрузить файл и запустить обработку данных',
        )

    await process_ibm_graph_pipeline_use_case.execute(job_model.id)

    return ResponseDTO(
        data=JobCreated(
            job_id=job_model.id,
            status=job_model.status,
            created_at=job_model.created_at,
        ),
    )


@router.post('/graph/processing')
async def upload_csv(
    request: Request,
    file: Annotated[UploadFile, File()],
    column_mapping: Annotated[str, Form()],
    upload_graph_use_case: FromDishka[UploadGraphUseCase],
    process_ibm_graph_pipeline_use_case: FromDishka[ProcessIbmGraphPipelineUseCase],
) -> ResponseDTO[JobCreated]:
    """Принять CSV с маппингом колонок, поставить в очередь, вернуть job_id.

    Алгоритм кластеризации выбирается автоматически на основе размера графа.
    """
    try:
        mapping = ColumnMapping.model_validate(json.loads(column_mapping))
    except Exception as e:
        raise HTTPException(
            status_code=HTTPStatus.UNPROCESSABLE_CONTENT,
            detail=f'Невалидный column_mapping: {e}',
        ) from e

    file_bytes = await file.read()

    if not file_bytes:
        raise HTTPException(status_code=HTTPStatus.BAD_REQUEST, detail='Файл пустой')

    user_ip = get_client_ip(request)

    if not user_ip:
        raise HTTPException(
            status_code=HTTPStatus.FORBIDDEN,
            detail='Не удалось определить IP клиента',
        )

    job_model = await upload_graph_use_case.execute(
        file_bytes=file_bytes,
        user_ip=user_ip,
        column_mapping=mapping,
    )

    if job_model is None:
        raise HTTPException(
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
            detail='Не удалось загрузить файл и запустить обработку данных',
        )

    await process_ibm_graph_pipeline_use_case.execute(job_model.id)

    return ResponseDTO(
        data=JobCreated(
            job_id=job_model.id,
            status=job_model.status,
            created_at=job_model.created_at,
        ),
    )
