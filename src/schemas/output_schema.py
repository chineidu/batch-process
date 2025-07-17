from datetime import datetime
from typing import Literal

from pydantic import Field, field_serializer

from src.schemas import BaseSchema, Float


class PredOutput(BaseSchema):
    """Schema for the output of the model."""

    person_id: str | None = Field(default=None, description="Unique identifier for the person.")
    survived: int = Field(default=0, description="Survival status of the passenger.")
    probability: Float = Field(default=0.0, description="Probability of the passenger surviving.")


class ModelOutput(BaseSchema):
    """Schema for the output of the model."""

    data: PredOutput | None = Field(default=None, description="Prediction output.")
    status: Literal["success", "error"] = Field(description="Status of the response.")
    created_at: datetime = Field(default_factory=datetime.now, description="Timestamp of the response.")

    @field_serializer("created_at")
    def serialize_created_at(self, value: datetime) -> str:
        """
        Serializes the created_at field to ISO format.

        Parameters
        ----------
        value : datetime
            The datetime object to serialize.

        Returns
        -------
        str
            The serialized datetime object as a string in ISO format.
        """
        return value.isoformat()


class MultiPredOutput(BaseSchema):
    """Schema for the output of the model."""

    outputs: list[ModelOutput] = Field(  # type: ignore
        default_factory=list, description="List of prediction outputs."
    )


# ====== API ENDPOINTS ======
class HealthCheck(BaseSchema):
    """
    Health check response model.
    """

    status: str = "healthy"
    version: str = "0.1.0"
