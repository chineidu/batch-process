import asyncio
import sys
from pathlib import Path
from pprint import pprint
from typing import Any

import joblib

from schemas import ModelOutput, PersonSchema
from src import PACKAGE_PATH, create_logger
from src.db_utils import insert_data_async
from src.ml.utils import get_prediction
from src.rabbitmq import rabbitmq_manager

logger = create_logger(name="RMQ_consumer")


async def main() -> None:
    model_dict_fp: Path = PACKAGE_PATH / "models/model.pkl"
    with open(model_dict_fp, "rb") as f:
        model_dict = joblib.load(f)

    async def prediction_callback(
        message: dict[str, Any], model_dict: dict[str, Any] = model_dict
    ) -> None:
        record: PersonSchema = PersonSchema(**message)
        result: ModelOutput = await asyncio.to_thread(
            get_prediction,  # type: ignore
            record,
            model_dict,  # type: ignore
        )
        result_dict: str = result.model_dump_json(by_alias=True)
        await insert_data_async(data=result_dict)
        logger.info(f"Inserted data with id {record.id!r} into database.")
        return None

    await rabbitmq_manager.connect()
    await rabbitmq_manager.consume(callback=prediction_callback)  # type: ignore
    await asyncio.Future()  # run forever

    # Close connection
    await rabbitmq_manager.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pprint(" Exiting... ")
        sys.exit(0)
