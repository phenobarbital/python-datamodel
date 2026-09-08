# TASK-10: Pin asyncdb.models and add strict ORM compatibility coverage

**Feature**: FEAT-2 - Compatible model execution performance
**Spec**: `sdd/specs/compatible-model-performance.spec.md`
**Status**: pending
**Priority**: high
**Estimated effort**: M (4h active engineering time; external evidence wait excluded)
**Depends-on**: TASK-8
**Parallel**: true
**Parallelism notes**: Can run alongside benchmark/policy work; own asyncdb-specific fixture and test files. Required before the Cython acceptance and release gates.
**Assigned-to**: unassigned

---

## Context

Implements M1 / AC12 of the approved specification; contributes to AC1, AC2, AC7, AC12. Constructor/ORM hydration performance is the priority, with strict compatibility for repository schema examples and real `asyncdb.models`. Rust, parallel execution and serialization are measured experiments, not automatic backend migrations.

Approval is recorded in spec frontmatter and resolved requirements in §8. Its older body status/release placeholders do not override those decisions.

## Scope

- Locate/pin a real company-relevant asyncdb distribution/source artifact; record version/commit/hash and verify its models implementation before naming its imports or methods.
- Extend this task's contract with actual asyncdb.models paths/signatures, then instantiate real consumer model classes under both datamodel artifacts.
- Cover hydration from raw/typed rows, fields and primary keys, nested relations, required/null/default behavior, aliases, assignment/history, serialization and observed ORM hooks.
- Use offline fixtures or a stubbed driver boundary for external I/O; do not replace asyncdb.models itself with a fake model.
- Retain any external service integration requirement as explicit evidence pending; missing asyncdb must fail the required integration gate, not silently skip.

**NOT in scope**: Modifying asyncdb source, production database writes, publishing packages, or choosing Pydantic semantics.

## Files to Create / Modify

Ownership is restricted to these implementation/test/report files, plus this task's completion note and per-spec index state. Expand scope only through an explicit task/spec update.

| File | Action | Responsibility |
|---|---|---|
| `tests/fixtures/model_performance/asyncdb_models.py` | CREATE | Compatibility fixtures, test support or regression tests |
| `tests/fixtures/model_performance/asyncdb_manifest.json` | CREATE | Compatibility fixtures, test support or regression tests |
| `tests/compatibility/test_asyncdb_models.py` | CREATE | Compatibility fixtures, test support or regression tests |
| `benchmarks/results/compatible-model-performance/asyncdb-baseline.json` | CREATE | Reproducible evidence and decision report |

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
- examples/rust_benchmark.py:35-51 — Employee's 11 fields, required/primary metadata and age bounds; PAYLOAD/NATIVE_PAYLOAD at 105-139.
- examples/test_qsmodel.py:38-68 — QueryModel schema with optional nested containers and defaults.
- examples/test_datadriver.py:8-45 — DataDriver with InitVar and custom __post_init__ calling super; inspect before executing examples with top-level code.
- tests/test_qsmodel.py:12-82 — existing QueryModel fixture pattern; tests/test_converter.py:6-61 — Organization/Client nested ORM-like models.

### Does NOT Exist

- Files marked CREATE below are planned artifacts, not existing interfaces. Read completed dependencies to verify their newly introduced APIs before using them.
- No existing production per-field validation policy, compatible rs_core backend loader, or public batch-construction API is established by this contract.
- `_validate_constraints` is a Cython cdef interface, not a Python-importable function. Do not invent Python imports for it.
- No local asyncdb installation/checkout was found during planning. Its import paths and company artifact pin remain execution-time discovery requirements; do not substitute guessed APIs.

## Implementation Notes

### Pattern to Follow

User's resolved requirement: “schema examples in examples/ folder and asyncdb.models (that uses under-the-hood python-datamodel) requires strict compat.” Local discovery found asyncdb unavailable and no local checkout. This is an explicit discovery boundary, not a verified import. Use the reference artifact from the spec and record the consumer version; request only genuinely unavailable company artifact information during execution.

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

- [ ] Manifest identifies a real pinned asyncdb artifact and verified adapter imports; no guessed asyncdb API is used.
- [ ] Representative real asyncdb.models instances match reference/candidate values, types, errors and ORM-visible state.
- [ ] Absence of the dependency cannot make the required suite report success.
- [ ] Company integration results and any genuine remaining external prerequisites are explicitly recorded.
- [ ] Required tests and evidence are recorded with actual commands/results; no new reference-relative regression is hidden.
- [ ] Only scoped files and task/index state change; AC1, AC2, AC7, AC12 evidence is linked in the completion note.

## Test Specification

- Run `python -m pytest tests/compatibility/test_asyncdb_models.py -q` in each isolated environment after installing the pinned artifact.
- Exercise successful hydration plus malformed rows, dynamic/default mutations and serialization with actual asyncdb models.

Tests are behavioral specifications, not permission to change the oracle. Verify import paths of new test-support modules after their dependency tasks land. A quick smoke run is not a substitute for the full acceptance protocol.

## Agent Instructions

1. Read the full spec and this task before acting; use `sdd/tasks/index/compatible-model-performance.json`, never the historical monolithic index.
2. Confirm dependencies are done/verified in that index and their task files are in `sdd/tasks/completed/`. Read their completion notes and newly implemented contracts.
3. Verify every relevant contract with `rg` and source reads before writing code. Record changed/new definitions first; do not guess imports or attributes.
4. Update only this task's assignment, start timestamp and status to `in-progress` in the per-spec index.
5. Implement only the declared scope, preserving other contributors' work. Respect the parallelism notes and serialize shared build/timing resources.
6. Run the scoped tests plus appropriate rebuilt-artifact differential checks. Record commands, artifact identities and raw evidence. If a prerequisite or required gate fails, keep the task incomplete and report it; do not waive it.
7. Fill the completion note, then use `scripts/sdd/close_task.sh TASK-10 compatible-model-performance verified` only when all required criteria are met. Verify the active copy is gone and the per-spec index points to the completed file.
8. Commit the scoped changes and task/index state in the feature worktree following the task-execution skill. Do not publish or merge the feature as part of this task.

## Completion Note

**Completed by**: sdd-worker (Claude Opus 5)
**Date**: 2026-09-08
**Notes**: Implemented AC12's consumer coverage in exactly the four declared
files. No production code was touched.

**The artifact the task said had to be discovered at execution time.** The
contract stated plainly: *"No local asyncdb installation/checkout was found
during planning. Its import paths and company artifact pin remain
execution-time discovery requirements; do not substitute guessed APIs."* The
real distribution is **`asyncdb` 2.16.0 on PyPI**, and it is company-relevant
on evidence rather than assumption:

- authored by `Jesus Lara <jesuslara@phenobarbital.info>` -- the same
  author/maintainer as python-datamodel itself,
- source `https://github.com/phenobarbital/asyncdb`,
- it declares `python-datamodel>=0.10.21`, which is **exactly** the engineering
  reference version this whole feature is measured against,
- sha256 `26b77d7b7d9cdd2e51049d632ed02d7c339509e7157f49efa7e3dd403f27c45f`,
  verified against the PyPI record and re-hashed from the downloaded file.

Every claim in `asyncdb_manifest.json` is machine-checked against the installed
distribution rather than trusted: the pinned version must equal the installed
version, the declared `python-datamodel` requirement must appear in the real
`Requires-Dist`, the recorded MRO must equal the live MRO, and **every**
`datamodel` symbol the manifest says asyncdb consumes must resolve by import
(`test_manifest_adapter_imports_all_resolve`). A stale manifest cannot look
verified.

**Real models, not a stand-in.** All six fixture models subclass the installed
`asyncdb.models.Model`. `test_models_are_real_asyncdb_models_not_local_fakes`
and `test_asyncdb_model_really_sits_on_datamodel` assert the live MRO contains
both `asyncdb.models.model.Model` and `datamodel.base.BaseModel`, so a fake
could not be substituted. This matters because asyncdb consumes a **wider**
surface than `BaseModel` alone -- `datamodel.abstract.Meta`,
`datamodel.types.MODEL_TYPES` and `datamodel.types.DB_TYPES` -- which is
precisely why it is the load-bearing consumer.

**The driver boundary is stubbed; the ORM is not.** Every database method
(`insert`/`update`/`select`/`get`/`makeModel`/...) is `async` and needs a live
connection, so all are excluded and *named* in the manifest, with
`test_excluded_methods_exist_but_are_deliberately_untested` asserting each
excluded name is a real attribute -- an exclusion list naming phantom methods
would overstate what was consciously left out. `set_connection()` is exercised
against an inert `StubConnection`; `get_connection()` is never called because
it imports a driver module and constructs a real client. No database was
contacted.

**RESULT -- zero divergences.** 18 cases across 6 models, built in two separate
subprocesses, each bound to its **own** compiled datamodel:

| | reference | candidate |
|---|---|---|
| datamodel | 0.10.21 (`d932c720`) | 0.12.0 (this worktree) |
| asyncdb | 2.16.0 | 2.16.0 (identical, so a difference could not be asyncdb's) |

Compared: hydration from raw all-string and already-typed rows, type coercion,
defaults, required/nullable/explicit-None, primary keys, aliases (by attribute
and by wire alias), nested relation hydration under `as_objects`, exception
**type, message and payload**, `to_dict()`, `json()`, assignment, rendered DDL
and column ordering. `divergences: 0` in all three areas
(`benchmarks/results/compatible-model-performance/asyncdb-baseline.json`).

**Three behaviours found by running the code, not by reading it:**

1. **`from __future__ import annotations` breaks datamodel model definition.**
   My first draft used it; every model failed with `TypeError: Expected type,
   got str`, because PEP 563 stringifies annotations while datamodel resolves
   `field.type` as a real object. `models.py` omits it for the same reason.
   Removed, and pinned by `test_fixture_module_does_not_use_postponed_annotations`
   so a cleanup cannot reintroduce it. (The guard initially failed against its
   own explanatory comment -- it now matches a real import statement via regex.)
2. **`min=` IS enforced on an int column.** I had assumed it was ignored and
   declared the case as expected-OK; the reference build raised
   `ValidationError`. The oracle is the reference build, so the observed
   behaviour is pinned instead of my assumption. This **contradicts a naive
   generalisation** of TASK-7's finding that `min`/`max` on a *str* field are
   silently ignored -- "constraints are not enforced" is false in general.
3. **asyncdb's DDL leaks a heap address.** `Model.model()` renders a
   `default_factory` column as
   `varchar DEFAULT <dataclasses._MISSING_TYPE object at 0x...>`. The address
   differs per process, so a raw comparison failed spuriously. It is identical
   on both builds, i.e. an asyncdb rendering quirk and *not* a compatibility
   break, so the differential normalises addresses to `0xADDR` and compares the
   DDL rather than the allocator. Recorded in the report's `observed_quirks`.

Also recorded: importing asyncdb **mutates datamodel module state**
(`DB_TYPES[numpy.int64] = 'bigint'` at import time), pinned by
`test_asyncdb_mutates_datamodel_db_types_at_import`.

**A missing dependency fails; it does not skip -- demonstrated, not asserted.**
`test_asyncdb_is_installed_in_this_environment` fails when asyncdb is absent,
and `test_the_required_integration_gate_cannot_pass_without_asyncdb` exercises
the gate's own logic against a simulated absence so the gate is not
self-certifying. I then verified it for real: re-running that test under a
`sys.meta_path` blocker that hides asyncdb produced
`1 failed`, **pytest exit code 1**, with the message "asyncdb is NOT
importable, so consumer compatibility is UNVERIFIED". The reference-comparison
tests *do* skip when the reference **worktree** is unbuilt -- a different
condition (an environment never built, not a missing dependency) -- and each
such skip states "a SKIPPED comparison is NOT a passing comparison".

**Trustworthiness of the differential itself.**
`test_the_differential_would_notice_a_planted_difference` plants a changed
outcome and requires the comparator to report it, so "zero divergences" is a
measurement rather than a tautology.
`test_the_two_environments_are_actually_different_builds` asserts the two runs
loaded **different** `datamodel.__file__` paths -- without it, both children
could load one build and the comparison would be vacuous. (That failure mode is
real: while verifying the install I ran the reference interpreter from the
candidate's cwd and it silently imported the *candidate's* datamodel, because
`python -c` puts cwd first on `sys.path`. The child mirrors `runner.py`'s
path discipline and re-checks `datamodel.__file__` is under its own root.)

**Verification commands/results**:
- `.venv/bin/python -m pytest tests/compatibility/test_asyncdb_models.py -q`
  -> **31 passed**, 0 skipped, 0 failed (reference worktree present).
- `.venv/bin/python -m pytest tests/ -q` -> **536 passed, 2 skipped, 0 failed**
  (505 before this task + 31 new; no new reference-relative regression).
- `.venv/bin/python -m ruff check --select F,E9 tests/compatibility/
  tests/fixtures/model_performance/ benchmarks/` -> clean.
- Missing-dependency gate under an import blocker -> `1 failed`, exit code 1.
- Live differential -> 18 cases, 6 models, **0 divergences**.

**Install used in both environments** (recorded in the manifest):
`uv pip install --no-deps <wheel>` into each root's own venv. `--no-deps` is
load-bearing: a plain install would resolve `python-datamodel>=0.10.21` from
PyPI and silently shadow the very build under test.

**Evidence paths and acceptance coverage**:
- AC12 / AC2 (real consumer parity): `asyncdb-baseline.json`
  (`result.divergences: 0`); `test_asyncdb_consumer_behaviour_is_identical`,
  `test_rendered_schema_is_identical`, `test_assignment_behaviour_is_identical`,
  `test_error_cases_are_compared_by_payload_not_just_by_raising`.
- AC1 (pinned artifact and isolated provenance): `asyncdb_manifest.json`;
  `test_manifest_pins_the_installed_distribution`,
  `test_manifest_records_a_verifiable_digest`,
  `test_manifest_declares_the_datamodel_requirement`,
  `test_manifest_mro_matches_reality`, `test_manifest_exports_all_resolve`,
  `test_the_two_environments_are_actually_different_builds`.
- AC7 (no shared state leaking into public results):
  `test_success_results_stay_independently_mutable` (every OK case asserts
  `to_dict()` returns a distinct object per call on **both** builds),
  `test_case_rows_are_independent_between_calls`.
- Determinism: `test_no_case_uses_a_nondeterministic_factory`.

**Deviations from spec**: none in scope or file ownership. Notes for the
reviewer:
1. **Genuinely pending external prerequisites, recorded rather than dropped**
   (manifest `external_prerequisites_pending`, mirrored into the report and
   asserted present by `test_manifest_records_pending_external_prerequisites`):
   (a) no company-internal asyncdb fork or private index was provided, so the
   pin is the public PyPI distribution by the same author -- if a private
   Navigator build diverges from 2.16.0 it must be re-pinned and the
   differential re-run before consumer compatibility can be claimed for it;
   (b) live driver integration (postgres/mysql/redis) needs service credentials
   this task is not authorized to use, so driver-level compatibility remains
   evidence-pending. Neither is claimed as verified.
2. TASK-10 does not own `runner.py`, whose child protocol is bound to the main
   corpus, so this module ships its own small child script mirroring that
   file's `sys.path` discipline, while reusing `runner`'s `Environment`
   discovery and `observations`' `Observer`/`compare` so the two tasks cannot
   disagree about what "the reference build" or "a difference" means.
3. `asyncdb` is installed into both venvs but is **not** added to
   `pyproject.toml`: it is a downstream consumer used as a test oracle, and
   making the library depend on its own consumer would be circular. Reproducing
   these results requires the documented `--no-deps` install.
