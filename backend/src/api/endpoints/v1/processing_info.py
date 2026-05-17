import logging
from http import HTTPStatus

from dishka.integrations.fastapi import DishkaRoute, FromDishka
from fastapi import APIRouter, HTTPException
from pydantic import UUID4

from src.modules.jobs.repositories.job import JobRepository
from src.modules.jobs.schemas import JobInfo

router = APIRouter(route_class=DishkaRoute)
log = logging.getLogger(__name__)


@router.get('/graph/{job_id:str}/processing')
async def job_info(
    job_id: UUID4,
    job_repository: FromDishka[JobRepository],
) -> JobInfo:
    """SSE-эндпоинт: real-time статус job + чанки графа по завершении."""
    try:
        job_model = await job_repository.get_job(str(job_id))

        if job_model is None:
            raise HTTPException(status_code=HTTPStatus.NOT_FOUND, detail='Задача не найдена')

        return JobInfo.model_validate(job_model)

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
