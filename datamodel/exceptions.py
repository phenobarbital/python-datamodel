"""
Base Exceptions for DataModel.
"""
from dataclasses import dataclass
from typing import (
    Optional,
    Union,
    Any
)


class ModelException(Exception):
    """Base class for other exceptions"""
    message: str = ''

    def __init__(self, message: str, *args: list) -> None:
        self.args = (
            message,
            *args
        )
        self.message = message
        super().__init__(message)

    def __repr__(self):
        return f"{__name__}({self.args!r})"

    def __str__(self):
        return f"{__name__}: {self.message}"


class ValidationError(ModelException):
    """Validation Error."""

    def __init__(self, message: str, *args: list) -> None:
        message = f'Validator Error: {message}'
        super().__init__(message)


class ParsingError(ModelException):
    """Parsing Error."""

    def __init__(self, message: str, *args: list) -> None:
        message = f'Parsing Error: {message}'
        super().__init__(message)


@dataclass
class ValidationModel:
    """
    Class for Error validation on DataModels.
    """
    field: str
    value: Optional[Union[str, Any]]
    error: str
    value_type: Any
    annotation: type
    exception: Optional[Exception]
