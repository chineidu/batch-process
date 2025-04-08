import asyncio
from pathlib import Path
from typing import Any

import numpy as np
import polars as pl
from tqdm import tqdm

from config import app_config
from schemas import PersonSchema
from src import PACKAGE_PATH
from src.ml.train import transform_age, transform_cat_column_to_lower, transform_id

from .rabbitmq import rabbitmq_manager


def process_batch_data(file_path: str | Path) -> list[dict[str, Any]]:
    """
    Process batch data from a Parquet file by applying transformations and generating IDs.

    Returns
    -------
    list[dict[str, Any]]
        Processed data containing transformed columns and generated IDs.
    """
    important_columns: list[str] = app_config.data.important_columns
    test_data: pl.DataFrame = (
        pl.read_parquet(file_path)
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
    return test_data.to_dicts()


async def publish_message(message: PersonSchema) -> None:
    await rabbitmq_manager.connect()
    # Simulate a long processing time
    delay: float = np.random.uniform(0.8, 2)
    await asyncio.sleep(delay)
    await rabbitmq_manager.publish(message)


def main() -> None:
    file_path: Path = PACKAGE_PATH / app_config.data.batch_data_path
    batch_data: list[dict[str, Any]] = process_batch_data(file_path=file_path)

    for data in (
        batch_data := tqdm(
            batch_data,
            desc="Processing batch data",
            unit="batch",
            total=len(batch_data),
        )
    ):
        message: PersonSchema = PersonSchema(**data)
        asyncio.run(publish_message(message=message))


if __name__ == "__main__":
    main()
