"""Logic for running tasks and publishing to a `general` RabbitMQ queue"""
import json
import time
from datetime import datetime
from itertools import chain
from typing import Any

from celery import chord, current_task, group, shared_task
from sqlalchemy import insert

from src.celery_app import MLTask
from src.config import app_config
from src.db.models import TransactionsLabel, get_db_session
from src.schemas import LABELS, QueueOutput, TransactionLabelSchema
from src.utilities import create_logger
from src.utilities.model_utils import _process_batch_labels
from src.utilities.rabbitmq import publish_message_sync

logger = create_logger(name="prediction_tasks")
logger.propagate = False  # This prevents double logging to the root logger


# Note: When `bind=True`, celery automatically passes the task instance as the first argument
# meaning that we need to use `self` and this provides additional functionality like retries, etc
@shared_task(bind=True, base=MLTask)
def process_txn_labels_data_chunk(self, chunk_data: list[dict[str, Any]], chunk_id: int) -> dict[str, Any]:  # noqa: ANN001
    """Process a chunk of data and return the processed data, processing time, and item count."""
    try:
        start_time: float = time.perf_counter()

        # Get pre-loaded model
        model = self.get_components()["model"]

        # Check model readiness
        if not self.model_manager.is_ready():
            raise RuntimeError("Model is not ready for inference.")

        # Process batch data
        pred_data: list[dict[str, Any]] = _process_batch_labels(
            chunk_data,
            model,
            labels=LABELS,
            threshold=app_config.model.threshold,
        )
        pred_data_formatted = [TransactionLabelSchema(**pred).model_dump(by_alias=True) for pred in pred_data]
        processed_data: list[dict[str, Any]] = []
        total_items: int | None = len(chunk_data)

        # Process and update task progress
        for i, pred in enumerate(pred_data_formatted):
            # Update (write) every 10 items or items at the end
            if i % 10 == 0 or i == total_items - 1:
                current_task.update_state(
                    state="PROGRESS",
                    meta={
                        "current": i + 1,
                        "total": total_items,
                        "chunk_id": chunk_id,
                        "percentage": round(((i + 1) / total_items) * 100, 1),
                    },
                )
            processed_data.append(pred)

        processing_time: float | None = time.perf_counter() - start_time
        extra_data: dict[str, Any] = {
            "task_id": current_task.request.id,
            "chunk_id": chunk_id,
            "item_count": total_items,
            "processing_time": round(processing_time, 2),
        }

        result = {
            "status": "completed",
            "chunk_id": chunk_id,
            "item_count": total_items,
            "processing_time": round(processing_time, 2),
            "response": processed_data,
            "task_id": current_task.request.id,
            "completed_at": time.time(),
        }

        logger.info(f"[+] Task completed successfully {json.dumps(extra_data)}")

        return result

    except Exception as e:
        logger.error(f"[+] Error processing data chunk {chunk_id}: {e}")
        raise self.retry(exc=e) from e


@shared_task
def combined_processed_labels(chunked_result: list[dict[str, Any]], run_id: str) -> dict[str, Any]:
    """Combine processed labels from multiple chunks."""
    queue_name = app_config.queues.custom_queue

    try:
        # Sort the results
        sorted_result: list[dict[str, Any]] = sorted(chunked_result, key=lambda x: x["chunk_id"])

        # Combine all responses
        item_count: int = sum(result["item_count"] for result in sorted_result)
        combined_response: list[dict[str, Any]] = list(chain.from_iterable(r["response"] for r in sorted_result))
        avg_processing_time: float = (
            sum(r["processing_time"] for r in sorted_result) / len(sorted_result) if sorted_result else 0.0
        )

        # Save data
        with get_db_session() as session:
            db_records = []
            for record in combined_response:
                db_record: dict[str, Any] = {
                    "id": record["id"],
                    "run_id": run_id,
                    "text": record["text"],
                    "entities": record["entities"],
                    "label": record["label"],
                    "score": record["score"],
                }
                db_records.append(db_record)

            session.execute(insert(TransactionsLabel), db_records)
            logger.info(f"[+] Saved {len(db_records)} records to database")

        final_result: dict[str, Any] = {
            "status": "success",
            "run_id": run_id,
            "task_id": current_task.request.id,
            "total_chunks": len(sorted_result),
            "item_count": item_count,
            "average_processing_time": round(avg_processing_time, 2),
            "model_name": app_config.model.name,
        }

        result_payload: dict[str, Any] = QueueOutput(
            **{
                "event": "task_completed",
                **final_result,
                "data": combined_response,
                "completed_at": datetime.now().isoformat(),
            }
        ).model_dump(by_alias=True)
        is_publish_successful = publish_message_sync(
            run_id=run_id,
            payload=result_payload,
            queue_name=queue_name,
            event_type="task_completed",
        )
        if is_publish_successful:
            logger.info(f"[+] Published message for run_id: {run_id!r}")
        else:
            logger.error(f"[x] Failed to publish message for run_id: {run_id!r}")

        # Add additional information
        final_result["message"] = f"Successfully processed {item_count} records and saved to database"
        final_result["sample_records"] = combined_response[:20]

        return final_result
    
    except Exception as e:
        logger.error(f"[x] Error processing run_id: {run_id!r} \nError: {e}")
        return {"status": "error", "message": str(e)}


@shared_task
def process_large_data(data: list[dict[str, Any]], chunk_size: int, run_id: str) -> dict[str, Any]:
    """Process large data by chunking it into smaller batches and processing them in parallel."""
    chunks: list[list[dict[str, Any]]] = [data[idx : idx + chunk_size] for idx in range(0, len(data), chunk_size)]

    # Process the chunked data in parallel using `group`
    # Aggregate the results using `chord`.
    job = chord(
        group(process_txn_labels_data_chunk.s(chunk, idx) for idx, chunk in enumerate(chunks)),
        combined_processed_labels.s(run_id),
    )
    result = job.apply_async()

    logger.info(f"[+] Chord created with ID: {result.id}")

    return {
        "status": "dispatched",
        "total_items": len(data),
        "chunks": len(chunks),
        "chord_id": result.id,
        "run_id": run_id,
    }
