import asyncio
import sys
from pathlib import Path
from pprint import pprint
from typing import Any

import aiosqlite
import joblib

from config import app_settings
from schemas import ModelOutput, PersonSchema
from src import PACKAGE_PATH, create_logger
from src.ml.utils import get_prediction
from src.rabbitmq import rabbitmq_manager
from src.utils import (
    async_timer,
    init_database_async,
    insert_data_async,
    insert_dlq_data_async,
)

logger = create_logger(name="RMQ_consumer")


@async_timer
async def main() -> None:
    """
    Main function to process messages from RabbitMQ queue and make predictions.

    This function initializes the model, sets up database connection, and processes
    messages from both main queue and dead letter queue (DLQ).

    Returns
    -------
    None
    """
    model_dict_fp: Path = PACKAGE_PATH / "models/model.pkl"
    with open(model_dict_fp, "rb") as f:
        model_dict = joblib.load(f)

    # Processed message counter and event completion flag
    processed_messages: int = 0
    processing_completed: asyncio.Event = asyncio.Event()

    conn: aiosqlite.Connection = await init_database_async()

    async def queue_is_empty() -> bool:
        """
        Check if the RabbitMQ queue is empty.

        Returns
        -------
        bool
            True if queue is empty and at least one message has been processed,
            False otherwise or in case of error.
        """
        try:
            # Check if the queue exists
            queue = await rabbitmq_manager.channel.declare_queue(  # type: ignore
                name=app_settings.RABBITMQ_DIRECT_EXCHANGE,
                durable=True,
                passive=True,  # Set to True to check if the queue exists
            )
            return processed_messages > 0 and queue.declaration_result.message_count == 0

        except Exception as e:
            logger.error(f"Error checking queue status: {e}")
            return False

    async def prediction_callback(
        message: dict[str, Any], model_dict: dict[str, Any] = model_dict
    ) -> None:
        """
        Process incoming messages and make predictions.

        Parameters
        ----------
        message : dict[str, Any]
            The message containing person data to process
        model_dict : dict[str, Any]
            The loaded model dictionary for making predictions

        Returns
        -------
        None
        """
        nonlocal processed_messages

        record: PersonSchema = PersonSchema(**message)
        result: ModelOutput = await asyncio.to_thread(
            get_prediction,  # type: ignore
            record,
            model_dict,  # type: ignore
        )
        result_dict: str = result.model_dump_json(by_alias=True)
        await insert_data_async(conn=conn, data=result_dict, logger=logger)
        logger.info(f"Inserted data with id {record.id!r} into database.")
        processed_messages += 1

        # Check if all messages have been processed (empty queue)
        # set the event flag to signal completion
        if await queue_is_empty():
            processing_completed.set()
            logger.info(f"All messages processed. Total messages: {processed_messages}")
        return None

    async def dlq_callback(
        message: dict[str, Any], model_dict: dict[str, Any] = model_dict
    ) -> None:
        """
        Process messages from the dead letter queue.

        Parameters
        ----------
        message : dict[str, Any]
            The message from DLQ to process
        model_dict : dict[str, Any]
            The loaded model dictionary (unused in DLQ processing)

        Returns
        -------
        None
        """
        record: PersonSchema = PersonSchema(**message)
        await insert_dlq_data_async(conn=conn, data=record.model_dump_json(), logger=logger)
        logger.info(f"Inserted DLQ data with id {record.id!r} into database.")
        return None

    await rabbitmq_manager.connect()
    await rabbitmq_manager.consume(callback=prediction_callback)  # type: ignore
    await rabbitmq_manager.consume_dlq(callback=dlq_callback)  # type: ignore

    try:
        while not processing_completed.is_set():
            try:
                await asyncio.wait_for(processing_completed.wait(), timeout=5)
            except asyncio.TimeoutError:
                if await queue_is_empty():
                    logger.info(f"All messages processed after {processed_messages}. Exiting...")
                    break
    finally:
        # Close connection
        await rabbitmq_manager.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pprint(" Exiting... ")
        sys.exit(0)
