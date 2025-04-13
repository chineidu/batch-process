from typing import Any

import numpy as np
import numpy.typing as npt
import polars as pl

from schemas import ModelOutput, MultiPersonsSchema, MultiPredOutput, PersonSchema


def record_to_dataframe(record: PersonSchema) -> pl.DataFrame:
    """Convert a PersonSchema record to a Polars DataFrame.

    Parameters
    ----------
    record : PersonSchema
        Input record containing person data.

    Returns
    -------
    pl.DataFrame
        Polars DataFrame containing the person data.
    """
    if isinstance(record, PersonSchema):
        return pl.from_records([record])
    return pl.from_records(record.persons)


def _get_prediction(
    record: PersonSchema | MultiPersonsSchema,
    model_dict: dict[str, Any],
) -> list[dict[str, Any]]:
    """Process a single record and return predictions.

    Parameters
    ----------
    record : PersonSchema | MultiPersonsSchema
        Input record containing person or multiple person data.
    model_dict : dict[str, Any]
        Dictionary containing model and processor objects.

    Returns
    -------
    list[dict[str, Any]]
        List of dictionaries containing predictions and features.
    """
    data: pl.DataFrame = record_to_dataframe(record)  # type: ignore
    # return data
    features: npt.NDArray[np.float64] = model_dict["processor"].transform(data)
    data_features: pl.DataFrame = pl.DataFrame(
        features, schema=model_dict["processor"].get_feature_names_out().tolist()
    ).drop(["num_vars__survived"])

    y_pred: npt.NDArray[np.float64] = model_dict["model"].predict_proba(data_features)[:, 1]
    data = data.with_columns(probability=y_pred).with_columns(  # type: ignore
        survived=(pl.col("probability") > 0.5).cast(pl.Int64)
    )
    data_dict: list[dict[str, Any]] = data.to_dicts()
    return data_dict


def get_prediction(
    record: PersonSchema,
    model_dict: dict[str, Any],
) -> ModelOutput:
    """Get prediction for a single record.

    Parameters
    ----------
    record : PersonSchema
        Input record containing person data.
    model_dict : dict[str, Any]
        Dictionary containing model and processor objects.

    Returns
    -------
    ModelOutput
        Model prediction output containing features and predictions.
    """
    data_dict: dict[str, Any] = _get_prediction(record, model_dict)[0]
    output: ModelOutput = ModelOutput(data=data_dict)  # type: ignore
    return output


def get_batch_prediction(
    record: MultiPersonsSchema,
    model_dict: dict[str, Any],
) -> MultiPredOutput:
    """Get predictions for multiple records.

    Parameters
    ----------
    record : MultiPersonsSchema
        Input records containing multiple person data.
    model_dict : dict[str, Any]
        Dictionary containing model and processor objects.

    Returns
    -------
    MultiPredOutput
        Model prediction output containing features and predictions for multiple records.
    """
    data_dict: list[dict[str, Any]] = _get_prediction(record, model_dict)
    output: MultiPredOutput = MultiPredOutput(
        outputs=[ModelOutput(**{"data": row}) for row in data_dict]  # type: ignore
    )
    return output
