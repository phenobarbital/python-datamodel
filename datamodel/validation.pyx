# cython: language_level=3, embedsignature=True, boundscheck=False, wraparound=True, initializedcheck=False
# Copyright (C) 2018-present Jesus Lara
#
from libcpp cimport bool
from dataclasses import _MISSING_TYPE
from functools import partial


cpdef bool is_callable(object value):
    if value is None:
        return False
    is_missing = (value == _MISSING_TYPE)
    return callable(value) if not is_missing else False


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

cdef bool is_function(object value):
    return isinstance(value, (types.BuiltinFunctionType, types.FunctionType, partial))

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
        print('VALIDATION ', val_type, annotated_type)
        if annotated_type.__module__ == 'typing':
            # TODO: validation of annotated types
            pass
        elif F.metadata['required'] is False or F.metadata['nullable'] is True:
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
