from celery.result import AsyncResult
from fastapi import APIRouter, status

from src.config import app_config
from src.schemas import GetTaskSchema, HealthCheck, TaskStatusSchema

router = APIRouter(tags=["health", "status"])


@router.get("/health", response_model=HealthCheck, status_code=status.HTTP_200_OK)
def health_check() -> HealthCheck:
    """
    Simple health check endpoint to verify API is operational.

    Returns:
        HealthCheck: Status of the API
    """

    return HealthCheck(status=app_config.api_config.status, version=app_config.api_config.version)


@router.post("/status", status_code=status.HTTP_200_OK)
async def task_status(data: GetTaskSchema) -> TaskStatusSchema:
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
    task = AsyncResult(data.task_id)
    if task.state == "SUCCESS":
        return TaskStatusSchema(**{"status": "SUCCESS", "result": task.result})
    if task.state == "PENDING":
        return TaskStatusSchema(**{"status": "PENDING", "result": {"task_id": data.task_id}})  # type: ignore
    return TaskStatusSchema(**{"status": "FAILURE", "result": {"task_id": data.task_id}})  # type: ignore
