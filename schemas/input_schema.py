# type: ignore
from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, BeforeValidator
from pydantic.alias_generators import to_camel

def round_probability(value: float) -> float:
    if isinstance(value, float):
        return round(value, 2)
    return value

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
Float = Annotated[float, BeforeValidator(round_probability)]

class PersonSchema(BaseSchema):
    sex: Literal["male", "female"] = Field(description="Sex of the passenger.")
    age: Float = Field(description="Age of the passenger.")
    pclass: int = Field(description="Passenger class.")
    sibsp: int = Field(description="Number of siblings/spouses aboard.")
    parch: int = Field(description="Number of parents/children aboard.")
    fare: Float = Field(description="Fare paid for the ticket.")
    embarked: Literal["s", "c", "q"] = Field(description="Port of embarkation.")
    survived: int = Field(default=0, description="Survival status of the passenger.")
