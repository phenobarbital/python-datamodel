"""Lazy error allocation in the validation path (FEAT-2 / TASK-12).

Three allocations were removed or deferred:

1. ``validation.pyx::_validate_constraints`` -- an ``error = {}`` that was
   assigned on every call and **never read**.  Each failure path returns
   ``_create_error(...)``, which builds its own dict, and the success path
   returns a fresh ``{}``.  One dead dict per primitive field, per construction.
2. ``validation.pyx::_validation`` -- ``cdef dict error = {}`` was allocated on
   entry but only returned by the final statement, so every early return threw
   it away.  It is now allocated at the point of return.
3. ``converters.pyx::processing_fields`` -- a ``cdef dict _typeinfo = {}``
   declared and never referenced anywhere in the function.  One dead dict per
   model construction.

What this file has to prove is **not** that things got faster.  It is that
nothing observable changed: the contract of the returned dictionaries, the
content and ordering of every error payload, and the number of times a parser
or callback runs.  A "removed allocation" that quietly changed a return type,
shared a singleton, or skipped a callback would be a bug, not an optimisation.

On measuring the effect
=======================

The removed dictionaries were **transient** -- allocated and freed within one
call -- so they never appear in retained memory, and `tracemalloc` deltas over
a batch show nothing.  Their cost was allocator churn (CPU), not footprint.
A targeted paired micro-measurement against the 0.10.21 reference put the
effect at roughly 0.3-0.5%, which is **below** the ~2% empirical cross-build
floor recorded in ``benchmarks/results/compatible-model-performance/baseline.json``.
So this change is justified structurally -- the work was provably dead -- and
is explicitly **not** claimed as a measurable speed-up.  See the TASK-12
completion note.
"""
import gc
import tracemalloc
from decimal import Decimal

import pytest

from datamodel import BaseModel, Column
from datamodel.exceptions import ValidationError
from datamodel.validation import _validation


class Bounded(BaseModel):
    v: int = Column(required=False, min=1, max=10)


class Plain(BaseModel):
    v: int = Column(required=False)


class Strings(BaseModel):
    s: str = Column(required=False, max_length=5)


# ===========================================================================
# Part 1 -- the success contract: a FRESH, independently mutable dict
# ===========================================================================


def _validate(model, name, value, annotated_type):
    field = model.__columns__[name]
    return _validation(field, name, value, annotated_type, type(value),
                       "primitive", False)


def test_successful_validation_still_returns_a_dict():
    """Not None, not a sentinel: the cpdef return contract is `dict`."""
    result = _validate(Plain, "v", 5, int)
    assert isinstance(result, dict)
    assert result == {}


def test_each_successful_call_returns_a_distinct_object():
    """A shared empty singleton would let one caller corrupt another."""
    first = _validate(Plain, "v", 5, int)
    second = _validate(Plain, "v", 5, int)
    assert first is not second


def test_successful_results_are_independently_mutable():
    first = _validate(Plain, "v", 5, int)
    second = _validate(Plain, "v", 5, int)
    first["injected"] = True
    assert second == {}, "mutating one success result was visible in another"


def test_many_successful_results_are_all_distinct():
    results = [_validate(Plain, "v", n, int) for n in range(50)]
    assert len({id(r) for r in results}) == 50
    results[0]["x"] = 1
    assert all(r == {} for r in results[1:])


def test_constraint_success_also_returns_a_fresh_dict():
    """The path through `_validate_constraints`, where the dead dict lived."""
    first = _validate(Bounded, "v", 5, int)
    second = _validate(Bounded, "v", 5, int)
    assert first == second == {}
    assert first is not second


def test_error_results_are_independently_mutable():
    first = _validate(Bounded, "v", 99, int)
    second = _validate(Bounded, "v", 99, int)
    assert first and second
    assert first is not second
    first["injected"] = True
    assert "injected" not in second


# ===========================================================================
# Part 2 -- error payloads, messages and ordering are unchanged
# ===========================================================================


def test_error_payload_shape_is_preserved():
    error = _validate(Bounded, "v", 99, int)
    assert set(error) == {
        "field", "value", "error", "value_type", "annotation", "exception",
    }
    assert error["field"] == "v"
    assert error["value"] == 99


def test_error_key_order_is_stable_across_calls():
    """Payload *order* is observable (it reaches ValidationError's message)."""
    first = list(_validate(Bounded, "v", 99, int))
    second = list(_validate(Bounded, "v", 99, int))
    assert first == second


def test_min_and_max_violations_still_produce_distinct_messages():
    below = _validate(Bounded, "v", 0, int)
    above = _validate(Bounded, "v", 99, int)
    assert below["error"] != above["error"]
    assert below["error"] and above["error"]


def test_string_constraint_errors_are_preserved():
    ok = _validate(Strings, "s", "abc", str)
    assert ok == {}
    too_long = _validate(Strings, "s", "abcdefghij", str)
    assert too_long, "max_length violation stopped being reported"
    assert too_long["field"] == "s"


def test_type_errors_are_still_reported():
    error = _validate(Plain, "v", "not an int", int)
    assert error, "a wrong-typed value stopped producing an error"
    assert error["field"] == "v"


def test_none_still_falls_through_the_constraint_path_to_a_type_error():
    """VERIFIED against the 0.10.21 reference, which is the oracle here.

    `_validate_constraints` does return early for None -- but `_validation`
    then continues to the instance check, which rejects None for an `int`
    field. So the observable result is an *error*, not `{}`. I first asserted
    `{}` from reading only the constraint function; the reference build says
    otherwise, so the reference wins and the observed behaviour is pinned.
    """
    result = _validate(Bounded, "v", None, int)
    assert result, "None on an int field stopped producing an error"
    assert result["field"] == "v"
    assert result["value"] is None
    assert "expected" in result["error"]


# ===========================================================================
# Part 3 -- multi-error accumulation through the model, strict and non-strict
# ===========================================================================


def test_multiple_field_errors_are_all_reported():
    class Multi(BaseModel):
        a: int = Column(required=False, min=1, max=10)
        b: int = Column(required=False, min=1, max=10)

        class Meta:
            strict = False

    instance = Multi(a=99, b=99)
    errors = instance.get_errors()
    assert set(errors) >= {"a", "b"}, errors


def test_strict_model_still_raises_with_a_payload():
    class StrictMulti(BaseModel):
        a: int = Column(required=False, min=1, max=10)

        class Meta:
            strict = True

    with pytest.raises((ValidationError, ValueError)) as caught:
        StrictMulti(a=99)
    assert caught.value is not None


def test_error_dicts_from_two_instances_do_not_share_state():
    class Loose(BaseModel):
        a: int = Column(required=False, min=1, max=10)

        class Meta:
            strict = False

    first = Loose(a=99)
    second = Loose(a=99)
    first.get_errors()["injected"] = True
    assert "injected" not in second.get_errors()


# ===========================================================================
# Part 4 -- no parser or callback runs an extra time
# ===========================================================================


def test_a_custom_encoder_runs_exactly_once_per_field():
    calls = []

    def counting_encoder(value):
        calls.append(value)
        return float(value)

    class Encoded(BaseModel):
        v: float = Column(required=False, encoder=counting_encoder)

    Encoded(v=1)
    assert len(calls) == 1, f"encoder ran {len(calls)} times, expected 1"


def test_a_custom_validator_on_a_primitive_stays_dead():
    """CHARACTERIZATION of a pre-existing dead route, verified on 0.10.21.

    `abstract.py` caches `validators[int]` into `f.validator`, so a user
    `validator=` on a primitive is never reached -- it runs **zero** times on
    both builds. TASK-7 recorded the same thing. Pinned here so that removing
    allocations (or a later "unified callback" refactor) cannot quietly
    *revive* it: going from 0 to 1 call would be a behaviour change.
    """
    calls = []

    def counting_validator(field, value, annotated_type, val_type):
        calls.append(value)
        return True

    class Validated(BaseModel):
        v: int = Column(required=False, validator=counting_validator)

    Validated(v=1)
    assert len(calls) == 0, (
        f"the dead primitive-validator route ran {len(calls)} times; it runs "
        "0 times on the reference build"
    )


def test_a_live_custom_validator_runs_exactly_once():
    """The List[str] route is live on both builds (TASK-7), so it is the
    one that can meaningfully assert 'exactly once'."""
    from typing import List

    calls = []

    def counting_validator(field, value, annotated_type, val_type):
        calls.append(value)
        return True

    class Validated2(BaseModel):
        v: List[str] = Column(required=False, validator=counting_validator)

    Validated2(v=["a"])
    assert len(calls) == 1, f"validator ran {len(calls)} times, expected 1"


def test_post_init_hook_runs_exactly_once():
    events = []

    class Hooked(BaseModel):
        v: int = Column(required=False)

        def __post_init__(self):
            events.append("post_init")
            super().__post_init__()

    Hooked(v=1)
    assert events == ["post_init"]


def test_a_failing_field_does_not_suppress_later_fields():
    """The error-fallthrough path must be unchanged."""
    seen = []

    def recorder(value):
        seen.append(value)
        return float(value)

    class Mixed(BaseModel):
        bad: int = Column(required=False, min=1, max=10)
        # `float`, not `str`: an encoder on a str field is a pre-existing dead
        # route (`parse_basic` short-circuits str before its encoder branch),
        # verified on 0.10.21 and recorded by TASK-7. Using it here would test
        # nothing.
        later: float = Column(required=False, encoder=recorder)

        class Meta:
            strict = False

    Mixed(bad=99, later=2)
    assert seen == [2], "a field after a failing one stopped being processed"


# ===========================================================================
# Part 5 -- diagnostic allocation evidence (separate from release timings)
# ===========================================================================


def test_no_new_per_field_allocation_replaced_the_removed_one():
    """The removed dict must not come back wearing a different hat.

    Retained memory per construction is compared against a generous ceiling.
    This cannot detect the transient dicts that were removed -- that is the
    point of the module docstring -- but it *can* detect a regression where a
    new per-field object is retained instead.
    """
    class Wide(BaseModel):
        a: int = Column(required=False)
        b: str = Column(required=False)
        c: float = Column(required=False)
        d: int = Column(required=False)
        e: str = Column(required=False)

    payload = dict(a=1, b="x", c=1.5, d=2, e="y")
    for _ in range(200):
        Wide(**payload)

    gc.collect()
    tracemalloc.start()
    before = tracemalloc.take_snapshot()
    held = [Wide(**payload) for _ in range(500)]
    after = tracemalloc.take_snapshot()
    tracemalloc.stop()

    retained = sum(s.size_diff for s in after.compare_to(before, "lineno"))
    per_construction = retained / len(held)
    # A model with 5 fields legitimately retains its instance and values.
    # A per-field error dict coming back would add >=64 bytes * 5.
    assert per_construction < 2048, (
        f"{per_construction:.0f} retained bytes per construction is far above "
        "what a 5-field model should hold; a per-field allocation may have "
        "been reintroduced"
    )
    assert len(held) == 500


def test_repeated_validation_retains_nothing():
    """Success results must not be accumulated anywhere internally."""
    field_model = Bounded
    gc.collect()
    tracemalloc.start()
    before = tracemalloc.take_snapshot()
    for _ in range(2000):
        _validate(field_model, "v", 5, int)
    gc.collect()
    after = tracemalloc.take_snapshot()
    tracemalloc.stop()

    retained = sum(s.size_diff for s in after.compare_to(before, "lineno"))
    assert retained < 200_000, (
        f"{retained} bytes retained across 2000 successful validations; "
        "results are being accumulated instead of discarded"
    )


def test_success_result_is_not_interned_across_types():
    """Different field types must not converge on one shared empty dict."""
    results = [
        _validate(Plain, "v", 5, int),
        _validate(Bounded, "v", 5, int),
        _validate(Strings, "s", "abc", str),
    ]
    assert all(r == {} for r in results)
    assert len({id(r) for r in results}) == 3


# ===========================================================================
# Part 6 -- end-to-end behaviour is untouched
# ===========================================================================


def test_valid_models_still_build():
    class Full(BaseModel):
        a: int = Column(required=False, min=1, max=10)
        b: str = Column(required=False)
        c: Decimal = Column(required=False)

    instance = Full(a=5, b="x", c=Decimal("1.5"))
    assert (instance.a, instance.b, instance.c) == (5, "x", Decimal("1.5"))
    assert instance.to_dict() == {"a": 5, "b": "x", "c": Decimal("1.5")}


def test_to_dict_is_still_fresh_per_call():
    instance = Bounded(v=5)
    assert instance.to_dict() is not instance.to_dict()
