import time
from typing import Any

from celery import current_task
from schemas import PersonSchema
from src import create_logger
from src.celery import celery_app
from src.database.db_models import BaseTask
from src.ml.utils import _get_prediction

logger = create_logger(name="ml_prediction")


# Note: When `bind=True`, celery automatically passes the task instance as the first argument
# meaning that we need to use `self` and this provides additional functionality like retries, etc
@celery_app.task(bind=True, base=BaseTask)
def process_data_chunk(self, data: list[dict[str, Any]], chunk_id: int) -> dict[str, Any]:  # noqa: ANN001, ARG001
    try:
        start_time: float = time.time()

        # Load model
        model_dict = self.model_dict

        processed_data: list[dict[str, Any]] = []
        total_items: int | None = len(data)

        for i, item in enumerate(data):
            # Update task progress
            current_task.update_state(
                state="PROGRESS",
                meta={"current": i + 1, "total": total_items, "chunk_id": chunk_id},
            )

            # Data processing
            record = PersonSchema(**item)
            data_dict: dict[str, Any] = _get_prediction(record, model_dict)[0]
            processed_data.append(data_dict)

        processing_time: float | None = time.time() - start_time
        return {
            "chunk_id": chunk_id,
            "data": processed_data,
            "processing_time": processing_time,
            "item_count": total_items,
        }

    except Exception as e:
        logger.error(f"Error processing chunk {chunk_id}: {e}")
        raise self.retry(exc=e) from e
