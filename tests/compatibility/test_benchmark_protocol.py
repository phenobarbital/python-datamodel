"""Protocol tests for the FEAT-2 performance harness (TASK-9).

These tests deliberately assert **protocol**, not speed.  A threshold on a
measured ratio would be flaky on any shared machine and, worse, would tempt a
future change to be judged by a noisy number.  What is checked here is that the
harness cannot lie:

* an acceptance run really does use 7 process pairs, 1,000 warm-up operations
  and 30 batches of 2,000 — and a run that does not is marked non-acceptance
  with its shortfalls spelled out;
* the clock is read twice per batch, never per constructor;
* input preparation happens outside the timed region;
* instrumentation is refused during acceptance timings and allocation numbers
  come from a separate pass;
* an improvement is only ever claimed when the whole 95% interval is below 1.0.
"""
from __future__ import annotations

import json
import math

import pytest

from benchmarks.model_performance import (
    ACCEPTANCE_BATCH_SIZE,
    ACCEPTANCE_BATCHES,
    ACCEPTANCE_PROCESS_PAIRS,
    ACCEPTANCE_WARMUP_OPERATIONS,
    BOOTSTRAP_SEED,
    DEFAULT_OUTPUT,
    REPORT_SCHEMA_VERSION,
    SMOKE_BATCH_SIZE,
    BenchmarkError,
    BenchmarkPlan,
    WORKLOADS,
    WORKLOADS_BY_NAME,
    _child_assert_clean_for_timing,
    _verdict,
    batch_size_for,
    bootstrap_ratio_interval,
    format_summary,
    is_acceptance_run,
    log_ratio_interval,
    percentile,
    run_benchmark,
    summarise_workload,
)
from tests.compatibility.runner import (
    candidate_environment,
    reference_environment,
)

REFERENCE_MISSING = (
    "the rebuilt engineering reference is not present; a skipped benchmark is "
    "NOT a passing benchmark. See tests/compatibility/reference_manifest.json "
    "-> 'reproduce'."
)


@pytest.fixture(scope="module")
def environments():
    reference = reference_environment()
    candidate = candidate_environment()
    if reference is None or not reference.python.is_file():
        pytest.skip(REFERENCE_MISSING)
    if not candidate.python.is_file():
        pytest.skip("the candidate worktree has no .venv")
    return reference, candidate


@pytest.fixture(scope="module")
def smoke_report(environments):
    reference, candidate = environments
    plan = BenchmarkPlan.smoke_plan(
        workloads=("employee_native", "to_dict"),
        run_diagnostics=True,
        diagnostics_iterations=20,
    )
    return run_benchmark(reference, candidate, plan)


# ===========================================================================
# Protocol constants
# ===========================================================================


def test_protocol_constants_match_the_specification():
    """Spec §4: >=7 paired processes, 1000 warm-up ops, >=30 batches of 2000."""
    assert ACCEPTANCE_PROCESS_PAIRS >= 7
    assert ACCEPTANCE_WARMUP_OPERATIONS >= 1_000
    assert ACCEPTANCE_BATCHES >= 30
    assert ACCEPTANCE_BATCH_SIZE >= 2_000


def test_the_default_plan_is_an_acceptance_plan():
    assert BenchmarkPlan.acceptance().meets_acceptance_protocol() == []


def test_a_smoke_plan_is_never_an_acceptance_plan():
    shortfalls = BenchmarkPlan.smoke_plan().meets_acceptance_protocol()
    assert shortfalls
    assert any("smoke" in reason for reason in shortfalls)


@pytest.mark.parametrize(
    "overrides",
    [
        {"process_pairs": ACCEPTANCE_PROCESS_PAIRS - 1},
        {"batches": ACCEPTANCE_BATCHES - 1},
        {"warmup": ACCEPTANCE_WARMUP_OPERATIONS - 1},
    ],
)
def test_every_undersized_dimension_is_reported(overrides):
    """Trimming any single dimension must disqualify the run."""
    plan = BenchmarkPlan.acceptance(**overrides)
    assert plan.meets_acceptance_protocol()


def test_is_acceptance_run_rejects_a_shortfall_report():
    assert is_acceptance_run({"acceptance": True, "protocol_shortfalls": []})
    assert not is_acceptance_run(
        {"acceptance": True, "protocol_shortfalls": ["2 batches < required 30"]}
    )
    assert not is_acceptance_run({"acceptance": False, "protocol_shortfalls": []})


def test_smoke_batch_sizes_are_smaller_than_acceptance_sizes():
    for workload in WORKLOADS:
        assert batch_size_for(workload, smoke=True) <= SMOKE_BATCH_SIZE
        assert batch_size_for(workload, smoke=False) == workload.batch_size_acceptance


def test_batch_size_depends_only_on_the_workload_not_the_backend():
    """Spec §4 allows a smaller batch only if it is 'equal between variants'.

    ``batch_size_for`` takes no backend argument at all, so the two sides
    cannot diverge by construction; this test pins that signature.
    """
    import inspect

    parameters = list(inspect.signature(batch_size_for).parameters)
    assert parameters == ["workload", "smoke"]


# ===========================================================================
# Workload table
# ===========================================================================


def test_every_workload_case_exists_in_the_corpus():
    from tests.fixtures.model_performance.cases import CASES_BY_NAME

    for workload in WORKLOADS:
        if workload.case is None:
            assert workload.kind == "class_creation", workload.name
            continue
        assert workload.case in CASES_BY_NAME, workload.name


def test_construct_workloads_use_success_cases_except_the_invalid_one():
    from tests.fixtures.model_performance.cases import CASES_BY_NAME, EXPECT_ERROR

    for workload in WORKLOADS:
        if workload.kind == "construct":
            assert CASES_BY_NAME[workload.case].expect != EXPECT_ERROR, workload.name
        if workload.kind == "construct_invalid":
            assert CASES_BY_NAME[workload.case].expect == EXPECT_ERROR, workload.name


def test_the_workload_set_covers_every_family_the_spec_lists():
    """Spec §4 'Workloads:' enumerates what must be measured."""
    kinds = {w.kind for w in WORKLOADS}
    assert {"construct", "construct_invalid", "class_creation", "assignment",
            "to_dict", "json"} <= kinds

    names = set(WORKLOADS_BY_NAME)
    for required in (
        "employee_raw", "employee_native",       # Employee raw/native
        "unconstrained_native",                   # unconstrained primitives
        "constrained_valid",                      # constrained fields
        "client_nested", "container_full",        # nested/container models
        "callback_hooks",                         # custom hooks
        "invalid_input",                          # invalid input
        "wide_native", "wide_raw",                # 50-field models
        "class_creation", "assignment",           # cold creation, assignment
        "to_dict", "json_warm",                   # dictionary + JSON conversion
    ):
        assert required in names, required


def test_workload_names_are_unique():
    names = [w.name for w in WORKLOADS]
    assert len(names) == len(set(names))


def test_ac5_workloads_are_the_two_employee_shapes():
    ac5 = {w.name for w in WORKLOADS if "ac5" in w.tags}
    assert ac5 == {"employee_raw", "employee_native"}


# ===========================================================================
# Statistics
# ===========================================================================


def test_percentile_is_linear_interpolation():
    values = [1, 2, 3, 4]
    assert percentile(values, 0) == 1
    assert percentile(values, 100) == 4
    assert percentile(values, 50) == pytest.approx(2.5)
    assert percentile([5], 95) == 5
    with pytest.raises(ValueError):
        percentile([], 95)


def test_percentile_ignores_input_order():
    assert percentile([9, 1, 5, 3], 95) == percentile([1, 3, 5, 9], 95)


def test_bootstrap_interval_is_deterministic():
    ratios = [0.80, 0.82, 0.79, 0.85, 0.81, 0.83, 0.78]
    first = bootstrap_ratio_interval(ratios)
    second = bootstrap_ratio_interval(ratios)
    assert first == second
    assert first["seed"] == BOOTSTRAP_SEED
    assert first["low"] < first["high"]


def test_bootstrap_interval_brackets_a_clear_improvement():
    ratios = [0.80, 0.82, 0.79, 0.85, 0.81, 0.83, 0.78]
    interval = bootstrap_ratio_interval(ratios)
    assert interval["high"] < 1.0


def test_bootstrap_interval_does_not_claim_a_noisy_improvement():
    ratios = [0.85, 1.15, 0.90, 1.10, 0.95, 1.05, 1.00]
    interval = bootstrap_ratio_interval(ratios)
    assert interval["low"] < 1.0 < interval["high"]


def test_log_ratio_interval_agrees_with_the_bootstrap_on_a_clear_case():
    ratios = [0.80, 0.82, 0.79, 0.85, 0.81, 0.83, 0.78]
    t_interval = log_ratio_interval(ratios)
    assert t_interval["high"] < 1.0
    assert math.isfinite(t_interval["low"])


def test_log_ratio_interval_needs_two_pairs():
    result = log_ratio_interval([0.9])
    assert math.isnan(result["low"])


def test_verdict_only_claims_an_improvement_when_the_whole_interval_is_below_one():
    improving = _verdict({
        "median_ratio_ci95_bootstrap": {"low": 0.75, "high": 0.90},
        "median_ratio_point_estimate": 0.82,
    })
    assert improving["label"] == "improvement"
    assert improving["improvement_pct_point_estimate"] == pytest.approx(18.0)

    straddling = _verdict({
        "median_ratio_ci95_bootstrap": {"low": 0.95, "high": 1.05},
        "median_ratio_point_estimate": 1.00,
    })
    assert straddling["label"] == "inconclusive"

    regressing = _verdict({
        "median_ratio_ci95_bootstrap": {"low": 1.06, "high": 1.20},
        "median_ratio_point_estimate": 1.12,
    })
    assert regressing["label"] == "regression"


def test_a_point_estimate_below_one_is_not_enough_for_an_improvement():
    """The failure mode this rule exists to prevent."""
    verdict = _verdict({
        "median_ratio_ci95_bootstrap": {"low": 0.70, "high": 1.02},
        "median_ratio_point_estimate": 0.86,
    })
    assert verdict["label"] == "inconclusive", (
        "a 14% mean improvement whose interval crosses 1.0 must not be claimed"
    )


def _process(median: float, p95: float) -> dict:
    return {"median_per_operation_ns": median, "p95_batch_latency_ns": p95}


def test_summarise_workload_pairs_processes_positionally():
    reference = [_process(100.0, 1000.0), _process(200.0, 2000.0)]
    candidate = [_process(50.0, 500.0), _process(100.0, 1000.0)]
    summary = summarise_workload("demo", reference, candidate)

    assert summary["process_pairs"] == 2
    assert summary["paired_median_ratios"] == [0.5, 0.5]
    assert summary["paired_p95_ratios"] == [0.5, 0.5]
    assert summary["median_ratio_point_estimate"] == pytest.approx(0.5)
    assert summary["verdict"]["label"] == "improvement"


def test_summarise_workload_reports_variability():
    reference = [_process(100.0, 1000.0), _process(120.0, 1200.0),
                 _process(110.0, 1100.0)]
    candidate = [_process(100.0, 1000.0), _process(120.0, 1200.0),
                 _process(110.0, 1100.0)]
    summary = summarise_workload("demo", reference, candidate)
    assert summary["reference"]["relative_stdev"] > 0
    assert summary["verdict"]["label"] == "inconclusive"
    assert summary["median_ratio_point_estimate"] == pytest.approx(1.0)


def test_paired_ratios_are_not_a_ratio_of_means():
    """Pairing matters: an unpaired ratio would hide per-process pairing."""
    reference = [_process(100.0, 1.0), _process(1000.0, 1.0)]
    candidate = [_process(50.0, 1.0), _process(900.0, 1.0)]
    summary = summarise_workload("demo", reference, candidate)
    assert summary["paired_median_ratios"] == [0.5, 0.9]
    # A ratio of means would be 950/1100 = 0.8636; the paired mean is 0.70.
    assert summary["median_ratio_point_estimate"] == pytest.approx(0.70)


# ===========================================================================
# Instrumentation refusal
# ===========================================================================


def test_timing_is_refused_while_tracemalloc_is_tracing():
    import tracemalloc

    tracemalloc.start()
    try:
        with pytest.raises(BenchmarkError, match="tracemalloc"):
            _child_assert_clean_for_timing()
    finally:
        tracemalloc.stop()


def test_timing_is_refused_while_a_profile_hook_is_installed():
    import sys as _sys

    def _hook(frame, event, arg):
        return None

    _sys.setprofile(_hook)
    try:
        with pytest.raises(BenchmarkError, match="profile hook"):
            _child_assert_clean_for_timing()
    finally:
        _sys.setprofile(None)


def test_timing_is_refused_while_another_thread_is_running():
    import threading

    stop = threading.Event()
    worker = threading.Thread(target=stop.wait)
    worker.start()
    try:
        with pytest.raises(BenchmarkError, match="threads are active"):
            _child_assert_clean_for_timing()
    finally:
        stop.set()
        worker.join()


def test_a_clean_process_passes_the_instrumentation_check():
    if __import__("sys").gettrace() is not None:
        pytest.skip("this test run is itself under a trace hook (coverage)")
    state = _child_assert_clean_for_timing()
    assert state == {
        "trace_hook": False, "profile_hook": False,
        "tracemalloc": False, "active_threads": 1,
    }


# ===========================================================================
# End-to-end smoke run
# ===========================================================================


def test_smoke_report_is_clearly_not_an_acceptance_measurement(smoke_report):
    assert smoke_report["mode"] == "smoke"
    assert smoke_report["acceptance"] is False
    assert smoke_report["protocol_shortfalls"]
    assert "NOT AN ACCEPTANCE MEASUREMENT" in smoke_report["warning"]
    assert not is_acceptance_run(smoke_report)


def test_smoke_report_records_the_full_protocol_it_used(smoke_report):
    protocol = smoke_report["protocol"]
    assert protocol["timer_calls_per_batch"] == 2
    assert protocol["upper_tail_metric"].startswith("p95")
    assert "never inside it" in protocol["input_preparation"]
    assert protocol["required"]["process_pairs"] == ACCEPTANCE_PROCESS_PAIRS
    assert protocol["batch_sizes"]
    # Order alternation: pair 0 reference-first, pair 1 candidate-first.
    order = protocol["order_alternation"]
    assert order[0][0] == "reference"
    assert order[1][0] == "candidate"


def test_smoke_report_validated_artifact_provenance(smoke_report):
    provenance = smoke_report["provenance"]
    assert provenance["problems"] == []
    reference = provenance["environments"]["reference"]
    candidate = provenance["environments"]["candidate"]
    assert reference["version"] == "0.10.21"
    assert reference["package_dir"] != candidate["package_dir"]
    assert reference["has_rust_parsers"] == candidate["has_rust_parsers"]


def test_the_clock_was_read_exactly_twice_per_batch(smoke_report):
    for side in ("reference", "candidate"):
        for run in smoke_report["raw"][side]:
            for workload in run["workloads"].values():
                assert workload["timer_calls_total"] == 2 * workload["batches"]
                for sample in workload["samples"]:
                    assert sample["timer_calls"] == 2


def test_every_batch_prepared_its_inputs_before_timing(smoke_report):
    for side in ("reference", "candidate"):
        for run in smoke_report["raw"][side]:
            for workload in run["workloads"].values():
                for sample in workload["samples"]:
                    assert "before timing" in sample["preparation"]


def test_timed_batches_ran_without_instrumentation(smoke_report):
    """Smoke runs pass ``acceptance=False`` to the child, so the state is None.

    The refusal itself is covered by the ``_child_assert_clean_for_timing``
    tests above; here we only require the field to exist so an acceptance
    report can be checked for it.
    """
    for side in ("reference", "candidate"):
        for run in smoke_report["raw"][side]:
            for workload in run["workloads"].values():
                assert "instrumentation" in workload


def test_allocation_diagnostics_are_a_separate_pass(smoke_report):
    diagnostics = smoke_report["diagnostics"]
    assert set(diagnostics) == {"reference", "candidate"}
    for side in diagnostics.values():
        for record in side.values():
            assert "peak_temporary_bytes" in record
            assert "retained_per_operation_bytes" in record
            assert "separate pass" in record["note"]
            # A diagnostic record must not carry timing fields, so it can never
            # be mistaken for, or averaged into, an acceptance measurement.
            assert "median_per_operation_ns" not in record
            assert "samples" not in record


def test_smoke_report_records_machine_noise(smoke_report):
    noise = smoke_report["noise"]
    assert noise["available"] is True
    assert noise["calibration_median_ns"] > 0
    assert "processes" in noise
    for entry in noise["processes"]:
        assert entry["side"] in ("reference", "candidate")
        assert entry["calibration_median_ns"] > 0


def test_summaries_cover_every_requested_workload(smoke_report):
    assert set(smoke_report["summaries"]) == {"employee_native", "to_dict"}
    for summary in smoke_report["summaries"].values():
        assert summary["process_pairs"] >= 1
        assert summary["verdict"]["label"] in {
            "improvement", "regression", "inconclusive"
        }


def test_report_can_be_serialised_and_summarised(smoke_report):
    text = json.dumps(smoke_report)
    assert json.loads(text)["schema_version"] == REPORT_SCHEMA_VERSION
    rendered = format_summary(smoke_report)
    assert "employee_native" in rendered
    assert "acceptance: False" in rendered


def test_pydantic_is_recorded_as_contextual_only(smoke_report):
    runtime = smoke_report["raw"]["reference"][0]["runtime"]
    assert "note_pydantic" in runtime
    assert "contextual" in runtime["note_pydantic"]
    # No summary or verdict may reference pydantic.
    assert "pydantic" not in json.dumps(smoke_report["summaries"]).lower()


def test_a_run_refuses_to_measure_when_provenance_is_invalid(environments):
    """No timing may be recorded against artifacts that failed validation."""
    from benchmarks import model_performance

    reference, candidate = environments
    original = model_performance._validate_provenance
    model_performance._validate_provenance = lambda envs: {
        "environments": {}, "problems": ["seeded provenance failure"],
    }
    try:
        with pytest.raises(BenchmarkError, match="seeded provenance failure"):
            run_benchmark(
                reference, candidate,
                BenchmarkPlan.smoke_plan(workloads=("to_dict",),
                                         run_diagnostics=False),
            )
    finally:
        model_performance._validate_provenance = original


# ===========================================================================
# The recorded baseline artifact
# ===========================================================================


def test_baseline_artifact_exists():
    assert DEFAULT_OUTPUT.is_file(), (
        f"{DEFAULT_OUTPUT} is missing; capture it with "
        "`python benchmarks/model_performance.py`"
    )


@pytest.fixture(scope="module")
def baseline():
    if not DEFAULT_OUTPUT.is_file():
        pytest.skip("baseline artifact not captured")
    return json.loads(DEFAULT_OUTPUT.read_text(encoding="utf-8"))


def test_baseline_is_a_full_acceptance_run(baseline):
    assert baseline["mode"] == "acceptance"
    assert baseline["protocol_shortfalls"] == []
    assert is_acceptance_run(baseline)
    assert baseline["protocol"]["process_pairs"] >= ACCEPTANCE_PROCESS_PAIRS
    assert baseline["protocol"]["batches_per_process"] >= ACCEPTANCE_BATCHES
    assert baseline["protocol"]["warmup_operations"] >= ACCEPTANCE_WARMUP_OPERATIONS


def test_baseline_covers_every_workload(baseline):
    assert set(baseline["summaries"]) == set(WORKLOADS_BY_NAME)


def test_baseline_records_both_artifact_identities(baseline):
    environments = baseline["provenance"]["environments"]
    assert environments["reference"]["version"] == "0.10.21"
    assert environments["reference"]["package_dir"] != (
        environments["candidate"]["package_dir"]
    )
    assert baseline["provenance"]["problems"] == []


def test_baseline_has_raw_samples_for_every_process(baseline):
    for side in ("reference", "candidate"):
        runs = baseline["raw"][side]
        assert len(runs) >= ACCEPTANCE_PROCESS_PAIRS
        for run in runs:
            for workload in run["workloads"].values():
                assert len(workload["samples"]) >= ACCEPTANCE_BATCHES


def test_baseline_is_a_no_change_measurement(baseline):
    """The candidate has no production change yet, so nothing may be claimed.

    ``datamodel/`` is byte-identical between the reference commit and this
    branch apart from ``version.py`` and the new ``libs/uvloop.py``; the only
    honest baseline verdict is therefore "no improvement claimed anywhere".
    A future task that changes the Cython gate will move these numbers, and
    *that* is when a verdict of "improvement" becomes meaningful.
    """
    claimed = {
        name: summary["verdict"]
        for name, summary in baseline["summaries"].items()
        if summary["verdict"]["label"] == "improvement"
    }
    assert not claimed, (
        "the baseline claims an improvement although no production code "
        f"changed; this indicates measurement bias, not a speed-up: {claimed}"
    )


def test_baseline_recorded_the_same_source_control(baseline):
    """A baseline without the control cannot be interpreted.

    The control is what converts "1.2% slower" from a finding into a
    measurement artifact. Without it the report states a difference it has no
    way to calibrate, so later tasks would have to take its verdicts on faith.
    """
    control = baseline.get("same_source_control")
    assert control is not None, (
        "the baseline was captured without --control-root; re-run with an "
        "independently built worktree of the reference commit so the report "
        "can state how much of its own output is noise"
    )
    assert control["same_commit"] is True, control
    assert control["reference_root"] != control["control_root"], control
    assert control["empirical_cross_build_floor"] is not None


def test_baseline_flags_nothing_beyond_the_cross_build_floor(baseline):
    """No verdict on byte-identical source may exceed measured build noise.

    ``datamodel/`` is byte-identical between the reference commit and this
    branch apart from ``version.py`` and ``libs/uvloop.py``, neither of which
    is on any measured path. So the true ratio is 1.0 everywhere and *every*
    non-inconclusive verdict here is an artifact. This test does not demand
    that the harness produce zero labels -- two independent builds genuinely
    differ by code layout -- it demands that no label exceed the floor the
    control measured. A verdict above that floor would mean the harness is
    reporting a difference its own calibration cannot explain, and TASK-11
    onwards would be optimising a phantom.
    """
    floor = baseline["same_source_control"]["empirical_cross_build_floor"]
    beyond = {
        name: {
            "ratio": summary["median_ratio_point_estimate"],
            "verdict": summary["verdict"]["label"],
        }
        for name, summary in baseline["summaries"].items()
        if summary["verdict"]["label"] != "inconclusive"
        and abs(summary["median_ratio_point_estimate"] - 1.0) > floor
    }
    assert not beyond, (
        f"these verdicts exceed the {floor:.2%} empirical cross-build floor "
        f"although no production code changed: {beyond}. Either the machine "
        "was too noisy to trust or the control is not comparable; re-measure "
        "before treating any of them as a real regression"
    )


def test_report_records_the_smallest_effect_it_could_resolve(smoke_report):
    """A run must state its own resolution, so a claim can be sanity-checked."""
    floor = smoke_report["noise_floor"]
    assert floor["available"] is True
    assert set(floor["per_workload"]) == set(smoke_report["summaries"])
    assert floor["worst_resolvable_effect"] >= floor["median_resolvable_effect"]
    assert isinstance(floor["can_resolve_ac6_5pct_regression"], bool)
    assert isinstance(floor["can_resolve_ac5_20pct_improvement"], bool)


def test_baseline_can_resolve_the_thresholds_it_will_be_used_for(baseline):
    """AC5 needs 20% and AC6 needs 5%: the baseline run must resolve both.

    If this fails the machine was too noisy, and every later comparison run on
    it is untrustworthy — which is a result worth failing over, not a flake to
    be retried until green.
    """
    floor = baseline["noise_floor"]
    assert floor["can_resolve_ac5_20pct_improvement"], floor
    assert floor["can_resolve_ac6_5pct_regression"], floor


def test_acceptance_requires_an_even_number_of_process_pairs():
    """An odd count cannot balance the first/second execution order."""
    assert ACCEPTANCE_PROCESS_PAIRS % 2 == 0
    odd = BenchmarkPlan.acceptance(process_pairs=ACCEPTANCE_PROCESS_PAIRS + 1)
    shortfalls = odd.meets_acceptance_protocol()
    assert any("odd" in reason for reason in shortfalls), shortfalls


def test_baseline_counterbalanced_the_execution_order(baseline):
    balance = baseline["protocol"]["position_balance"]
    assert balance["balanced"] is True, balance
    counts = balance["times_each_backend_ran_first"]
    assert counts["reference"] == counts["candidate"], counts
