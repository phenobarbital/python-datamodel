# cython: language_level=3, embedsignature=True
# Copyright (C) 2018-present Jesus Lara
#
cdef class ModelException(Exception):
    """Base class for other Data-Model exceptions"""
    def __init__(self, str message, *args):
        if not message:
            message = f"{args!s}"
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

    def get(self):
        return self.message

cdef class ValidationError(Exception):
    """Validation Error."""

    def __init__(self, str message, *args, object payload = None):
        self.payload = payload
        super().__init__(message)


class ParsingError(ModelException):
    """Parsing Error."""

    def __init__(self, message: str, *args: list) -> None:
        message = f'Parsing Error: {message}'
        super().__init__(message)
