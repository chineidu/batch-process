from celery.result import AsyncResult
from fastapi import APIRouter, status

from src.schemas import APITaskStatusSchema
from src.celery_pkg import celery_app
router = APIRouter(tags=["task-status"])


@router.get("/task-status/{task_id}", status_code=status.HTTP_200_OK)
async def get_task_status(task_id: str) -> dict[str, Any]:
    """
    Get the status of a task (works for both individual tasks and chord callbacks)
    """
    try:
        result = AsyncResult(task_id, app=celery_app)

        response = {
            "task_id": task_id,
            "state": result.state,
            "ready": result.ready(),
        }

        if result.state == "PENDING":
            response.update(
                {
                    "status": "Task is waiting to be processed or does not exist",
                    "current": 0,
                    "total": 1,
                }
            )

        elif result.state == "PROGRESS":
            info = result.info or {}
            response.update(
                {
                    "status": "Task is currently being processed",
                    "current": info.get("current", 0),
                    "total": info.get("total", 1),
                    "chunk_id": info.get("chunk_id"),
                }
            )

        elif result.state == "SUCCESS":
            response.update(
                {
                    "status": "Task completed successfully",
                    "result": result.result,
                    "successful": True,
                }
            )

        elif result.state == "FAILURE":
            response.update(
                {
                    "status": "Task failed",
                    "error": str(result.info),
                    "traceback": result.traceback,
                    "successful": False,
                }
            )

        elif result.state == "RETRY":
            response.update({"status": "Task is being retried", "error": str(result.info), "percentage": 0})

        elif result.state == "REVOKED":
            response.update({"status": "Task was revoked", "percentage": 0})

        return response

    except Exception as e:
        logger.error(f"Error getting task status for {task_id}: {e}")
        return {
            "task_id": task_id,
            "state": "ERROR",
            "status": f"Error retrieving task status: {str(e)}",
            "error": str(e),
        }

