# cython: language_level=3, embedsignature=True, boundscheck=False, wraparound=True, initializedcheck=False
# Copyright (C) 2018-present Jesus Lara
#
from libcpp cimport bool
from dataclasses import _MISSING_TYPE
from functools import partial
import types
from .types import uint64_min, uint64_max

cpdef is_dataclass(object obj):
    """Returns True if obj is a dataclass or an instance of a
    dataclass."""
    cls = obj if isinstance(obj, type) and not isinstance(obj, types.GenericAlias) else type(obj)
    return hasattr(cls, '__dataclass_fields__')

cdef bool is_function(object value):
    return isinstance(value, (types.BuiltinFunctionType, types.FunctionType, partial))

cpdef bool is_callable(object value):
    if value is None or value == _MISSING_TYPE:
        return False
    if is_function(value):
        return callable(value)
    return False

cpdef bool is_empty(object value):
    cdef bool result = False
    if value is None:
        return True
    if isinstance(value, _MISSING_TYPE) or value == _MISSING_TYPE:
        result = True
    elif isinstance(value, str) and value == '':
        result = True
    elif not value:
        result = True
    return result

cpdef bool is_instanceof(object value, type annotated_type):
    if annotated_type.__module__ == 'typing':
        return True # TODO: validate subscripted generic (typing extensions)
    else:
        try:
            return isinstance(value, annotated_type)
        except (AttributeError, TypeError, ValueError) as e:
            raise TypeError(
                f"{e}"
            )

def validator(object F, str name, object value, object annotated_type):
    val_type = type(value)
    if not annotated_type:
        annotated_type = F.type
    errors = []
    # first: calling (if exists) custom validator:
    if 'validator' in F.metadata:
        fn = F.metadata['validator']
        if is_callable(fn):
            try:
                result = fn(F, value)
                if not result:
                    errors.append({
                        "field": name,
                        "value": value,
                        "error": f"Validator {fn!r}: {result}",
                        "value_type": val_type,
                        "annotation": annotated_type,
                        "exception": None
                    })
            except (ValueError, AttributeError, TypeError) as e:
                errors.append({
                    "field": name,
                    "value": value,
                    "error": f"Validator {fn!r}",
                    "value_type": val_type,
                    "annotation": annotated_type,
                    "exception": e
                })
    # check: data type hint
    try:
        if annotated_type.__module__ == 'typing':
            # TODO: validation of annotated types
            pass
        elif hasattr(F, 'required'):
            if F.required() is False or F.nullable() is True:
                if value is None:
                    pass
        elif is_function(val_type):
            pass # value will be calculated.
        elif val_type <> annotated_type:
            instance = is_instanceof(value, annotated_type)
            if not instance:
                errors.append({
                    "field": name,
                    "value": value,
                    "error": "Instance Type",
                    "value_type": val_type,
                    "annotation": annotated_type,
                    "exception": None
                })
        else:
            return errors
    except (TypeError, ValueError) as e:
        errors.append({
            "field": name,
            "value": value,
            "error": "Instance Type",
            "value_type": val_type,
            "annotation": annotated_type,
            "exception": e
        })
    return errors

# Define a validator function for uint64
def validate_uint64(value: int) -> None:
    """Validate uint64 values.
    """
    if value < uint64_min or value > uint64_max:
        raise ValueError(f"{value} is not a valid uint64")
