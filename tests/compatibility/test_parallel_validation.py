"""Bounded parallel native execution (FEAT-2 / TASK-19).

``NativePlan.execute_batch`` runs in three strictly separated phases:

1. **snapshot** — GIL held, every row converted to owned Rust values or marked
   ineligible;
2. **detach** — GIL released, workers see only the owned snapshot inside a
   bounded, reusable Rayon pool;
3. **rebuild** — GIL re-acquired, results returned in the *original* row order.

The safety property is structural rather than statistical: **no worker can
touch Python, because nothing Python-shaped crosses into phase 2.** These tests
check the consequences of that — identical results to sequential execution,
deterministic ordering under oversubscription, ineligible rows kept serial in
their own slots, and no callback ever running inside a worker.

Experimental and development-only: no public batch API, no threading default,
nothing wired into ``datamodel``.
"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from benchmarks.native_validation import (  # noqa: E402
    AC9_THROUGHPUT_FACTOR,
    NativeUnavailable,
    descriptors_for,
    eligible_demo_model,
    load_native,
    parallel_ordering_check,
)
from datamodel import BaseModel, Column  # noqa: E402


@pytest.fixture(scope="module")
def native():
    try:
        return load_native(build=True)
    except NativeUnavailable as exc:
        pytest.fail(
            f"the experimental extension could not be built, so the parallel "
            f"experiment is UNVERIFIED (not passing): {exc}"
        )


@pytest.fixture(scope="module")
def plans(native):
    descriptors, ineligible = descriptors_for(eligible_demo_model())
    assert not ineligible
    return {
        "sequential": native.NativePlan(descriptors),
        "parallel": native.NativePlan(descriptors, 4),
        "oversubscribed": native.NativePlan(descriptors, 16),
        "descriptors": descriptors,
    }


def _row(**overrides):
    row = {"an_int": 7, "a_str": "hello", "a_float": 1.5,
           "a_bool": True, "bounded": 5, "short": "ok"}
    row.update(overrides)
    return row


# ===========================================================================
# Part 1 -- bounded, reusable workers; no threading default
# ===========================================================================


def test_a_plan_without_threads_is_sequential_only(plans):
    assert plans["sequential"].threads == 0


def test_a_bounded_pool_reports_its_size(plans):
    assert plans["parallel"].threads == 4
    assert plans["oversubscribed"].threads == 16


def test_zero_threads_means_sequential_not_unbounded(native, plans):
    """Rayon's default is one worker per core; asking for 0 must not get that."""
    plan = native.NativePlan(plans["descriptors"], 0)
    assert plan.threads == 0


def test_the_pool_is_reused_across_batches(plans):
    """The same plan object serves many batches; workers are not per-call."""
    plan = plans["parallel"]
    before = plan.threads
    for _ in range(20):
        plan.execute_batch([_row()], True)
    assert plan.threads == before


def test_no_public_batch_api_or_threading_default_is_introduced():
    class Probe(BaseModel):
        v: int = Column(required=False)

    for forbidden in ("execute_batch", "validate_many", "threads",
                      "parallel", "bulk_create"):
        assert not hasattr(Probe, forbidden), forbidden
        assert not hasattr(Probe(v=1), forbidden), forbidden


# ===========================================================================
# Part 2 -- parallel must equal sequential, exactly and in order
# ===========================================================================


MIXED_ROWS = [
    _row(),                              # all valid
    _row(bounded=99),                    # constraint violation
    _row(short="waytoolong"),            # length violation
    _row(an_int=2 ** 96),                # INELIGIBLE -> serial slot
    _row(an_int=[1]),                    # wrong type -> decided invalid
    _row(an_int=0, a_str="", short=""),  # zero/empty are values
    _row(an_int=True),                   # bool-as-int -> INELIGIBLE
]


def test_parallel_matches_sequential_exactly(plans):
    sequential = plans["sequential"].execute_batch(list(MIXED_ROWS), False)
    parallel = plans["parallel"].execute_batch(list(MIXED_ROWS), True)
    assert sequential == parallel


def test_ordering_is_deterministic_across_repeated_runs(plans):
    """Completion order must never leak into result order."""
    expected = plans["sequential"].execute_batch(list(MIXED_ROWS), False)
    for _ in range(30):
        assert plans["parallel"].execute_batch(list(MIXED_ROWS), True) == expected


def test_ordering_holds_under_oversubscription(plans):
    """16 workers on a 7-row batch: far more threads than work."""
    expected = plans["sequential"].execute_batch(list(MIXED_ROWS), False)
    for _ in range(20):
        assert plans["oversubscribed"].execute_batch(list(MIXED_ROWS), True) == expected


def test_ordering_check_helper_agrees(native):
    report = parallel_ordering_check(native, MIXED_ROWS)
    assert report["identical"] is True
    assert report["ineligible_slots_preserved"] is True


def test_a_large_batch_preserves_row_identity(plans):
    """Every row must map back to its own slot, not just the right multiset."""
    rows = [_row(bounded=(index % 20)) for index in range(500)]
    sequential = plans["sequential"].execute_batch(list(rows), False)
    parallel = plans["parallel"].execute_batch(list(rows), True)
    assert sequential == parallel
    for index, entry in enumerate(parallel):
        expected_ok = 1 <= (index % 20) <= 10
        assert dict(entry)["bounded"] is expected_ok, index


# ===========================================================================
# Part 3 -- ineligible work stays serial, in its own slot
# ===========================================================================


def test_ineligible_rows_are_none_and_keep_their_position(plans):
    result = plans["parallel"].execute_batch(list(MIXED_ROWS), True)
    assert result[3] is None, "the 2**96 row was executed natively"
    assert result[6] is None, "the bool-as-int row was executed natively"
    assert result[0] is not None and result[1] is not None


def test_an_ineligible_plan_returns_all_none(native):
    plan = native.NativePlan([
        ("a", "int", None, None, None, None),
        ("when", "date", None, None, None, None),
    ], 4)
    assert plan.eligible is False
    result = plan.execute_batch([{"a": 1, "when": "x"}, {"a": 2, "when": "y"}], True)
    assert result == [None, None]


def test_a_batch_of_only_ineligible_rows_is_all_none(plans):
    rows = [_row(an_int=2 ** 96), _row(an_int=True)]
    assert plans["parallel"].execute_batch(rows, True) == [None, None]


# ===========================================================================
# Part 4 -- no worker touches Python
# ===========================================================================


def test_no_callback_runs_during_batch_execution(plans):
    """The decisive safety property, checked by consequence.

    Nothing Python-shaped reaches phase 2, so a user callback cannot run
    there. If one ever did, this counter would move.
    """
    events = []

    class Watcher:
        def __eq__(self, other):
            events.append("eq")
            return NotImplemented

        def __hash__(self):
            events.append("hash")
            return 0

    rows = [_row(), _row(an_int=Watcher()), _row()]
    events.clear()
    result = plans["parallel"].execute_batch(rows, True)
    assert len(result) == 3
    assert events == [], f"Python was called during execution: {events}"


def test_batch_execution_does_not_construct_models(plans):
    """The executor validates; it must never build an instance or run a hook."""
    built = []

    Hooked = type("ParallelHooked", (BaseModel,), {
        "__annotations__": {"an_int": int},
        "an_int": Column(required=False, default=0),
        "Meta": type("Meta", (), {"strict": False}),
        "__post_init__": lambda self: built.append("hook"),
    })
    assert Hooked  # the model exists but must not be touched by the executor

    built.clear()
    plans["parallel"].execute_batch([_row() for _ in range(50)], True)
    assert built == []


def test_hostile_values_in_a_batch_do_not_panic(plans):
    class Exploding:
        def __eq__(self, other):
            raise RuntimeError("boom")

        def __hash__(self):
            return 0

    rows = [_row(an_int=hostile) for hostile in
            (None, [], {}, object(), Exploding(), float("nan"), b"bytes")]
    result = plans["parallel"].execute_batch(rows, True)
    assert len(result) == len(rows)
    for entry in result:
        assert entry is None or isinstance(entry, list)


# ===========================================================================
# Part 5 -- boundaries: empty, single, malformed
# ===========================================================================


def test_empty_batch(plans):
    assert plans["parallel"].execute_batch([], True) == []
    assert plans["sequential"].execute_batch([], False) == []


def test_single_row_batch(plans):
    result = plans["parallel"].execute_batch([_row()], True)
    assert len(result) == 1
    assert all(ok for _, ok in result[0])


@pytest.mark.parametrize("size", [1, 2, 10, 100])
def test_batch_length_is_always_preserved(plans, size):
    rows = [_row() for _ in range(size)]
    assert len(plans["parallel"].execute_batch(rows, True)) == size
    assert len(plans["sequential"].execute_batch(rows, False)) == size


def test_malformed_rows_raise_rather_than_being_guessed(plans):
    with pytest.raises(TypeError):
        plans["parallel"].execute_batch(["not-a-dict"], True)


def test_parallel_flag_is_honoured_but_never_required(plans):
    """`parallel=True` on a pool-less plan must still work, sequentially."""
    result = plans["sequential"].execute_batch([_row()], True)
    assert len(result) == 1
    assert all(ok for _, ok in result[0])


# ===========================================================================
# Part 6 -- the recorded decision
# ===========================================================================


def test_the_parallel_decision_report_exists_and_retains_sequential():
    import json

    report_path = (
        Path(__file__).resolve().parents[2] / "benchmarks" / "results"
        / "compatible-model-performance" / "rust-parallel.json"
    )
    assert report_path.is_file(), f"{report_path} is missing"
    report = json.loads(report_path.read_text(encoding="utf-8"))

    assert report["decision"] in {"retain_sequential", "promote_parallel"}
    gate = report["promotion_gate"]
    assert gate["required_throughput_factor"] == AC9_THROUGHPUT_FACTOR
    if report["decision"] == "retain_sequential":
        assert gate["met"] is False
        assert report["grid"]["ac9_met_at_any_size"] is False
        assert report["grid"]["crossover_size"] is None
    for size in ("1", "10", "100", "1000", "10000"):
        assert size in report["grid"]["sizes"], f"size {size} was not measured"
