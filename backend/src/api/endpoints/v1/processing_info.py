import logging
from http import HTTPStatus
from typing import Annotated

from dishka.integrations.fastapi import DishkaRoute, FromDishka
from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import UUID4

from src.modules.jobs.repositories.job import JobRepository
from src.modules.jobs.schemas import JobInfo
from src.shared.helpers import get_client_ip
from src.shared.schemas import PaginatedResponseDTO, PaginationMetaDTO, ResponseDTO

router = APIRouter(route_class=DishkaRoute)
log = logging.getLogger(__name__)


@router.get('/graph/{job_id:str}/processing')
async def job_info(
    job_id: UUID4,
    job_repository: FromDishka[JobRepository],
) -> ResponseDTO[JobInfo]:
    """Возвращает информацию о задаче на обработку данных по его job_id."""
    try:
        job_model = await job_repository.get_job(str(job_id))

        if job_model is None:
            raise HTTPException(status_code=HTTPStatus.NOT_FOUND, detail='Задача не найдена')

        return ResponseDTO(
            data=JobInfo.model_validate(job_model),
        )

    except Exception as err:
        if isinstance(err, HTTPException) and err.status_code != HTTPStatus.INTERNAL_SERVER_ERROR:
            raise err

        log.error(str(err))

        raise HTTPException(
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
            detail=(
                'Произошла ошибка при получении информации о задаче '
                f'обработки датасета с ID "{job_id}"'
            ),
        ) from err


@router.get('/graph/processing/latest')
async def latest_jobs_by_user_ip(
    request: Request,
    job_repository: FromDishka[JobRepository],
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 10,
) -> PaginatedResponseDTO[list[JobInfo]]:
    """Возвращает последние задачи на обработку данных текущего пользователя."""

    try:
        user_ip = get_client_ip(request)

        if not user_ip:
            raise HTTPException(
                status_code=HTTPStatus.FORBIDDEN,
                detail='Не удалось определить IP клиента',
            )

        offset = (page - 1) * page_size

        jobs, total = await job_repository.get_latest_jobs_by_user_ip(
            user_ip=user_ip,
            limit=page_size,
            offset=offset,
        )

        return PaginatedResponseDTO(
            data=[JobInfo.model_validate(job_model) for job_model in jobs],
            meta=PaginationMetaDTO(
                total=total,
                limit=page_size,
                offset=offset,
            ),
        )

    except Exception as err:
        if isinstance(err, HTTPException) and err.status_code != HTTPStatus.INTERNAL_SERVER_ERROR:
            raise err

        log.error(str(err))

        raise HTTPException(
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
            detail='Произошла ошибка при получении последних задач для текущего пользователя',
        ) from err
