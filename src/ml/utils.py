from typing import Any
import numpy as np
import numpy.typing as npt
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
    features: npt.NDArray[np.float64] = model_dict["processor"].transform(data)
    data_features: pl.DataFrame = pl.DataFrame(
        features, schema=model_dict["processor"].get_feature_names_out().tolist()
    ).drop(["num_vars__survived"])

    y_pred: npt.NDArray[np.float64] = model_dict["model"].predict_proba(data_features)[
        :, 1
    ]
    data = data.with_columns(probability=y_pred).with_columns(
        survived=(pl.col("probability") > 0.5).cast(pl.Int64)
    )
    data_dict: dict[str, Any] = data.to_dicts()[0]
    data_dict["id"] = record.id
    output: ModelOutput = ModelOutput(data=data_dict)
    return output
