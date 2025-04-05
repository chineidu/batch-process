# type: ignore
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator
from pydantic.alias_generators import to_camel


class BaseSchema(BaseModel):
    """Base schema class that inherits from Pydantic BaseModel.

    This class provides common configuration for all schema classes including
    camelCase alias generation, population by field name, and attribute mapping.
    """

    model_config: ConfigDict = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        from_attributes=True,
        arbitrary_types_allowed=True,
    )


class PersonSchema(BaseSchema):
    sex: Literal["male", "female"] = Field(description="Sex of the passenger.")
    age: float = Field(description="Age of the passenger.")
    pclass: int = Field(description="Passenger class.")
    sibsp: int = Field(description="Number of siblings/spouses aboard.")
    parch: int = Field(description="Number of parents/children aboard.")
    fare: float = Field(description="Fare paid for the ticket.")
    embarked: str = Field(description="Port of embarkation.")
    survived: int = Field(default=0, description="Survival status of the passenger.")
