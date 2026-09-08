#!/usr/bin/env python
"""Paired reference/candidate performance harness for FEAT-2 (TASK-9).

This implements the measurement protocol in §4 of
``sdd/specs/compatible-model-performance.spec.md`` and is the **only** protocol
later tasks may use to claim a speed-up or a regression.

Protocol, as implemented
========================

* **Paired fresh processes.**  At least 7 process pairs per backend, each a
  brand-new interpreter running that environment's own venv against that
  environment's own compiled artifacts.  Order alternates: pair 0 runs the
  reference first, pair 1 the candidate first, and so on, so a warm-up or
  thermal trend cannot favour one side.
* **Warm-up.**  1,000 operations of the workload before any batch is recorded.
* **Batches, not calls.**  At least 30 batches of 2,000 constructions.  The
  clock is read exactly **twice per batch** — never around an individual
  constructor — and that count is recorded in the output so the claim is
  checkable rather than asserted.
* **Input preparation is untimed.**  Every batch's payloads are built before
  the timer starts, so the measurement isolates the constructor.
* **Instrumentation is off.**  Acceptance runs refuse to proceed if a trace
  hook, a profile hook or ``tracemalloc`` is active, and they never enable one.
  Allocation figures come from a *separate* diagnostic pass.
* **Statistics.**  Median per-build latency and a p95 upper-tail batch latency
  per process; process-level **paired** ratios; a 95% confidence interval on
  the paired ratio by seeded bootstrap and by a t-interval on log-ratios.  A
  claimed improvement requires the whole interval to sit below 1.0.

Smoke mode
==========

``--smoke`` shrinks every count so the harness can be exercised in a test.  Its
output carries ``"acceptance": false`` and a ``"warning"`` string, and
:func:`is_acceptance_run` returns ``False`` for it.  A smoke report can never be
mistaken for a release measurement.

Usage
=====

::

    # full protocol (minutes, needs an otherwise idle machine)
    python benchmarks/model_performance.py \\
        --output benchmarks/results/compatible-model-performance/baseline.json

    # fast schema/provenance check
    python benchmarks/model_performance.py --smoke --output /tmp/smoke.json

This is a development-only tool.  It adds no runtime dependency: everything
below is standard library plus the repository's own fixture corpus.
"""
from __future__ import annotations

import argparse
import gc
import json
import math
import os
import platform
import random
import statistics
import subprocess
import sys
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

HARNESS_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = (
    HARNESS_ROOT / "benchmarks" / "results" / "compatible-model-performance"
    / "baseline.json"
)

#: Bumped when the report schema changes incompatibly.
REPORT_SCHEMA_VERSION = 1

# --- protocol constants (spec §4 "Performance protocol") -------------------

#: Eight, not seven. The spec's floor is 7 paired processes, but the order
#: alternates within each pair, so an ODD count leaves the schedule
#: unbalanced: with 7 pairs the reference would run first 4 times and the
#: candidate only 3. Any within-pair position effect (the second process
#: starts on a warmer core) would then be charged systematically to one side.
#: An even count makes first/second positions exactly equal.
ACCEPTANCE_PROCESS_PAIRS = 8
ACCEPTANCE_WARMUP_OPERATIONS = 1_000
ACCEPTANCE_BATCHES = 30
ACCEPTANCE_BATCH_SIZE = 2_000

SMOKE_PROCESS_PAIRS = 2
SMOKE_WARMUP_OPERATIONS = 25
SMOKE_BATCHES = 3
SMOKE_BATCH_SIZE = 50

#: Bootstrap resamples for the paired-ratio confidence interval.  Fixed seed:
#: the same samples must always produce the same interval.
BOOTSTRAP_RESAMPLES = 10_000
BOOTSTRAP_SEED = 20260908

CHILD_TIMEOUT_SECONDS = 3_600


class BenchmarkError(RuntimeError):
    """Raised when a run cannot be trusted and must not be reported."""


# ===========================================================================
# Workloads
# ===========================================================================


@dataclass(frozen=True)
class Workload:
    """One measurable operation, with its own batch size.

    ``batch_size`` may be smaller than the protocol default for expensive
    workloads (spec §4 permits it "if recorded and equal between variants").
    It is recorded per workload and is by construction identical for both
    backends, because both read this same table.
    """

    name: str
    kind: str
    description: str
    batch_size_acceptance: int = ACCEPTANCE_BATCH_SIZE
    #: Corpus case supplying the payload, when the workload builds a model.
    case: Optional[str] = None
    tags: Tuple[str, ...] = ()


WORKLOADS: Tuple[Workload, ...] = (
    Workload("employee_raw", "construct",
             "Employee built from all-string input (full converter chain)",
             case="employee_raw", tags=("ac5", "employee", "raw")),
    Workload("employee_native", "construct",
             "Employee built from already-typed input",
             case="employee_native", tags=("ac5", "employee", "native")),
    Workload("unconstrained_native", "construct",
             "Eight unconstrained scalars, already typed",
             case="unconstrained_native", tags=("ac3", "scalar")),
    Workload("unconstrained_raw", "construct",
             "Eight unconstrained scalars parsed from strings",
             case="unconstrained_raw", tags=("ac3", "scalar")),
    Workload("constrained_valid", "construct",
             "Five constrained scalars inside their bounds",
             case="constrained_valid", tags=("constraint",)),
    Workload("client_nested", "construct",
             "ORM-like nested hydration with as_objects and an alias",
             case="client_with_object", tags=("ac6", "orm", "nested")),
    Workload("container_full", "construct",
             "Typed containers of nested models, tuples and mappings",
             batch_size_acceptance=500,
             case="container_full", tags=("ac6", "container", "nested")),
    Workload("wide_native", "construct",
             "50-field model, already typed",
             batch_size_acceptance=500,
             case="wide_native", tags=("wide",)),
    Workload("wide_raw", "construct",
             "50-field model parsed from strings",
             batch_size_acceptance=500,
             case="wide_raw", tags=("wide",)),
    Workload("callback_hooks", "construct",
             "Custom validator and custom encoder callbacks",
             case="callback_valid", tags=("ac6", "callback")),
    Workload("invalid_input", "construct_invalid",
             "Construction that raises: error construction path",
             case="employee_age_below_min", tags=("ac6", "invalid")),
    Workload("class_creation", "class_creation",
             "Cold model class creation through the metaclass",
             batch_size_acceptance=200, tags=("ac6", "cold")),
    Workload("assignment", "assignment",
             "Attribute assignment on a built model (history + conversion)",
             case="employee_native", tags=("ac6", "assignment")),
    Workload("to_dict", "to_dict",
             "Dictionary conversion of a built model",
             case="employee_native", tags=("ac6", "serialization")),
    Workload("json_warm", "json",
             "JSON serialization of a built model (warm encoder)",
             case="employee_native", tags=("ac6", "ac10", "serialization")),
)

WORKLOADS_BY_NAME: Dict[str, Workload] = {w.name: w for w in WORKLOADS}


def batch_size_for(workload: Workload, smoke: bool) -> int:
    if smoke:
        return min(SMOKE_BATCH_SIZE, workload.batch_size_acceptance)
    return workload.batch_size_acceptance


# ===========================================================================
# Child side: preparing and timing one workload
# ===========================================================================


def _child_prepare(workload: Workload, count: int) -> Tuple[Callable[[], Any], str]:
    """Return ``(operation, note)`` with **all** preparation already done.

    The returned callable takes no arguments and performs exactly one unit of
    the workload.  Everything it needs — payload dictionaries, pre-built model
    instances, class namespaces — is constructed here, outside the timed
    region, because the protocol isolates the operation and not its inputs.
    """
    from tests.fixtures.model_performance import cases as cases_mod

    if workload.kind in ("construct", "construct_invalid"):
        case = cases_mod.CASES_BY_NAME[workload.case]
        model = case.resolve_model()
        payloads = [cases_mod.build_kwargs(case) for _ in range(count)]
        cursor = iter(payloads)
        if workload.kind == "construct":
            def operation(_next=cursor.__next__, _model=model):
                return _model(**_next())
        else:
            def operation(_next=cursor.__next__, _model=model):
                try:
                    return _model(**_next())
                except Exception as exc:  # noqa: BLE001 - the error IS the work
                    return exc
        return operation, f"{count} payloads prepared before timing"

    if workload.kind == "class_creation":
        from datamodel import BaseModel, Column

        namespaces = []
        for index in range(count):
            annotations = {"a": int, "b": str, "c": float}
            namespaces.append((
                f"ColdModel{index}",
                {
                    "__annotations__": annotations,
                    "__module__": "benchmarks.model_performance",
                    "a": Column(required=False, default=0),
                    "b": Column(required=False, default=''),
                    "c": Column(required=False, default=0.0),
                },
            ))
        cursor = iter(namespaces)

        def operation(_next=cursor.__next__, _base=BaseModel):
            name, namespace = _next()
            return type(name, (_base,), dict(namespace))

        return operation, f"{count} class namespaces prepared before timing"

    case = cases_mod.CASES_BY_NAME[workload.case]
    model = case.resolve_model()

    if workload.kind == "assignment":
        instances = [model(**cases_mod.build_kwargs(case)) for _ in range(count)]
        cursor = iter(instances)

        def operation(_next=cursor.__next__):
            instance = _next()
            instance.name = "Reassigned Name"
            return instance

        return operation, f"{count} instances built before timing"

    # to_dict / json operate repeatedly on one warm instance: the cost under
    # test is the conversion, not the construction.
    instance = model(**cases_mod.build_kwargs(case))
    if workload.kind == "to_dict":
        def operation(_instance=instance):
            return _instance.to_dict()

        return operation, "one instance built before timing; to_dict called warm"

    if workload.kind == "json":
        instance.json()  # warm the encoder; cold cost is reported separately

        def operation(_instance=instance):
            return _instance.json()

        return operation, "one instance built and encoder warmed before timing"

    raise BenchmarkError(f"unknown workload kind: {workload.kind!r}")


def _child_assert_clean_for_timing() -> Dict[str, Any]:
    """Refuse to time anything while instrumentation or rivals are running."""
    import tracemalloc

    problems: List[str] = []
    if sys.gettrace() is not None:
        problems.append("a trace hook is installed (coverage/debugger?)")
    if sys.getprofile() is not None:
        problems.append("a profile hook is installed")
    if tracemalloc.is_tracing():
        problems.append("tracemalloc is tracing")
    active = threading.active_count()
    if active != 1:
        problems.append(f"{active} threads are active; timing must be single-threaded")
    if problems:
        raise BenchmarkError(
            "refusing to record acceptance timings: " + "; ".join(problems)
        )
    return {
        "trace_hook": False,
        "profile_hook": False,
        "tracemalloc": False,
        "active_threads": active,
    }


def _child_time_workload(
    workload: Workload,
    batches: int,
    batch_size: int,
    warmup: int,
    acceptance: bool,
) -> Dict[str, Any]:
    """Time one workload in this process and return its raw samples."""
    environment_state = _child_assert_clean_for_timing() if acceptance else None

    # Warm-up: same operation, discarded.
    warm_operation, _ = _child_prepare(workload, warmup)
    for _ in range(warmup):
        warm_operation()

    batch_records: List[Dict[str, Any]] = []
    gc_was_enabled = gc.isenabled()
    for index in range(batches):
        operation, note = _child_prepare(workload, batch_size)
        gc.collect()
        gc.disable()
        try:
            # --- timed region: exactly two clock reads, never inside the loop
            start = time.perf_counter_ns()
            for _ in range(batch_size):
                operation()
            end = time.perf_counter_ns()
            # --- end timed region
        finally:
            if gc_was_enabled:
                gc.enable()
        elapsed = end - start
        batch_records.append({
            "index": index,
            "elapsed_ns": elapsed,
            "operations": batch_size,
            "per_operation_ns": elapsed / batch_size,
            "timer_calls": 2,
            "preparation": note,
        })

    per_operation = [record["per_operation_ns"] for record in batch_records]
    batch_latency = [record["elapsed_ns"] for record in batch_records]
    return {
        "workload": workload.name,
        "kind": workload.kind,
        "batches": batches,
        "batch_size": batch_size,
        "warmup_operations": warmup,
        "gc_disabled_during_timing": True,
        "timer_calls_total": 2 * batches,
        "instrumentation": environment_state,
        "samples": batch_records,
        "median_per_operation_ns": statistics.median(per_operation),
        "mean_per_operation_ns": statistics.fmean(per_operation),
        "stdev_per_operation_ns": (
            statistics.stdev(per_operation) if len(per_operation) > 1 else 0.0
        ),
        "p95_batch_latency_ns": percentile(batch_latency, 95),
        "min_per_operation_ns": min(per_operation),
        "max_per_operation_ns": max(per_operation),
    }


def _child_diagnostics(workload: Workload, iterations: int) -> Dict[str, Any]:
    """Allocation figures, collected in a **separate**, untimed pass.

    ``tracemalloc`` roughly doubles call cost, so this never runs during a
    timed batch; spec §4 requires the separation explicitly.
    """
    import tracemalloc

    operation, _ = _child_prepare(workload, iterations)
    gc.collect()
    tracemalloc.start()
    baseline_current, _ = tracemalloc.get_traced_memory()
    retained = []
    for _ in range(iterations):
        retained.append(operation())
    peak_current, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    # Retained: what survives while the results are still referenced, minus the
    # container holding them.
    retained_bytes = peak_current - baseline_current
    del retained
    gc.collect()
    return {
        "workload": workload.name,
        "iterations": iterations,
        "peak_traced_bytes": peak,
        "peak_temporary_bytes": peak - baseline_current,
        "retained_while_referenced_bytes": retained_bytes,
        "retained_per_operation_bytes": retained_bytes / iterations if iterations else 0,
        "note": (
            "collected with tracemalloc in a separate pass; these numbers are "
            "NOT comparable with the timed batches and were not recorded while "
            "any acceptance timing was in progress"
        ),
    }


#: A fixed, allocation-free integer loop. Its runtime depends only on the core
#: this process landed on and its clock speed -- never on `datamodel`. Timing it
#: in every child turns "was this process on a slow core?" from a suspicion into
#: a recorded number.
CALIBRATION_ITERATIONS = 2_000_000


def _child_calibrate() -> Dict[str, Any]:
    """Time a fixed pure-Python loop to expose per-process CPU-speed noise."""
    def _spin(count: int) -> int:
        total = 0
        for index in range(count):
            total += index ^ (index >> 3)
        return total

    _spin(50_000)  # warm the loop itself
    samples = []
    for _ in range(3):
        start = time.perf_counter_ns()
        _spin(CALIBRATION_ITERATIONS)
        samples.append(time.perf_counter_ns() - start)
    return {
        "iterations": CALIBRATION_ITERATIONS,
        "samples_ns": samples,
        "median_ns": statistics.median(samples),
        "note": (
            "pure-Python integer loop, independent of datamodel; a process "
            "whose calibration deviates from the median indicates CPU "
            "frequency scaling or core migration, not a code change"
        ),
    }


def _child_pin_cpu(cpu: Optional[int]) -> Dict[str, Any]:
    """Pin this process to one CPU when the platform allows it."""
    if cpu is None:
        return {"requested": None, "applied": False,
                "reason": "not requested"}
    try:
        os.sched_setaffinity(0, {cpu})
    except (AttributeError, OSError) as exc:
        return {"requested": cpu, "applied": False, "reason": str(exc)}
    return {"requested": cpu, "applied": True,
            "effective": sorted(os.sched_getaffinity(0))}


def _child_runtime_provenance() -> Dict[str, Any]:
    import datamodel

    try:
        from datamodel.rs_parsers import HAS_RUST
    except Exception:  # pragma: no cover - defensive
        HAS_RUST = None

    try:
        affinity = sorted(os.sched_getaffinity(0))
    except (AttributeError, OSError):  # pragma: no cover - non-Linux
        affinity = None
    try:
        load = os.getloadavg()
    except (AttributeError, OSError):  # pragma: no cover - non-POSIX
        load = None

    try:
        import Cython
        cython_version = Cython.__version__
    except Exception:  # pragma: no cover - defensive
        cython_version = None

    try:
        import pydantic
        pydantic_version = pydantic.VERSION
    except Exception:
        pydantic_version = None

    return {
        "datamodel_file": datamodel.__file__,
        "datamodel_version": getattr(datamodel.version, "__version__", None),
        "has_rust_parsers": HAS_RUST,
        "python": sys.version,
        "python_executable": sys.executable,
        "implementation": platform.python_implementation(),
        "platform": platform.platform(),
        "processor": platform.processor(),
        "machine": platform.machine(),
        "cpu_count": os.cpu_count(),
        "cpu_affinity": affinity,
        "loadavg_at_start": load,
        "gc_policy": "collected then disabled inside each timed batch",
        "cython_version": cython_version,
        "pydantic_version": pydantic_version,
        "note_pydantic": (
            "pydantic is a contextual reference only; acceptance decisions use "
            "same-contract old/new python-datamodel ratios exclusively"
        ),
    }


def _child_main() -> int:
    request = json.loads(sys.stdin.read())
    expect_root = Path(request["expect_root"]).resolve()
    harness_root = Path(request["harness_root"]).resolve()

    try:
        sys.path.insert(0, str(expect_root))
        import datamodel  # noqa: F401

        loaded = Path(datamodel.__file__).resolve()
        if expect_root not in loaded.parents:
            raise BenchmarkError(
                f"imported datamodel from {loaded}, not from {expect_root}: "
                "the environment is not isolated, so its timings are meaningless"
            )
        while str(expect_root) in sys.path:
            sys.path.remove(str(expect_root))
        sys.path.insert(0, str(harness_root))

        pinning = _child_pin_cpu(request.get("pin_cpu"))
        runtime = _child_runtime_provenance()
        runtime["cpu_pinning"] = pinning
        runtime["calibration"] = _child_calibrate()
        payload: Dict[str, Any] = {"runtime": runtime, "error": None}
        if request["mode"] == "diagnostics":
            payload["diagnostics"] = [
                _child_diagnostics(
                    WORKLOADS_BY_NAME[name], request["iterations"]
                )
                for name in request["workloads"]
            ]
        else:
            payload["workloads"] = [
                _child_time_workload(
                    WORKLOADS_BY_NAME[name],
                    batches=request["batches"],
                    batch_size=batch_size_for(
                        WORKLOADS_BY_NAME[name], request["smoke"]
                    ),
                    warmup=request["warmup"],
                    acceptance=request["acceptance"],
                )
                for name in request["workloads"]
            ]
    except BaseException as exc:  # noqa: BLE001 - report, never crash silently
        import traceback

        payload = {
            "error": {
                "type": type(exc).__name__,
                "message": f"{exc}\n{traceback.format_exc()}",
            }
        }

    sys.stdout.write(json.dumps(payload))
    sys.stdout.flush()
    return 0


# ===========================================================================
# Statistics
# ===========================================================================


def percentile(values: Sequence[float], percent: float) -> float:
    """Linear-interpolation percentile.

    Defined explicitly rather than left to a library so "upper-tail batch
    latency" means one thing across every future comparison: ``p95`` is the
    linear interpolation between the two order statistics bracketing the
    0.95 position of the sorted batch latencies.
    """
    if not values:
        raise ValueError("percentile of an empty sample")
    ordered = sorted(values)
    if len(ordered) == 1:
        return float(ordered[0])
    position = (len(ordered) - 1) * (percent / 100.0)
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return float(ordered[int(position)])
    weight = position - lower
    return float(ordered[lower] * (1 - weight) + ordered[upper] * weight)


#: Two-sided 95% critical values of Student's t, indexed by degrees of freedom.
#: Only used as a cross-check on the bootstrap interval; no SciPy dependency.
_T_95: Dict[int, float] = {
    1: 12.706, 2: 4.303, 3: 3.182, 4: 2.776, 5: 2.571, 6: 2.447, 7: 2.365,
    8: 2.306, 9: 2.262, 10: 2.228, 11: 2.201, 12: 2.179, 13: 2.160, 14: 2.145,
    15: 2.131, 16: 2.120, 17: 2.110, 18: 2.101, 19: 2.093, 20: 2.086,
    21: 2.080, 22: 2.074, 23: 2.069, 24: 2.064, 25: 2.060, 26: 2.056,
    27: 2.052, 28: 2.048, 29: 2.045, 30: 2.042,
}


def _t_critical(degrees_of_freedom: int) -> float:
    if degrees_of_freedom <= 0:
        return float("nan")
    if degrees_of_freedom in _T_95:
        return _T_95[degrees_of_freedom]
    return 1.96  # large-sample limit


def bootstrap_ratio_interval(
    ratios: Sequence[float],
    resamples: int = BOOTSTRAP_RESAMPLES,
    seed: int = BOOTSTRAP_SEED,
) -> Dict[str, float]:
    """Seeded percentile bootstrap of the mean paired ratio."""
    if not ratios:
        raise ValueError("no paired ratios")
    rng = random.Random(seed)
    size = len(ratios)
    means = []
    for _ in range(resamples):
        means.append(
            statistics.fmean(ratios[rng.randrange(size)] for _ in range(size))
        )
    means.sort()
    return {
        "method": "percentile bootstrap of the mean paired ratio",
        "resamples": resamples,
        "seed": seed,
        "low": percentile(means, 2.5),
        "high": percentile(means, 97.5),
    }


def log_ratio_interval(ratios: Sequence[float]) -> Dict[str, float]:
    """t-interval on log ratios, back-transformed. Cross-check on the bootstrap."""
    if len(ratios) < 2:
        return {"method": "t-interval on log ratios", "low": float("nan"),
                "high": float("nan"), "note": "needs at least two pairs"}
    logs = [math.log(value) for value in ratios]
    mean = statistics.fmean(logs)
    stdev = statistics.stdev(logs)
    n = len(logs)
    half_width = _t_critical(n - 1) * stdev / math.sqrt(n)
    return {
        "method": "t-interval on log ratios, back-transformed",
        "degrees_of_freedom": n - 1,
        "low": math.exp(mean - half_width),
        "high": math.exp(mean + half_width),
    }


def _position_balance(order_log: List[List[str]]) -> Dict[str, Any]:
    """Did each backend run first exactly as often as it ran second?

    Within a pair the two processes run one after the other, and the second one
    starts on a warmer core.  If one backend occupies the second slot more
    often than the other, that thermal difference is charged to it as though it
    were a code difference.  This records the schedule so the reader can see
    the counterbalancing actually happened.
    """
    first_counts: Dict[str, int] = {}
    for order in order_log:
        first_counts[order[0]] = first_counts.get(order[0], 0) + 1
    counts = sorted(first_counts.values())
    balanced = len(set(counts)) <= 1 and len(first_counts) == 2
    return {
        "pairs": len(order_log),
        "times_each_backend_ran_first": first_counts,
        "balanced": balanced,
        "why_it_matters": (
            "the second process in a pair starts on a warmer core; an "
            "unbalanced schedule turns that into a systematic bias against "
            "whichever backend runs second more often"
        ),
    }


def _noise_floor(summaries: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
    """The smallest effect this run could actually have resolved.

    A 95% interval of, say, [0.996, 1.022] means the measurement cannot
    distinguish anything smaller than about 1.3% in either direction.  Recording
    that explicitly matters because AC6 allows a 5% regression and AC5 requires
    a 20% improvement: a later task must be able to see at a glance whether its
    machine was quiet enough for those thresholds to mean anything.
    """
    half_widths = {}
    for name, summary in summaries.items():
        interval = summary["median_ratio_ci95_bootstrap"]
        half_widths[name] = (interval["high"] - interval["low"]) / 2.0
    values = sorted(half_widths.values())
    if not values:
        return {"available": False}
    median = statistics.median(values)
    worst = max(values)
    return {
        "available": True,
        "definition": (
            "half-width of the 95% bootstrap interval on the paired median "
            "ratio, expressed as a fraction of 1.0"
        ),
        "per_workload": half_widths,
        "median_resolvable_effect": median,
        "worst_resolvable_effect": worst,
        "can_resolve_ac6_5pct_regression": worst < 0.05,
        "can_resolve_ac5_20pct_improvement": worst < 0.20,
        "guidance": (
            "an effect smaller than the worst resolvable effect must be "
            "reported as inconclusive and re-measured in a quieter "
            "environment, never rounded into a claim"
        ),
        "multiple_comparisons": {
            "workloads": len(summaries),
            "expected_false_flags_per_run": round(0.05 * len(summaries), 2),
            "caution": (
                "each verdict uses an independent 95% interval, so across "
                f"{len(summaries)} workloads roughly "
                f"{0.05 * len(summaries):.1f} spurious 'regression' or "
                "'improvement' labels are expected per run by chance alone. "
                "A single flagged workload whose effect is near the noise "
                "floor is not evidence; look for an effect that is large "
                "relative to the resolvable effect, or that reproduces across "
                "independent runs."
            ),
        },
    }


def _noise_report(runs: Dict[str, List[Dict[str, Any]]]) -> Dict[str, Any]:
    """Expose per-process CPU-speed noise so it cannot be mistaken for a result.

    Every child times an identical pure-Python loop that never touches
    ``datamodel``.  If one process's calibration is far from the median, that
    process ran on a slower core (or at a lower clock) and *all* of its numbers
    are shifted -- a fact that must be visible in the report rather than
    silently folded into a ratio.

    Nothing here rescales a measurement.  Normalising timings by a calibration
    factor would be massaging the data; reporting the factor is not.
    """
    entries: List[Dict[str, Any]] = []
    for side, side_runs in runs.items():
        for run in side_runs:
            calibration = run["runtime"].get("calibration") or {}
            entries.append({
                "side": side,
                "pair": run["pair"],
                "calibration_median_ns": calibration.get("median_ns"),
                "cpu_pinning": run["runtime"].get("cpu_pinning"),
                "loadavg_at_start": run["runtime"].get("loadavg_at_start"),
            })
    values = [e["calibration_median_ns"] for e in entries
              if e["calibration_median_ns"]]
    if not values:
        return {"available": False, "processes": entries}

    median = statistics.median(values)
    spread = (max(values) - min(values)) / median if median else 0.0
    for entry in entries:
        value = entry["calibration_median_ns"]
        entry["deviation_from_median"] = (
            (value - median) / median if value and median else None
        )
        entry["suspect"] = bool(
            value and median and abs(value - median) / median > 0.10
        )
    suspects = [e for e in entries if e["suspect"]]
    return {
        "available": True,
        "calibration_median_ns": median,
        "calibration_spread": spread,
        "suspect_processes": len(suspects),
        "usable_environment": spread <= 0.10,
        "guidance": (
            "spec §4: if machine noise prevents distinguishing a 5% regression, "
            "rerun in a controlled environment rather than declare success. A "
            "calibration spread above 10% means this machine was not quiet; "
            "treat every inconclusive verdict as 'measure again', not 'no change'."
        ),
        "processes": entries,
    }


def summarise_workload(
    name: str,
    reference_processes: Sequence[Dict[str, Any]],
    candidate_processes: Sequence[Dict[str, Any]],
) -> Dict[str, Any]:
    """Paired summary for one workload across all process pairs."""
    reference_medians = [p["median_per_operation_ns"] for p in reference_processes]
    candidate_medians = [p["median_per_operation_ns"] for p in candidate_processes]
    reference_p95 = [p["p95_batch_latency_ns"] for p in reference_processes]
    candidate_p95 = [p["p95_batch_latency_ns"] for p in candidate_processes]

    pairs = min(len(reference_medians), len(candidate_medians))
    median_ratios = [
        candidate_medians[i] / reference_medians[i] for i in range(pairs)
    ]
    p95_ratios = [candidate_p95[i] / reference_p95[i] for i in range(pairs)]

    bootstrap = bootstrap_ratio_interval(median_ratios)
    t_interval = log_ratio_interval(median_ratios)
    summary = {
        "workload": name,
        "process_pairs": pairs,
        "reference": _describe_series(reference_medians, reference_p95),
        "candidate": _describe_series(candidate_medians, candidate_p95),
        "paired_median_ratios": median_ratios,
        "paired_p95_ratios": p95_ratios,
        "median_ratio_point_estimate": statistics.fmean(median_ratios),
        "p95_ratio_point_estimate": statistics.fmean(p95_ratios),
        "median_ratio_ci95_bootstrap": bootstrap,
        "median_ratio_ci95_log_t": t_interval,
    }
    summary["verdict"] = _verdict(summary)
    return summary


def _describe_series(medians: Sequence[float], p95s: Sequence[float]) -> Dict[str, Any]:
    return {
        "process_medians_ns": list(medians),
        "median_of_process_medians_ns": statistics.median(medians),
        "mean_of_process_medians_ns": statistics.fmean(medians),
        "stdev_of_process_medians_ns": (
            statistics.stdev(medians) if len(medians) > 1 else 0.0
        ),
        "relative_stdev": (
            statistics.stdev(medians) / statistics.fmean(medians)
            if len(medians) > 1 and statistics.fmean(medians) else 0.0
        ),
        "process_p95_batch_ns": list(p95s),
        "median_p95_batch_ns": statistics.median(p95s),
    }


def _verdict(summary: Dict[str, Any]) -> Dict[str, Any]:
    """Classify the result under the spec's decision rule.

    An improvement may only be claimed when the *entire* 95% interval lies
    below 1.0; a regression only when it lies entirely above.  Anything else is
    inconclusive — which, per spec §4, means rerun in a controlled environment,
    not "call it a win".
    """
    low = summary["median_ratio_ci95_bootstrap"]["low"]
    high = summary["median_ratio_ci95_bootstrap"]["high"]
    if high < 1.0:
        label = "improvement"
    elif low > 1.0:
        label = "regression"
    else:
        label = "inconclusive"
    return {
        "label": label,
        "ci_low": low,
        "ci_high": high,
        "rule": (
            "improvement requires the whole 95% CI below 1.0; regression "
            "requires it entirely above 1.0; otherwise inconclusive"
        ),
        "improvement_pct_point_estimate": (
            (1.0 - summary["median_ratio_point_estimate"]) * 100.0
        ),
    }


# ===========================================================================
# Parent side: orchestration
# ===========================================================================


@dataclass
class BenchmarkPlan:
    """Everything that decides whether a report is an acceptance measurement."""

    smoke: bool = False
    process_pairs: int = ACCEPTANCE_PROCESS_PAIRS
    batches: int = ACCEPTANCE_BATCHES
    warmup: int = ACCEPTANCE_WARMUP_OPERATIONS
    workloads: Tuple[str, ...] = tuple(w.name for w in WORKLOADS)
    diagnostics_iterations: int = 2_000
    run_diagnostics: bool = True
    #: CPU to pin every child to. Runs are strictly sequential, so pinning both
    #: backends to the SAME core is correct: it removes core-migration noise
    #: without giving either side an advantage.
    pin_cpu: Optional[int] = None

    @classmethod
    def acceptance(cls, **overrides: Any) -> "BenchmarkPlan":
        return cls(**overrides)

    @classmethod
    def smoke_plan(cls, **overrides: Any) -> "BenchmarkPlan":
        base = dict(
            smoke=True,
            process_pairs=SMOKE_PROCESS_PAIRS,
            batches=SMOKE_BATCHES,
            warmup=SMOKE_WARMUP_OPERATIONS,
            diagnostics_iterations=50,
        )
        base.update(overrides)
        return cls(**base)

    def meets_acceptance_protocol(self) -> List[str]:
        """Reasons this plan is *not* an acceptance run (empty list = it is)."""
        problems: List[str] = []
        if self.smoke:
            problems.append("plan is marked smoke")
        if self.process_pairs < ACCEPTANCE_PROCESS_PAIRS:
            problems.append(
                f"{self.process_pairs} process pairs "
                f"< required {ACCEPTANCE_PROCESS_PAIRS}"
            )
        if self.process_pairs % 2 != 0:
            problems.append(
                f"{self.process_pairs} process pairs is odd, so the "
                "first/second execution order cannot be balanced between the "
                "two backends"
            )
        if self.batches < ACCEPTANCE_BATCHES:
            problems.append(f"{self.batches} batches < required {ACCEPTANCE_BATCHES}")
        if self.warmup < ACCEPTANCE_WARMUP_OPERATIONS:
            problems.append(
                f"{self.warmup} warm-up operations "
                f"< required {ACCEPTANCE_WARMUP_OPERATIONS}"
            )
        for name in self.workloads:
            workload = WORKLOADS_BY_NAME[name]
            if batch_size_for(workload, self.smoke) < workload.batch_size_acceptance:
                problems.append(f"{name}: batch size below its recorded acceptance size")
        return problems


def is_acceptance_run(report: Dict[str, Any]) -> bool:
    """True only for a report produced under the full protocol."""
    return bool(report.get("acceptance")) and not report.get("protocol_shortfalls")


def _invoke_child(env, request: Dict[str, Any]) -> Dict[str, Any]:
    request = dict(request)
    request["harness_root"] = str(HARNESS_ROOT)
    request["expect_root"] = str(env.root)

    child_env = dict(os.environ)
    child_env.pop("PYTHONPATH", None)
    child_env["PYTHONNOUSERSITE"] = "1"
    child_env["PYTHONDONTWRITEBYTECODE"] = "1"
    child_env["PYTHONHASHSEED"] = "0"

    completed = subprocess.run(
        [str(env.python), str(Path(__file__).resolve()), "--worker"],
        input=json.dumps(request),
        capture_output=True,
        text=True,
        cwd=str(env.root),
        env=child_env,
        timeout=CHILD_TIMEOUT_SECONDS,
    )
    if completed.returncode != 0:
        raise BenchmarkError(
            f"{env.name}: child exited {completed.returncode}\n"
            f"--- stderr ---\n{completed.stderr}"
        )
    payload = json.loads(completed.stdout)
    if payload.get("error"):
        raise BenchmarkError(
            f"{env.name}: {payload['error']['type']}: {payload['error']['message']}"
        )
    return payload


def _validate_provenance(environments) -> Dict[str, Any]:
    """Fresh, matching, separately built artifacts — or refuse to measure."""
    sys.path.insert(0, str(HARNESS_ROOT))
    from tests.compatibility.runner import (
        describe_environment,
        load_manifest,
        verify_manifest,
    )

    described = {env.name: describe_environment(env) for env in environments}
    problems = verify_manifest(load_manifest(), list(environments))

    backends = {name: info.get("has_rust_parsers") for name, info in described.items()}
    if len(set(backends.values())) > 1:
        problems.append(
            "backend availability differs between environments "
            f"({backends}); timings would compare different feature sets"
        )
    package_dirs = [info.get("package_dir") for info in described.values()]
    if len(set(package_dirs)) != len(package_dirs):
        problems.append("two environments share one package directory")

    return {"environments": described, "problems": problems}


def run_benchmark(
    reference_env,
    candidate_env,
    plan: BenchmarkPlan,
    allow_provenance_drift: bool = False,
) -> Dict[str, Any]:
    """Execute the paired protocol and return the full report."""
    provenance = _validate_provenance([reference_env, candidate_env])
    if provenance["problems"] and not allow_provenance_drift:
        raise BenchmarkError(
            "artifact provenance is not valid, so no timing was recorded:\n  - "
            + "\n  - ".join(provenance["problems"])
            + "\nRebuild both environments and regenerate "
            "tests/compatibility/reference_manifest.json, or pass "
            "--allow-provenance-drift to record an explicitly untrusted run."
        )

    request_base = {
        "mode": "time",
        "batches": plan.batches,
        "warmup": plan.warmup,
        "smoke": plan.smoke,
        "acceptance": not plan.smoke,
        "workloads": list(plan.workloads),
        "pin_cpu": plan.pin_cpu,
    }

    started = time.time()
    runs: Dict[str, List[Dict[str, Any]]] = {"reference": [], "candidate": []}
    order_log: List[List[str]] = []
    for pair in range(plan.process_pairs):
        # Alternate which backend goes first, so a warm-up or thermal trend
        # cannot systematically favour one side.
        order = (
            [("reference", reference_env), ("candidate", candidate_env)]
            if pair % 2 == 0
            else [("candidate", candidate_env), ("reference", reference_env)]
        )
        order_log.append([name for name, _ in order])
        for name, env in order:
            payload = _invoke_child(env, request_base)
            runs[name].append({
                "pair": pair,
                "runtime": payload["runtime"],
                "workloads": {w["workload"]: w for w in payload["workloads"]},
            })

    diagnostics = None
    if plan.run_diagnostics:
        diagnostics = {}
        for name, env in (("reference", reference_env), ("candidate", candidate_env)):
            payload = _invoke_child(env, {
                "mode": "diagnostics",
                "iterations": plan.diagnostics_iterations,
                "workloads": list(plan.workloads),
                "smoke": plan.smoke,
                "acceptance": False,
                "pin_cpu": plan.pin_cpu,
            })
            diagnostics[name] = {d["workload"]: d for d in payload["diagnostics"]}

    summaries = {}
    for name in plan.workloads:
        summaries[name] = summarise_workload(
            name,
            [run["workloads"][name] for run in runs["reference"]],
            [run["workloads"][name] for run in runs["candidate"]],
        )

    shortfalls = plan.meets_acceptance_protocol()
    report: Dict[str, Any] = {
        "schema_version": REPORT_SCHEMA_VERSION,
        "feature": "FEAT-2",
        "task": "TASK-9",
        "spec": "sdd/specs/compatible-model-performance.spec.md",
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S+00:00", time.gmtime(started)),
        "duration_seconds": round(time.time() - started, 3),
        "mode": "smoke" if plan.smoke else "acceptance",
        "acceptance": not shortfalls,
        "protocol_shortfalls": shortfalls,
        "protocol": {
            "process_pairs": plan.process_pairs,
            "batches_per_process": plan.batches,
            "warmup_operations": plan.warmup,
            "batch_sizes": {
                name: batch_size_for(WORKLOADS_BY_NAME[name], plan.smoke)
                for name in plan.workloads
            },
            "order_alternation": order_log,
            "position_balance": _position_balance(order_log),
            "required": {
                "process_pairs": ACCEPTANCE_PROCESS_PAIRS,
                "batches": ACCEPTANCE_BATCHES,
                "batch_size": ACCEPTANCE_BATCH_SIZE,
                "warmup_operations": ACCEPTANCE_WARMUP_OPERATIONS,
            },
            "upper_tail_metric": "p95 of per-batch elapsed time, linear interpolation",
            "input_preparation": "performed before each timed region, never inside it",
            "timer_calls_per_batch": 2,
        },
        "provenance": provenance,
        "workload_definitions": {
            w.name: {"kind": w.kind, "description": w.description,
                     "case": w.case, "tags": list(w.tags)}
            for w in WORKLOADS if w.name in plan.workloads
        },
        "summaries": summaries,
        "noise": _noise_report(runs),
        "noise_floor": _noise_floor(summaries),
        "raw": runs,
        "diagnostics": diagnostics,
        "same_source_control": None,
    }
    if plan.smoke:
        report["warning"] = (
            "SMOKE RUN -- NOT AN ACCEPTANCE MEASUREMENT. Sample counts are far "
            "below the protocol in spec §4; the ratios here carry no statistical "
            "weight and must never be cited for AC5, AC6, AC8, AC9 or AC10."
        )
    return report


def run_same_source_control(
    reference_env,
    control_env,
    plan: "BenchmarkPlan",
) -> Dict[str, Any]:
    """Measure two independent builds of the **same source** against each other.

    This is the experiment that tells a reader how much of any later result is
    real.  Both trees are the identical commit, so the true ratio is exactly
    1.0 for every workload; whatever the harness reports instead is the
    combined effect of machine noise and *binary layout* — two separate
    compilations of the same ``.pyx`` land at different code addresses, and a
    1-2% shift from alignment alone is normal and stable.

    Empirically (see the recorded baseline) this control can produce a verdict
    of "improvement" with a 95% interval entirely below 1.0 despite zero code
    difference.  That is precisely why AC5 asks for 20% and AC6 tolerates 5%,
    and why a 1-2% movement must never be reported as a change.
    """
    control_plan = BenchmarkPlan(
        smoke=plan.smoke,
        process_pairs=plan.process_pairs,
        batches=plan.batches,
        warmup=plan.warmup,
        workloads=plan.workloads,
        run_diagnostics=False,
        pin_cpu=plan.pin_cpu,
    )
    # The control tree is deliberately not in the manifest: it exists only to
    # calibrate the harness, so provenance drift is expected and recorded.
    report = run_benchmark(
        reference_env, control_env, control_plan, allow_provenance_drift=True
    )

    condensed = {}
    spurious = []
    deviations = []
    for name, summary in report["summaries"].items():
        verdict = summary["verdict"]
        condensed[name] = {
            "ratio": summary["median_ratio_point_estimate"],
            "ci95": [verdict["ci_low"], verdict["ci_high"]],
            "verdict": verdict["label"],
        }
        deviations.append(abs(summary["median_ratio_point_estimate"] - 1.0))
        if verdict["label"] != "inconclusive":
            spurious.append({"workload": name, **condensed[name]})

    return {
        "purpose": (
            "calibration: both sides are the SAME commit built independently, "
            "so the true ratio is 1.0 everywhere. Anything else this reports is "
            "harness noise plus binary-layout effects."
        ),
        "reference_root": str(reference_env.root),
        "control_root": str(control_env.root),
        "same_commit": True,
        "workloads": condensed,
        "spurious_verdicts": spurious,
        "spurious_verdict_count": len(spurious),
        "empirical_cross_build_floor": max(deviations) if deviations else None,
        "median_cross_build_deviation": (
            statistics.median(deviations) if deviations else None
        ),
        "conclusion": (
            "treat any movement within the empirical cross-build floor as no "
            "change, regardless of what its confidence interval says. A single "
            "workload flagged near this floor is not evidence; a real result "
            "must be large relative to it and reproduce across runs."
        ),
        "noise": report["noise"],
    }


def write_report(report: Dict[str, Any], path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n",
                    encoding="utf-8")
    return path


def format_summary(report: Dict[str, Any]) -> str:
    """Human-readable digest of a report."""
    lines = [
        f"mode: {report['mode']}  acceptance: {report['acceptance']}",
    ]
    noise = report.get("noise") or {}
    if noise.get("available"):
        lines.append(
            f"calibration spread: {noise['calibration_spread']:.1%}"
            f"  suspect processes: {noise['suspect_processes']}"
            f"  quiet machine: {noise['usable_environment']}"
        )
    control = report.get("same_source_control")
    if control:
        lines.append(
            "same-source control: empirical cross-build floor "
            f"{control['empirical_cross_build_floor']:.2%}, "
            f"{control['spurious_verdict_count']} spurious verdict(s) "
            "from identical code"
        )
    floor = report.get("noise_floor") or {}
    if floor.get("available"):
        lines.append(
            f"resolvable effect: median {floor['median_resolvable_effect']:.2%},"
            f" worst {floor['worst_resolvable_effect']:.2%}"
            f"  (AC6 5% resolvable: {floor['can_resolve_ac6_5pct_regression']},"
            f" AC5 20% resolvable: {floor['can_resolve_ac5_20pct_improvement']})"
        )
    if report.get("protocol_shortfalls"):
        lines.append("shortfalls: " + "; ".join(report["protocol_shortfalls"]))
    header = f"{'workload':<22}{'ref ns/op':>12}{'cand ns/op':>12}{'ratio':>9}  verdict"
    lines.append(header)
    lines.append("-" * len(header))
    for name, summary in report["summaries"].items():
        lines.append(
            f"{name:<22}"
            f"{summary['reference']['median_of_process_medians_ns']:>12.1f}"
            f"{summary['candidate']['median_of_process_medians_ns']:>12.1f}"
            f"{summary['median_ratio_point_estimate']:>9.4f}"
            f"  {summary['verdict']['label']}"
            f" [{summary['verdict']['ci_low']:.4f}, {summary['verdict']['ci_high']:.4f}]"
        )
    return "\n".join(lines)


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--worker", action="store_true",
                        help=argparse.SUPPRESS)
    parser.add_argument("--smoke", action="store_true",
                        help="fast, NON-ACCEPTANCE run for schema checks")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--workloads", type=str, default=None,
                        help="comma-separated subset of workload names")
    parser.add_argument("--process-pairs", type=int, default=None)
    parser.add_argument("--batches", type=int, default=None)
    parser.add_argument("--warmup", type=int, default=None)
    parser.add_argument("--no-diagnostics", action="store_true")
    parser.add_argument("--allow-provenance-drift", action="store_true",
                        help="record a run whose artifacts failed validation "
                             "(the report will say so)")
    parser.add_argument("--reference-root", type=Path, default=None)
    parser.add_argument("--control-root", type=Path, default=None,
                        help="a second, independently built worktree of the "
                             "SAME commit as the reference. Enables the "
                             "same-source control that calibrates how much of "
                             "any result is real.")
    parser.add_argument("--pin-cpu", type=int, default=None,
                        help="pin every child to this CPU (Linux). Both "
                             "backends share it; runs are sequential, so this "
                             "removes core-migration noise without bias.")
    args = parser.parse_args(argv)

    if args.worker:
        return _child_main()

    sys.path.insert(0, str(HARNESS_ROOT))
    from tests.compatibility.runner import (
        candidate_environment,
        reference_environment,
    )

    reference_env = reference_environment(args.reference_root)
    if reference_env is None:
        print(
            "No reference environment found. Build one from "
            "d932c720e9e36bbacdaca2b1a2af0688f2636c40 (see "
            "tests/compatibility/reference_manifest.json -> reproduce) or set "
            "$DATAMODEL_REFERENCE_ROOT.",
            file=sys.stderr,
        )
        return 2

    overrides: Dict[str, Any] = {}
    if args.workloads:
        names = tuple(name.strip() for name in args.workloads.split(",") if name.strip())
        unknown = [name for name in names if name not in WORKLOADS_BY_NAME]
        if unknown:
            print(f"unknown workload(s): {unknown}", file=sys.stderr)
            return 2
        overrides["workloads"] = names
    if args.process_pairs is not None:
        overrides["process_pairs"] = args.process_pairs
    if args.batches is not None:
        overrides["batches"] = args.batches
    if args.warmup is not None:
        overrides["warmup"] = args.warmup
    if args.no_diagnostics:
        overrides["run_diagnostics"] = False
    if args.pin_cpu is not None:
        overrides["pin_cpu"] = args.pin_cpu

    plan = (
        BenchmarkPlan.smoke_plan(**overrides)
        if args.smoke
        else BenchmarkPlan.acceptance(**overrides)
    )

    try:
        report = run_benchmark(
            reference_env,
            candidate_environment(),
            plan,
            allow_provenance_drift=args.allow_provenance_drift,
        )
    except BenchmarkError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    if args.control_root is not None:
        from tests.compatibility.runner import Environment

        control_root = args.control_root.resolve()
        control_env = Environment(
            "candidate", control_root, control_root / ".venv" / "bin" / "python"
        )
        try:
            report["same_source_control"] = run_same_source_control(
                reference_env, control_env, plan
            )
        except BenchmarkError as exc:
            print(f"same-source control failed: {exc}", file=sys.stderr)
            return 1

    write_report(report, args.output)
    print(format_summary(report))
    print(f"\nwritten: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
