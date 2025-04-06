import asyncio
from pathlib import Path
import sys
from typing import Any

import joblib

from schemas import ModelOutput, PersonSchema
from src.ml.utils import get_prediction
from src.rabbitmq import rabbitmq_manager
from src import PACKAGE_PATH


async def main() -> None:

    model_dict_fp: Path = PACKAGE_PATH / "models/model.pkl"
    with open(model_dict_fp, "rb") as f:
        model_dict = joblib.load(f)

    async def prediction_callback(
        message: dict[str, Any], model_dict: dict[str, Any] = model_dict
    ) -> None:
        record: PersonSchema = PersonSchema(**message)
        result: ModelOutput = await asyncio.to_thread(
            get_prediction, record, model_dict
        )
        result_dict: dict[str, Any] = result.model_dump_json(by_alias=True)
        print(result_dict)
        return None

    await rabbitmq_manager.connect()
    await rabbitmq_manager.consume(callback=prediction_callback)
    await asyncio.Future()  # run forever


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print(" Exiting...")
        sys.exit(0)
