from celery.result import AsyncResult
from fastapi import APIRouter, status

from src.config import app_config
from src.schemas import APITaskStatusSchema, HealthCheck

router = APIRouter(tags=["health", "status"])


@router.get("/health", response_model=HealthCheck, status_code=status.HTTP_200_OK)
async def health_check() -> HealthCheck:
    """
    Simple health check endpoint to verify API is operational.

    Returns:
        HealthCheck: Status of the API
    """

    return HealthCheck(status=app_config.api_config.status, version=app_config.api_config.version)


@router.get("/status/{task_id}", status_code=status.HTTP_200_OK)
async def task_status(task_id: str) -> APITaskStatusSchema:
    """
    Retrieve the status of a task.

    Parameters
    ----------
    data : GetTaskSchema
        The input data for the task.

    Returns
    -------
    dict
        A dictionary containing the status and result of the task
    """
    task = AsyncResult(task_id)
    if task.state == "SUCCESS":
        return APITaskStatusSchema(**{"task_id": task_id, "status": "SUCCESS", "result": task.result["response"]})  # type: ignore
    if task.state == "PENDING":
        return APITaskStatusSchema(**{"task_id": task_id, "status": "PENDING", "result": {}})  # type: ignore
    return APITaskStatusSchema(**{"task_id": task_id, "status": "FAILURE", "result": {}})  # type: ignore
