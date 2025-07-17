import json
from datetime import datetime
from typing import Annotated, Any, Literal
from uuid import uuid4

from pydantic import BaseModel, BeforeValidator, ConfigDict, Field, field_serializer  # type: ignore
from pydantic.alias_generators import to_camel


def round_probability(value: float) -> float:
    """Round a float value to two decimal places.

    Returns:
        float: Rounded value.
    """
    if isinstance(value, float):
        return round(value, 2)
    return value


class BaseSchema(BaseModel):
    """Base schema class that inherits from Pydantic BaseModel.

    This class provides common configuration for all schema classes including
    camelCase alias generation, population by field name, and attribute mapping.
    """

    model_config: ConfigDict = ConfigDict(  # type: ignore
        alias_generator=to_camel,
        populate_by_name=True,
        from_attributes=True,
        arbitrary_types_allowed=True,
    )


Float = Annotated[float, BeforeValidator(round_probability)]


class PersonSchema(BaseSchema):
    """Schema for a person."""

    person_id: str | None = Field(default=None, description="Unique identifier for the person.")
    sex: Literal["male", "female"] = Field(description="Sex of the passenger.")
    age: Float = Field(description="Age of the passenger.")
    pclass: int = Field(description="Passenger class.")
    sibsp: int = Field(description="Number of siblings/spouses aboard.")
    parch: int = Field(description="Number of parents/children aboard.")
    fare: Float = Field(description="Fare paid for the ticket.")
    embarked: Literal["s", "c", "q"] = Field(description="Port of embarkation.")
    survived: int = Field(default=0, description="Survival status of the passenger.")
    created_at: datetime = Field(alias="createdAt", default_factory=datetime.now, description="Timestamp of the entry.")

    class Config:
        allow_population_by_field_name = True
        json_schema_extra = {
            "examples": [
                {
                    "person_id": "1",
                    "sex": "male",
                    "age": 22,
                    "pclass": 1,
                    "sibsp": 1,
                    "parch": 0,
                    "fare": 7.25,
                    "embarked": "s",
                }
            ]
        }


class MultiPersonsSchema(BaseSchema):
    """Schema for multiple people."""

    persons: list[PersonSchema] = Field(description="List of people.")


class TaskSchema(BaseSchema):
    """Data schema for task results."""

    task_id: str = Field(default_factory=lambda: uuid4().hex, description="Task id")
    task_name: str = Field(description="Task name")
    status: Literal["PENDING", "STARTED", "SUCCESS", "FAILURE"] = Field(default="PENDING", description="Task status")
    result: dict[str, Any] = Field(default_factory=dict, description="Task result")
    error_message: str = Field(default="", description="Error message")
    created_at: datetime = Field(default_factory=datetime.now, description="Creation time")
    completed_at: datetime | None = Field(default=None, description="Completion time")


class EmailSchema(BaseSchema):
    """Data schema for email data."""

    recipient: str = Field(description="The recipient")
    subject: str = Field(description="Email subject")
    body: str = Field(description="Email body")
    status: Literal["dispatched", "failed", "processing", "success"] = Field(
        default="processing", description="Email status"
    )
    created_at: datetime = Field(default_factory=datetime.now, description="Creation time")
    sent_at: datetime | None = Field(default=None, description="Time sent")


class JobProcessingSchema(BaseSchema):
    """Data schema for data processing job."""

    job_name: str = Field(description="The name of the job")
    input_data: str = Field(description="The input data")
    output_data: str = Field(description="The output data")
    processing_time: float = Field(description="The processing time")
    status: Literal["failed", "pending", "processing", "completed"] = Field(
        default="pending", description="Email status"
    )
    created_at: datetime = Field(default_factory=datetime.now, description="Creation time")
    completed_at: datetime | None = Field(default=None, description="Completion time")


class CeleryTasksLogSchema(BaseSchema):
    """Data schema for celery task logs."""

    task_id: str = Field(description="The task id")
    task_name: str | None = Field(default=None, description="The task name")
    status: Literal["PENDING", "STARTED", "SUCCESS", "FAILURE", "RETRY", "REVOKED"] = Field(
        default="PENDING", description="Task status"
    )
    updated_at: datetime | None = Field(default=None, description="Update time")
    args: Any | None = Field(default=None, description="Task arguments")
    kwargs: Any | None = Field(default=None, description="Task keyword arguments")
    result: str | None = Field(default=None, description="Task result")
    error: str | None = Field(default=None, description="Task error")

    @field_serializer("args", "kwargs", "result", "error")
    def serialize(self, value: Any) -> str:
        """Serializes datetime fields to ISO format."""
        if isinstance(value, datetime):
            return value.isoformat()
        return json.dumps(value)
