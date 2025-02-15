# cython: language_level=3, embedsignature=True, boundscheck=False, wraparound=True, initializedcheck=False
# Copyright (C) 2018-present Jesus Lara
#
from typing import get_args, get_origin, Union, Optional
from collections.abc import Callable, Awaitable
import typing
import asyncio
import inspect
from libcpp cimport bool as bool_t
from cpython.object cimport PyObject_IsInstance, PyObject_IsSubclass
from cpython.type cimport PyType_Check
from enum import Enum
from decimal import Decimal
import datetime
from uuid import UUID
import asyncpg.pgproto.pgproto as pgproto
from .types import uint64_min, uint64_max, Text
from .fields import Field
from .functions import (
    is_iterable,
    is_primitive,
    is_dataclass,
    is_function,
    is_callable,
    is_empty
)


cdef str valid_int(object field, str name, object value, object _type):
    # Basic check for integer type.
    if not isinstance(value, int):
        return f"Field {name} expected an integer, got {value!r} of type {type(value).__name__}"
    return None

cdef str valid_float(object field, str name, object value, object _type):
    if not isinstance(value, (float, int)):  # sometimes ints are allowed
        return f"Field {name} expected a float, got {value!r} of type {type(value).__name__}"
    return None

cdef str valid_str(object field, str name, object value, object _type):
    if not isinstance(value, str):
        return f"Field {name} expected a string, got {value!r} of type {type(value).__name__}"
    return None

cdef str valid_uuid(object field, str name, object value, object _type):
    if not isinstance(value, (UUID, pgproto.UUID)):
        return f"Field {name} expected a UUID, got {value!r} of type {type(value).__name__}"
    return None

cdef str valid_boolean(object field, str name, object value, object _type):
    if not isinstance(value, bool):
        return f"Field {name} expected a boolean, got {value!r} of type {type(value).__name__}"
    return None

cdef str valid_date(object field, str name, object value, object _type):
    if not isinstance(value, datetime.date):
        return f"Field {name} expected a date, got {value!r} of type {type(value).__name__}"
    return None

cdef str valid_datetime(object field, str name, object value, object _type):
    if isinstance(value, datetime.datetime):
        return None
    if isinstance(value, datetime.date):
        return None
    return f"Field {name} expected a datetime, got {value!r} of type {type(value).__name__}"

cdef str valid_timedelta(object field, str name, object value, object _type):
    if not isinstance(value, datetime.timedelta):
        return f"Field {name} expected a timedelta, got {value!r} of type {type(value).__name__}"
    return None

cdef str valid_time(object field, str name, object value, object _type):
    if not isinstance(value, datetime.time):
        return f"Field {name} expected a time, got {value!r} of type {type(value).__name__}"
    return None

cdef str valid_decimal(object field, str name, object value, object _type):
    if not isinstance(value, Decimal):
        return f"Field {name} expected a Decimal, got {value!r} of type {type(value).__name__}"
    return None


# List of Validators (primitive types):
validators = {
    str: valid_str,
    int: valid_int,
    float: valid_float,
    UUID: valid_uuid,
    pgproto.UUID: valid_uuid,
    bool: valid_boolean,
    datetime.date: valid_date,
    datetime.datetime: valid_datetime,
    datetime.timedelta: valid_timedelta,
    datetime.time: valid_time,
    Decimal: valid_decimal,
    Text: valid_str
}


cdef inline bint is_enum_class(object annotated_type):
    cdef int res
    # First, check if annotated_type is a type
    if not PyType_Check(annotated_type):
        return False
    # Then check if it is a subclass of Enum.
    res = PyObject_IsSubclass(annotated_type, <object>Enum)
    if res < 0:
        # If an error occurred, you might want to raise an exception.
        raise RuntimeError("Error in PyObject_IsSubclass")
    return res != 0

cdef bool_t is_instanceof(object value, type annotated_type):
    if annotated_type.__module__ == 'typing':
        return True # TODO: validate subscripted generic (typing extensions)
    elif value in (datetime.date, datetime.time, datetime.datetime):
        # check if is a pendulum instance:
        return issubclass(value, (datetime.date, datetime.time, datetime.datetime))
    else:
        try:
            return isinstance(value, annotated_type)
        except (AttributeError, TypeError, ValueError) as e:
            raise TypeError(
                f"{e}"
            )

cpdef bool_t is_optional_type(object annotated_type):
    if get_origin(annotated_type) is Union:
        return type(None) in get_args(annotated_type)
    return False

cdef object get_primary_key_field(object annotated_type, str name, object field_meta):
    for f in annotated_type.__dataclass_fields__.values():
        if name == f.name:
            return f
        if field_meta.get('alias') == f.name:
            return f
        if f.metadata.get('primary_key', False):
            return f
    return None

cpdef dict _validation(
    object F,
    str name,
    object value,
    object annotated_type,
    object val_type,
    str field_type,
    bint as_objects=False
):
    cdef bint _valid = False
    cdef object field_meta = F.metadata
    cdef dict error = {}

    if not annotated_type:
        annotated_type = F.type
    elif isinstance(annotated_type, Field):
        annotated_type = annotated_type.type

    if fn := F.metadata.get('validator', None):
        try:
            result = fn(F, value, annotated_type, val_type)
            if result is False:
                msg = f"Validation failed for *{name}*: {value} with result: {result}"
                return _create_error(name, value, msg, val_type, annotated_type)
        except ValueError:
            raise
    # check: data type hint
    # If field_type is known, short-circuit certain checks
    if F.type == Text:
        if val_type != str:
            return _create_error(name, value, f'invalid type for {annotated_type}.{name}, expected {annotated_type}', val_type, annotated_type)
        return {}
    # if inspect.isclass(annotated_type) and issubclass(annotated_type, Enum):
    if is_enum_class(annotated_type):
        return validate_enum(name, value, annotated_type, val_type)
    if F.origin is Callable:
        if not is_callable(value):
            return _create_error(name, value, f'Invalid function type, expected {annotated_type}', val_type, annotated_type)
        return {}
    elif F.origin is Awaitable:
        if asyncio.iscoroutinefunction(value):
            return  _create_error(name, value, f"Field '{name}': provided coroutine function is not awaitable; call it to obtain a coroutine object.", val_type, annotated_type)
        # Otherwise, check if it is awaitable
        elif not hasattr(value, '__await__'):
            return _create_error(name, value, f"Field '{name}': provided object is not awaitable; it does not have an '__await__' method. but got {type(value)}.", val_type, annotated_type)
        return {}
    elif field_type == 'type':
        return validate_type(F, name, value, annotated_type, val_type)
    elif field_type == 'typing' or hasattr(annotated_type, '__module__') and annotated_type.__module__ == 'typing':
        if F.origin is tuple:
            # Check if we are in the homogeneous case: Tuple[T, ...]
            if len(F.args) == 2 and F.args[1] is Ellipsis:
                for i, elem in enumerate(value):
                    if not isinstance(elem, F.args[0]):
                        return _create_error(
                            f"{name}[{i}]",
                            elem,
                            f"Invalid type at index {i}: expected {F.args[0]}",
                            type(elem), F.args[0]
                        )
            else:
                if len(value) != len(F.args):
                    return _create_error(name, value, f"Invalid length for {annotated_type}.{name}, expected {len(F.args)} elements", val_type, annotated_type)
                else:
                    for i, elem in enumerate(value):
                        if not isinstance(elem, F.args[i]):
                            return _create_error(
                                f"{name}[{i}]",
                                elem,
                                f"Invalid type at index {i}: expected {F.args[i]}",
                                type(elem), F.args[i]
                            )
        # Handle Optional Types:
        elif F.origin is Union and type(None) in F.args:
            inner_types = [t for t in F.args if t is not type(None)]
            # If value is None then that is valid:
            if value is None:
                return {}
            # Otherwise check that value is an instance of at least one inner type:
            for t in inner_types:
                base_type = get_origin(t) or t
                if isinstance(value, base_type):
                    _valid = True
                    break
            if not _valid:
                return _create_error(name, value, f"Invalid type for {annotated_type}.{name}, expected one of {inner_types}", val_type, annotated_type)
    elif type(annotated_type).__name__ == "ModelMeta":
        # Check if there's a field in the annotated type that matches the name and type
        if as_objects:
            if isinstance(value, annotated_type):
                # if value is already a Object, no further check needed for columns
                return {}
            try:
                field = annotated_type.get_column(name)
            except AttributeError as e:
                return _create_error(name, value, f'{annotated_type} has no column {name}', val_type, annotated_type, e)
            ftype = field.type
            if ftype <> val_type:
                return _create_error(name, value, f"Invalid type for {annotated_type}.{name}, expected {ftype}", val_type, annotated_type)
        else:
            # Validate primary key
            pk_field = get_primary_key_field(annotated_type, name, field_meta)
            if pk_field:
                pk_type = pk_field.type
                if not isinstance(value, pk_type):
                    return _create_error(
                        name,
                        value,
                        f"Invalid type for {annotated_type}.{pk_field.name}, expected {pk_type}",
                        val_type,
                        pk_type
                    )
    elif is_optional_type(annotated_type):
        inner_types = get_args(annotated_type)
        for t in inner_types:
            if t is type(None) and value is None:
                break
            elif is_instanceof(val_type, t):
                break
            elif val_type == t:
                break
        else:
            return _create_error(name, value, f"Invalid type for {annotated_type}.{name}, expected one of {inner_types}", val_type, annotated_type)
    elif val_type != annotated_type:
        instance = is_instanceof(value, annotated_type)
        if not instance:
            return _create_error(name, value, f"Invalid Instance for {annotated_type}.{name}, expected {annotated_type}", val_type, annotated_type)
    return error

cdef dict _create_error(str name, object value, object error, object val_type, object annotated_type, object exception = None):
    return {
        "field": name,
        "value": value,
        "error": error,
        "value_type": val_type,
        "annotation": annotated_type,
        "exception": exception
    }

# Define a validator function for uint64
def validate_uint64(value: int) -> None:
    """Validate uint64 values.
    """
    if value < uint64_min or value > uint64_max:
        raise ValueError(f"{value} is not a valid uint64")

cdef dict validate_type(object F, object name, object value, object annotated_type, object val_type):
    """
    Validate that 'value' is of type 'annotated_type'.
    If 'annotated_type' is a Union, checks if 'value' is an instance of any of the union types.
    Returns None if valid; otherwise, returns an error object via _create_error.
    """
    if not isinstance(value, type):
        return _create_error(name, value, f'Invalid type for {annotated_type}.{name}, expected a type', val_type, annotated_type)
    inner_types = get_args(F.args[0])
    for allowed in inner_types:
        if value is allowed:
            return {}
    expected = ', '.join([str(t) for t in F.args])
    return _create_error(name, value, f'Invalid type for {annotated_type}.{name}, expected a type of {expected}', val_type, annotated_type)

cdef dict validate_enum(object name, object value, object annotated_type, object val_type):
    """
    Validate that 'value' is a valid member of the enum 'annotated_type'.
    If 'value' is an instance of 'annotated_type', use its .value.
    Cache the allowed enum values on the enum type to avoid repeated introspection.
    Returns None if valid; otherwise, returns an error object via _create_error.
    """
    cdef object val = value.value if PyObject_IsInstance(value, annotated_type) else value
    cdef object enum_values = [e.value for e in annotated_type]
    if val not in enum_values:
        return _create_error(
            name, value, f"Invalid value for {annotated_type}.{name}, expected one of {enum_values}", val_type, annotated_type
        )
    return {}
