from datetime import datetime
from typing import Annotated, Literal
from pydantic import Field

from schemas import BaseSchema, Float


class PredOutput(BaseSchema):
    """Schema for the output of the model."""

    id: str | None = Field(
        default=None, description="Unique identifier for the person."
    )
    survived: int = Field(default=0, description="Survival status of the passenger.")
    probability: Float = Field(
        default=0.0, description="Probability of the passenger surviving."
    )


class ModelOutput(BaseSchema):
    """Schema for the output of the model."""

    status: Literal["success", "error"] = Field(
        default="success", description="Status of the response."
    )
    timestamp: datetime = Field(
        default_factory=datetime.now, description="Timestamp of the response."
    )
    data: PredOutput | None = Field(default=None, description="Prediction output.")
