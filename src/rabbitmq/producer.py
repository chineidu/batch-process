import asyncio
from pathlib import Path
from typing import Any

import polars as pl
from tqdm import tqdm

from config import app_config
from schemas import PersonSchema
from src import PACKAGE_PATH, create_logger
from src.ml.train import transform_age, transform_cat_column_to_lower, transform_id
from src.utils import create_path, download_file_from_gdrive_async

from .rabbitmq import rabbitmq_manager

logger = create_logger(name="RMQ_producer")


async def process_batch_data(file_path: str | Path, is_remote: bool = True) -> list[dict[str, Any]]:
    """Process batch data from a parquet file.

    Parameters
    ----------
    file_path : str | Path
        Path to the parquet file.
    is_remote : bool, optional
        Whether the file is remote, by default True

    Returns
    -------
    list[dict[str, Any]]
        List of dictionaries containing the processed data.
    """
    create_path(path=file_path)
    # Download the file from remote storage
    if is_remote:
        try:
            await download_file_from_gdrive_async(
                file_id=app_config.data.batch_data.remote_data_id,
                destination=file_path,
            )
            logger.info(f"File downloaded to {file_path!r}")
        except Exception as e:
            logger.error(f"Error downloading file: {e}")
            return []

    important_columns: list[str] = app_config.data.important_columns
    test_data: pl.LazyFrame = (
        pl.scan_parquet(file_path)
        .select(important_columns)
        .with_columns(
            transform_cat_column_to_lower("sex"),
            transform_age("age"),
            transform_cat_column_to_lower("embarked"),
        )
        .drop_nulls()
        .with_columns(
            transform_id("id"),
        )
    )
    return test_data.collect().to_dicts()


async def _get_batch_data() -> list[dict[str, Any]]:
    # Sleep for 5 seconds to allow RabbitMQ to start
    await asyncio.sleep(5)
    await rabbitmq_manager.connect()
    file_path: Path = PACKAGE_PATH / app_config.data.batch_data.download_path
    batch_data: list[dict[str, Any]] = await process_batch_data(
        file_path=file_path, is_remote=app_config.data.batch_data.is_remote
    )
    return batch_data


async def publish_messages() -> None:
    """Publish messages to RabbitMQ from batch data.

    Returns
    -------
    None
    """
    batch_data: list[dict[str, Any]] = await _get_batch_data()

    for data in (
        batch_data := tqdm(
            batch_data,
            desc="Processing batch data",
            unit="batch",
            total=len(batch_data),
        )  # type: ignore
    ):
        message: PersonSchema = PersonSchema(**data)

        await rabbitmq_manager.publish(message)


async def batch_publish_messages() -> None:
    """Publish messages to RabbitMQ from batch data.

    Returns
    -------
    None
    """
    batch_data: list[dict[str, Any]] = await _get_batch_data()

    for data in (
        batch_data := tqdm(
            batch_data,
            desc="Processing batch data",
            unit="batch",
            total=len(batch_data),
        )  # type: ignore
    ):
        message: PersonSchema = PersonSchema(**data)

        await rabbitmq_manager.publish(message)


if __name__ == "__main__":
    asyncio.run(publish_messages())
