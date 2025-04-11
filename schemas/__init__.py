from schemas.input_schema import BaseSchema, Float, MultiPersonsSchema, PersonSchema  # type: ignore
from schemas.output_schema import ModelOutput, MultiPredOutput, PredOutput  # type: ignore

__all__: list[str] = [
    "BaseSchema",
    "Float",
    "PersonSchema",
    "PredOutput",
    "ModelOutput",
    "MultiPersonsSchema",
    "MultiPredOutput",
]
