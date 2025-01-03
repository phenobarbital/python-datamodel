# cython: language_level=3, embedsignature=True, boundscheck=False, wraparound=True, initializedcheck=False
# Copyright (C) 2018-present Jesus Lara
#
cdef class ModelException(Exception):
    """Base class for other Data-Model exceptions"""

    def __init__(self, str message, **kwargs):
        super().__init__(message)
        self.stacktrace = None
        if 'stacktrace' in kwargs:
            self.stacktrace = kwargs['stacktrace']
        self.message = message
        self.args = kwargs

    def __repr__(self):
        return f"{self.message}"

    def __str__(self):
        return f"{self.message!s}"

    def get(self):
        return self.message

cdef class ValidationError(ModelException):
    """Validation Error."""
    def __init__(self, str message, dict payload = None):
        super().__init__(message)
        self.payload = payload or {}

    def __str__(self):
        base = super().__str__()
        if self.payload:
            # collect the keys that had errors
            field_names = ", ".join(self.payload.keys())
            # attach them to the base message so we see them in the final str
            return f"{base} (Fields with errors: {field_names})"
        else:
            return base

cdef class ParsingError(ModelException):
    """Parsing Error."""
    def __init__(self, str message):
        message = f'Parsing Error: {message}'
        super().__init__(message)

cdef class ParserError(ModelException):
    """Parsing Error."""
    def __init__(self, str message):
        message = f'Parsing Error: {message}'
        super().__init__(message)
