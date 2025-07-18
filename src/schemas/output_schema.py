from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

from src.schemas import BaseSchema, BaseWithSerializerSchema, Float


class PredOutput(BaseSchema):
    """Schema for the output of the model."""

    person_id: str | None = Field(default=None, description="Unique identifier for the person.")
    survived: int = Field(default=0, description="Survival status of the passenger.")
    probability: Float = Field(default=0.0, description="Probability of the passenger surviving.")


class ModelOutput(BaseWithSerializerSchema):
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


class APITaskStatusSchema(BaseModel):
    """
    Data schema for task status.

    Parameters
    ----------
    task_id : str
        Task id
    status : Literal["PENDING", "STARTED", "SUCCESS", "FAILURE"]
        Task status, default is "PENDING"
    result : dict[str, Any]
        Task result, default is an empty dictionary

    Methods
    -------
    serialize(self, value: Any) -> str
        Serialize task result to a string
    """

    task_id: str = Field(description="Task id")
    status: Literal["PENDING", "STARTED", "SUCCESS", "FAILURE"] = Field(default="PENDING", description="Task status")
    result: dict[str, Any] = Field(default_factory=dict, description="Task result")
