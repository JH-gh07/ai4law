from typing import Any, TypeVar

from pydantic import BaseModel, ValidationError

ModelT = TypeVar("ModelT", bound=BaseModel)


class SchemaValidationError(ValueError):
    """Raised when payload does not pass schema validation."""


def validate_model(data: dict[str, Any], model_cls: type[ModelT]) -> ModelT:
    try:
        return model_cls.model_validate(data)
    except ValidationError as exc:
        raise SchemaValidationError(str(exc)) from exc
