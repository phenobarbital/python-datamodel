# cython: language_level=3, embedsignature=True, boundscheck=False, wraparound=True, initializedcheck=False
# Copyright (C) 2018-present Jesus Lara
#
"""DataModel Exceptions."""
cdef class ModelException(Exception):
    """Base class for other exceptions"""

## Other Errors:
cdef class ValidationError(ModelException):
    pass

cdef class ParserError(ModelException):
    pass
