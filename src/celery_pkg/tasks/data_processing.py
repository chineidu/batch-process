import json
import time
from datetime import datetime
from typing import Any

from celery import chord, current_task, group, shared_task

from src import create_logger
from src.database import get_db_session
from src.database.db_models import BaseTask, DataProcessingJobLog
from src.schemas import JobProcessingSchema

logger = create_logger(name="data_processing")
logger.propagate = False  # This prevents double logging to the root logger

# Note: When `bind=True`, celery automatically passes the task instance as the first argument
# meaning that we need to use `self` and this provides additional functionality like retries, etc
@shared_task(bind=True, base=BaseTask)
def process_data_chunk(self, chunk_data: list[str], chunk_id: int) -> dict[str, Any | None | float | int]:  # noqa: ANN001, ARG001
    """
    Process a chunk of data

    Parameters
    ----------
    chunk_data : list[str]
        List of strings to be processed
    chunk_id : int
        Unique identifier for this chunk

    Returns
    -------
    dict[str, Any | None | float | int]
        Dictionary containing processed data, processing time, and item count
    """
    try:
        start_time = time.time()

        # Simulate data processing
        processed_data: list[str] = []
        total_items: int | None = len(chunk_data)

        for i, item in enumerate(chunk_data):
            # Update task progress
            current_task.update_state(
                state="PROGRESS",
                meta={"current": i + 1, "total": total_items, "chunk_id": chunk_id},
            )

            # Simulate processing time
            time.sleep(0.9)

            if isinstance(item, str):
                processed_item = item.upper()

            else:
                processed_item = item

            processed_data.append(processed_item)

        processing_time: float | None = time.time() - start_time

        logger.info(f"Processed chunk {chunk_id} with {total_items} items in {processing_time:.2f}s")

        return {
            "chunk_id": chunk_id,
            "output_data": processed_data,
            "processing_time": processing_time,
            "items_count": total_items,
        }

    except Exception as e:
        logger.error(f"Error processing chunk {chunk_id}: {e}")
        raise self.retry(exc=e) from e


@shared_task
def combine_processed_chunks(chunk_results: list[Any]) -> dict[str, Any]:
    """
    Combine results from multiple data processing chunks
    """
    try:
        with get_db_session() as session:
            # Sort chunks by chunk_id
            sorted_results = sorted(chunk_results, key=lambda x: x["chunk_id"])

            # Combine all processed data
            combined_data: list[str] = []
            total_processing_time: int = 0
            total_items: int = 0

            for result in sorted_results:
                combined_data.extend(result["processed_data"])
                total_processing_time += result["processing_time"]
                total_items += result["items_count"]

            avg_processing_time = round((total_processing_time / len(sorted_results)), 2)
            # Save to database
            data = JobProcessingSchema(
                job_name="bulk_data_processing",
                input_data=json.dumps({"chunks": sorted_results}),
                output_data=json.dumps({"combined_data": combined_data, "total_items": total_items}),
                processing_time=avg_processing_time,
                status="completed",
                completed_at=datetime.now(),
            ).model_dump()
            job = DataProcessingJobLog(**data)
            session.add(job)
            session.flush()

            logger.info(f"Combined {len(sorted_results)} chunks with {total_items} total items")

            return {
                "status": "completed",
                "total_chunks": len(sorted_results),
                "total_items": total_items,
                "avg_processing_time": avg_processing_time,
                "job_id": job.id,
            }

    except Exception as e:
        logger.error(f"Error combining chunks: {e}")
        raise


@shared_task
def process_large_dataset(data: list[Any], chunk_size: int = 10) -> dict[str, Any]:
    """
    Process a large dataset by splitting into chunks and using chord
    """
    try:
        # Split data into chunks
        chunks: list[list[Any]] = [data[i : i + chunk_size] for i in range(0, len(data), chunk_size)]

        # Create a chord: process chunks in parallel, then combine results
        job = chord(
            group(process_data_chunk.s(chunk, i) for i, chunk in enumerate(chunks)),
            combine_processed_chunks.s(),
        )

        result = job.apply_async()

        return {
            "status": "dispatched",
            "total_items": len(data),
            "chunks": len(chunks),
            "chord_id": result.id,
        }

    except Exception as e:
        logger.error(f"Error dispatching large dataset processing: {e}")
        raise
