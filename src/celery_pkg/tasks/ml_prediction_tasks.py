import json
import time
from datetime import datetime
from typing import Any

from celery import chord, current_task, group, shared_task
from sqlalchemy import insert

from src import create_logger
from src.database.db_models import MLTask, PersonLog, PredictionLog, PredictionProcessingJobLog, get_db_session
from src.ml.utils import _get_prediction, get_batch_prediction
from src.schemas import JobProcessingSchema, ModelOutput, MultiPersonsSchema, PersonSchema

logger = create_logger(name="ml_prediction")


# Note: When `bind=True`, celery automatically passes the task instance as the first argument
# meaning that we need to use `self` and this provides additional functionality like retries, etc
@shared_task(bind=True, base=MLTask)
def process_single_data(self, data: dict[str, Any]) -> dict[str, Any]:  # noqa: ANN001, ARG001
    """
    Process a single person data.

    Parameters
    ----------
    data : dict[str, Any]
        Dictionary containing person data.

    Returns
    -------
    dict[str, Any]
        Dictionary containing processed data and status.

    Raises
    ------
    Exception
        Any error that occurs during data processing.
    """
    try:
        start_time: float = time.time()
        # Load model
        model_dict: dict[str, Any] = self.model_dict

        # Data processing
        record = PersonSchema(**data)
        data_dict: dict[str, Any] = _get_prediction(record, model_dict)[0]
        pred: dict[str, Any] = ModelOutput(**{"data": data_dict, "status": "success"}).model_dump()  # type: ignore

        # Save to database
        with get_db_session() as session:
            # Save input
            session.execute(insert(PersonLog), [record.model_dump()])
            session.execute(insert(PredictionLog), [pred])

        logger.info("[+] Successfully processed data")
        return {
            "status": "success",
            "response": [pred],
            "processing_time": time.time() - start_time,
            "sent_at": datetime.now().isoformat(),
        }

    except Exception as e:
        logger.error("[+] Error processing data")
        raise self.retry(exc=e) from e


# Note: When `bind=True`, celery automatically passes the task instance as the first argument
# meaning that we need to use `self` and this provides additional functionality like retries, etc
@shared_task(bind=True, base=MLTask)
def process_ml_data_chunk(self, chunk_data: list[dict[str, Any]], chunk_id: int) -> dict[str, Any]:  # noqa: ANN001, ARG001
    """
    Process a chunk of data and return the processed data, processing time, and item count.

    Parameters
    ----------
    chunk_data : list[dict[str, Any]]
        List of dictionaries containing person data to be processed.
    chunk_id : int
        Unique identifier for this chunk.

    Returns
    -------
    dict[str, Any]
        Dictionary containing processed data, processing time, item count, and chunk_id.
    """
    try:
        start_time: float = time.time()

        # Load model
        model_dict = self.model_dict
        records: MultiPersonsSchema = MultiPersonsSchema(persons=chunk_data)  # type: ignore
        pred_data: list[dict[str, Any]] = get_batch_prediction(records, model_dict).model_dump()["outputs"]

        processed_data: list[dict[str, Any]] = []
        total_items: int | None = len(chunk_data)

        for i, (item, pred) in enumerate(zip(chunk_data, pred_data)):
            # Update task progress
            current_task.update_state(
                state="PROGRESS",
                meta={"current": i + 1, "total": total_items, "chunk_id": chunk_id},
            )

            # Data processing
            record = PersonSchema(**item)
            # Save to database
            with get_db_session() as session:
                # Save input
                session.execute(insert(PersonLog), [record.model_dump()])
                session.execute(insert(PredictionLog), [pred])
                processed_data.append(pred)

        processing_time: float | None = time.time() - start_time
        return {
            "chunk_id": chunk_id,
            "input_data": chunk_data,
            "response": processed_data,
            "processing_time": processing_time,
            "item_count": total_items,
        }

    except Exception as e:
        logger.error(f"[+] Error processing data chunk {chunk_id}: {e}")
        raise self.retry(exc=e) from e


@shared_task
def combine_processed_chunks(chunked_results: list[dict[str, Any]]) -> dict[str, Any]:
    """
    Combine results from multiple processed data chunks.

    Parameters
    ----------
    chunked_results : list[dict[str, Any]]
        List of dictionaries containing processed data with associated metadata.

    Returns
    -------
    dict[str, Any]
        Dictionary containing the status of the operation, total number of chunks,
        combined processed data, average processing time, and total item count.
    """

    try:
        sorted_results: list[dict[str, Any]] = sorted(chunked_results, key=lambda x: x["chunk_id"])

        # Combine all processed data and generate response
        processing_time: float = 0
        item_count: int = 0
        input_data: list[dict[str, Any]] = []
        combined_data: list[dict[str, Any]] = []

        for result in sorted_results:
            input_data.extend(result["input_data"])
            combined_data.extend(result["response"])
            processing_time += result["processing_time"]
            item_count += result["item_count"]

        average_processing_time: float = round((processing_time / len(sorted_results)), 2)
        data = JobProcessingSchema(
            job_name="ml_prediction",
            input_data=json.dumps({"input_chunks": input_data}),
            output_data=json.dumps({"combined_data": combined_data, "total_items": item_count}),
            processing_time=average_processing_time,
            status="completed",
            completed_at=datetime.now(),
        )

        # Save to database
        logger.info("Saving to database...")
        with get_db_session() as session:
            session.execute(insert(PredictionProcessingJobLog), [data.model_dump()])

        # Return response
        return {
            "status": "completed",
            "total_chunks": len(sorted_results),
            "processing_time": average_processing_time,
            "item_count": item_count,
        }
    except Exception as e:
        logger.error(f"[+] Error combining processed chunks: {e}")
        raise e


@shared_task
def process_bulk_data(data_chunks: list[list[dict[str, Any]]]) -> dict[str, Any]:
    """
    Dispatch a bulk data processing job using Celery.

    Parameters
    ----------
    data_chunks : list[list[dict[str, Any]]]
        List of data chunks to be processed in bulk.

    Returns
    -------
    dict[str, Any]
        Dictionary containing the dispatch status, total number of items, number of chunks,
        and the group ID for tracking the job.
    """
    try:
        job = group(process_ml_data_chunk.s(chunk, i) for i, chunk in enumerate(data_chunks))
        result = job.apply_async()
        # Get individual task IDs
        task_ids = [child.id for child in result.children]
        return {
            "status": "dispatched",
            "total_items": len(data),
            "chunks": len(data),
            "group_id": result.id,
            "task_ids": task_ids,
        }

    except Exception as e:
        logger.error(f"[+] Error dispatching bulk data processing: {e}")
        raise


@shared_task
def ml_process_large_dataset(data: list[Any], chunk_size: int = 10) -> dict[str, Any]:
    """
    Process a large dataset by splitting it into chunks and executing parallel processing using Celery chords.

    Parameters
    ----------
    data : list[Any]
        The large dataset to be processed, represented as a list of any type.
    chunk_size : int, optional
        The size of each chunk for splitting the dataset. Defaults to 10.

    Returns
    -------
    dict[str, Any]
        A dictionary containing processing metadata, including:
            - 'status' (str): Current status of the job ("dispatched")
            - 'total_items' (int): Total number of items in the original dataset
            - 'chunks' (int): Number of chunks the data was split into
            - 'chord_id' (str): The Celery task ID of the dispatched chord

    Raises
    ------
    Exception
        Re-raises any exception that occurs during processing dispatch.
    """
    try:
        # Split the input data into smaller chunks of specified size
        # This allows for parallel processing of large datasets
        chunks: list[list[Any]] = [data[i : i + chunk_size] for i in range(0, len(data), chunk_size)]

        # Create a chord pattern for parallel processing:
        # - group: Execute multiple `process_ml_data_chunk` tasks in parallel, one for each chunk
        # - chord: After all chunks are processed, execute `combine_processed_chunks` callback
        #          with the results from all the chunk processing tasks
        job = chord(
            group(process_ml_data_chunk.s(chunk, i) for i, chunk in enumerate(chunks)),
            combine_processed_chunks.s(),
        )

        # Dispatch the chord asynchronously and get the result handle
        result = job.apply_async()

        # Return metadata about the dispatched job for monitoring and tracking
        return {
            "status": "dispatched",
            "total_items": len(data),
            "chunks": len(chunks),
            "chord_id": result.id,
        }

    except Exception as e:
        # Log any errors that occur during job dispatch for debugging and monitoring
        logger.error(f"[+] Error dispatching large dataset processing: {e}")
        raise
