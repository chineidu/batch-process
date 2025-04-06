from typing import Annotated, Literal
from pydantic import Field

from schemas import BaseSchema, Float


class ModelOutput(BaseSchema):
    """Schema for the output of the model."""

    status: Literal["success", "error"] = Field(
        default="success", description="Status of the response."
    )
    survived: int = Field(default=0, description="Survival status of the passenger.")
    probability: Float = Field(
        default=0.0, description="Probability of the passenger surviving."
    )
