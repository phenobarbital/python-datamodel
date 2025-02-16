# cython: language_level=3, embedsignature=True, boundscheck=False, wraparound=True, initializedcheck=False
# Copyright (C) 2018-present Jesus Lara
#
from typing import get_args, get_origin, Union, Optional
from collections.abc import Iterable
from libcpp cimport bool as bool_t
from cpython.object cimport (
    PyObject_IsInstance,
    PyObject_IsSubclass,
    PyObject_HasAttr,
)
from uuid import UUID
import asyncpg.pgproto.pgproto as pgproto
from decimal import Decimal
import datetime
import types
from functools import partial
from dataclasses import _MISSING_TYPE


cpdef bool_t is_iterable(object value):
    """Returns True if value is an iterable."""
    if isinstance(value, Iterable) and not isinstance(value, (str, bytes)):
        return True
    return False


cpdef bool_t is_primitive(object value):
    """Returns True if value is a primitive type."""
    return value in (
        int,
        float,
        str,
        UUID,
        pgproto.UUID,
        Decimal,
        bool,
        bytes,
        datetime.date,
        datetime.datetime,
        datetime.time,
        datetime.timedelta
    )


cpdef bool_t is_dataclass(object obj):
    """Returns True if obj is a dataclass or an instance of a
    dataclass."""
    cls = obj if isinstance(obj, type) and not isinstance(obj, types.GenericAlias) else type(obj)
    return PyObject_HasAttr(cls, '__dataclass_fields__')


cpdef bool_t is_function(object value):
    """Returns True if value is a function."""
    return isinstance(value, (types.BuiltinFunctionType, types.FunctionType, partial))


cpdef bool_t is_callable(object value):
    """Returns True if value is a callable object."""
    if value is None or value == _MISSING_TYPE:
        return False
    if is_function(value):
        return callable(value)
    return False

cpdef bool_t is_empty(object value):
    cdef bool_t result = False
    if value is None:
        return True
    if isinstance(value, _MISSING_TYPE) or value == _MISSING_TYPE:
        result = True
    elif isinstance(value, str) and value == '':
        result = True
    elif isinstance(value, (int, float)) and value == 0:
        result = False
    elif isinstance(value, dict) and value == {}:
        result = False
    elif isinstance(value, (list, tuple, set)) and value == []:
        result = False
    elif not value:
        result = True
    return result
