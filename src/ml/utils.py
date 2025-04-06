from typing import Any
import numpy as np
import numpy.typing as npt
import pandas as pd
import polars as pl

from schemas import ModelOutput, PersonSchema


def record_to_dataframe(record: PersonSchema) -> pl.DataFrame:
    return pl.DataFrame([record.model_dump()])


def get_prediction(
    record: PersonSchema,
    model_dict: dict[str, Any],
) -> float:
    """Get prediction for a single record."""

    data: pl.DataFrame = record_to_dataframe(record)
    data_features: pl.DataFrame = (
        model_dict["processor"].transform(data).drop(["num_vars__survived"])
    )
    y_pred: npt.NDArray[np.float64] = model_dict["model"].predict_proba(data_features)[:, 1]
    data = data.with_columns(probability=y_pred).with_columns(
        survived=(pl.col("probability") > 0.5).cast(pl.Int64)
    )
    output: ModelOutput = ModelOutput(**(data.to_dicts()[0]))
    return output
