from typing import Any

from celery import group
from fastapi import APIRouter, status

from src import create_logger
from src.celery_pkg.tasks import process_ml_data_chunk, process_single_data
from src.config import app_config
from src.schemas import MultiplePersonSchema, SinglePersonSchema

logger = create_logger(name="prediction")
router = APIRouter(tags=["prediction"])


@router.post("/predict-single", status_code=status.HTTP_200_OK)
async def predict_single(data: SinglePersonSchema) -> dict[str, Any]:
    """
    Handle a POST request to make a single prediction.

    Parameters
    ----------
    data : SinglePersonSchema
        The input data for the prediction, encapsulated in a SinglePersonSchema.

    Returns
    -------
    dict[str, Any]
        The result of the prediction, containing the status and response.

    Raises
    ------
    Exception
        If there is an error during prediction processing or the task times out.
    """
    logger.info("Making prediction ...")

    _data: dict[str, Any] = data.model_dump()["data"][0]
    task = process_single_data.delay(_data)
    return {
        "status": "dispatched",
        "task_id": task.id,
        "message": "Task dispatched. You can query the result using the task ID.",
    }


@router.post("/predict-multiple-data", status_code=status.HTTP_200_OK)
async def predict_multiple(data: MultiplePersonSchema) -> dict[str, Any]:
    """
    Handle a POST request to make a single prediction.

    Parameters
    ----------
    data : SinglePersonSchema
        The input data for the prediction, encapsulated in a MultiplePersonSchema.

    Returns
    -------
    dict[str, Any]
        The prediction status and task IDs(s)

    Raises
    ------
    Exception
        If there is an error during prediction processing or the task times out.
    """
    logger.info("Making batch predictions ...")

    received_data: list[dict[str, Any]] = data.model_dump()["data"]
    # Chunk data
    chunk_size: int = app_config.api_config.batch_size
    chunks: list[list[dict[str, Any]]] = [
        received_data[i : i + chunk_size] for i in range(0, len(received_data), chunk_size)
    ]
    job = group(process_ml_data_chunk.s(chunk, idx) for idx, chunk in enumerate(chunks))
    result = job.apply_async()

    # Get individual task IDs
    task_ids = [child.id for child in result.children]

    return {
        "status": "dispatched",
        "total_items": len(received_data),
        "chunks": len(chunks),
        "task_ids": task_ids,
        "message": "Task dispatched. You can query the result using the task ID(s).",
    }
