import json
from datetime import datetime
from typing import Annotated, Any, Literal
from uuid import uuid4

from pydantic import BaseModel, BeforeValidator, ConfigDict, Field  # type: ignore
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

    id: str | None = Field(default=None, description="Unique identifier for the person.")
    sex: Literal["male", "female"] = Field(description="Sex of the passenger.")
    age: Float = Field(description="Age of the passenger.")
    pclass: int = Field(description="Passenger class.")
    sibsp: int = Field(description="Number of siblings/spouses aboard.")
    parch: int = Field(description="Number of parents/children aboard.")
    fare: Float = Field(description="Fare paid for the ticket.")
    embarked: Literal["s", "c", "q"] = Field(description="Port of embarkation.")
    survived: int = Field(default=0, description="Survival status of the passenger.")
    timestamp: datetime = Field(default_factory=datetime.now, description="Timestamp of the entry.")


class MultiPersonsSchema(BaseSchema):
    """Schema for multiple people."""

    persons: list[PersonSchema] = Field(description="List of people.")


class TaskSchema(BaseModel):
    """Data schema for task results."""

    task_id: str = Field(default_factory=lambda: uuid4().hex, description="Task id")
    task_name: str = Field(description="Task id")
    status: Literal["pending", "completed"] = Field(default="pending", description="Task status")
    result: dict[str, Any] = Field(default_factory=dict, description="Task result")
    error_message: str = Field(default="", description="Error message")
    created_at: datetime = Field(default_factory=datetime.now, description="Creation time")
    completed_at: str | None = Field(default=None, description="Completion time")

    def to_data_model_dict(self) -> dict[str, Any]:
        """Converts the task schema to a dictionary that can be inserted into the database."""
        return json.loads(self.model_dump_json())


class EmailSchema(BaseModel):
    """Data schema for email data."""

    recipient: str = Field(description="The recipient")
    subject: str = Field(description="Email subject")
    body: str = Field(description="Email body")
    status: Literal["dispatched", "failed", "processing", "sent"] = Field(
        default="processing", description="Email status"
    )
    created_at: datetime = Field(default_factory=datetime.now, description="Creation time")
    sent_at: str | None = Field(default=None, description="Time sent")

    def to_data_model_dict(self) -> dict[str, Any]:
        """Converts the task schema to a dictionary that can be inserted into the database."""
        return json.loads(self.model_dump_json())


class DataProcessingSchema(BaseModel):
    """Data schema for data processing job."""

    job_name: str = Field(description="The name of the ejob")
    input_data: str = Field(description="The input data")
    output_data: str = Field(description="The output data")
    processing_time: float = Field(description="The processing time")
    status: Literal["failed", "pending", "processing", "completed"] = Field(
        default="pending", description="Email status"
    )
    created_at: datetime = Field(default_factory=datetime.now, description="Creation time")
    completed_at: str | None = Field(default=None, description="Completion time")

    def to_data_model_dict(self) -> dict[str, Any]:
        """Converts the task schema to a dictionary that can be inserted into the database."""
        return json.loads(self.model_dump_json())
