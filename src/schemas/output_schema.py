from datetime import datetime
from typing import Literal

from pydantic import Field

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
