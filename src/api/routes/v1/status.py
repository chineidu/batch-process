from celery.result import AsyncResult
from fastapi import APIRouter, status

from src.schemas import APITaskStatusSchema

router = APIRouter(tags=["task-status"])


@router.get("/task-status/{task_id}", status_code=status.HTTP_200_OK)
async def task_status(task_id: str) -> APITaskStatusSchema:
    """
    Get the status of a task.

    Parameters
    ----------
    task_id : str
        The task id

    Returns
    -------
    APITaskStatusSchema
        The status of the task.
    """
    task_result = AsyncResult(task_id)
    result = task_result.result["response"] if task_result.ready() else []

    return APITaskStatusSchema(**{
        "task_id": task_id,
        "num_records": len(result) if result else 0,
        "status": task_result.status,
        "processing_time": task_result.result["processing_time"] if result else 0,
        "result": result,
    })
