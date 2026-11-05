# TASK-19: Evaluate bounded native parallelism for large pure workloads

**Feature**: FEAT-2 - Compatible model execution performance
**Spec**: `sdd/specs/compatible-model-performance.spec.md`
**Status**: pending
**Priority**: medium
**Estimated effort**: M (4h active engineering time; external evidence wait excluded)
**Depends-on**: TASK-18
**Parallel**: true
**Parallelism notes**: Serial after sequential native work; disjoint from serialization files. Timing and any shared build resources must be scheduled exclusively.
**Assigned-to**: unassigned

---

## Context

Implements M6 of the approved specification; contributes to AC9, AC11. Constructor/ORM hydration performance is the priority, with strict compatibility for repository schema examples and real `asyncdb.models`. Rust, parallel execution and serialization are measured experiments, not automatic backend migrations.

Approval is recorded in spec frontmatter and resolved requirements in §8. Its older body status/release placeholders do not override those decisions.

## Scope

- Add development-only native snapshot execution with detached caller, immutable owned work, bounded reusable Rayon workers and deterministic result ordering.
- Restrict eligibility to independent pure computations; preserve serial boundaries for custom callbacks, errors, descriptors and mutations.
- Measure sizes 1,10,100,1000,10000, thread counts and crossover including extraction/reconstruction and memory; retain sequential execution for small work.
- Record the AC9 >=1.25x throughput decision against sequential Rust. Do not require sequential Rust production promotion before investigating eligible native bulk workloads.

**NOT in scope**: Parallel execution of arbitrary Python callbacks, unbounded pools, package deployment or live ORM bulk writes.

## Files to Create / Modify

Ownership is restricted to these implementation/test/report files, plus this task's completion note and per-spec index state. Expand scope only through an explicit task/spec update.

| File | Action | Responsibility |
|---|---|---|
| `rust/rs_core/src/lib.rs` | MODIFY | Scoped runtime/experimental implementation |
| `benchmarks/native_validation.py` | MODIFY | Development-only measurement harness |
| `tests/compatibility/test_parallel_validation.py` | CREATE | Compatibility fixtures, test support or regression tests |
| `benchmarks/results/compatible-model-performance/rust-parallel.json` | CREATE | Reproducible evidence and decision report |
| `benchmarks/results/compatible-model-performance/rust-parallel.md` | CREATE | Reproducible evidence and decision report |

## Codebase Contract (Anti-Hallucination)

References were re-read against the current `dev` tree after FEAT-001 integration and before task creation (runtime baseline `1d578ab`; reservation `4d5f97d`). Verify freshness again before implementation. Planned dependency outputs are not yet existing contracts.

### Verified Imports

```python
from datamodel import BaseModel, Field, Column
from datamodel.exceptions import ValidationError
```

### Existing Signatures to Use

- rust/rs_core/src/lib.rs:1-7 — `use pyo3::prelude::*;` and `use rayon::prelude::*;`.
- rust/rs_core/src/lib.rs:180-237 — get_field_info extracts a new native vector, narrows integer values and skips unsupported field types.
- rust/rs_core/src/lib.rs:245-282 — parse_datamodel(py: Python<'_>, dataclass_instance: Py<PyAny>) -> PyResult<Vec<(String,bool)>>; current Rayon prototype is not compatible model validation.
- rust/rs_core/Cargo.toml:1-19 — cdylib rs_core; PyO3 0.29, Rayon 1.5.3 declaration, chrono 0.4.
- rust/Cargo.toml:1-14 — workspace includes rs_core, rs_parsers and rs_validators.
- datamodel/rs_parsers/__init__.py:8-30 — existing optional rs_parsers loader, not a loader for rs_core.
- datamodel/base.py:35-55 — errors/state observable at construction.
- datamodel/models.py:134-152,209-226,304-308 — reset_values/old_value, to_dict and json.
- datamodel/abstract.py:66-145 — assignment history and parser-only assignment validation.
- tests/test_descriptors.py:6-80 — descriptors execute through normal attribute access; tests/test_field.py:8-70 — fields/defaults/metadata.

### Does NOT Exist

- Files marked CREATE below are planned artifacts, not existing interfaces. Read completed dependencies to verify their newly introduced APIs before using them.
- No existing production per-field validation policy, compatible rs_core backend loader, or public batch-construction API is established by this contract.
- `_validate_constraints` is a Cython cdef interface, not a Python-importable function. Do not invent Python imports for it.

## Implementation Notes

### Pattern to Follow

If no eligible workload survives sequential parity, record that demonstrated result and retain sequential behavior; do not fabricate a speed comparison. Pure snapshots must preserve all reference-observable semantics.

Use the existing paths and behavior described in the contract, not the illustrative placeholders in the generic task template. Read §2–§5 of the specification for dispatch semantics, measurement protocol and acceptance thresholds.

### Key Constraints

- Preserve reference behavior, including legacy quirks; do not migrate consumers to Pydantic, weaken checks, change public/cpdef return contracts, or require model rebuild calls.
- Reference: d932c720e9e36bbacdaca2b1a2af0688f2636c40 (0.10.21), rebuilt in isolation. Candidate targets 0.11.0 and preserves FEAT-001 Linux/Windows × CPython 3.10–3.14 support.
- Use deterministic offline inputs. No production database writes, release publication, new backend packaging, or service credentials are authorized by this task.
- Rebuild affected Cython/Rust artifacts before testing. Separate diagnostic instrumentation from release timings; benchmark runs and shared extension builds require exclusive execution.
- Do not count missing dependencies, platforms, failed builds or unfinished measurements as successful verification or a completed negative experiment.
- Work in the per-spec feature worktree. You are not alone in the codebase: preserve others' edits and coordinate shared files rather than reverting their work.

### References in Codebase

The verified contract above is the source for existing behavior. New interfaces from `TASK-18` must be documented with their actual definitions, never inferred from proposed filenames.

## Acceptance Criteria

- [ ] No worker accesses Python while detached or relies on the caller holding the interpreter during Python callbacks.
- [ ] Results/error order and callback counts match; ineligible work remains serial with no extra side effects.
- [ ] Threshold/workers/memory/full-cost results are recorded; negative measured result retains sequential execution.
- [ ] No public batch API or constructor threading default is introduced.
- [ ] Required tests and evidence are recorded with actual commands/results; no new reference-relative regression is hidden.
- [ ] Only scoped files and task/index state change; AC9, AC11 evidence is linked in the completion note.

## Test Specification

- Run `python -m pytest tests/compatibility/test_parallel_validation.py -q` with the development extension.
- Measure the specified size grid sequentially and in bounded native parallel mode, including ineligible input behavior.
- Check thread oversubscription, deterministic order, invalid values, zero/small batches and threshold boundaries.

Tests are behavioral specifications, not permission to change the oracle. Verify import paths of new test-support modules after their dependency tasks land. A quick smoke run is not a substitute for the full acceptance protocol.

## Agent Instructions

1. Read the full spec and this task before acting; use `sdd/tasks/index/compatible-model-performance.json`, never the historical monolithic index.
2. Confirm dependencies are done/verified in that index and their task files are in `sdd/tasks/completed/`. Read their completion notes and newly implemented contracts.
3. Verify every relevant contract with `rg` and source reads before writing code. Record changed/new definitions first; do not guess imports or attributes.
4. Update only this task's assignment, start timestamp and status to `in-progress` in the per-spec index.
5. Implement only the declared scope, preserving other contributors' work. Respect the parallelism notes and serialize shared build/timing resources.
6. Run the scoped tests plus appropriate rebuilt-artifact differential checks. Record commands, artifact identities and raw evidence. If a prerequisite or required gate fails, keep the task incomplete and report it; do not waive it.
7. Fill the completion note, then use `scripts/sdd/close_task.sh TASK-19 compatible-model-performance verified` only when all required criteria are met. Verify the active copy is gone and the per-spec index points to the completed file.
8. Commit the scoped changes and task/index state in the feature worktree following the task-execution skill. Do not publish or merge the feature as part of this task.

## Completion Note

*(Fill in only after implementation and verification.)*

**Completed by**: pending
**Date**: pending
**Notes**: pending
**Verification commands/results**: pending
**Evidence paths and acceptance coverage**: pending
**Deviations from spec**: pending
