import asyncio
import io
import sys
import time
from functools import wraps
from pathlib import Path
from pprint import pprint
from typing import Any, Callable

import anyio
import joblib
from aio_pika.abc import AbstractQueue

from config import app_config, app_settings
from schemas import ModelOutput, MultiPersonsSchema, MultiPredOutput, PersonSchema
from src import PACKAGE_PATH, create_logger
from src.ml.utils import get_batch_prediction, get_prediction
from src.rabbitmq import rabbitmq_manager
from src.utils import (
    DatabaseConnectionPool,
    create_path,
    init_database_async,
    insert_batch_dlq_data_async,
    insert_data_async,
    insert_dlq_data_async,
)

logger = create_logger(name="RMQ_consumer")


def async_timer(func: Callable[..., Any]) -> Callable[..., Any]:
    """
    A decorator that measures and prints the execution time of an async function.

    Parameters
    ----------
    func : Callable
        The async function to be timed.

    Returns
    -------
    Callable
        A wrapped async function that prints execution time.
    """

    @wraps(func)
    async def wrapper(*args: Any, **kwargs: Any) -> Any:
        start_time: float = time.perf_counter()
        result = await func(*args, **kwargs)
        duration: float = time.perf_counter() - start_time
        logger.info(f"{func.__name__} executed in {duration:.2f} seconds")
        return result

    return wrapper


async def load_model_dict(filepath: Path) -> dict[str, Any]:
    """Asynchronously load the model dictionary from a file.

    Parameters
    ----------
    filepath : Path
        The path to the file containing the model dictionary.

    Returns
    -------
    dict[str, Any]
        The loaded model dictionary.
    """
    async with await anyio.open_file(filepath, "rb") as f:
        contents: bytes = await f.read()
        # Create a file-like object from the bytes
        bytes_io = io.BytesIO(contents)
        # Run joblib.load in a thread
        return await anyio.to_thread.run_sync(joblib.load, bytes_io)


async def single_prediction_callback(
    pool: DatabaseConnectionPool, message: dict[str, Any], model_dict: dict[str, Any]
) -> None:
    """
    Process incoming messages and make predictions.

    Parameters
    ----------
    pool : DatabaseConnectionPool
        The database connection pool.
    message : dict[str, Any]
        The incoming message.
    model_dict : dict[str, Any]
        The model dictionary.
    """
    record: PersonSchema = PersonSchema(**message)
    result: ModelOutput = await asyncio.to_thread(
        get_prediction,  # type: ignore
        record,
        model_dict,  # type: ignore
    )
    result_dict: str = result.model_dump_json(by_alias=True)  # type: ignore
    await insert_data_async(pool=pool, data=result_dict, logger=logger)
    logger.info(f"Inserted data with id {record.id!r} into database.")
    return


async def batch_prediction_callback(
    pool: DatabaseConnectionPool, message: dict[str, Any], model_dict: dict[str, Any]
) -> int:
    """Process batch messages and make predictions.

    Parameters
    ----------
    pool : DatabaseConnectionPool
        The database connection pool.
    message : dict[str, Any]
        The incoming message.
    model_dict : dict[str, Any]
        The model dictionary.

    Returns
    -------
    int
        The number of messages processed.
    """
    record: MultiPersonsSchema = MultiPersonsSchema(**message)
    result: ModelOutput = await asyncio.to_thread(
        get_batch_prediction,  # type: ignore
        record,
        model_dict,  # type: ignore
    )
    result_string: str = result.model_dump_json(by_alias=True)  # type: ignore
    for row in (results_list := MultiPredOutput.model_validate_json(result_string).outputs):  # type: ignore
        await insert_data_async(pool=pool, data=row, logger=logger)
    logger.info("Inserted batch data into database.")
    return len(results_list)


async def dlq_callback(pool: DatabaseConnectionPool, message: dict[str, Any]) -> None:
    """
    Process messages from the dead letter queue.

    Parameters
    ----------
    pool : DatabaseConnectionPool
        The database connection pool.
    message : dict[str, Any]
        The message from DLQ to process
    """
    record: PersonSchema = PersonSchema(**message)
    await insert_dlq_data_async(pool=pool, data=record.model_dump_json(), logger=logger)  # type: ignore
    logger.info(f"Inserted DLQ data with id {record.id!r} into database.")
    return


async def batch_dlq_callback(pool: DatabaseConnectionPool, message: dict[str, Any]) -> None:
    """
    Process batch messages from the dead letter queue.

    Parameters
    ----------
    pool : DatabaseConnectionPool
        The database connection pool.
    message : dict[str, Any]
        The message from DLQ to process
    """
    record: MultiPersonsSchema = MultiPersonsSchema(**message)
    await insert_batch_dlq_data_async(pool=pool, data=record, logger=logger)
    logger.info("Inserted batch DLQ data with into database.")
    return


async def is_queue_empty(processed_messages: int) -> bool:
    """
    Check if the RabbitMQ queue is empty.

    Parameters
    ----------
    processed_messages : int
        The number of messages processed.

    Returns
    -------
    bool
        True if queue is empty and at least one message has been processed,
        False otherwise or in case of error.
    """
    try:
        # Check if the queue exists
        queue: AbstractQueue = await rabbitmq_manager.channel.declare_queue(  # type: ignore
            name=app_settings.RABBITMQ_DIRECT_EXCHANGE,
            durable=True,
            passive=True,  # Set to True to check if the queue exists
        )
        return processed_messages > 0 and queue.declaration_result.message_count == 0

    except Exception as e:
        logger.error(f"Error checking queue status: {e}")
        return False


@async_timer
async def process_queue(batch_mode: bool = False) -> None:
    """Process incoming messages and make predictions.

    Parameters
    ----------
    batch_mode : bool, optional
        If True, process batch messages, by default False
    """
    model_dict_fp: Path = PACKAGE_PATH / "models/model.pkl"
    model_dict: dict[str, Any] = await load_model_dict(filepath=model_dict_fp)

    # Processed message counter and event completion flag
    processed_messages: int = 0
    processing_completed = asyncio.Event()

    db_path: str = app_config.db.db_path
    max_connections: int = app_config.db.max_connections
    # Create the database file if it doesn't exist
    create_path(db_path)
    # Initialize the database
    pool = await DatabaseConnectionPool().create_pool(db_path, max_connections)
    await init_database_async(pool)

    async def prediction_wrapper(message: dict[str, Any]) -> None:
        """
        Process incoming messages and make predictions.

        Parameters
        ----------
        message : dict[str, Any]
            The message containing person data to process
        model_dict : dict[str, Any]
            The loaded model dictionary for making predictions

        """
        nonlocal processed_messages

        try:
            if batch_mode:
                processed_messages += await batch_prediction_callback(pool, message, model_dict)
            else:
                await single_prediction_callback(pool, message, model_dict)
                processed_messages += 1

            # Check if all messages have been processed (empty queue)
            # set the event flag to signal completion
            if await is_queue_empty(processed_messages):
                processing_completed.set()
                logger.info(f"All messages processed. Total messages: {processed_messages}")

        except Exception as e:
            logger.error(f"Error making prediction(s): {e}")
            raise

    async def dlq_wrapper(message: dict[str, Any]) -> None:
        """Process messages from the dead letter queue.

        Parameters
        ----------
        message : dict[str, Any]
            The message from DLQ to process
        """
        try:
            if batch_mode:
                await batch_dlq_callback(pool, message)
            else:
                await dlq_callback(pool, message)

        except Exception as e:
            logger.error(f"Error processing DLQ message(s): {e}")

    await rabbitmq_manager.connect()
    await rabbitmq_manager.consume(callback=prediction_wrapper)  # type: ignore
    await rabbitmq_manager.consume_dlq(callback=dlq_wrapper)  # type: ignore

    try:
        while not processing_completed.is_set():
            try:
                await asyncio.wait_for(processing_completed.wait(), timeout=5)
            except asyncio.TimeoutError:
                if await is_queue_empty(processed_messages):
                    logger.info(f"All messages processed after {processed_messages}. Exiting...")
                    await asyncio.sleep(2)  # Add delay for graceful shutdown
                    break
    finally:
        # Close connection
        await rabbitmq_manager.close()
        await pool.close()


if __name__ == "__main__":
    try:
        asyncio.run(process_queue(batch_mode=app_config.data.batch_data.batch_mode))
    except KeyboardInterrupt:
        pprint(" Exiting... ")
        sys.exit(0)
