from typing import Any
from fastapi import APIRouter, status

from src import create_logger
from src.celery_pkg.tasks import process_large_dataset, process_single_data, send_bulk_emails, send_email
from src.schemas import SinglePersonSchema

logger = create_logger(name="prediction")
router = APIRouter(tags=["prediction"])

@router.post("/predict-single", status_code=status.HTTP_200_OK)
def predict_single(data: SinglePersonSchema) -> None:
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
