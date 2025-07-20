from typing import Any

from fastapi import APIRouter, status

from src import create_logger
from src.celery_pkg.tasks import process_single_data
from src.celery_pkg.tasks.ml_prediction_tasks import process_bulk_data
from src.schemas import MultiplePersonSchema, SinglePersonSchema

logger = create_logger(name="prediction")
router = APIRouter(tags=["prediction"])


@router.post("/predict-single", status_code=status.HTTP_200_OK)
async def predict_single(data: SinglePersonSchema) -> None:
    """
    Handle a POST request to make a single prediction.

    Parameters
    ----------
    data : SinglePersonSchema
        The input data for the prediction, encapsulated in a SinglePersonSchema.

    Returns
    -------
    dict
        The result of the prediction, containing the status and response.

    Raises
    ------
    Exception
        If there is an error during prediction processing or the task times out.
    """
    logger.info("Making prediction ...")

    _data: dict[str, Any] = data.model_dump()["data"][0]
    result = process_single_data.delay(_data)
    return result.get(timeout=180)


@router.post("/predict-multiple-data", status_code=status.HTTP_200_OK)
async def predict_multiple(data: MultiplePersonSchema) -> None:
    """
    Handle a POST request to make a single prediction.

    Parameters
    ----------
    data : SinglePersonSchema
        The input data for the prediction, encapsulated in a SinglePersonSchema.

    Returns
    -------
    dict
        The result of the prediction, containing the status and response.

    Raises
    ------
    Exception
        If there is an error during prediction processing or the task times out.
    """
    logger.info("Making prediction ...")

    _data: list[dict[str, Any]] = data.model_dump()["data"]
    # Chunk data
    chunk_size: int = 20
    chunks = [_data[i : i + chunk_size] for i in range(0, len(_data), chunk_size)]
    result = process_bulk_data.delay(chunks)
    return result.get(timeout=60)
