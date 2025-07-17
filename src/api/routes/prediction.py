from fastapi import APIRouter, status

from src import create_logger
from src.celery_pkg.tasks import process_single_data, process_large_dataset, send_bulk_emails, send_email
from src.schemas import PersonSchema

logger = create_logger(name="main")
router = APIRouter(tags=["prediction"])

@router.post("/predict", status_code=status.HTTP_200_OK)
def predict_single(data: PersonSchema) -> None:
    """
    Handle a POST request to make a single prediction.

    Parameters
    ----------
    data : PersonSchema
        The input data for the prediction, encapsulated in a PersonSchema.

    Returns
    -------
    dict
        The result of the prediction, containing the status and response.

    Raises
    ------
    Exception
        If there is an error during prediction processing or the task times out.
    """

    _data = data.model_dump()
    result = process_single_data.delay(_data)
    return result.get(timeout=5)
