import json
import time
from datetime import datetime
from typing import Any

import numpy as np

from celery import chord, current_task, group
from schemas import DataProcessingSchema
from schemas.db_models import DataProcessingJob, get_db_session
from src import create_logger
from src.celery import celery_app

logger = create_logger()

rng = np.random.default_rng(42)


@celery_app.task(bind=True)
def process_data_chunk(chunk_data: list[str], chunk_id: int) -> dict[str, Any]:
    """Process a chunk of data"""
    try:
        start_time = time.time()

        # Simulate data processing
        processed_data = []
        total_items = len(chunk_data)

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

            processed_data.append(processed_item)

        processing_time = time.time() - start_time

        logger.info(
            f"Processed chunk {chunk_id} with {total_items} items in {processing_time:.2f}s"
        )

        return {
            "chunk_id": chunk_id,
            "processed_data": processed_data,
            "processing_time": processing_time,
            "items_count": total_items,
        }

    except Exception as e:
        logger.error(f"Error processing chunk {chunk_id}: {e}")
        return {
            "chunk_id": chunk_id,
            "processed_data": [],
            "processing_time": None,
            "items_count": None,
        }


@celery_app.task
def combine_processed_chunks(chunk_results: list[Any]) -> dict[str, Any]:
    """
    Combine results from multiple data processing chunks
    """
    try:
        with get_db_session() as session:
            # Sort chunks by chunk_id
            sorted_results = sorted(chunk_results, key=lambda x: x["chunk_id"])

            # Combine all processed data
            combined_data = []
            total_processing_time: int = 0
            total_items: int = 0

            for result in sorted_results:
                combined_data.extend(result["processed_data"])
                total_processing_time += result["processing_time"]
                total_items += result["items_count"]

            # Save to database
            data = DataProcessingSchema(
                job_name="bulk_data_processing",
                input_data=json.dumps({"chunks": len(sorted_results)}),
                output_data=json.dumps({"total_items": total_items}),
                processing_time=total_processing_time,
                status="completed",
                completed_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            ).to_data_model_dict()
            job = DataProcessingJob(**data)
            session.add(job)
            session.flush()

            logger.info(f"Combined {len(sorted_results)} chunks with {total_items} total items")

            return {key: getattr(job, key) for key in job.output_fields()}  # type: ignore

    except Exception as exc:
        logger.error(f"Error combining chunks: {exc}")
        raise


@celery_app.task
def process_large_dataset(data: list[Any], chunk_size: int = 10) -> dict[str, Any]:
    """
    Process a large dataset by splitting into chunks and using chord
    """
    try:
        # Split data into chunks
        chunks = [data[i : i + chunk_size] for i in range(0, len(data), chunk_size)]

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
