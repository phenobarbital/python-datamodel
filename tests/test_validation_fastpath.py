"""The gated scalar validation fast path (FEAT-2 / TASK-13).

``processing_fields`` now consults ``fastpath_kind()`` at the post-conversion
boundary.  When a field's value is an *exactly* typed supported scalar whose
cached validator and parser are still the ones the policy recorded, the generic
``_validation_`` dispatch is skipped: the type is already proven, so the
built-in validator is known to return ``None``, and only the live constraints
remain.

The danger this file exists to guard against is a fast path that is subtly
*wider* than the behaviour it replaces.  Every test below is therefore about
something the gate must **refuse** to take over, or about a check it must still
perform.  The gate returning ``FASTPATH_NONE`` is always safe -- it just costs
a dispatch -- so all the risk lives on the other side.

``fastpath_kind`` is ``cdef`` and deliberately not importable from Python.
These tests exercise it through observable behaviour, which is the level that
actually matters, and the dispatch counts themselves are measured by
``tests/compatibility/profile_validation.py`` in a separate profiling build.
"""
import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import List, Optional

import pytest

from datamodel import BaseModel, Column
from datamodel.exceptions import ValidationError
from datamodel.validation import (
    generic_dispatch_count,
    profiling_compiled_in,
    reset_generic_dispatch_count,
    validators,
)


# ===========================================================================
# Part 1 -- diagnostic counters are absent from the release build
# ===========================================================================


def test_release_build_has_no_counters_compiled_in():
    """AC: diagnostic counters must not affect release timings.

    The counter is behind a C macro that defaults to 0, so the branch is
    folded away by the C compiler. If this ever reports True in a normal
    build, instrumentation has leaked into the default application flow.
    """
    assert profiling_compiled_in() is False


def test_counter_reads_zero_and_is_harmless_in_a_release_build():
    reset_generic_dispatch_count()
    assert generic_dispatch_count() == 0
    for _ in range(100):
        Scalars(an_int=1, a_str="x")
    assert generic_dispatch_count() == 0


def test_public_validation_surface_is_still_importable():
    """The .pxd gained declarations; nothing was removed or re-signed."""
    from datamodel.validation import (  # noqa: F401
        _validation,
        build_field_policy,
        field_policy,
        is_optional_type,
        policy_is_current,
    )

    assert callable(_validation)
    assert callable(is_optional_type)


# ===========================================================================
# Part 2 -- exactly-typed scalars still validate correctly
# ===========================================================================


class Scalars(BaseModel):
    an_int: int = Column(required=False)
    a_str: str = Column(required=False)
    a_float: float = Column(required=False)
    a_bool: bool = Column(required=False)
    a_decimal: Decimal = Column(required=False)
    a_uuid: uuid.UUID = Column(required=False)
    a_date: date = Column(required=False)
    a_datetime: datetime = Column(required=False)


def test_every_supported_scalar_builds_with_an_exact_value():
    instance = Scalars(
        an_int=7, a_str="text", a_float=1.5, a_bool=True,
        a_decimal=Decimal("2.25"),
        a_uuid=uuid.UUID("f47ac10b-58cc-4372-a567-0e02b2c3d479"),
        a_date=date(2024, 3, 17),
        a_datetime=datetime(2024, 3, 17, 12, 30, 45),
    )
    assert instance.an_int == 7
    assert instance.a_decimal == Decimal("2.25")
    assert instance.a_date == date(2024, 3, 17)


def test_zero_and_false_are_values_not_absence():
    """`is_empty(0)` and `is_empty(False)` are both False.

    If the gate treated them as missing it would skip `_field_checks_` for a
    genuinely absent value, or divert a present one into presence handling.
    Either would be a behaviour change.
    """
    instance = Scalars(an_int=0, a_float=0.0, a_bool=False)
    assert instance.an_int == 0
    assert instance.a_float == 0.0
    assert instance.a_bool is False


def test_empty_string_still_reaches_the_legacy_presence_path():
    instance = Scalars(a_str="")
    assert instance.a_str == ""


def test_wrong_types_are_still_rejected():
    with pytest.raises((ValidationError, ValueError, TypeError)):
        Scalars(an_int="not an int")


# ===========================================================================
# Part 3 -- what the gate must REFUSE to take over
# ===========================================================================


def test_a_str_subclass_is_not_treated_as_a_str():
    """Exact type identity, never isinstance: the reference rejects subclasses.

    `type(value) is str` is False for a subclass, so the gate must decline and
    let the legacy path apply its exact-type check.
    """
    class MyStr(str):
        pass

    with pytest.raises((ValidationError, ValueError, TypeError)):
        Scalars(a_str=MyStr("subclassed"))


def test_bool_supplied_to_an_int_field_keeps_reference_behaviour():
    """`bool` is a subclass of `int`, so `type(True) is int` is False.

    The gate declines and the legacy path decides. Whatever it decides, the
    two builds must agree -- which the differential corpus asserts. Here we
    only pin that the value is not silently mangled.
    """
    instance = Scalars(an_int=True)
    assert instance.an_int in (True, 1)
    assert instance.an_int == 1


def test_an_int_subclass_is_not_treated_as_an_int():
    class MyInt(int):
        pass

    instance = Scalars(an_int=MyInt(5))
    assert instance.an_int == 5


def test_a_replaced_validator_is_honoured_not_bypassed():
    """Swapping `f.validator` at runtime must send the field back to legacy.

    If the gate kept using its recorded identity, a user's replacement would
    be silently ignored -- exactly the "replaced validator silently accepted"
    failure the AC forbids.
    """
    class Swappable(BaseModel):
        v: int = Column(required=False)

        class Meta:
            strict = False

    calls = []

    def rejecting_validator(field, name, value, _type):
        calls.append(value)
        return "rejected by the replacement validator"

    original = Swappable.__columns__["v"].validator
    Swappable.__columns__["v"].validator = rejecting_validator
    try:
        instance = Swappable(v=5)
        assert calls, "the replacement validator was never called"
        assert instance.get_errors(), "its rejection was ignored"
    finally:
        Swappable.__columns__["v"].validator = original


def test_clearing_the_validator_sends_the_field_to_the_generic_path():
    class Cleared(BaseModel):
        v: int = Column(required=False)

    original = Cleared.__columns__["v"].validator
    Cleared.__columns__["v"].validator = None
    try:
        assert Cleared(v=5).v == 5
        with pytest.raises((ValidationError, ValueError, TypeError)):
            Cleared(v="not an int")
    finally:
        Cleared.__columns__["v"].validator = original


def test_a_replaced_parser_sends_the_field_to_the_generic_path():
    class Parsed(BaseModel):
        v: int = Column(required=False)

    original = Parsed.__columns__["v"].parser
    Parsed.__columns__["v"].parser = lambda value: value
    try:
        assert Parsed(v=5).v == 5
    finally:
        Parsed.__columns__["v"].parser = original


def test_a_field_without_a_policy_is_untouched():
    class Complex(BaseModel):
        items: List[str] = Column(required=False, default_factory=list)
        maybe: Optional[str] = Column(required=False)

    instance = Complex(items=["a", "b"], maybe="x")
    assert instance.items == ["a", "b"]
    assert instance.maybe == "x"


# ===========================================================================
# Part 4 -- constraints, including ones that appear at runtime
# ===========================================================================


class Bounded(BaseModel):
    """Non-strict on purpose: a strict model *raises* on the first error, so
    `get_errors()` would never be reachable. Strict behaviour has its own
    tests below."""

    v: int = Column(required=False, min=1, max=10)

    class Meta:
        strict = False


class Lengths(BaseModel):
    s: str = Column(required=False, max_length=5)

    class Meta:
        strict = False


def test_constraints_are_still_enforced_on_the_fast_path():
    assert Bounded(v=5).v == 5
    for bad in (0, 99):
        instance = Bounded(v=bad)
        assert instance.get_errors(), f"{bad} passed a min/max constraint"


def test_string_constraints_are_still_enforced():
    assert Lengths(s="abc").s == "abc"
    assert Lengths(s="way too long").get_errors()


def test_a_constraint_added_at_runtime_cannot_be_skipped():
    """The single most important guarantee in this task.

    The policy recorded "no constraints" for this field. If the gate trusted
    that recorded shape it would skip a constraint added later. It does not:
    it re-reads the live metadata through `_validate_constraints` on every
    build, so the new constraint takes effect immediately.
    """
    class Late(BaseModel):
        v: int = Column(required=False)

        class Meta:
            strict = False

    assert Late(v=99).v == 99, "precondition: unconstrained to begin with"

    field = Late.__columns__["v"]
    field._meta["max"] = 10
    field.metadata = field._meta
    try:
        assert Late(v=99).get_errors(), (
            "a constraint added after class creation was skipped by the gate"
        )
        assert not Late(v=5).get_errors()
    finally:
        field._meta.pop("max", None)
        field.metadata = field._meta


def test_a_constraint_removed_at_runtime_stops_applying():
    class Removable(BaseModel):
        v: int = Column(required=False, max=10)

        class Meta:
            strict = False

    assert Removable(v=99).get_errors()

    field = Removable.__columns__["v"]
    removed = field._meta.pop("max")
    field.metadata = field._meta
    try:
        assert not Removable(v=99).get_errors()
    finally:
        field._meta["max"] = removed
        field.metadata = field._meta


def test_decimal_constraints_remain_ignored_on_this_route():
    """CHARACTERIZATION: `_validation_` honours constraints only for
    str/int/float.

    A Decimal `min`/`max` is silently ignored by the reference on this route.
    The gate reproduces that exactly rather than "fixing" it -- activating a
    previously-ignored constraint is listed as a non-goal in spec section 1,
    and would be a behaviour change.
    """
    class Money(BaseModel):
        amount: Decimal = Column(required=False, min=1, max=10)

        class Meta:
            strict = False

    instance = Money(amount=Decimal("9999"))
    assert instance.amount == Decimal("9999")
    assert not instance.get_errors(), (
        "a Decimal constraint started being enforced; the reference ignores it"
    )


def test_constraint_error_payload_is_unchanged():
    errors = Bounded(v=99).get_errors()
    assert "v" in errors
    payload = errors["v"]
    assert payload["field"] == "v"
    assert payload["value"] == 99


# ===========================================================================
# Part 5 -- presence, primary keys and nullability still route to legacy
# ===========================================================================


def test_required_field_still_reports_when_missing():
    class Req(BaseModel):
        needed: str = Column(required=True)

    with pytest.raises((ValidationError, ValueError)):
        Req()


def test_primary_key_checks_still_run():
    class Keyed(BaseModel):
        pk: int = Column(primary_key=True, required=True)
        other: str = Column(required=False)

    assert Keyed(pk=1, other="x").pk == 1
    with pytest.raises((ValidationError, ValueError)):
        Keyed(other="x")


def test_nullable_false_behaviour_is_unchanged():
    class NotNull(BaseModel):
        v: str = Column(required=False, nullable=False, default="d")

    with pytest.raises((ValidationError, ValueError, TypeError)):
        NotNull(v="")


def test_defaults_still_apply_when_a_field_is_omitted():
    class Defaulted(BaseModel):
        a: int = Column(required=False, default=7)
        b: str = Column(required=False, default="d")

    instance = Defaulted()
    assert (instance.a, instance.b) == (7, "d")


# ===========================================================================
# Part 6 -- callbacks run exactly once, and conversion is never repeated
# ===========================================================================


def test_conversion_is_not_repeated_when_the_gate_declines():
    """The gate sits *after* conversion, so a fallback must not re-parse."""
    calls = []

    def counting_encoder(value):
        calls.append(value)
        return float(value)

    # NOTE the deliberately unique class name. The class cache is keyed on
    # (name, bases, annotations) and ignores defaults, so a plain `Encoded`
    # here would silently reuse the Field -- and the *encoder* -- belonging to
    # the identically-shaped `Encoded` in test_validation_allocations.py. This
    # test passed alone and failed in the full suite until the name was made
    # unique; see test_class_cache_shares_field_objects_for_identical_signatures.
    class EncodedFastpathProbe(BaseModel):
        # float has a policy, but the custom encoder replaces `parser`, so the
        # gate declines and `_validation_` runs -- with the already-converted
        # value. The encoder must still have run exactly once.
        v: float = Column(required=False, encoder=counting_encoder)

    EncodedFastpathProbe(v=2)
    assert len(calls) == 1, f"encoder ran {len(calls)} times, expected 1"


def test_post_init_runs_once_with_the_gate_active():
    events = []

    class Hooked(BaseModel):
        v: int = Column(required=False)

        def __post_init__(self):
            events.append("hook")
            super().__post_init__()

    Hooked(v=1)
    assert events == ["hook"]


def test_a_mutation_in_post_init_is_seen_by_validation():
    """The gate must observe post-callback state, not pre-callback state.

    The hook overwrites a valid 1 with an out-of-range 99 *before* validation
    runs. If the gate had captured the value earlier, or trusted the
    pre-callback state, the 99 would sail through. It does not: the violation
    is reported, which proves the boundary is genuinely post-callback.
    """
    class Mutating(BaseModel):
        v: int = Column(required=False, max=10)

        def __post_init__(self):
            self.__dict__["v"] = 99
            super().__post_init__()

    with pytest.raises((ValidationError, ValueError)):
        Mutating(v=1)


# ===========================================================================
# Part 7 -- strict vs non-strict multi-error behaviour
# ===========================================================================


def test_non_strict_accumulates_every_field_error():
    class Multi(BaseModel):
        a: int = Column(required=False, max=10)
        b: int = Column(required=False, max=10)
        c: str = Column(required=False, max_length=2)

        class Meta:
            strict = False

    errors = Multi(a=99, b=99, c="far too long").get_errors()
    assert set(errors) >= {"a", "b", "c"}, errors


def test_a_valid_field_after_an_invalid_one_is_still_processed():
    class Mixed(BaseModel):
        bad: int = Column(required=False, max=10)
        good: int = Column(required=False)

        class Meta:
            strict = False

    instance = Mixed(bad=99, good=5)
    assert instance.good == 5
    assert "bad" in instance.get_errors()


def test_strict_model_still_raises():
    class StrictBounded(BaseModel):
        v: int = Column(required=False, max=10)

        class Meta:
            strict = True

    assert StrictBounded(v=5).v == 5
    with pytest.raises((ValidationError, ValueError)):
        StrictBounded(v=99)


# ===========================================================================
# Part 8 -- results stay independent
# ===========================================================================


def test_results_are_not_shared_between_instances():
    first = Scalars(an_int=1, a_str="a")
    second = Scalars(an_int=2, a_str="b")
    assert first.to_dict() != second.to_dict()
    assert first.to_dict() is not first.to_dict()


def test_error_dicts_are_not_shared_between_instances():
    first = Bounded(v=99)
    second = Bounded(v=99)
    first.get_errors()["injected"] = True
    assert "injected" not in second.get_errors()


def test_builtin_validator_identity_is_still_what_the_gate_expects():
    """A sanity check on the assumption the whole gate rests on."""
    field = Scalars.__columns__["an_int"]
    assert field.validator is validators[int]
    assert field._policy is not None
    assert field._policy.validator_ref is validators[int]
