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

*(Fill in only after implementation and verification.)*

**Completed by**: pending
**Date**: pending
**Notes**: pending
**Verification commands/results**: pending
**Evidence paths and acceptance coverage**: pending
**Deviations from spec**: pending
