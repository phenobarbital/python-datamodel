"""The experimental sequential native executor (FEAT-2 / TASK-17).

``rs_core.NativePlan`` is a bounded, sequential, model-level validator for a
declared eligible subset of scalar fields.  It is a **prototype for
measurement**, not a backend: nothing in ``datamodel`` imports it, and TASK-18
decides whether it is even a promotion candidate.

The interesting property of a fallback-based design is that almost every way it
can be wrong is a way it *over-reaches*.  Returning ``None`` — "ineligible, run
the legacy path" — is always safe; producing a result for something it should
have declined is not.  So most of this file is about what the executor must
**refuse**.

`execute()` returning ``None`` is not a validation result and is never treated
as one here.

Availability is a hard gate: if the crate cannot be built, these tests
**fail**. An unbuildable experiment is unverified, not passing.
"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from benchmarks.native_validation import (  # noqa: E402
    KIND_BY_TYPE,
    NativeUnavailable,
    describe_interface,
    load_native,
    plan_for,
    python_validity,
)
from datamodel import BaseModel, Column  # noqa: E402


@pytest.fixture(scope="module")
def native():
    try:
        return load_native(build=True)
    except NativeUnavailable as exc:
        pytest.fail(
            f"the experimental native extension could not be built, so the "
            f"native experiment is UNVERIFIED (not passing): {exc}"
        )


def _model(name, annotations, **columns):
    attributes = {"__annotations__": annotations,
                  "Meta": type("Meta", (), {"strict": False})}
    attributes.update(columns)
    return type(name, (BaseModel,), attributes)


# ===========================================================================
# Part 1 -- the extension is development-only
# ===========================================================================


def test_datamodel_does_not_import_rs_core():
    """AC: no default-backend or package-loader change.

    Importing datamodel must not pull in the experimental extension, whether
    or not it happens to be built.
    """
    for name in list(sys.modules):
        if name == "rs_core" or name.startswith("rs_core."):
            del sys.modules[name]
    import importlib

    import datamodel

    importlib.reload(datamodel)
    assert "rs_core" not in sys.modules, (
        "importing datamodel loaded the experimental extension"
    )


def test_no_new_public_constructor_api():
    class Probe(BaseModel):
        v: int = Column(required=False)

    for forbidden in ("native_plan", "execute_native", "use_native", "backend"):
        assert not hasattr(Probe, forbidden), forbidden
        assert not hasattr(Probe(v=1), forbidden), forbidden


def test_the_extension_is_loaded_explicitly_by_path(native):
    assert Path(native.__loaded_from__).is_file()
    assert native.__provenance__["artifact"].endswith("librs_core.so")
    assert len(native.__provenance__["sha256"]) == 64


# ===========================================================================
# Part 2 -- the declared interface
# ===========================================================================


def test_supported_kinds_are_exactly_the_declared_scalars(native):
    assert set(native.SUPPORTED_KINDS) == {"str", "int", "float", "bool"}
    assert set(KIND_BY_TYPE.values()) == set(native.SUPPORTED_KINDS)


def test_interface_description_matches_the_module(native):
    described = describe_interface(native)
    assert described["supported_kinds"] == list(native.SUPPORTED_KINDS)
    assert "INELIGIBLE" in described["none_means"]


def test_plan_reports_its_shape(native):
    plan = native.NativePlan([
        ("a", "int", None, None, None, None),
        ("b", "str", None, None, None, None),
    ])
    assert plan.eligible is True
    assert plan.field_count == 2
    assert list(plan.kinds) == ["int", "str"]


def test_malformed_descriptors_raise_rather_than_being_guessed(native):
    with pytest.raises(TypeError):
        native.NativePlan([("a", "int", None)])
    with pytest.raises(TypeError):
        native.NativePlan(["not-a-tuple"])


# ===========================================================================
# Part 3 -- exact scalar success, and parity with the Python path
# ===========================================================================


Scalars = _model(
    "NativeScalars",
    {"an_int": int, "a_str": str, "a_float": float, "a_bool": bool},
    an_int=Column(required=False, default=0),
    a_str=Column(required=False, default="x"),
    a_float=Column(required=False, default=0.0),
    a_bool=Column(required=False, default=False),
)


def test_exact_scalars_execute_natively(native):
    model_plan = plan_for(native, Scalars)
    assert model_plan.eligible
    result = model_plan.plan.execute(
        {"an_int": 7, "a_str": "hello", "a_float": 1.5, "a_bool": True}
    )
    assert result is not None, "an entirely eligible row fell back"
    assert dict(result) == {"an_int": True, "a_str": True,
                            "a_float": True, "a_bool": True}


def test_zero_and_empty_are_values_not_absence(native):
    model_plan = plan_for(native, Scalars)
    result = model_plan.plan.execute(
        {"an_int": 0, "a_str": "", "a_float": 0.0, "a_bool": False}
    )
    assert result is not None
    assert all(ok for _, ok in result)


def test_native_decisions_match_the_python_path(native):
    """AC8/AC2: parity on the declared eligible subset."""
    model_plan = plan_for(native, Scalars)
    rows = [
        {"an_int": 7, "a_str": "hello", "a_float": 1.5, "a_bool": True},
        {"an_int": 0, "a_str": "", "a_float": 0.0, "a_bool": False},
        {"an_int": -1, "a_str": "ünïcödé", "a_float": -2.5, "a_bool": True},
    ]
    compared = 0
    for row in rows:
        result = model_plan.plan.execute(dict(row))
        if result is None:
            continue
        expected = python_validity(Scalars, dict(row))
        for name, ok in result:
            assert expected[name] == ok, (name, row, ok, expected[name])
            compared += 1
    assert compared >= 9, f"only {compared} field decisions were compared"


def test_unicode_length_is_counted_in_characters_not_bytes(native):
    """`len()` on a Python str counts code points; so must the executor."""
    Short = _model("NativeShort", {"s": str},
                   s=Column(required=False, default="", max_length=3))
    plan = plan_for(native, Short).plan
    assert dict(plan.execute({"s": "ünï"}))["s"] is True     # 3 chars, 5 bytes
    assert dict(plan.execute({"s": "ünïcö"}))["s"] is False  # 5 chars


# ===========================================================================
# Part 4 -- what the executor must REFUSE (the whole safety story)
# ===========================================================================


def test_large_integer_falls_back_and_is_never_truncated(native):
    """The prototype flaw the acceptance criteria call out by name.

    Python integers are arbitrary precision. `extract::<i64>()` fails for
    2**96, and the pre-existing prototypes in lib.rs report that as *invalid*.
    This executor must instead decline the whole row, so Python decides.
    """
    plan = plan_for(native, Scalars).plan
    result = plan.execute(
        {"an_int": 2 ** 96, "a_str": "s", "a_float": 1.0, "a_bool": True}
    )
    assert result is None, (
        "a 2**96 int was judged natively; it must fall back, and it must "
        "certainly not be reported as invalid"
    )
    # And Python accepts it, which is exactly why declining matters.
    assert Scalars(an_int=2 ** 96, a_str="s", a_float=1.0,
                   a_bool=True).an_int == 2 ** 96


@pytest.mark.parametrize("boundary", [2 ** 63, -(2 ** 63) - 1, 2 ** 200])
def test_every_out_of_range_integer_falls_back(native, boundary):
    plan = plan_for(native, Scalars).plan
    assert plan.execute(
        {"an_int": boundary, "a_str": "s", "a_float": 1.0, "a_bool": True}
    ) is None


@pytest.mark.parametrize("edge", [2 ** 63 - 1, -(2 ** 63)])
def test_in_range_integer_boundaries_still_execute(native, edge):
    plan = plan_for(native, Scalars).plan
    result = plan.execute(
        {"an_int": edge, "a_str": "s", "a_float": 1.0, "a_bool": True}
    )
    assert result is not None and dict(result)["an_int"] is True


def test_bool_supplied_to_an_int_field_falls_back(native):
    """`bool` is a subclass of `int` and Python's valid_int accepts it."""
    plan = plan_for(native, Scalars).plan
    assert plan.execute(
        {"an_int": True, "a_str": "s", "a_float": 1.0, "a_bool": True}
    ) is None


def test_subclass_instances_fall_back(native):
    class MyStr(str):
        pass

    class MyInt(int):
        pass

    plan = plan_for(native, Scalars).plan
    assert plan.execute(
        {"an_int": 1, "a_str": MyStr("x"), "a_float": 1.0, "a_bool": True}
    ) is None
    assert plan.execute(
        {"an_int": MyInt(1), "a_str": "x", "a_float": 1.0, "a_bool": True}
    ) is None


def test_wrong_types_are_reported_invalid_not_skipped(native):
    plan = plan_for(native, Scalars).plan
    result = plan.execute(
        {"an_int": [1], "a_str": "s", "a_float": 1.0, "a_bool": True}
    )
    assert result is not None
    assert dict(result)["an_int"] is False
    assert len(result) == 4, "a field was skipped instead of being decided"


def test_missing_field_falls_back(native):
    """Presence/default handling is not implemented, so it must decline."""
    plan = plan_for(native, Scalars).plan
    assert plan.execute({"an_int": 1, "a_str": "s", "a_float": 1.0}) is None


def test_an_unsupported_kind_makes_the_whole_plan_ineligible(native):
    """A field is never skipped -- the model stops being a candidate."""
    plan = native.NativePlan([
        ("a", "int", None, None, None, None),
        ("when", "date", None, None, None, None),
    ])
    assert plan.eligible is False
    assert plan.execute({"a": 1, "when": "2024-03-17"}) is None


def test_temporal_and_decimal_models_are_ineligible(native):
    """Deliberately excluded: the prototype's chrono handling does not
    reproduce Python's temporal variants, so those fields decline."""
    from datetime import date
    from decimal import Decimal

    Rich = _model("NativeRich", {"n": int, "when": date, "amount": Decimal},
                  n=Column(required=False, default=0),
                  when=Column(required=False),
                  amount=Column(required=False))
    model_plan = plan_for(native, Rich)
    assert model_plan.eligible is False
    assert set(model_plan.ineligible_fields) == {"when", "amount"}


def test_callback_bearing_fields_fall_back(native):
    """AC: unsupported values/fields select legacy behaviour before callbacks.

    The executor validates only. A field carrying a user encoder or validator
    must therefore never run natively, or the callback would be skipped.
    """
    Hooked = _model(
        "NativeHooked", {"plain": int, "hooked": float},
        plain=Column(required=False, default=0),
        hooked=Column(required=False, default=0.0,
                      encoder=lambda value: float(value)),
    )
    model_plan = plan_for(native, Hooked)
    assert model_plan.eligible is False
    assert "hooked" in model_plan.ineligible_fields


def test_validator_bearing_fields_fall_back(native):
    Validated = _model(
        "NativeValidated", {"plain": int, "checked": int},
        plain=Column(required=False, default=0),
        checked=Column(required=False, default=0,
                       validator=lambda f, v, a, t: True),
    )
    model_plan = plan_for(native, Validated)
    assert model_plan.eligible is False
    assert "checked" in model_plan.ineligible_fields


# ===========================================================================
# Part 5 -- constraints
# ===========================================================================


Bounded = _model("NativeBounded", {"v": int, "s": str},
                 v=Column(required=False, default=1, min=1, max=10),
                 s=Column(required=False, default="", max_length=5))


def test_constraints_are_enforced_natively(native):
    plan = plan_for(native, Bounded).plan
    assert dict(plan.execute({"v": 5, "s": "ok"})) == {"v": True, "s": True}
    assert dict(plan.execute({"v": 0, "s": "ok"}))["v"] is False
    assert dict(plan.execute({"v": 99, "s": "ok"}))["v"] is False
    assert dict(plan.execute({"v": 5, "s": "toolong"}))["s"] is False


def test_constraint_boundaries_are_inclusive(native):
    plan = plan_for(native, Bounded).plan
    assert dict(plan.execute({"v": 1, "s": "abcde"})) == {"v": True, "s": True}
    assert dict(plan.execute({"v": 10, "s": "abcde"})) == {"v": True, "s": True}


def test_constraint_decisions_match_the_python_path(native):
    plan = plan_for(native, Bounded).plan
    for row in ({"v": 5, "s": "ok"}, {"v": 0, "s": "ok"},
                {"v": 99, "s": "ok"}, {"v": 5, "s": "toolong"}):
        result = plan.execute(dict(row))
        assert result is not None
        expected = python_validity(Bounded, dict(row))
        for name, ok in result:
            assert expected[name] == ok, (row, name, ok, expected[name])


# ===========================================================================
# Part 6 -- eligibility is decided before any side effect
# ===========================================================================


def test_an_ineligible_field_declines_the_whole_row(native):
    """A row is never half-executed.

    The last field is the unusable one, so a single-pass implementation would
    already have produced decisions for the first three before discovering it.
    Returning None for the whole row is what lets the caller re-run from a
    clean state without any parser running twice.
    """
    # The int field is deliberately LAST here: a single-pass implementation
    # would already have decided the first three fields before reaching the
    # out-of-range value that forces the fallback.
    Trailing = _model(
        "NativeTrailingInt",
        {"a_str": str, "a_float": float, "a_bool": bool, "an_int": int},
        a_str=Column(required=False, default="x"),
        a_float=Column(required=False, default=0.0),
        a_bool=Column(required=False, default=False),
        an_int=Column(required=False, default=0),
    )
    plan = plan_for(native, Trailing).plan
    assert list(plan.kinds)[-1] == "int", "precondition: int field must be last"

    assert plan.execute(
        {"a_str": "s", "a_float": 1.0, "a_bool": True, "an_int": 2 ** 96}
    ) is None, "an ineligible trailing field did not decline the whole row"

    # A plain wrong type is a decision, not a fallback.
    assert plan.execute(
        {"a_str": "s", "a_float": 1.0, "a_bool": "not-a-bool", "an_int": 1}
    ) is not None


def test_execute_is_repeatable_and_holds_no_state(native):
    plan = plan_for(native, Scalars).plan
    row = {"an_int": 7, "a_str": "hello", "a_float": 1.5, "a_bool": True}
    first = plan.execute(dict(row))
    for _ in range(50):
        assert plan.execute(dict(row)) == first
    assert plan.execute(
        {"an_int": 2 ** 96, "a_str": "s", "a_float": 1.0, "a_bool": True}
    ) is None
    assert plan.execute(dict(row)) == first, "a fallback left the plan altered"


def test_results_are_fresh_objects(native):
    plan = plan_for(native, Scalars).plan
    row = {"an_int": 1, "a_str": "s", "a_float": 1.0, "a_bool": True}
    first, second = plan.execute(dict(row)), plan.execute(dict(row))
    assert first == second
    assert first is not second


def test_hostile_values_do_not_panic(native):
    """No unwrap/panic on user data: every one of these must be handled."""
    plan = plan_for(native, Scalars).plan

    class Exploding:
        def __eq__(self, other):
            raise RuntimeError("boom")

        def __hash__(self):
            return 0

    for hostile in (None, [], {}, object(), Exploding(), float("nan"),
                    float("inf"), b"bytes"):
        outcome = plan.execute(
            {"an_int": hostile, "a_str": "s", "a_float": 1.0, "a_bool": True}
        )
        assert outcome is None or isinstance(outcome, list)


def test_benchmark_corpus_models_are_honestly_reported_ineligible(native):
    """The prototype cannot run the acceptance workloads, and says so.

    This is a finding, not a failure: every corpus model carries Decimal,
    UUID, temporal or container fields. TASK-18 needs it stated plainly rather
    than discovered later.
    """
    from tests.fixtures.model_performance.models import (
        Employee, UnconstrainedScalars,
    )

    for model in (Employee, UnconstrainedScalars):
        model_plan = plan_for(native, model)
        assert model_plan.eligible is False
        assert model_plan.ineligible_fields


# ===========================================================================
# Part 7 -- TASK-18: full-cost comparison and promotion eligibility
# ===========================================================================


def test_a_fallback_does_not_duplicate_a_callback(native):
    """A declined row must cost the Python path exactly once.

    The executor validates only -- it never runs a user callback -- so a
    fallback must not leave a hook having fired twice. This is the property
    that makes "attempt natively, then fall back" safe rather than a
    double-execution hazard.
    """
    events = []

    Hooked = _model("NativeFallbackHook", {"an_int": int, "a_str": str},
                    an_int=Column(required=False, default=0),
                    a_str=Column(required=False, default="x"))

    def post_init(self):
        events.append("hook")
        BaseModel.__post_init__(self)

    Hooked.__post_init__ = post_init
    plan = plan_for(native, Hooked).plan

    events.clear()
    assert plan.execute({"an_int": 2 ** 96, "a_str": "s"}) is None
    assert events == [], "the native attempt ran a user callback"

    Hooked(an_int=2 ** 96, a_str="s")
    assert events == ["hook"], f"callback ran {len(events)} times, expected 1"


def test_fallback_cost_is_reported_in_the_distribution(native):
    """A fallback is additive: the native attempt PLUS the full Python path."""
    from benchmarks.native_validation import eligible_demo_rows, fallback_cost

    report = fallback_cost(native, eligible_demo_rows())
    assert report["rows"] == 5
    assert report["fell_back"] >= 1, "no row exercised the fallback path"
    assert 0.0 < report["fallback_rate"] <= 1.0
    assert "additive" in report["note"]


@pytest.fixture(scope="module")
def full_cost(native):
    """Run the paired-process comparison ONCE; it spawns real subprocesses."""
    from benchmarks.native_validation import full_cost_comparison

    return full_cost_comparison()


def test_full_cost_comparison_uses_paired_processes(full_cost):
    """The decision must rest on process ratios, not a scalar microbenchmark."""
    report = full_cost
    assert report["process_pairs"] >= 4
    assert report["order_alternated"] is True
    assert len(report["paired_ratios_native_over_cython"]) == report["process_pairs"]
    assert len(report["raw"]) == report["process_pairs"]
    for run in report["raw"]:
        assert len(run["cython_ns"]) == report["batches_per_process"]
        assert len(run["native_ns"]) == report["batches_per_process"]


def test_the_boundary_floor_is_measured_and_labelled(full_cost):
    """The decisive number, and the honest label on the misleading one."""
    report = full_cost
    assert report["boundary_only_ns"], "the boundary floor was not measured"
    assert all(share > 0 for share in report["boundary_share_of_cython_construction"])
    # The optimistic ratio must never be presented as an improvement.
    assert "not be quoted as an improvement" in report["why_the_ratio_is_not_a_speed_up"]
    assert "UPPER BOUND" in report["native_side_is_optimistic"]


def test_the_decision_report_exists_and_retains_cython():
    """The persisted decision must be explicit and must match the evidence."""
    import json

    report_path = (
        Path(__file__).resolve().parents[2] / "benchmarks" / "results"
        / "compatible-model-performance" / "rust-sequential.json"
    )
    assert report_path.is_file(), f"{report_path} is missing"
    report = json.loads(report_path.read_text(encoding="utf-8"))

    assert report["decision"] in {"retain_cython", "promote_eligible"}
    assert report["decision"] == "retain_cython", (
        "the report claims the native executor is promotion-eligible; the "
        "measured evidence must then show >=10% additional improvement"
    )
    gate = report["promotion_gate"]
    assert gate["required_additional_improvement_pct"] == 10.0
    assert gate["met"] is False
    assert report["eligibility"]["corpus_workloads_eligible"] == 0
    assert report["measurements"]["boundary_floor_ns"] > 0
