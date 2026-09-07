# TASK-8: Add isolated reference and candidate compatibility runner

**Feature**: FEAT-2 - Compatible model execution performance
**Spec**: `sdd/specs/compatible-model-performance.spec.md`
**Status**: done
**Priority**: high
**Estimated effort**: M (4h active engineering time; external evidence wait excluded)
**Depends-on**: TASK-7
**Parallel**: false
**Parallelism notes**: Consumes fixture contract; publishes a reusable runner for later independent benchmark and asyncdb tasks.
**Assigned-to**: unassigned

---

## Context

Implements M1 of the approved specification; contributes to AC1, AC2, AC4, AC7. Constructor/ORM hydration performance is the priority, with strict compatibility for repository schema examples and real `asyncdb.models`. Rust, parallel execution and serialization are measured experiments, not automatic backend migrations.

Approval is recorded in spec frontmatter and resolved requirements in §8. Its older body status/release placeholders do not override those decisions.

## Scope

- Create separate-subprocess reference/candidate execution using the fixture corpus and explicitly selected interpreters/artifacts.
- Record rebuilt reference d932c720e9e36bbacdaca2b1a2af0688f2636c40 and candidate source/binary/dependency provenance; reference version 0.10.21, current candidate 0.11.0.
- Compare type-tagged values, ordered field/error state, exception messages/payload/causes, input mutations, callback order/count and relative alias/copy relationships.
- Define and document the runner interface inside its module so dependent tasks can verify rather than invent imports.
- Support tests of the harness itself: deliberately introduced type/order/copy divergences must be detected; timestamps/randomness are controlled.

**NOT in scope**: Timing harness, runtime backend switches, source-level production changes.

## Files to Create / Modify

Ownership is restricted to these implementation/test/report files, plus this task's completion note and per-spec index state. Expand scope only through an explicit task/spec update.

| File | Action | Responsibility |
|---|---|---|
| `tests/compatibility/runner.py` | CREATE | Compatibility fixtures, test support or regression tests |
| `tests/compatibility/observations.py` | CREATE | Compatibility fixtures, test support or regression tests |
| `tests/compatibility/test_runner.py` | CREATE | Compatibility fixtures, test support or regression tests |
| `tests/compatibility/reference_manifest.json` | CREATE | Compatibility fixtures, test support or regression tests |

## Codebase Contract (Anti-Hallucination)

References were re-read against the current `dev` tree after FEAT-001 integration and before task creation (runtime baseline `1d578ab`; reservation `4d5f97d`). Verify freshness again before implementation. Planned dependency outputs are not yet existing contracts.

### Verified Imports

```python
from datamodel import BaseModel, Field, Column
from datamodel.exceptions import ValidationError
```

### Existing Signatures to Use

- datamodel/__init__.py:6-9 — existing public exports.
- datamodel/base.py:29-55 — BaseModel.__post_init__(self) -> None snapshots columns, calls processing_fields, and handles strict/non-strict validity.
- datamodel/exceptions.pyx:24-38 — ValidationError(message, payload=None); string output includes ordered payload field names.
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

Do not serialize observations with lossy plain JSON conversions. Compare identity relationships rather than process addresses. If fresh baseline builds need platform accommodations, document matching build-only changes and keep semantic source fixed.

Use the existing paths and behavior described in the contract, not the illustrative placeholders in the generic task template. Read §2–§5 of the specification for dispatch semantics, measurement protocol and acceptance thresholds.

### Key Constraints

- Preserve reference behavior, including legacy quirks; do not migrate consumers to Pydantic, weaken checks, change public/cpdef return contracts, or require model rebuild calls.
- Reference: d932c720e9e36bbacdaca2b1a2af0688f2636c40 (0.10.21), rebuilt in isolation. Candidate targets 0.11.0 and preserves FEAT-001 Linux/Windows × CPython 3.10–3.14 support.
- Use deterministic offline inputs. No production database writes, release publication, new backend packaging, or service credentials are authorized by this task.
- Rebuild affected Cython/Rust artifacts before testing. Separate diagnostic instrumentation from release timings; benchmark runs and shared extension builds require exclusive execution.
- Do not count missing dependencies, platforms, failed builds or unfinished measurements as successful verification or a completed negative experiment.
- Work in the per-spec feature worktree. You are not alone in the codebase: preserve others' edits and coordinate shared files rather than reverting their work.

### References in Codebase

The verified contract above is the source for existing behavior. New interfaces from `TASK-7` must be documented with their actual definitions, never inferred from proposed filenames.

## Acceptance Criteria

- [ ] Separate environments cannot accidentally load the same compiled candidate artifact; manifest detects stale/mismatched binaries.
- [ ] Identical reference runs compare equal and seeded semantic mismatches compare unequal with actionable paths.
- [ ] Original errors and fresh mutable return behavior remain distinguishable; no live customer callbacks execute twice.
- [ ] Reference/candidate runner tests pass; baseline failures are recorded rather than silently blessed.
- [ ] Required tests and evidence are recorded with actual commands/results; no new reference-relative regression is hidden.
- [ ] Only scoped files and task/index state change; AC1, AC2, AC4, AC7 evidence is linked in the completion note.

## Test Specification

- Run `python -m pytest tests/compatibility/test_runner.py tests/compatibility/test_fixture_corpus.py -q`.
- Demonstrate detection of int versus bool, same-value/different-type, error order, shared-default contamination and modified callback-count cases.

Tests are behavioral specifications, not permission to change the oracle. Verify import paths of new test-support modules after their dependency tasks land. A quick smoke run is not a substitute for the full acceptance protocol.

## Agent Instructions

1. Read the full spec and this task before acting; use `sdd/tasks/index/compatible-model-performance.json`, never the historical monolithic index.
2. Confirm dependencies are done/verified in that index and their task files are in `sdd/tasks/completed/`. Read their completion notes and newly implemented contracts.
3. Verify every relevant contract with `rg` and source reads before writing code. Record changed/new definitions first; do not guess imports or attributes.
4. Update only this task's assignment, start timestamp and status to `in-progress` in the per-spec index.
5. Implement only the declared scope, preserving other contributors' work. Respect the parallelism notes and serialize shared build/timing resources.
6. Run the scoped tests plus appropriate rebuilt-artifact differential checks. Record commands, artifact identities and raw evidence. If a prerequisite or required gate fails, keep the task incomplete and report it; do not waive it.
7. Fill the completion note, then use `scripts/sdd/close_task.sh TASK-8 compatible-model-performance verified` only when all required criteria are met. Verify the active copy is gone and the per-spec index points to the completed file.
8. Commit the scoped changes and task/index state in the feature worktree following the task-execution skill. Do not publish or merge the feature as part of this task.

## Completion Note

**Completed by**: sdd-worker (Claude Opus 5)
**Date**: 2026-09-08
**Notes**: Implemented the differential harness in exactly the four declared
files. The runner executes each environment in a **separate subprocess** using
that environment's **own venv interpreter** against its **own built
artifacts**. The child binds `datamodel` from the environment root first, then
removes that root from `sys.path` and prepends this worktree so the shared
fixture corpus imports without re-binding `datamodel` — verified by the child
reporting `datamodel.__file__` per run.

**Runner interface** (documented in the module docstring so dependent tasks
verify rather than invent): `Environment`, `ProvenanceError`, `RunnerError`,
`RunResult`, `CaseObservation`, `candidate_environment()`,
`reference_environment(root=None)`, `describe_environment(env)`,
`run_environment(env, cases=None)`, `compare_runs(ref, cand)`,
`describe_divergences(divs, limit)`, `write_manifest(envs, path=None)`,
`load_manifest(path=None)`, `verify_manifest(manifest, envs)`,
`DEFAULT_MANIFEST_PATH`, `REFERENCE_COMMIT`, `REFERENCE_VERSION`.

**Two guards were corrected after failing against reality:**

1. `Environment` originally called `Path.resolve()` on the interpreter. A
   venv's `bin/python` is a symlink to the *base* interpreter, so resolving it
   launched every child outside the virtualenv — site-packages vanished and
   children died on `ModuleNotFoundError: orjson`. Now normalised with
   `os.path.abspath` without following symlinks, and pinned by
   `test_environment_does_not_resolve_the_venv_symlink`.
2. The provenance guard originally *filtered out* extension modules loaded from
   outside the environment's package directory. An editable install registers a
   meta-path finder keyed on the full dotted name, so a decoy root could supply
   `datamodel` while the real tree supplied `datamodel.converters` — a mixed
   half-and-half environment that the manifest reported as simply having zero
   binaries. It is now a hard `ProvenanceError`
   (`test_a_mixed_environment_is_rejected`).

Isolation is asserted **by path, not by digest**. With the Rust and Cython
sources currently identical between 0.10.21 and the candidate, a reproducible
build legitimately produces byte-identical artifacts in both trees
(`_rs_parsers...so` digests match exactly). Treating that as a fault was a
false positive; two environments importing the *same file* is the real one.

**Verification commands/results**:
- `.venv/bin/python -m pytest tests/compatibility/ -q` → **201 passed**
  (41 runner + 160 corpus), 0 skipped, 0 failed.
- `.venv/bin/python -m pytest tests/ -q` → **451 passed, 2 skipped, 0 failed**.
- `.venv/bin/python -m ruff check --select F,E9 tests/compatibility/` → clean.
- Live differential: `compare_runs(run_environment(ref), run_environment(cand))`
  over all **45 cases** → **no divergences**.
- Self-consistency: two independent reference processes compare equal
  (`test_a_reference_run_compares_equal_to_itself`).
- Manifest: `verify_manifest(load_manifest(), [ref, cand])` → `[]`.

**Environments (recorded in `tests/compatibility/reference_manifest.json`)**:
| | reference | candidate |
|---|---|---|
| commit | `d932c720` | `66a4d509` |
| version | 0.10.21 | 0.12.0 |
| root | `.claude/worktrees/ref-FEAT-2-d932c720` | this worktree |
| interpreter | its own `.venv` (CPython 3.13.11) | its own `.venv` (CPython 3.13.11) |
| extensions | 8, sha256-recorded | 8, sha256-recorded |
| rs_parsers | built (`HAS_RUST=True`) | built (`HAS_RUST=True`) |

**MAJOR FINDING — the repository baseline is green, not broken.** TASK-7
recorded 17 pre-existing failures/errors
(`test_types.py` collection, `test_data.py::test_user_model_success`,
`test_primitives.py::test_encoders[to_date-...]`, 14 `test_generic.py` errors).
Building `rs_parsers` (`cargo build --release` in `rust/rs_parsers`, copy
`rust/target/release/lib_rs_parsers.so` to
`datamodel/rs_parsers/_rs_parsers.<abi>.so`) makes **all of them pass**: the
suite goes to 451 passed / 0 failed. Every one of those failures was
`converters.pyx:199,236` dereferencing `rc.to_date`/`rc.to_datetime` on a
module that defines only `HAS_RUST = False`. So the correct baseline
configuration for this feature is **rs_parsers present in BOTH environments**,
which is what the manifest now records. `uv pip install -e .` does not build
it — the build steps are recorded in the manifest's `reproduce` field.

**Harness validated against a real build difference.** Before aligning the
backends I deliberately ran rs_parsers-present candidate vs. rs_parsers-absent
reference. The harness reported exactly **8 divergences across exactly 2 cases**
(`employee_raw`, `unconstrained_raw`), each with an actionable path
(`$.cases.employee_raw.outcome: value reference='error' candidate='ok'`, plus
the error/instance/fresh_results consequences) and no false positives among the
other 43 cases. That is end-to-end proof the comparator detects genuine
build-level divergence, not just synthetic fixtures.

**Evidence paths and acceptance coverage**:
- AC1 (reference artifact/provenance, freshly built matching environments):
  `tests/compatibility/reference_manifest.json`;
  `test_manifest_is_present_and_names_the_specified_reference`,
  `test_manifest_records_separately_built_environments`,
  `test_manifest_records_matching_backend_availability`,
  `test_live_manifest_still_matches_the_built_artifacts`,
  `test_verify_manifest_detects_a_stale_binary`.
- AC2 (all differential cases match exactly):
  `test_reference_and_candidate_agree_on_every_case` — 45/45, zero divergences.
- AC4 (error payloads, order, callback counts retained):
  `test_error_cases_carry_a_comparable_payload` (≥8 error cases compared by
  type, message and payload order), `test_every_case_ran_exactly_once`,
  `test_changed_callback_count_is_detected`,
  `test_error_payload_order_is_detected`.
- AC7 (fresh mutable results, unchanged public behaviour):
  `test_success_results_stay_independently_mutable` (≥20 cases assert
  `to_dict()` returns a distinct object per call on both builds),
  `test_shared_success_result_is_detected`.
- Seeded-divergence detection (harness trustworthiness): 20 tests in Part 1 of
  `test_runner.py`, covering every family the task enumerates — int vs bool,
  same-value/different-type, error order, shared-default contamination and
  modified callback counts.

**Deviations from spec**: none in scope or file ownership. Notes for the
reviewer:
1. The task's Codebase Contract states "datamodel/version.py:9 — current
   version is already 0.11.0; do not bump it again." On the current `dev` it is
   **0.12.0** (commit `1f3664b`, "new release for changes on performance", which
   landed after this task was written). I did not touch it. TASK-22 will need
   the maintainer to reconcile the declared 0.11.0 target with reality.
2. The reference worktree lives at
   `.claude/worktrees/ref-FEAT-2-d932c720` (gitignored). `reference_environment()`
   also honours `$DATAMODEL_REFERENCE_ROOT`, and every reference-dependent test
   skips with an explicit "a skipped comparison is NOT a passing comparison"
   message when it is absent.
3. Compiled artifacts (`*.so`) are gitignored, so a fresh clone must rebuild
   both environments and regenerate the manifest before the provenance tests
   pass. That is intentional: the manifest records what was actually measured.
