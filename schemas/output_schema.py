from typing import Literal
from pydantic import Field, field_validator

from .input_schema import BaseSchema


class ModelOutput(BaseSchema):
    """Schema for the output of the model."""

    status: Literal["success", "error"] = Field(
        default="success", description="Status of the response."
    )
    survived: int = Field(default=0, description="Survival status of the passenger.")
    probability: float = Field(
        default=0.0, description="Probability of the passenger surviving."
    )

    @field_validator("probability", mode="before")
    def round_probability(cls, v) -> float:
        if isinstance(v, float):
            return round(v, 2)
        return v
