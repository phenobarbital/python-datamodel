"""The FEAT-2 differential corpus: one :class:`Case` per observed behaviour.

A *case* is a pure description of "build this model with these arguments".  It
carries no expected values, because the oracle is the reference build, not a
hand-written literal — see spec §4.  What it does carry is enough metadata for
the runner to know *how* to observe the result (does it touch the shared
callback log?  is it expected to raise?).

Two invariants matter more than anything else here and are asserted by
``tests/compatibility/test_fixture_corpus.py``:

1. ``case.build()`` returns **fresh** mutable objects every call, so the
   reference run and the candidate run can never share, or observe, each
   other's mutations.
2. Aliases that are *inside* one payload are preserved across calls, because
   "these two fields received the same list object" is itself an observable
   property that a candidate must not change.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Callable, Dict, Tuple

from . import models as _models
from .models import (
    FROZEN_NOW,
    FROZEN_UUID,
    IntSubclass,
    StrSubclass,
)

#: Sentinel meaning "this case is expected to raise"; the runner still records
#: the exact exception type, message, payload and ``__cause__``.
EXPECT_OK = "ok"
EXPECT_ERROR = "error"


@dataclass(frozen=True)
class Case:
    """A single differential/performance scenario."""

    name: str
    model_name: str
    build: Callable[[], Dict[str, Any]]
    expect: str = EXPECT_OK
    tags: Tuple[str, ...] = ()
    notes: str = ""
    #: True when the case appends to ``models.hook_events``; the runner resets
    #: that log before the case and records it afterwards.
    observes_callbacks: bool = False
    #: Pairs of *payload paths* that must resolve to the same object.  A path
    #: is dot-separated and may address dict keys, e.g. ``"attributes.tags"``.
    aliased_args: Tuple[Tuple[str, str], ...] = ()
    #: Suitable for the paired timing harness (deterministic, no exception).
    benchmark: bool = False
    #: True when the case parses a date/datetime **from a string**.  With the
    #: ``rs_parsers`` extension absent, ``converters.pyx:199,236`` dereference
    #: ``rc.to_date``/``rc.to_datetime`` on a module that only defines
    #: ``HAS_RUST = False``, so the conversion fails.  That gap exists
    #: identically at the engineering reference (verified on
    #: ``d932c720``: same ``import datamodel.rs_parsers as rc`` call sites), so
    #: differential parity still holds -- but a local run without the extension
    #: cannot exercise these builds.
    requires_rust_parsers: bool = False

    def resolve_model(self) -> type:
        """Look the model class up by name in :mod:`.models`.

        Resolution is deliberately by *name*: the runner imports this module in
        a subprocess whose ``datamodel`` may be the reference or the candidate,
        so a class object captured at definition time would be the wrong one.
        """
        return getattr(_models, self.model_name)


# ---------------------------------------------------------------------------
# Payload builders.  Each returns a brand-new dict of brand-new mutables.
# ---------------------------------------------------------------------------


def _employee_raw() -> Dict[str, Any]:
    """Employee from all-string input -- examples/rust_benchmark.py:105-119."""
    return {
        "employee_id": "f47ac10b-58cc-4372-a567-0e02b2c3d479",
        "name": "Jesus Lara",
        "email": "jesuslara@jesuslara.com",
        "age": "42",
        "salary": "85000.50",
        "rating": "4.75",
        "active": "true",
        "hired_at": "2020-03-15",
        "updated_at": "2026-09-08T10:30:00",
        "skills": ["python", "rust", "cython"],
        "manager": "Ada Lovelace",
    }


def _employee_native() -> Dict[str, Any]:
    """Employee from already-typed input -- examples/rust_benchmark.py:122-135."""
    return {
        "employee_id": uuid.UUID("f47ac10b-58cc-4372-a567-0e02b2c3d479"),
        "name": "Jesus Lara",
        "email": "jesuslara@jesuslara.com",
        "age": 42,
        "salary": Decimal("85000.50"),
        "rating": 4.75,
        "active": True,
        "hired_at": date(2020, 3, 15),
        "updated_at": datetime(2026, 9, 8, 10, 30),
        "skills": ["python", "rust", "cython"],
        "manager": "Ada Lovelace",
    }


def _employee_shared_skills() -> Dict[str, Any]:
    """A payload with a deliberate intra-case alias.

    ``skills`` is the *same* list object that the caller also keeps under
    ``manager``-adjacent bookkeeping in real ORM hydration.  Here the alias is
    expressed between the payload's own entries so the runner can assert the
    relationship survives construction identically on both backends.
    """
    shared = ["python", "rust"]
    payload = _employee_native()
    payload["skills"] = shared
    payload["_alias_probe"] = shared  # popped by the runner; see aliased_args
    return payload


def _employee_missing_required() -> Dict[str, Any]:
    payload = _employee_native()
    del payload["name"]
    return payload


def _employee_age_below_min() -> Dict[str, Any]:
    payload = _employee_native()
    payload["age"] = 17
    return payload


def _employee_age_at_min() -> Dict[str, Any]:
    payload = _employee_native()
    payload["age"] = 18
    return payload


def _employee_age_at_max() -> Dict[str, Any]:
    payload = _employee_native()
    payload["age"] = 99
    return payload


def _employee_bad_uuid() -> Dict[str, Any]:
    payload = _employee_raw()
    payload["employee_id"] = "not-a-uuid"
    return payload


def _employee_null_optional() -> Dict[str, Any]:
    payload = _employee_native()
    payload["manager"] = None
    payload["updated_at"] = None
    return payload


def _unconstrained_native() -> Dict[str, Any]:
    return {
        "an_int": 42,
        "a_str": "hello",
        "a_float": 4.75,
        "a_bool": True,
        "a_decimal": Decimal("85000.50"),
        "a_uuid": uuid.UUID("f47ac10b-58cc-4372-a567-0e02b2c3d479"),
        "a_date": date(2020, 3, 15),
        "a_datetime": datetime(2026, 9, 8, 10, 30),
    }


def _unconstrained_raw() -> Dict[str, Any]:
    return {
        "an_int": "42",
        "a_str": "hello",
        "a_float": "4.75",
        "a_bool": "true",
        "a_decimal": "85000.50",
        "a_uuid": "f47ac10b-58cc-4372-a567-0e02b2c3d479",
        "a_date": "2020-03-15",
        "a_datetime": "2026-09-08T10:30:00",
    }


def _constrained_valid() -> Dict[str, Any]:
    return {
        "bounded_int": 42,
        "bounded_float": 4.75,
        "bounded_decimal": Decimal("500"),
        "sized_str": "hello",
        "patterned_str": "AB-1234",
    }


def _constrained_at_bounds() -> Dict[str, Any]:
    """Inclusive bounds: validation.pyx:427,437 accept the endpoints."""
    return {
        "bounded_int": 18,
        "bounded_float": 10.0,
        "bounded_decimal": Decimal("0"),
        "sized_str": "ab",
        "patterned_str": "ZZ-0000",
    }


def _constrained_int_too_low() -> Dict[str, Any]:
    payload = _constrained_valid()
    payload["bounded_int"] = 17
    return payload


def _constrained_str_too_long() -> Dict[str, Any]:
    payload = _constrained_valid()
    payload["sized_str"] = "far-too-long-for-this"
    return payload


def _constrained_pattern_mismatch() -> Dict[str, Any]:
    payload = _constrained_valid()
    payload["patterned_str"] = "ab-1234"
    return payload


def _constrained_multiple_errors() -> Dict[str, Any]:
    """Several invalid fields at once: pins error order and fall-through."""
    return {
        "bounded_int": 5,
        "bounded_float": 99.0,
        "bounded_decimal": Decimal("-1"),
        "sized_str": "x",
        "patterned_str": "nope",
    }


def _wide_native() -> Dict[str, Any]:
    payload: Dict[str, Any] = {}
    for name in _models.WIDE_FIELD_NAMES:
        if name.startswith("int_"):
            payload[name] = 7
        elif name.startswith("str_"):
            payload[name] = "value"
        elif name.startswith("float_"):
            payload[name] = 1.5
        elif name.startswith("bool_"):
            payload[name] = True
        else:
            payload[name] = Decimal("2.25")
    return payload


def _wide_raw() -> Dict[str, Any]:
    payload: Dict[str, Any] = {}
    for name in _models.WIDE_FIELD_NAMES:
        if name.startswith("int_"):
            payload[name] = "7"
        elif name.startswith("str_"):
            payload[name] = "value"
        elif name.startswith("float_"):
            payload[name] = "1.5"
        elif name.startswith("bool_"):
            payload[name] = "true"
        else:
            payload[name] = "2.25"
    return payload


def _client_with_object() -> Dict[str, Any]:
    """as_objects=True hydration with a nested model instance."""
    return {
        "client_id": 1,
        "client_name": "Client A",
        "status": True,
        "orgid": {"org_id": 1, "name": "Org A"},
        "org_name": "Org A Name",
    }


def _client_via_alias() -> Dict[str, Any]:
    """The nested field is supplied under its alias ``org_id``."""
    return {
        "client_id": 2,
        "client_name": "Client B",
        "status": True,
        "org_id": {"org_id": 2, "name": "Org B"},
        "org_name": "Org B Name",
    }


def _client_bad_nested() -> Dict[str, Any]:
    payload = _client_with_object()
    payload["orgid"] = "Arenas"
    return payload


def _container_full() -> Dict[str, Any]:
    return {
        "name": "container",
        "addresses": [
            {"street": "123 Main St", "zipcode": 12345},
            {"street": "456 Side St", "zipcode": 67890},
        ],
        "accounts": [
            {"provider": "email", "address": {"street": "1 A St", "zipcode": 1}},
            {"provider": "sms", "address": None},
        ],
        "tags": ["a", "b", "c"],
        "attributes": {"example": "value", "count": 3},
        "directives": ("23.1", 12.8),
        "supported": ("1.0", 2.0, "3.0"),
        "example": {"a": "hello", "b": 123},
    }


def _container_shared_list() -> Dict[str, Any]:
    """``tags`` and ``attributes['tags']`` are the same list object."""
    shared = ["x", "y"]
    return {
        "name": "shared",
        "addresses": [],
        "accounts": [],
        "tags": shared,
        "attributes": {"tags": shared},
        "directives": (1.0, 2.0),
        "supported": (1.0,),
        "example": {"a": "hello"},
    }


def _container_empty() -> Dict[str, Any]:
    return {"name": "empty"}


def _aliased_payload() -> Dict[str, Any]:
    return {"id": 7, "displayName": "Ada", "plain": "kept"}


def _aliased_canonical() -> Dict[str, Any]:
    """Same record supplied under the canonical names instead of aliases."""
    return {"record_id": 7, "display_name": "Ada", "plain": "kept"}


def _presence_minimal() -> Dict[str, Any]:
    """Only the required keys: everything else exercises defaults."""
    return {"pk": 1, "required_str": "present"}


def _presence_falsy() -> Dict[str, Any]:
    """0/False/''/[] are values, not absences (on nullable fields)."""
    return {
        "pk": 0,
        "required_str": "",
        "nullable_str": "",
        "zero_int": 0,
        "false_bool": False,
        "empty_str": "",
        "empty_list": [],
    }


def _presence_empty_string_not_nullable() -> Dict[str, Any]:
    """``nullable=False`` treats ``''`` as null -- verified legacy behaviour."""
    payload = _presence_minimal()
    payload["not_nullable"] = ""
    return payload


def _presence_explicit_none() -> Dict[str, Any]:
    """Explicit ``None`` must stay distinct from an absent key."""
    return {
        "pk": 2,
        "required_str": "present",
        "nullable_str": None,
        "with_db_default": None,
    }


def _presence_missing_required() -> Dict[str, Any]:
    return {"pk": 3}


def _presence_null_not_nullable() -> Dict[str, Any]:
    payload = _presence_minimal()
    payload["not_nullable"] = None
    return payload


def _callback_valid() -> Dict[str, Any]:
    return {
        "live_tags": ["python", "rust"],
        "live_scaled": "2.5",
        "dead_validator": 3,
        "dead_encoder": "quiet",
        "untouched": 1,
    }


def _callback_rejected() -> Dict[str, Any]:
    """The container validator returns False -> the reference raises."""
    return {
        "live_tags": ["python", ""],
        "live_scaled": "2.5",
        "dead_validator": 3,
        "dead_encoder": "quiet",
        "untouched": 1,
    }


def _descriptor_defaults() -> Dict[str, Any]:
    return {}


def _descriptor_values() -> Dict[str, Any]:
    return {"quantity_on_hand": 20.75, "description": "  padded  "}


def _hook_payload() -> Dict[str, Any]:
    return {"name": "  Jesus Lara  "}


def _boundaries_extremes() -> Dict[str, Any]:
    """The F002 large-integer counterexample and friends."""
    return {
        "big_int": 2 ** 96 + 1,
        "small_int": IntSubclass(5),
        "precise_decimal": Decimal("1.000000000000000000000000001"),
        "unicode_text": "Ω ascii-and-🐍 çãé",
        "raw_bytes": b"\x00\xff binary",
        "a_datetime": FROZEN_NOW,
        "an_id": FROZEN_UUID,
    }


def _boundaries_bool_as_int() -> Dict[str, Any]:
    """``bool`` is an ``int`` subclass; validation.pyx:28 accepts it."""
    return {
        "big_int": True,
        "small_int": False,
        "precise_decimal": Decimal("0"),
        "unicode_text": "plain",
        "raw_bytes": b"",
        "a_datetime": FROZEN_NOW,
        "an_id": FROZEN_UUID,
    }


def _boundaries_date_for_datetime() -> Dict[str, Any]:
    """Verified: conversion rejects a ``date`` for a ``datetime`` field."""
    payload = _boundaries_bool_as_int()
    payload["a_datetime"] = date(2020, 3, 15)
    return payload


def _boundaries_str_subclass() -> Dict[str, Any]:
    """Verified: conversion rejects a ``str`` subclass for a ``str`` field."""
    payload = _boundaries_bool_as_int()
    payload["unicode_text"] = StrSubclass("subclassed")
    return payload


def _boundaries_defaults() -> Dict[str, Any]:
    return {}


def _org_strict() -> Dict[str, Any]:
    return {"org_id": 1, "name": "Org A"}


def _org_bad_type() -> Dict[str, Any]:
    return {"org_id": "Chance", "name": "Org A"}


# ---------------------------------------------------------------------------
# The corpus
# ---------------------------------------------------------------------------

CASES: Tuple[Case, ...] = (
    # -- Employee -----------------------------------------------------------
    Case(
        "employee_raw", "Employee", _employee_raw,
        tags=("employee", "raw", "coercion"), benchmark=True,
        requires_rust_parsers=True,
        notes="Every value arrives as a string; the full converter chain runs.",
    ),
    Case(
        "employee_native", "Employee", _employee_native,
        tags=("employee", "native"), benchmark=True,
        notes="Already-typed input; the 'already typed' fast-path candidate.",
    ),
    Case(
        "employee_shared_skills", "Employee", _employee_shared_skills,
        tags=("employee", "alias", "identity"),
        aliased_args=(("skills", "_alias_probe"),),
        notes="Intra-payload alias; the relationship must survive identically.",
    ),
    Case(
        "employee_null_optional", "Employee", _employee_null_optional,
        tags=("employee", "presence", "null"),
        notes="Explicit None on two optional fields.",
    ),
    Case(
        "employee_age_at_min", "Employee", _employee_age_at_min,
        tags=("employee", "constraint", "boundary"),
        notes="min=18 is inclusive (validation.pyx:427).",
    ),
    Case(
        "employee_age_at_max", "Employee", _employee_age_at_max,
        tags=("employee", "constraint", "boundary"),
        notes="max=99 is inclusive (validation.pyx:437).",
    ),
    Case(
        "employee_age_below_min", "Employee", _employee_age_below_min,
        expect=EXPECT_ERROR, tags=("employee", "constraint", "invalid"),
        notes="Pins both the predicate and the legacy 'greater than' wording.",
    ),
    Case(
        "employee_missing_required", "Employee", _employee_missing_required,
        expect=EXPECT_ERROR, tags=("employee", "presence", "invalid"),
    ),
    Case(
        "employee_bad_uuid", "Employee", _employee_bad_uuid,
        expect=EXPECT_ERROR, tags=("employee", "parse-failure", "invalid"),
        notes="converters.pyx:1994 captures the parser error and continues.",
    ),

    # -- Scalars ------------------------------------------------------------
    Case(
        "unconstrained_native", "UnconstrainedScalars", _unconstrained_native,
        tags=("scalar", "unconstrained", "native", "ac3"), benchmark=True,
        notes="AC3 target: zero generic _validation_ dispatches.",
    ),
    Case(
        "unconstrained_raw", "UnconstrainedScalars", _unconstrained_raw,
        tags=("scalar", "unconstrained", "raw", "ac3"), benchmark=True,
        requires_rust_parsers=True,
    ),
    Case(
        "constrained_valid", "ConstrainedScalars", _constrained_valid,
        tags=("scalar", "constraint"), benchmark=True,
    ),
    Case(
        "constrained_at_bounds", "ConstrainedScalars", _constrained_at_bounds,
        tags=("scalar", "constraint", "boundary"),
    ),
    Case(
        "constrained_int_too_low", "ConstrainedScalars", _constrained_int_too_low,
        expect=EXPECT_ERROR, tags=("scalar", "constraint", "invalid"),
    ),
    Case(
        "constrained_str_too_long", "ConstrainedScalars", _constrained_str_too_long,
        expect=EXPECT_OK,
        tags=("scalar", "constraint", "ignored-constraint", "characterization"),
        notes=(
            "VERIFIED LEGACY BEHAVIOUR: min/max on a str field are never "
            "enforced -- a 21-character value constructs successfully. Spec §1 "
            "makes activating previously ignored constraints a non-goal, so "
            "this case pins the *absence* of a length check."
        ),
    ),
    Case(
        "constrained_pattern_mismatch", "ConstrainedScalars",
        _constrained_pattern_mismatch,
        expect=EXPECT_ERROR, tags=("scalar", "constraint", "invalid"),
    ),
    Case(
        "constrained_multiple_errors", "ConstrainedScalars",
        _constrained_multiple_errors,
        expect=EXPECT_ERROR, tags=("scalar", "constraint", "invalid", "order"),
        notes="Five invalid fields: pins payload order and fall-through.",
    ),

    # -- Wide ---------------------------------------------------------------
    Case(
        "wide_native", "WideModel", _wide_native,
        tags=("wide", "native"), benchmark=True,
    ),
    Case(
        "wide_raw", "WideModel", _wide_raw,
        tags=("wide", "raw"), benchmark=True,
    ),

    # -- Nested / ORM -------------------------------------------------------
    Case(
        "org_strict", "Organization", _org_strict, tags=("orm", "strict"),
    ),
    Case(
        "org_bad_type", "Organization", _org_bad_type,
        expect=EXPECT_ERROR, tags=("orm", "strict", "invalid"),
    ),
    Case(
        "client_with_object", "Client", _client_with_object,
        tags=("orm", "nested", "as_objects"), benchmark=True,
    ),
    Case(
        "client_via_alias", "Client", _client_via_alias,
        tags=("orm", "nested", "alias"),
    ),
    Case(
        "client_bad_nested", "Client", _client_bad_nested,
        expect=EXPECT_ERROR, tags=("orm", "nested", "invalid"),
    ),
    Case(
        "container_full", "BigContainer", _container_full,
        tags=("container", "nested"), benchmark=True,
    ),
    Case(
        "container_shared_list", "BigContainer", _container_shared_list,
        tags=("container", "identity"),
        aliased_args=(("tags", "attributes.tags"),),
        notes="attributes['tags'] is the very same list as tags.",
    ),
    Case(
        "container_empty", "BigContainer", _container_empty,
        tags=("container", "defaults"),
        notes="Exercises default_factory for four separate fields.",
    ),

    # -- Aliases ------------------------------------------------------------
    Case(
        "aliased_by_alias", "AliasedRecord", _aliased_payload,
        tags=("alias",),
    ),
    Case(
        "aliased_canonical", "AliasedRecord", _aliased_canonical,
        tags=("alias",),
    ),

    # -- Presence -----------------------------------------------------------
    Case(
        "presence_minimal", "PresenceRules", _presence_minimal,
        tags=("presence", "defaults"), benchmark=True,
    ),
    Case(
        "presence_falsy", "PresenceRules", _presence_falsy,
        tags=("presence", "falsy"),
        notes="0/False/''/[] must not be read as 'missing' on nullable fields.",
    ),
    Case(
        "presence_empty_string_not_nullable", "PresenceRules",
        _presence_empty_string_not_nullable,
        expect=EXPECT_ERROR,
        tags=("presence", "falsy", "null", "invalid", "characterization"),
        notes=(
            "VERIFIED LEGACY BEHAVIOUR: nullable=False rejects '' with "
            "ValueError ':: *not_nullable* Cannot be null.' -- while an "
            "explicit None on the same field silently uses the default "
            "(see presence_null_not_nullable). Both halves are pinned."
        ),
    ),
    Case(
        "presence_explicit_none", "PresenceRules", _presence_explicit_none,
        tags=("presence", "null", "db_default"),
    ),
    Case(
        "presence_missing_required", "PresenceRules", _presence_missing_required,
        expect=EXPECT_ERROR, tags=("presence", "invalid"),
    ),
    Case(
        "presence_null_not_nullable", "PresenceRules", _presence_null_not_nullable,
        expect=EXPECT_OK,
        tags=("presence", "null", "characterization"),
        notes=(
            "VERIFIED LEGACY BEHAVIOUR: an explicit None on a nullable=False "
            "field does NOT raise; the field falls back to its default 'x'."
        ),
    ),

    # -- Callbacks / hooks / descriptors ------------------------------------
    Case(
        "callback_valid", "CallbackModel", _callback_valid,
        tags=("callback", "custom", "characterization"), observes_callbacks=True,
        notes=(
            "VERIFIED: exactly two callbacks fire -- the container validator "
            "and the float "
            "encoder. The int validator and the str encoder are dead in the "
            "reference (cached f.validator wins; parse_basic short-circuits "
            "str), and must stay dead."
        ),
    ),
    Case(
        "callback_rejected", "CallbackModel", _callback_rejected,
        expect=EXPECT_ERROR, tags=("callback", "custom", "invalid"),
        observes_callbacks=True,
        notes="Callback invocation count must match the reference exactly.",
    ),
    Case(
        "descriptor_defaults", "DescriptorModel", _descriptor_defaults,
        tags=("descriptor",),
    ),
    Case(
        "descriptor_values", "DescriptorModel", _descriptor_values,
        tags=("descriptor",),
        notes="__set__ coerces; the fast path must never bypass a descriptor.",
    ),
    Case(
        "hook_post_init", "HookModel", _hook_payload,
        tags=("hook", "post_init"), observes_callbacks=True,
    ),

    # -- Native boundaries --------------------------------------------------
    Case(
        "boundaries_extremes", "Boundaries", _boundaries_extremes,
        tags=("boundary", "native"),
        notes=(
            "2**96 integer (the F002 counterexample), 28-digit Decimal, "
            "non-ASCII text and raw bytes."
        ),
    ),
    Case(
        "boundaries_bool_as_int", "Boundaries", _boundaries_bool_as_int,
        tags=("boundary", "subclass"),
        notes="bool passed to int fields; validation.pyx:28 accepts it.",
    ),
    Case(
        "boundaries_date_for_datetime", "Boundaries", _boundaries_date_for_datetime,
        expect=EXPECT_ERROR,
        tags=("boundary", "native", "invalid", "characterization"),
        notes=(
            "VERIFIED: a date supplied to a datetime field is rejected during "
            "*conversion* ('argument must be str'); validation.pyx:59's "
            "date-accepting datetime validator is never reached."
        ),
    ),
    Case(
        "boundaries_str_subclass", "Boundaries", _boundaries_str_subclass,
        expect=EXPECT_ERROR,
        tags=("boundary", "subclass", "invalid", "characterization"),
        notes=(
            "VERIFIED: a str subclass is rejected with 'Expected str, got "
            "StrSubclass'. The reference already performs an exact-type check "
            "here, so a fast path must not widen it either."
        ),
    ),
    Case(
        "boundaries_defaults", "Boundaries", _boundaries_defaults,
        tags=("boundary", "defaults"),
    ),
)

CASES_BY_NAME: Dict[str, Case] = {case.name: case for case in CASES}


def case_names() -> Tuple[str, ...]:
    """All case names, in corpus order."""
    return tuple(case.name for case in CASES)


def cases_with_tag(tag: str) -> Tuple[Case, ...]:
    """Every case carrying ``tag``."""
    return tuple(case for case in CASES if tag in case.tags)


#: Keys a builder may add purely so the runner can assert an alias; they are
#: not model fields and must be removed before construction.
PROBE_KEYS: Tuple[str, ...] = ("_alias_probe",)


def build_kwargs(case: Case) -> Dict[str, Any]:
    """Fresh constructor kwargs for ``case``, with probe keys stripped."""
    payload = case.build()
    for key in PROBE_KEYS:
        payload.pop(key, None)
    return payload


def resolve_path(payload: Dict[str, Any], path: str) -> Any:
    """Resolve a dot-separated ``aliased_args`` path inside a payload."""
    node: Any = payload
    for part in path.split("."):
        node = node[part]
    return node
