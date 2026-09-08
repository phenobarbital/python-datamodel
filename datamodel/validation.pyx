# cython: language_level=3, embedsignature=True, initializedcheck=False
# Copyright (C) 2018-present Jesus Lara
#
from typing import get_args, get_origin, Union, Optional, Literal
from collections.abc import Callable, Awaitable
import typing
import asyncio
import inspect
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
# NOTE (FEAT-2/TASK-16 review): `is_empty` is declared `cpdef` in
# functions.pxd, so cimporting it for a direct C call in `fastpath_kind` looks
# attractive -- and a code review raised exactly that. It does not compile:
# functions.pxd declares its return type via `from libcpp cimport bool as
# bool_t`, and functions.pyx is built with language="c++" (setup.py:51-54)
# while validation.pyx is built with language="c" (setup.py:45-47). Cimporting
# across that boundary fails with "unknown type name 'bool'". Acting on it
# would mean changing setup.py or functions.pxd, both outside this scope.


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

# ===========================================================================
# FEAT-2 / TASK-11 -- conservative per-field validation policy
# ===========================================================================
#
# PRIVATE CONTRACT (consumed by the gated-loop task, TASK-13).  Nothing here
# changes which validators execute: `_validation` does not consult a policy in
# this task.  This module only *precomputes* what work a field could possibly
# require, so a later task can gate the generic loop cheaply.
#
# The rules that make this safe:
#
# * A policy is only ever built for an **exactly supported scalar** field: its
#   annotated type must be one of the built-in scalar types AND the field's
#   cached validator must be *identically* the built-in we shipped for that
#   type.  Identity is checked against `_BUILTIN_VALIDATORS`, a snapshot taken
#   at import time -- never against a function's display name, and never
#   against the public, mutable `validators` mapping, so replacing an entry
#   there cannot make a foreign function look "known".
# * Anything unknown, dynamic, custom-Field, descriptor-backed or non-scalar
#   yields `None`, the LEGACY policy, meaning "do all the work".  `None` is the
#   safe default, so a field that was never visited behaves exactly as before.
# * Only the *shape* of constraints is recorded (which keys are present), never
#   their values, and never anything from Meta or from a live metadata mapping.
#   Constraint values stay live and must still be read at validation time.
# * `policy_is_current()` re-derives the identities and the constraint shape and
#   returns False on any drift, so a parser/validator/type swap or a metadata
#   mutation performed inside a callback can never leave a stale permanent
#   "skip" decision behind.
# * A policy holds only references the Field already holds (its type and its
#   cached callables) and lives on the Field itself, so it is collected with
#   the class.  There is no global registry and no per-instance storage: no
#   instance values, default results or errors are ever kept here.

#: Work-mask bits.  A set bit means "this kind of work may be required".
POLICY_WORK_TYPE_CHECK = 0x01
POLICY_WORK_CONSTRAINTS = 0x02
POLICY_WORK_CUSTOM_VALIDATOR = 0x04
POLICY_WORK_ALL = 0x07

#: Snapshot of the validators we shipped, taken before any user code can run.
#: Identity comparisons use this, not the mutable public `validators` mapping.
_BUILTIN_VALIDATORS = dict(validators)

#: Metadata keys `_validate_constraints` reads for each supported category.
_CONSTRAINT_KEYS_STR = ('length', 'min_length', 'max_length', 'pattern')
_CONSTRAINT_KEYS_NUMERIC = ('min', 'max')
#: Field attributes `_validate_constraints` reads directly.
_CONSTRAINT_ATTRS_STR = ('_pattern',)
_CONSTRAINT_ATTRS_NUMERIC = ('gt', 'lt', 'ge', 'le', 'eq', 'ne')

_NUMERIC_TYPES = (int, float, Decimal)

#: Shared, immutable 'no constraints' shape.
_EMPTY_CONSTRAINT_SHAPE = frozenset()


cdef class FieldPolicy:
    """Immutable, precomputed description of a field's possible validation work.

    Private to datamodel.  Never exposed on a dataclass field, never
    serialised, and never part of the public API.
    """

    cdef readonly unsigned int work_mask
    cdef readonly object type_ref
    cdef readonly object validator_ref
    cdef readonly object parser_ref
    cdef readonly frozenset constraint_shape
    cdef readonly bint exact_scalar

    def __cinit__(
        self,
        unsigned int work_mask,
        object type_ref,
        object validator_ref,
        object parser_ref,
        frozenset constraint_shape,
        bint exact_scalar,
    ):
        self.work_mask = work_mask
        self.type_ref = type_ref
        self.validator_ref = validator_ref
        self.parser_ref = parser_ref
        self.constraint_shape = constraint_shape
        self.exact_scalar = exact_scalar

    def __repr__(self):
        return (
            "FieldPolicy(work_mask=0x%02x, exact_scalar=%r, constraints=%r)"
            % (self.work_mask, bool(self.exact_scalar), sorted(self.constraint_shape))
        )


cdef frozenset _constraint_shape(object field, object annotated_type):
    """The *names* of constraints present, never their values."""
    cdef list present = []
    cdef object metadata
    cdef object value

    try:
        metadata = field.metadata
    except AttributeError:
        return frozenset()

    if annotated_type is str or annotated_type is Text:
        keys = _CONSTRAINT_KEYS_STR
        attrs = _CONSTRAINT_ATTRS_STR
    elif annotated_type in _NUMERIC_TYPES:
        keys = _CONSTRAINT_KEYS_NUMERIC
        attrs = _CONSTRAINT_ATTRS_NUMERIC
    else:
        keys = ()
        attrs = ()

    for key in keys:
        try:
            value = metadata.get(key, None)
        except (AttributeError, TypeError):
            # A metadata mapping that cannot be read is a reason to be
            # conservative, not a reason to assume there are no constraints.
            return None
        if value is not None:
            present.append(key)

    for key in attrs:
        value = getattr(field, key, None)
        if value is not None:
            present.append('@' + key)

    # A custom validator callback is part of the shape: adding one later must
    # invalidate the policy.
    try:
        if metadata.get('validator', None) is not None:
            present.append('@@validator')
    except (AttributeError, TypeError):
        return None

    if not present:
        # Most fields carry no constraints at all. frozenset is immutable, so a
        # single shared empty instance is safe and avoids an allocation per
        # field at class creation.
        return _EMPTY_CONSTRAINT_SHAPE
    return frozenset(present)


cpdef object build_field_policy(object field, object annotated_type):
    """Build a conservative policy, or return None for the legacy behaviour.

    Returning ``None`` is always safe: it means "this field gets the full,
    unchanged treatment".  A policy is only produced when every identity we
    depend on is exactly what we shipped.
    """
    cdef object builtin
    cdef frozenset shape
    cdef unsigned int mask

    if field is None or annotated_type is None:
        return None

    # Only exact, non-subclassed scalar types are eligible.  `type(x) is not T`
    # for a subclass, so a str subclass or an IntEnum never qualifies.
    if not isinstance(annotated_type, type):
        return None
    if annotated_type not in _BUILTIN_VALIDATORS:
        return None

    # The field must be a plain datamodel Field, not a user subclass whose
    # behaviour we cannot reason about.
    if type(field) is not Field:
        return None

    # It must be categorised as a primitive: that is the only category for
    # which `_validation` reaches `_validate_constraints`.
    if getattr(field, '_type_category', None) != 'primitive':
        return None

    # The cached validator must be *identically* the built-in for this type.
    builtin = _BUILTIN_VALIDATORS.get(annotated_type, None)
    if builtin is None:
        return None
    if getattr(field, 'validator', None) is not builtin:
        return None

    shape = _constraint_shape(field, annotated_type)
    if shape is None:
        return None

    mask = POLICY_WORK_TYPE_CHECK
    if shape:
        mask |= POLICY_WORK_CONSTRAINTS
    if '@@validator' in shape:
        mask |= POLICY_WORK_CUSTOM_VALIDATOR

    return FieldPolicy(
        mask,
        annotated_type,
        builtin,
        getattr(field, 'parser', None),
        shape,
        True,
    )


cpdef bint policy_is_current(object field, object policy):
    """True only when every identity the policy relied on still holds.

    Callers MUST consult this before acting on a policy.  It re-derives the
    constraint shape, so a metadata mutation performed inside a callback
    invalidates the policy instead of leaving a stale decision in place.
    """
    cdef FieldPolicy plan

    if policy is None or field is None:
        return False
    if not isinstance(policy, FieldPolicy):
        return False

    plan = <FieldPolicy> policy

    if type(field) is not Field:
        return False
    if getattr(field, 'type', None) is not plan.type_ref:
        return False
    if getattr(field, 'validator', None) is not plan.validator_ref:
        return False
    if getattr(field, 'parser', None) is not plan.parser_ref:
        return False
    if _BUILTIN_VALIDATORS.get(plan.type_ref, None) is not plan.validator_ref:
        return False
    if getattr(field, '_type_category', None) != 'primitive':
        return False

    return _constraint_shape(field, plan.type_ref) == plan.constraint_shape


cpdef object field_policy(object field):
    """The policy attached to ``field``, or None. Never raises."""
    return getattr(field, '_policy', None)


# ---------------------------------------------------------------------------
# FEAT-2 / TASK-13 -- the gate, and its diagnostic-only counter
# ---------------------------------------------------------------------------

cdef extern from *:
    """
    /* Diagnostic dispatch counting is OFF unless a profiling build defines
       this macro (see tests/compatibility/profile_validation.py). Because it
       is a compile-time constant, the C compiler folds the guarded branch
       away entirely in a release build: there is no counter, and no test of
       a counter, in the default application flow. */
    #ifndef DATAMODEL_PROFILE_VALIDATION
    #define DATAMODEL_PROFILE_VALIDATION 0
    #endif
    """
    int DATAMODEL_PROFILE_VALIDATION

cdef long _generic_dispatches = 0


cdef void count_generic_dispatch() noexcept:
    """Record one generic `_validation_` dispatch. Compiled out in release."""
    global _generic_dispatches
    if DATAMODEL_PROFILE_VALIDATION:
        _generic_dispatches += 1


cpdef bint profiling_compiled_in():
    """True only in a build made with -DDATAMODEL_PROFILE_VALIDATION=1."""
    return DATAMODEL_PROFILE_VALIDATION != 0


cpdef long generic_dispatch_count():
    """Generic dispatches counted so far. Always 0 in a release build."""
    return _generic_dispatches


cpdef void reset_generic_dispatch_count():
    global _generic_dispatches
    _generic_dispatches = 0


#: `fastpath_kind` results.
FASTPATH_NONE = 0         # fall back to the legacy `_validation_`
FASTPATH_COMPLETE = 1     # all required work is provably done; skip
FASTPATH_CONSTRAINTS = 2  # skip, but run `_validate_constraints` first


cdef int fastpath_kind(object f, object value, object annotated_type) except -1:
    """Decide whether narrow inline checks can replace `_validation_`.

    This mirrors **exactly** the branch `_validation_` takes for a field that
    carries a cached built-in validator:

        error = f.validator(f, name, value, _type)   # None for an exact type
        if not error and _type in (str, int, float):
            return _validate_constraints(...)
        return None

    Every assumption below is a cheap pointer comparison; anything unexpected
    returns ``FASTPATH_NONE`` and the legacy path runs completely unchanged.

    Deliberately NOT used here: `policy_is_current()`. It rebuilds the
    constraint shape as a frozenset, which would cost more per field than the
    dispatch it is meant to avoid. It remains the full audit for callers that
    want the complete guarantee. Its constraint-shape half is unnecessary in
    this gate because the gate *always* runs `_validate_constraints` live for
    the three types whose constraints the legacy route honours -- so a
    constraint added at runtime is read, never skipped.
    """
    cdef FieldPolicy plan
    cdef object policy = getattr(f, '_policy', None)

    if policy is None:
        return FASTPATH_NONE
    # Checked cast. `Field` is a plain Python class with __slots__, so `_policy`
    # is externally writable; an unchecked <FieldPolicy> would reinterpret an
    # arbitrary object's pointer. `policy_is_current` guards with isinstance for
    # the same reason -- this is the hot-path equivalent, and it costs one type
    # check against the pointer comparisons that follow.
    plan = <FieldPolicy?> policy

    # EXACT type identity, never isinstance: a subclass must keep the legacy
    # path, which may treat it differently.
    if type(value) is not plan.type_ref:
        return FASTPATH_NONE
    if annotated_type is not plan.type_ref:
        return FASTPATH_NONE

    # The cached validator and parser must still be the ones the policy saw;
    # a user may replace either at runtime.
    if f.validator is not plan.validator_ref:
        return FASTPATH_NONE
    if f.parser is not plan.parser_ref:
        return FASTPATH_NONE

    # `_validation_` routes empty/None values to `_field_checks_`, which
    # enforces primary-key, required, db_default and nullable rules. Those
    # must never be skipped. NOTE: is_empty(0) and is_empty(False) are both
    # False -- 0 and False are values, not absence -- so numeric zero and
    # boolean false still take the fast path, as they must.
    if is_empty(value):
        return FASTPATH_NONE

    # `_validation_` also diverts when the value *is* the annotated type.
    if value is annotated_type:
        return FASTPATH_NONE

    # The legacy route honours constraints only for these three types; for
    # every other scalar it returns immediately after the validator. Preserve
    # that exactly, including the quirk that a Decimal min/max is ignored here.
    if annotated_type is str or annotated_type is int or annotated_type is float:
        return FASTPATH_CONSTRAINTS
    return FASTPATH_COMPLETE

cdef dict _create_error(str name, object value, object error, object val_type, object annotated_type, object exception = None):
    return {
        "field": name,
        "value": value,
        "error": error,
        "value_type": val_type,
        "annotation": annotated_type,
        "exception": exception
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

cdef bint is_instanceof(object value, type annotated_type):
    """
    Check if value is an instance of annotated_type, handling typing objects properly.
    For generic types (List[int], etc.), just check against the base container type.
    """
    # Get origin type for generics
    origin = get_origin(annotated_type)

    # If it's a typing module type like List[int], Dict[str, int], etc.
    if annotated_type.__module__ == 'typing':
        # For Union, check each option
        if origin is Union:
            args = get_args(annotated_type)
            return any(is_instanceof(value, arg) for arg in args if arg is not type(None)) or value is None and type(None) in args

        # For container types, check against base type
        elif origin in (list, tuple, set, frozenset, dict):
            container_map = {
                list: list,
                tuple: tuple,
                set: set,
                frozenset: frozenset,
                dict: dict
            }
            return isinstance(value, container_map.get(origin, object))

        # For other typing constructs, consider it valid (can be refined further)
        return True

    # For datetime types, use issubclass check
    elif value in (datetime.date, datetime.time, datetime.datetime):
        # Check if is a pendulum instance:
        return issubclass(value, (datetime.date, datetime.time, datetime.datetime))

    # For normal types, use isinstance
    else:
        try:
            return isinstance(value, annotated_type)
        except (AttributeError, TypeError, ValueError) as e:
            # For errors with subscripted generics, just return True
            if "subscripted generics" in str(e):
                return True
            raise TypeError(f"{e}")

cpdef bint is_optional_type(object annotated_type):
    """
    Check if annotated_type is an Optional type (Union[T, None]).
    """
    origin = get_origin(annotated_type)

    # If it's a Union, check if None is one of the options
    if origin is Union:
        args = get_args(annotated_type)
        return type(None) in args

    # For backward compatibility with Python 3.8
    # Check old-style Optional typing
    if hasattr(annotated_type, "__origin__") and annotated_type.__origin__ is Union:
        args = annotated_type.__args__
        return type(None) in args

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

cdef dict _validate_union_field(
    object F,           # Field object (your internal representation)
    str name,           # Field name
    object value,       # Actual runtime value
    object annotated_type  # The declared type (e.g. Union[str, List[str]], etc.)
):
    """
    Validates a complex or nested Union (including Optional and nested structures)
    Returns {} if validation passes, or a dict describing the error.
    """
    cdef object origin = get_origin(annotated_type)
    cdef tuple targs = get_args(annotated_type)
    cdef object subtype_origin = None
    cdef list errors = []
    cdef dict sub_error
    cdef tuple list_args = ()
    cdef object inner_type = None
    cdef list item_errors = []
    cdef tuple dict_args = ()
    cdef object key_type = None
    cdef object val_type = None

    # 1) Handle Optional (Union[..., None]) if present
    if type(None) in targs and value is None:
        return {}  # Valid because it's None

    # 2) Try each subtype in the Union
    for subtype in targs:
        # Skip NoneType if it isn't our value
        if subtype is type(None):
            continue

        subtype_origin = get_origin(subtype)

        try:
            # 2a) If there's no origin, it's a simple or direct type (str, int, custom class, etc.)
            if subtype_origin is None:
                # If it's just a normal type, check with isinstance
                if isinstance(value, subtype):
                    # PASS: we found a valid subtype
                    return {}
                # Not matching? We'll record an error & continue
                errors.append(f"Value is not instance of {subtype}")

            # 2b) If it's a nested Union, validate recursively
            elif subtype_origin is Union:
                sub_error = _validate_union_field(F, name, value, subtype)
                if not sub_error:
                    return {}  # success
                errors.append(f"Nested union check failed for {subtype}: {sub_error}")

            # 2c) If it's a list origin, e.g. List[str]
            elif subtype_origin is list:
                list_args = get_args(subtype)
                if not isinstance(value, list):
                    errors.append(f"Expected list, got {type(value).__name__}")
                else:
                    # Validate each item if you like (e.g. ensure each item is str)
                    inner_type = list_args[0]
                    item_errors = []
                    for idx, item in enumerate(value):
                        # For simple inner type
                        if get_origin(inner_type) is None:
                            if not isinstance(item, inner_type):
                                item_errors.append(f"Index {idx}: {type(item).__name__} != {inner_type}")
                        else:
                            # Possibly nested structure again
                            sub_error = _validate_union_field(F, f"{name}[{idx}]", item, inner_type)
                            if sub_error:
                                item_errors.append(str(sub_error))
                    if not item_errors:
                        return {}  # All items validated
                    errors.append(f"List item errors: {item_errors}")

            # 2d) If it's a dict origin, e.g. Dict[str, int] or Dict[str, Union[int, ...]]
            elif subtype_origin is dict:
                dict_args = get_args(subtype)  # (key_type, value_type)
                key_type = dict_args[0]
                val_type = dict_args[1]
                if not isinstance(value, dict):
                    errors.append(f"Expected dict, got {type(value).__name__}")
                else:
                    dict_errors = []
                    # Validate each key, value
                    for k, v in value.items():
                        # Check key
                        if not isinstance(k, key_type):
                            dict_errors.append(f"Key {k!r} type mismatch; expected {key_type}")
                        # Then check value
                        sub_error = _validate_union_field(F, f'{name}[\"{k}\"]', v, val_type)
                        if sub_error:
                            dict_errors.append(f"For key={k}: {sub_error}")
                    if not dict_errors:
                        return {}  # success
                    errors.append(f"Dict item errors: {dict_errors}")

            else:
                # If you have other complex type origins (tuple, etc.), handle them similarly
                errors.append(f"Unhandled type origin: {subtype_origin} for subtype={subtype}")

        except Exception as exc:
            errors.append(f"Exception in subtype {subtype}: {exc}")

    # 3) If no subtype matched, create an error record
    return _create_error(
        name,
        value,
        f"Invalid type for {annotated_type}.{name}, expected one of {targs}",
        type(value),
        annotated_type,
        errors
    )

cdef dict _validate_constraints(
    object field,
    str name,
    object value,
    object annotated_type,
    object val_type
):
    """
    Validates primitive field constraints based on field metadata.

    Handles the following validations:
    - For strings: length, min_length, max_length
    - For numbers: min, max, gt, lt, ge, le, eq

    Args:
        field: The Field object
        name: Field name
        value: The value to validate
        annotated_type: The annotated type
        val_type: The actual value type

    Returns:
        Empty dict if validation passes, error dict otherwise
    """
    # string comparisons
    cdef object length = None
    cdef object min_length = None
    cdef object max_length = None
    # integer/float comparisons
    cdef object min_val = None
    cdef object max_val = None
    cdef object ge_val = None
    cdef object le_val = None
    cdef object eq_val = None
    cdef object ne_val = None
    cdef object pattern = None
    # Skip validation if value is None
    if value is None:
        return {}

    metadata = field.metadata
    # NOTE (FEAT-2/TASK-12): there was an `error = {}` here. It was assigned on
    # every call and never read -- each failure path returns `_create_error(...)`,
    # which builds its own dict, and the success path returns a fresh `{}`. It
    # was therefore one dead dict allocation per primitive field per
    # construction. Removing it is unobservable: no branch, payload, message or
    # ordering depends on it.

    # String validations
    if annotated_type is str:
        length = metadata.get('length', None)
        min_length = metadata.get('min_length', None)
        max_length = metadata.get('max_length', None)
        pattern = metadata.get('pattern', getattr(field, '_pattern', None))
        # Length validation
        if length is not None and len(value) != length:
            return _create_error(
                name,
                value,
                f"String length must be exactly {length} characters, got {len(value)}",
                val_type,
                annotated_type
            )

        # Min length validation
        if min_length is not None and len(value) < min_length:
            return _create_error(
                name,
                value,
                f"String length must be at least {min_length} characters, got {len(value)}",
                val_type,
                annotated_type
            )

        # Max length validation
        if max_length is not None and len(value) > max_length:
            return _create_error(
                name,
                value,
                f"String length must be at most {max_length} characters, got {len(value)}",
                val_type,
                annotated_type
            )

        # Pattern validation
        if pattern is not None:
            import re
            if not re.match(pattern, value):
                return _create_error(
                    name,
                    value,
                    f"String does not match pattern {pattern}",
                    val_type,
                    annotated_type
                )

    # Numeric validations (int, float, Decimal)
    elif annotated_type in (int, float, Decimal):
        min_val = metadata.get('min', getattr(field, 'gt', None))
        max_val = metadata.get('max', getattr(field, 'lt', None))
        ge_val = getattr(field, 'ge', None)
        le_val = getattr(field, 'le', None)
        eq_val = getattr(field, 'eq', None)
        ne_val = getattr(field, 'ne', None)
        # Equal validation
        if eq_val is not None and value != eq_val:
            return _create_error(
                name,
                value,
                f"Value must be equal to {eq_val}",
                val_type,
                annotated_type
            )

        # Not equal validation
        if ne_val is not None and value == ne_val:
            return _create_error(
                name,
                value,
                f"Value must not be equal to {ne_val}",
                val_type,
                annotated_type
            )

        # Minimum value validation (greater than)
        if min_val is not None and value < min_val:  # inclusive
            return _create_error(
                name,
                value,
                f"Value must be greater than {min_val}",
                val_type,
                annotated_type
            )

        # Maximum value validation (less than)
        if max_val is not None and value > max_val:  # inclusive
            return _create_error(
                name,
                value,
                f"Value must be less than {max_val}",
                val_type,
                annotated_type
            )

        # Greater than or equal validation
        if ge_val is not None and value < ge_val:
            return _create_error(
                name,
                value,
                f"Value must be greater than or equal to {ge_val}",
                val_type,
                annotated_type
            )

        # Less than or equal validation
        if le_val is not None and value > le_val:
            return _create_error(
                name,
                value,
                f"Value must be less than or equal to {le_val}",
                val_type,
                annotated_type
            )

    # If we've made it here, all validations passed
    return {}

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
    # NOTE (FEAT-2/TASK-12): this used to be `cdef dict error = {}`, allocated
    # on entry but only ever returned by the final statement. Every early
    # return -- and there are many -- threw it away. The allocation now happens
    # at the point of return, so the success contract is unchanged: callers
    # still receive a FRESH, independently mutable dict, never a shared
    # singleton and never None.
    cdef list allowed_values = []

    if not annotated_type:
        annotated_type = F.type
    elif isinstance(annotated_type, Field):
        annotated_type = annotated_type.type
    # print('VAL > ', name, ' F ', F, ' VALUE > ', value)
    if fn := F.metadata.get('validator', None):
        try:
            result = fn(F, value, annotated_type, val_type)
            if result is False:
                msg = f"Validation failed for *{name}*: {value} with result: {result}"
                return _create_error(name, value, msg, val_type, annotated_type)
        except ValueError:
            raise
    # Check for primitive type constraints if the value is not None
    if F._type_category == 'primitive':
        errors = _validate_constraints(F, name, value, annotated_type, val_type)
        if errors:
            return errors
    # check: data type hint
    # If field_type is known, short-circuit certain checks
    if F.type == Text:
        if val_type != str:
            return _create_error(
                name,
                value,
                f'invalid type for {annotated_type}.{name}, expected {annotated_type}',
                val_type,
                annotated_type
            )
        return {}

    if is_enum_class(annotated_type):
        return validate_enum(name, value, annotated_type, val_type)

    if F.origin is Callable:
        if not is_callable(value):
            return _create_error(
                name, value, f'Invalid function type, expected {annotated_type}', val_type, annotated_type
            )
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

    elif F.origin is Literal:
        allowed_values = list(F.args)
        if value not in allowed_values:
            return _create_error(
                name,
                value,
                f"Invalid value for {annotated_type}.{name}, expected one of {allowed_values}",
                val_type,
                annotated_type
            )
        return {}

    # Handle Union (including Optional)
    elif F.origin is Union:
        # If None is allowed and value is None, it's valid
        if type(None) in F.args and value is None:
            return {}
        # return _validate_union_field(F, name, value, annotated_type)
    elif field_type == 'typing' or hasattr(annotated_type, '__module__') and annotated_type.__module__ == 'typing':
        if F.origin is tuple:
            tuple_args = F.args
            # Check if we are in the homogeneous case: Tuple[T, ...]
            if len(tuple_args) == 2 and tuple_args[1] is Ellipsis:
                element_type = tuple_args[0]
                for i, elem in enumerate(value):
                    # Can't use isinstance with generic types
                    elem_origin = get_origin(element_type)
                    if elem_origin is None:
                        if not isinstance(elem, element_type):
                            return _create_error(
                                f"{name}[{i}]",
                                elem,
                                f"Invalid type at index {i}: expected {element_type}",
                                type(elem), element_type
                            )
                    else:
                        if not is_instanceof(elem, element_type):
                            return _create_error(
                                f"{name}[{i}]",
                                elem,
                                f"Invalid type at index {i}: expected {element_type}",
                                type(elem), element_type
                            )
                    if not isinstance(elem, F.args[0]):
                        return _create_error(
                            f"{name}[{i}]",
                            elem,
                            f"Invalid type at index {i}: expected {F.args[0]}",
                            type(elem), F.args[0]
                        )
                return {}
            else:
                if len(value) != len(F.args):
                    return _create_error(name, value, f"Invalid length for {annotated_type}.{name}, expected {len(F.args)} elements", val_type, annotated_type)
                else:
                    for i, (elem, elem_type) in enumerate(zip(value, F.args)):
                        elem_origin = get_origin(elem_type)
                        if elem_origin is None and not isinstance(elem, elem_type):
                            return _create_error(
                                f"{name}[{i}]",
                                elem,
                                f"Invalid type at index {i}: expected {F.args[i]}",
                                type(elem), F.args[i]
                            )
                return {}
        elif F.origin is list:
            if not isinstance(value, list):
                return _create_error(
                    name,
                    value,
                    f"Invalid type for {annotated_type}.{name}, expected list",
                    val_type,
                    annotated_type
                )
            # List content validation is more complex and should be done in parsing
            return {}
        # For sets
        elif F.origin in (set, frozenset):
            if not isinstance(value, F.origin):
                return _create_error(
                    name,
                    value,
                    f"Invalid type for {annotated_type}.{name}, expected {F.origin}",
                    val_type,
                    annotated_type
                )
            return {}
        # For dictionaries
        elif F.origin is dict:
            if not isinstance(value, dict):
                return _create_error(
                    name,
                    value,
                    f"Invalid type for {annotated_type}.{name}, expected dict",
                    val_type,
                    annotated_type
                )
            return {}
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
                return _create_error(
                    name,
                    value,
                    f"Invalid type for {annotated_type}.{name}, expected one of {inner_types}",
                    val_type,
                    annotated_type
                )
    elif type(annotated_type).__name__ == "ModelMeta":
        # If value is already an instance of the expected type, it's valid
        if isinstance(value, annotated_type):
            return {}
        # Check if there's a field in the annotated type that matches the name and type
        if as_objects:
            try:
                field = annotated_type.get_column(name)
            except AttributeError as e:
                return _create_error(name, value, f'{annotated_type} has no column {name}', val_type, annotated_type, e)
            ftype = field.type
            if ftype <> val_type:
                return _create_error(
                    name,
                    value,
                    f"Invalid type for {annotated_type}.{name}, expected {ftype}",
                    val_type,
                    annotated_type
                )
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
            return _create_error(
                name,
                value,
                f"Invalid type for {annotated_type}.{name}, expected one of {inner_types}",
                val_type,
                annotated_type
            )
    elif val_type != annotated_type:
        instance = is_instanceof(value, annotated_type)
        if not instance:
            return _create_error(
                name,
                value,
                f"Invalid Instance for {annotated_type}.{name}, expected {annotated_type}",
                val_type,
                annotated_type
            )
    return {}

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
