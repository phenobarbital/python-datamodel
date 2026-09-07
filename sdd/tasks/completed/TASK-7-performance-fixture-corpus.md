# TASK-7: Build deterministic model compatibility fixtures

**Feature**: FEAT-2 - Compatible model execution performance
**Spec**: `sdd/specs/compatible-model-performance.spec.md`
**Status**: done
**Priority**: high
**Estimated effort**: M (3h active engineering time; external evidence wait excluded)
**Depends-on**: none
**Parallel**: true
**Parallelism notes**: Initial task; future harness work reads its stable fixtures. Own fixture files only.
**Assigned-to**: unassigned

---

## Context

Implements M1 of the approved specification; contributes to AC1, AC2, AC7. Constructor/ORM hydration performance is the priority, with strict compatibility for repository schema examples and real `asyncdb.models`. Rust, parallel execution and serialization are measured experiments, not automatic backend migrations.

Approval is recorded in spec frontmatter and resolved requirements in §8. Its older body status/release placeholders do not override those decisions.

## Scope

- Extract deterministic Employee raw/native fixtures and representative repository schema examples; inventory schema-bearing examples and record coverage or explicit exclusion reasons in examples_manifest.json.
- Add unconstrained/constrained scalars, 50-field models, nested containers/ORM-like relationships, invalid values, descriptor/custom-hook, mutation and alias scenarios.
- Ensure each case creates independent mutable inputs while preserving deliberate aliases within a case; stub nondeterministic factories and external effects.
- Cover bool/int, date/datetime, arbitrary-size integers, Decimal context/extremes, bytes/string, subclass, empty/default cases without normalizing their semantics.

**NOT in scope**: Reference runner, timings, asyncdb integration, production optimizations.

## Files to Create / Modify

Ownership is restricted to these implementation/test/report files, plus this task's completion note and per-spec index state. Expand scope only through an explicit task/spec update.

| File | Action | Responsibility |
|---|---|---|
| `tests/fixtures/model_performance/__init__.py` | CREATE | Compatibility fixtures, test support or regression tests |
| `tests/fixtures/model_performance/models.py` | CREATE | Compatibility fixtures, test support or regression tests |
| `tests/fixtures/model_performance/cases.py` | CREATE | Compatibility fixtures, test support or regression tests |
| `tests/fixtures/model_performance/examples_manifest.json` | CREATE | Compatibility fixtures, test support or regression tests |
| `tests/compatibility/test_fixture_corpus.py` | CREATE | Compatibility fixtures, test support or regression tests |

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
- examples/rust_benchmark.py:35-51 — Employee's 11 fields, required/primary metadata and age bounds; PAYLOAD/NATIVE_PAYLOAD at 105-139.
- examples/test_qsmodel.py:38-68 — QueryModel schema with optional nested containers and defaults.
- examples/test_datadriver.py:8-45 — DataDriver with InitVar and custom __post_init__ calling super; inspect before executing examples with top-level code.
- tests/test_qsmodel.py:12-82 — existing QueryModel fixture pattern; tests/test_converter.py:6-61 — Organization/Client nested ORM-like models.

### Does NOT Exist

- Files marked CREATE below are planned artifacts, not existing interfaces. Read completed dependencies to verify their newly introduced APIs before using them.
- No existing production per-field validation policy, compatible rs_core backend loader, or public batch-construction API is established by this contract.
- `_validate_constraints` is a Cython cdef interface, not a Python-importable function. Do not invent Python imports for it.

## Implementation Notes

### Pattern to Follow

Importing arbitrary examples may execute top-level code. Adapt verified schemas into fixtures rather than bulk-importing examples. Preserve full source-to-fixture provenance.

Use the existing paths and behavior described in the contract, not the illustrative placeholders in the generic task template. Read §2–§5 of the specification for dispatch semantics, measurement protocol and acceptance thresholds.

### Key Constraints

- Preserve reference behavior, including legacy quirks; do not migrate consumers to Pydantic, weaken checks, change public/cpdef return contracts, or require model rebuild calls.
- Reference: d932c720e9e36bbacdaca2b1a2af0688f2636c40 (0.10.21), rebuilt in isolation. Candidate targets 0.11.0 and preserves FEAT-001 Linux/Windows × CPython 3.10–3.14 support.
- Use deterministic offline inputs. No production database writes, release publication, new backend packaging, or service credentials are authorized by this task.
- Rebuild affected Cython/Rust artifacts before testing. Separate diagnostic instrumentation from release timings; benchmark runs and shared extension builds require exclusive execution.
- Do not count missing dependencies, platforms, failed builds or unfinished measurements as successful verification or a completed negative experiment.
- Work in the per-spec feature worktree. You are not alone in the codebase: preserve others' edits and coordinate shared files rather than reverting their work.

### References in Codebase

The verified contract above is the source for existing behavior. New interfaces from this task must be documented with their actual definitions, never inferred from proposed filenames.

## Acceptance Criteria

- [ ] Employee preserves all 11 declarations, defaults and constraints; fixtures include both supplied input forms.
- [ ] Fixture reuse cannot leak mutations, class-cache collisions or callback logs between independent cases.
- [ ] Examples coverage manifest identifies every inventoried schema example and any reason for safe adaptation instead of top-level execution.
- [ ] Fixture tests pass on the current baseline; no application behavior is changed.
- [ ] Required tests and evidence are recorded with actual commands/results; no new reference-relative regression is hidden.
- [ ] Only scoped files and task/index state change; AC1, AC2, AC7 evidence is linked in the completion note.

## Test Specification

- Run `python -m pytest tests/compatibility/test_fixture_corpus.py -q`.
- Tests: independent inputs; preserved intra-case aliases; deterministic factories; complete Employee metadata; side-effect-free example adaptations.

Tests are behavioral specifications, not permission to change the oracle. Verify import paths of new test-support modules after their dependency tasks land. A quick smoke run is not a substitute for the full acceptance protocol.

## Agent Instructions

1. Read the full spec and this task before acting; use `sdd/tasks/index/compatible-model-performance.json`, never the historical monolithic index.
2. Confirm dependencies are done/verified in that index and their task files are in `sdd/tasks/completed/`. Read their completion notes and newly implemented contracts.
3. Verify every relevant contract with `rg` and source reads before writing code. Record changed/new definitions first; do not guess imports or attributes.
4. Update only this task's assignment, start timestamp and status to `in-progress` in the per-spec index.
5. Implement only the declared scope, preserving other contributors' work. Respect the parallelism notes and serialize shared build/timing resources.
6. Run the scoped tests plus appropriate rebuilt-artifact differential checks. Record commands, artifact identities and raw evidence. If a prerequisite or required gate fails, keep the task incomplete and report it; do not waive it.
7. Fill the completion note, then use `scripts/sdd/close_task.sh TASK-7 compatible-model-performance verified` only when all required criteria are met. Verify the active copy is gone and the per-spec index points to the completed file.
8. Commit the scoped changes and task/index state in the feature worktree following the task-execution skill. Do not publish or merge the feature as part of this task.

## Completion Note

**Completed by**: sdd-worker (Claude Opus 5)
**Date**: 2026-09-08
**Notes**: Implemented M1's fixture corpus exactly within the five declared
files. `Employee` is a field-for-field port of `examples/rust_benchmark.py:35-51`
(all 11 declarations, defaults, `age` min/max, `employee_id` primary/required),
with both supplied input forms (`PAYLOAD` raw strings and `NATIVE_PAYLOAD`
already-typed) as separate cases. Sixteen models and 45 cases cover
unconstrained/constrained scalars, a 50-field model, nested ORM relationships
(`Organization`/`Client` with `as_objects` + a model-typed alias), typed
containers, invalid payloads, descriptors, a `super().__post_init__()` hook
model, aliases, presence rules and native boundaries (2**96 int, 28-digit
Decimal, bool-as-int, non-ASCII, bytes, subclasses).

Several expectations I initially wrote from the spec's reading were **wrong
against the actual reference build**. Rather than assert my assumption, I
verified each against the running code and pinned the observed behaviour as a
`characterization`-tagged case with a `VERIFIED:` note:

- `min`/`max` on a `str` field are never enforced (a 21-char value builds fine).
  Spec §1 lists activating previously-ignored constraints as a non-goal, so the
  corpus pins the *absence* of the check.
- `nullable=False` raises `ValueError ':: *f* Cannot be null.'` for `''` but
  silently falls back to the default for an explicit `None`. Both halves pinned.
- A `date` supplied to a `datetime` field is rejected during *conversion*
  ("argument must be str"); `validation.pyx:59`'s date-accepting datetime
  validator is never reached.
- A `str` subclass is rejected for a `str` field ("Expected str, got ...") —
  the reference already performs an exact-type check there.
- A user `validator=` on a primitive is dead (`abstract.py:257` caches
  `validators[int]` into `f.validator`, so `converters.pyx:2354` never reaches
  `validation.pyx:488`), and a user `encoder=` on a `str` is dead
  (`parse_basic` short-circuits `str` before its encoder branch). Both dead
  routes are pinned so a "unified callback" refactor cannot quietly revive them.
  The live counterparts (`List[str]` validator, `float` encoder) are pinned too.

**Verification commands/results**:
- `.venv/bin/python -m pytest tests/compatibility/test_fixture_corpus.py -q`
  → **156 passed, 3 skipped** (skips are the rust-absent date cases, below).
- `.venv/bin/python -m pytest tests/ -q --ignore=tests/test_types.py`
  → **382 passed, 2 failed, 5 skipped, 14 errors**.
  Pre-change baseline on the same worktree/commit was **226 passed, 2 failed,
  2 skipped, 14 errors**: identical failure set, so **no new
  reference-relative regression**. The pre-existing failures are
  `tests/test_data.py::test_user_model_success`,
  `tests/test_primitives.py::test_encoders[to_date-...]`, the 14
  `tests/test_generic.py` errors, and the `tests/test_types.py` collection
  error — all the same root cause (below).
- `.venv/bin/python -m ruff check --select F,E9 tests/fixtures/model_performance/
  tests/compatibility/` → clean. (The repo has no ruff config; default rules
  report 9 errors on pre-existing `tests/test_converter.py` too, so full-default
  ruff is not a gate here.)

**Environment**: dedicated worktree venv, CPython 3.13.11, Cython 3.2.9,
`uv pip install -e ".[dev]"`, extensions built in place from this worktree
(`datamodel/converters.cpython-313-x86_64-linux-gnu.so` etc. resolve to the
worktree, verified via `datamodel.converters.__file__`).

**rs_parsers-absent gap (characterized, not fixed)**: `converters.pyx:199,236`
call `rc.to_date` / `rc.to_datetime` unconditionally, but
`datamodel/rs_parsers/__init__.py` only defines `HAS_RUST = False` when the
extension is missing — so every string→date/datetime conversion raises. This
is the root cause of *all* pre-existing suite failures listed above. I verified
via `git show d932c720...:datamodel/converters.pyx` that the engineering
reference has the **identical** call sites, so differential parity is
unaffected; the gap is shared. Spec §4 explicitly requires characterizing this
separately rather than claiming the fallback works, so the corpus exposes it as
`Case.requires_rust_parsers` plus a dedicated
`test_rs_parsers_absent_gap_is_characterized` test, and does not fix it (spec
§1 non-goal: "fixing incidental legacy bugs"). `cargo build --release` in
`rust/rs_parsers` succeeds, so a rust-present configuration is available for
later measurement tasks — but both reference and candidate must be built with
the *same* backend availability.

**Evidence paths and acceptance coverage**:
- AC1 (deterministic compatibility corpus): `tests/fixtures/model_performance/`
  — frozen clocks/UUIDs, `test_no_case_uses_a_nondeterministic_factory`,
  `test_frozen_defaults_are_used_instead_of_clocks`.
- AC2 (no new failures): full-suite run above, identical failure set to baseline.
- AC7 (no leakage of new state into public results): the corpus adds no
  production code at all; `test_every_model_class_is_distinct_and_provenanced`
  and `test_case_payloads_are_independent_between_calls` guard against shared
  class plans and shared mutables.
- Examples coverage: `tests/fixtures/model_performance/examples_manifest.json`
  (74 modules, 60 schema-bearing, 3 adapted, 57 excluded with reasons),
  enforced by `test_manifest_covers_every_example_module`,
  `test_manifest_matches_the_live_inventory` and
  `test_every_schema_example_states_a_disposition_and_reason`.

**Deviations from spec**: none in scope or file ownership. Two observations for
the reviewer, neither acted upon:
1. `datamodel/version.py` on `dev` is already `0.12.0`, while the spec's §8
   resolution names **0.11.0** as the release carrying this work (and origin
   already carries a `0.11.0` tag). This does not affect implementation, but
   the release-documentation task (TASK-22) will need the maintainer to
   reconcile the target version.
2. The corpus deliberately contains no expected-value literals for behaviour;
   the reference build is the oracle, per spec §4. `EXPECT_OK`/`EXPECT_ERROR`
   labels are only coarse routing hints and are themselves asserted honest by
   `test_ok_cases_build` / `test_error_cases_raise`.
