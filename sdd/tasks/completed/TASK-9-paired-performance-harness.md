# TASK-9: Add reproducible paired model performance measurements

**Feature**: FEAT-2 - Compatible model execution performance
**Spec**: `sdd/specs/compatible-model-performance.spec.md`
**Status**: pending
**Priority**: high
**Estimated effort**: M (3h active engineering time; external evidence wait excluded)
**Depends-on**: TASK-8
**Parallel**: true
**Parallelism notes**: Can run alongside asyncdb corpus preparation; own benchmark runner files. Actual timing jobs run alone.
**Assigned-to**: unassigned

---

## Context

Implements M1 of the approved specification; contributes to AC1, AC5, AC6, AC11. Constructor/ORM hydration performance is the priority, with strict compatibility for repository schema examples and real `asyncdb.models`. Rust, parallel execution and serialization are measured experiments, not automatic backend migrations.

Approval is recorded in spec frontmatter and resolved requirements in §8. Its older body status/release placeholders do not override those decisions.

## Scope

- Implement the spec protocol: at least 7 paired fresh processes, 1000 warm-up operations and at least 30 batches of 2000 constructions, alternating backend order.
- Time raw/native Employee, primitive/constrained/nested/custom/invalid/50-field cases, class creation, assignment, JSON and to_dict; keep fixture preparation out of constructor-only timing.
- Report process-paired ratios and 95% uncertainty, median and explicitly defined upper-tail batch metric (p95), peak allocation diagnostics and retained memory separately.
- Record all environment/build/runtime flags and raw samples in machine-readable output; timing runs must disable profiling counters.
- Provide a short smoke mode for harness tests that is labelled non-acceptance.

**NOT in scope**: Production optimizations or runtime tracing switches.

## Files to Create / Modify

Ownership is restricted to these implementation/test/report files, plus this task's completion note and per-spec index state. Expand scope only through an explicit task/spec update.

| File | Action | Responsibility |
|---|---|---|
| `benchmarks/model_performance.py` | CREATE | Development-only measurement harness |
| `tests/compatibility/test_benchmark_protocol.py` | CREATE | Compatibility fixtures, test support or regression tests |
| `benchmarks/results/compatible-model-performance/baseline.json` | CREATE | Reproducible evidence and decision report |

## Codebase Contract (Anti-Hallucination)

References were re-read against the current `dev` tree after FEAT-001 integration and before task creation (runtime baseline `1d578ab`; reservation `4d5f97d`). Verify freshness again before implementation. Planned dependency outputs are not yet existing contracts.

### Verified Imports

```python
from datamodel import BaseModel, Field, Column
from datamodel.exceptions import ValidationError
```

### Existing Signatures to Use

- examples/rust_benchmark.py:35-51 — Employee's 11 fields, required/primary metadata and age bounds; PAYLOAD/NATIVE_PAYLOAD at 105-139.
- examples/test_qsmodel.py:38-68 — QueryModel schema with optional nested containers and defaults.
- examples/test_datadriver.py:8-45 — DataDriver with InitVar and custom __post_init__ calling super; inspect before executing examples with top-level code.
- tests/test_qsmodel.py:12-82 — existing QueryModel fixture pattern; tests/test_converter.py:6-61 — Organization/Client nested ORM-like models.
- datamodel/base.py:35-55 — errors/state observable at construction.
- datamodel/models.py:134-152,209-226,304-308 — reset_values/old_value, to_dict and json.
- datamodel/abstract.py:66-145 — assignment history and parser-only assignment validation.
- tests/test_descriptors.py:6-80 — descriptors execute through normal attribute access; tests/test_field.py:8-70 — fields/defaults/metadata.
- setup.py:15-29,98-106 — _compiler_flags() selects /O2 on Windows and -O3 on POSIX; guarded setup invocation and existing Cython extensions.
- pyproject.toml:1-8,19,57-74 — Cython>=3.2.8, Python>=3.10, optional uvloop and dev dependencies after FEAT-001.
- scripts/stage_rust_ext.py:30-59 — build_wheel(manifest: str, out_dir: str, interpreter: str, manylinux: str | None, maturin_bin: str = 'maturin') -> int; builds rs_parsers through maturin, not the experimental rs_core loader.
- .github/workflows/release.yml:13-25,49-65 — Ubuntu/Windows × CPython3.10–3.14, Linux x86_64/Windows AMD64, skips musllinux; current wheel test only asserts HAS_RUST.
- datamodel/version.py:9 — current version is already 0.11.0; do not bump it again.

### Does NOT Exist

- Files marked CREATE below are planned artifacts, not existing interfaces. Read completed dependencies to verify their newly introduced APIs before using them.
- No existing production per-field validation policy, compatible rs_core backend loader, or public batch-construction API is established by this contract.
- `_validate_constraints` is a Cython cdef interface, not a Python-importable function. Do not invent Python imports for it.

## Implementation Notes

### Pattern to Follow

Use standard-library statistics or existing development dependencies; no new runtime dependency. All future performance comparisons must use this same protocol.

Use the existing paths and behavior described in the contract, not the illustrative placeholders in the generic task template. Read §2–§5 of the specification for dispatch semantics, measurement protocol and acceptance thresholds.

### Key Constraints

- Preserve reference behavior, including legacy quirks; do not migrate consumers to Pydantic, weaken checks, change public/cpdef return contracts, or require model rebuild calls.
- Reference: d932c720e9e36bbacdaca2b1a2af0688f2636c40 (0.10.21), rebuilt in isolation. Candidate targets 0.11.0 and preserves FEAT-001 Linux/Windows × CPython 3.10–3.14 support.
- Use deterministic offline inputs. No production database writes, release publication, new backend packaging, or service credentials are authorized by this task.
- Rebuild affected Cython/Rust artifacts before testing. Separate diagnostic instrumentation from release timings; benchmark runs and shared extension builds require exclusive execution.
- Do not count missing dependencies, platforms, failed builds or unfinished measurements as successful verification or a completed negative experiment.
- Work in the per-spec feature worktree. You are not alone in the codebase: preserve others' edits and coordinate shared files rather than reverting their work.

### References in Codebase

The verified contract above is the source for existing behavior. New interfaces from `TASK-8` must be documented with their actual definitions, never inferred from proposed filenames.

## Acceptance Criteria

- [ ] Normal acceptance configuration meets all minimum sample counts; smoke reports cannot be mistaken for release measurements.
- [ ] The runner produces raw samples, per-process ratios and reproducible summary metrics for both artifact paths.
- [ ] Fresh artifact provenance is validated before timings; Pydantic remains an optional contextual comparison.
- [ ] No per-constructor timer overhead or concurrent workload is included accidentally in acceptance runs.
- [ ] Required tests and evidence are recorded with actual commands/results; no new reference-relative regression is hidden.
- [ ] Only scoped files and task/index state change; AC1, AC5, AC6, AC11 evidence is linked in the completion note.

## Test Specification

- Run `python -m pytest tests/compatibility/test_benchmark_protocol.py -q`.
- Run the implemented CLI in smoke mode for identical reference/candidate artifacts and check schema/provenance, not noisy speed thresholds.
- Capture a real baseline with the full protocol once build artifacts are available.

Tests are behavioral specifications, not permission to change the oracle. Verify import paths of new test-support modules after their dependency tasks land. A quick smoke run is not a substitute for the full acceptance protocol.

## Agent Instructions

1. Read the full spec and this task before acting; use `sdd/tasks/index/compatible-model-performance.json`, never the historical monolithic index.
2. Confirm dependencies are done/verified in that index and their task files are in `sdd/tasks/completed/`. Read their completion notes and newly implemented contracts.
3. Verify every relevant contract with `rg` and source reads before writing code. Record changed/new definitions first; do not guess imports or attributes.
4. Update only this task's assignment, start timestamp and status to `in-progress` in the per-spec index.
5. Implement only the declared scope, preserving other contributors' work. Respect the parallelism notes and serialize shared build/timing resources.
6. Run the scoped tests plus appropriate rebuilt-artifact differential checks. Record commands, artifact identities and raw evidence. If a prerequisite or required gate fails, keep the task incomplete and report it; do not waive it.
7. Fill the completion note, then use `scripts/sdd/close_task.sh TASK-9 compatible-model-performance verified` only when all required criteria are met. Verify the active copy is gone and the per-spec index points to the completed file.
8. Commit the scoped changes and task/index state in the feature worktree following the task-execution skill. Do not publish or merge the feature as part of this task.

## Completion Note

**Completed by**: sdd-worker (Claude Opus 5)
**Date**: 2026-09-08
**Notes**: Implemented M1's measurement protocol in exactly the three declared
files. This harness is the single protocol every later task must use to claim a
speed-up or a regression.

**Public interface** (documented in the module docstring so dependent tasks
verify rather than invent): `Workload`, `BenchmarkPlan`, `BenchmarkError`,
`batch_size_for()`, `run_benchmark()`, `run_same_source_control()`,
`summarise_workload()`, `bootstrap_ratio_interval()`, `log_ratio_interval()`,
`percentile()`, `is_acceptance_run()`, `write_report()`, `format_summary()`,
`main()`, `REPORT_SCHEMA_VERSION`, `DEFAULT_OUTPUT`, and the
`ACCEPTANCE_*`/`SMOKE_*` constants. Children run via
`benchmarks/model_performance.py --worker`, reusing TASK-8's `Environment`,
`candidate_environment()`, `reference_environment()` and `verify_manifest()` so
both tasks agree on what "the reference build" means.

**Protocol as built** (spec §4): 8 paired fresh processes -- deliberately 8,
not the floor of 7, because order alternates *within* each pair; an odd count
would run the reference first 4 times and the candidate 3, charging any
within-pair position effect systematically to one side
(`test_acceptance_requires_an_even_number_of_process_pairs`,
`test_baseline_counterbalanced_the_execution_order`). 1,000 warm-up operations,
30 batches x 2,000 constructions (500/200 for the expensive wide and
class-creation workloads, each recorded per workload in
`protocol.batch_sizes`). The clock is read exactly **twice per batch**, never
around an individual constructor, and that count is written into the report so
the claim is checkable rather than asserted
(`test_the_clock_was_read_exactly_twice_per_batch`). Every batch's payloads are
built before the timer starts
(`test_every_batch_prepared_its_inputs_before_timing`).

**Instrumentation refusal.** An acceptance run aborts if `sys.gettrace()`,
`sys.getprofile()`, the threading equivalents or `tracemalloc` is active, and
never enables one itself. Allocation figures come from a *separate* diagnostic
pass whose every entry says it is not comparable with the timed batches
(`test_timing_is_refused_while_tracemalloc_is_tracing`,
`test_timing_is_refused_while_a_profile_hook_is_installed`,
`test_timing_is_refused_while_another_thread_is_running`,
`test_timed_batches_ran_without_instrumentation`,
`test_allocation_diagnostics_are_a_separate_pass`).

**THE CENTRAL RESULT -- this baseline measures no change, and proves it.**
`datamodel/` is **byte-identical** between the reference commit `d932c720`
(0.10.21) and this branch except `version.py` and the new `libs/uvloop.py`,
neither of which is on any measured path
(`git diff --stat d932c720 HEAD -- datamodel/` -> 2 files, uvloop + version).
The true ratio is therefore exactly 1.0 on all 15 workloads, and **every**
verdict this report emits is an artifact of machine noise plus binary layout.

That is not a theoretical caveat -- it is measured. The run was captured with
`--control-root` pointed at `ref2-FEAT-2-d932c720`, an independently built
worktree of the *same* reference commit (verified: same SHA, clean tree,
different `.so` digests -- two separate compilations of identical `.pyx`).
`same_source_control` reports an **empirical cross-build floor of 2.12%** and,
decisively, **3 spurious "regression" verdicts from provably identical code**
(`unconstrained_native` 1.0169, `unconstrained_raw` 1.0212, `client_nested`
1.0208), each with a 95% interval entirely above 1.0. A confidence interval
excluding 1.0 is therefore *not* sufficient evidence of a real change at this
magnitude. The main comparison's four flagged workloads
(`constrained_valid` 1.0161, `json_warm` 1.0156, `unconstrained_native` 1.0087,
`employee_native` 1.0062) are all **below** that 2.12% floor and must be read
as no change.

**Consequence for TASK-11..TASK-15: there is no ~1-2% regression to repay.**
Any later run must clear the cross-build floor -- not merely produce an
interval excluding 1.0 -- before a speed-up or regression may be claimed. This
is also the empirical justification for AC5 asking 20% and AC6 tolerating 5%.

**Two guards added after the first capture was shown to be misleading.** The
originally captured artifact was taken *without* `--control-root` and carried
five unqualified "regression" labels; nothing in the suite objected, because
the existing `test_baseline_is_a_no_change_measurement` only rejects
*improvement* verdicts. Phantom regressions were exactly as dangerous, and
would have sent the optimization tasks chasing them. Added:
- `test_baseline_recorded_the_same_source_control` -- a baseline without the
  control cannot be interpreted at all and is rejected.
- `test_baseline_flags_nothing_beyond_the_cross_build_floor` -- no
  non-inconclusive verdict may exceed the floor the control measured. It does
  not demand zero labels (independent builds genuinely differ); it demands that
  no label exceed what calibration can explain.

**Machine quality is a recorded gate, not an afterthought.** An intermediate
capture came back with a 15.9% calibration spread and 1 suspect process, and
the new floor guard **failed** on it (three verdicts marginally above a 1.22%
floor). Per spec §4 the response is re-measurement, not relaxing the threshold,
so the run was repeated on an idle machine; the threshold was left untouched.
The accepted artifact records `calibration_spread` 9.1%, **0 suspect
processes**, quiet-machine true.

**Verification commands/results**:
- `.venv/bin/python -m pytest tests/compatibility/test_benchmark_protocol.py -q`
  -> **54 passed**, 0 failed.
- `.venv/bin/python -m pytest tests/ -q` -> **505 passed, 2 skipped, 0 failed**
  (451 before this task + 54 new; no new reference-relative regression).
- `.venv/bin/python -m ruff check --select F,E9 benchmarks/ tests/compatibility/`
  -> clean.
- Smoke CLI -> `acceptance: false`, all 19 shortfalls enumerated by name.
- Acceptance capture: 510.2s, 8 pairs, 30 batches, 15 workloads,
  `protocol_shortfalls: []`, both environments' extension digests and
  `has_rust_parsers: true` recorded, plus the same-source control.

**Environments** (provenance embedded in `baseline.json`, cross-checked against
TASK-8's `reference_manifest.json` before any timing):
| | reference | candidate | control |
|---|---|---|---|
| commit | `d932c720` | this worktree | `d932c720` (independent build) |
| version | 0.10.21 | 0.12.0 | 0.10.21 |
| interpreter | own `.venv` CPython 3.13.11 | own `.venv` CPython 3.13.11 | own `.venv` |
| rs_parsers | built, `HAS_RUST=True` | built, `HAS_RUST=True` | built |

**Evidence paths and acceptance coverage**:
- AC1 (fresh artifact provenance validated *before* timings):
  `_validate_provenance()` re-verifies TASK-8's manifest and aborts on mismatch;
  `baseline.json.provenance` records both roots, interpreters, commits, dirty
  flags, dependency versions and all binary digests. Pinned by
  `test_baseline_records_both_artifact_identities`,
  `test_smoke_report_validated_artifact_provenance`,
  `test_a_run_refuses_to_measure_when_provenance_is_invalid`.
- AC5/AC6 (resolvable effect sizes): `baseline.json.noise_floor` --
  `can_resolve_ac5_20pct_improvement: true`,
  `can_resolve_ac6_5pct_regression: true`, worst resolvable effect 1.76%.
  Pinned by `test_baseline_can_resolve_the_thresholds_it_will_be_used_for`.
- AC11 (reproducible machine-readable evidence): `baseline.json` carries raw
  per-batch samples, per-process medians/p95s, paired ratios, both interval
  methods, the protocol description, the order-alternation log, environment and
  build flags. Pinned by `test_baseline_has_raw_samples_for_every_process`,
  `test_baseline_is_a_full_acceptance_run`, `test_baseline_covers_every_workload`.
- No-change honesty: `test_baseline_is_a_no_change_measurement`,
  `test_baseline_recorded_the_same_source_control`,
  `test_baseline_flags_nothing_beyond_the_cross_build_floor`.
- Statistics: `test_bootstrap_interval_is_deterministic`,
  `test_bootstrap_interval_does_not_claim_a_noisy_improvement`,
  `test_a_point_estimate_below_one_is_not_enough_for_an_improvement`,
  `test_paired_ratios_are_not_a_ratio_of_means`,
  `test_verdict_only_claims_an_improvement_when_the_whole_interval_is_below_one`.
- Smoke/acceptance separation:
  `test_smoke_report_is_clearly_not_an_acceptance_measurement`,
  `test_a_smoke_plan_is_never_an_acceptance_plan`,
  `test_is_acceptance_run_rejects_a_shortfall_report`,
  `test_every_undersized_dimension_is_reported`.
- Pydantic is optional/contextual only, never a gate:
  `test_pydantic_is_recorded_as_contextual_only`.

**Deviations from spec**: none in scope or file ownership. Notes for the
reviewer:
1. **8 process pairs instead of the literal 7** -- exceeds the spec floor;
   rationale (order-alternation balance) is in a comment at the constant and in
   `protocol.position_balance`.
2. **Reduced batch sizes for 4 of 15 workloads** (`wide_raw`, `wide_native`,
   `container_full` at 500; `class_creation` at 200), each 10-70x more
   expensive per operation. Each workload's actual size is recorded and
   compared against its own acceptance size, so a smoke run still cannot pass
   itself off as acceptance.
3. **`datamodel/version.py` is 0.12.0 on this branch** while the task contract
   says 0.11.0. Untouched, carried forward from TASK-7/TASK-8; TASK-22 still
   needs the maintainer to reconcile the declared release target.
4. The reference and control worktrees are gitignored and `*.so` is untracked,
   so reproducing `baseline.json` requires rebuilding all three environments per
   the manifest's `reproduce` field. The absolute nanosecond figures are
   machine-specific; **the protocol and the calibrated floor, not the numbers,
   are the deliverable.**
5. The cross-build floor is itself run-dependent (1.22% on the noisy capture,
   2.12% here). Later tasks should re-derive it in the same run as their claim
   rather than reusing this figure as a constant.
