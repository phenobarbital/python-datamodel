# cython: language_level=3, embedsignature=True, boundscheck=False, wraparound=True, initializedcheck=False
# Copyright (C) 2018-present Jesus Lara
#
from typing import get_args, get_origin, Union, Optional
import typing
import inspect
from libcpp cimport bool as bool_t
from enum import Enum
import pendulum
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


cpdef bool_t is_instanceof(object value, type annotated_type):
    if annotated_type.__module__ == 'typing':
        return True # TODO: validate subscripted generic (typing extensions)
    elif value in (pendulum.Date, pendulum.Time, pendulum.DateTime):
        # check if is a pendulum instance:
        return issubclass(value, (datetime.date, datetime.time, datetime.datetime, pendulum.Date, pendulum.Time, pendulum.DateTime))
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

cpdef list _validation(object F, str name, object value, object annotated_type, object val_type, str field_type):
    if not annotated_type:
        annotated_type = F.type
    elif isinstance(annotated_type, Field):
        annotated_type = annotated_type.type
    errors = []

    # first: calling (if exists) custom validator:
    fn = F.metadata.get('validator', None)
    if fn is not None:
        if is_callable(fn):
            try:
                result = fn(F, value)
                if not result:
                    error_msg = f"Validator {fn!r} Failed: {result}"
                    errors.append(
                        _create_error(name, value, error_msg, val_type, annotated_type)
                    )
            except (ValueError, AttributeError, TypeError) as e:
                error_msg = f"Validator {fn!r} Failed: {result}"
                errors.append(
                    _create_error(name, value, error_msg, val_type, annotated_type, e)
                )
    # check: data type hint
    try:
        # If field_type is known, short-circuit certain checks
        if field_type == 'primitive':
            # For primitives, just check if val_type matches annotated_type
            if annotated_type == datetime.date:
                if not (isinstance(value, datetime.date) or isinstance(value, pendulum.Date)):
                    errors.append(
                        _create_error(name, value, f'Invalid Date type, expected {annotated_type}', val_type, annotated_type)
                    )
            elif annotated_type == datetime.datetime:
                if not (isinstance(value, datetime.datetime) or isinstance(value, pendulum.DateTime)):
                    errors.append(
                        _create_error(name, value, f'Invalid DateTime type, expected {annotated_type}', val_type, annotated_type)
                    )
            elif val_type != annotated_type:
                errors.append(
                    _create_error(name, value, f'Invalid type, expected {annotated_type}', val_type, annotated_type)
                )
        elif annotated_type == Text:
            if val_type != str:
                errors.append(
                    _create_error(name, value, f'invalid type for {annotated_type}.{name}, expected {annotated_type}', val_type, annotated_type)
                )
        elif hasattr(annotated_type, '__module__') and annotated_type.__module__ == 'typing':
            # TODO: validation of annotated types
            return errors
        # elif type(annotated_type) is ModelMeta:
        elif type(annotated_type).__name__ == "ModelMeta":
            # Check if there's a field in the annotated type that matches the name and type
            if isinstance(value, annotated_type):
                # if value is already a User, no further check needed for columns
                return errors
            try:
                field = annotated_type.get_column(name)
                ftype = field.type
                if ftype <> val_type:
                    errors.append(
                        _create_error(name, value, f'invalid type for {annotated_type}.{name}, expected {ftype}', val_type, annotated_type)
                    )
            except AttributeError as e:
                errors.append(
                    _create_error(name, value, f'{annotated_type} has no column {name}', val_type, annotated_type, e)
                )
            except Exception as e:
                errors.append(
                    _create_error(name, value, f'Error validating {annotated_type}.{name}', val_type, annotated_type, e)
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
                errors.append(
                    _create_error(name, value, f'invalid type for {annotated_type}.{name}, expected {t}', val_type, annotated_type)
                )
        elif inspect.isclass(annotated_type) and issubclass(annotated_type, Enum):
            # Enum validation
            enum_values = [e.value for e in annotated_type]
            val = value.value if isinstance(value, annotated_type) else value
            if val not in enum_values:
                error_msg = f"Value {value} is not a valid option for {annotated_type}. Valid options: {enum_values}"
                errors.append(
                    _create_error(name, value, error_msg, val_type, annotated_type)
                )
        elif annotated_type is UUID:
            if not isinstance(value, (UUID, pgproto.UUID)):
                errors.append(
                    _create_error(name, value, f'invalid type for {annotated_type}.{name}, expected {annotated_type}', val_type, annotated_type)
                )
        elif val_type != annotated_type:
            instance = is_instanceof(value, annotated_type)
            if not instance:
                errors.append(
                    _create_error(name, value, "Instance Type", val_type, annotated_type)
                )
    except (TypeError, ValueError) as e:
        error_msg = f"Value type {val_type} does not match expected type {annotated_type}."
        errors.append(
            _create_error(name, value, error_msg, val_type, annotated_type, e)
        )
    return errors

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
