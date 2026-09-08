# TASK-20: Evaluate compatible JSON traversal optimizations

**Feature**: FEAT-2 - Compatible model execution performance
**Spec**: `sdd/specs/compatible-model-performance.spec.md`
**Status**: pending
**Priority**: medium
**Estimated effort**: M (4h active engineering time; external evidence wait excluded)
**Depends-on**: TASK-16
**Parallel**: true
**Parallelism notes**: Disjoint runtime files from native experiment; own serialization tests/reports. Benchmarks run alone.
**Assigned-to**: unassigned

---

## Context

Implements M7 of the approved specification; contributes to AC2, AC6, AC7, AC10, AC11. Constructor/ORM hydration performance is the priority, with strict compatibility for repository schema examples and real `asyncdb.models`. Rust, parallel execution and serialization are measured experiments, not automatic backend migrations.

Approval is recorded in spec frontmatter and resolved requirements in §8. Its older body status/release placeholders do not override those decisions.

## Scope

- Measure warm/cold json() separately from to_dict() and test a narrow traversal/temporary-object optimization.
- Preserve exact output type/content, Decimal conversion, per-call options, nested dataclass copying, custom encoders, __deepcopy__ and exclusion/null side effects.
- Run differential parity across fixtures and real asyncdb consumer models using existing harness interfaces.
- Promote a candidate only with >=10% warm JSON improvement and <=5% other regressions; otherwise remove experimental runtime changes and retain the original path with evidence.

**NOT in scope**: New JSON semantics, Pydantic serializers, changing null/exclusion rules or mandatory schema migration.

## Files to Create / Modify

Ownership is restricted to these implementation/test/report files, plus this task's completion note and per-spec index state. Expand scope only through an explicit task/spec update.

| File | Action | Responsibility |
|---|---|---|
| `datamodel/models.py` | MODIFY | Scoped runtime/experimental implementation |
| `datamodel/parsers/json.pyx` | MODIFY | Scoped runtime/experimental implementation |
| `tests/test_json.py` | MODIFY | Compatibility fixtures, test support or regression tests |
| `tests/compatibility/test_serialization_parity.py` | CREATE | Compatibility fixtures, test support or regression tests |
| `benchmarks/results/compatible-model-performance/serialization.json` | CREATE | Reproducible evidence and decision report |
| `benchmarks/results/compatible-model-performance/serialization.md` | CREATE | Reproducible evidence and decision report |

## Codebase Contract (Anti-Hallucination)

References were re-read against the current `dev` tree after FEAT-001 integration and before task creation (runtime baseline `1d578ab`; reservation `4d5f97d`). Verify freshness again before implementation. Planned dependency outputs are not yet existing contracts.

### Verified Imports

```python
from datamodel.models import ModelMixin
from datamodel.parsers.json import JSONContent
from datamodel import BaseModel, Field, Column
from datamodel.exceptions import ValidationError
```

### Existing Signatures to Use

- datamodel/models.py:96,209-226,304-308 — ModelMixin.to_dict(self,remove_nulls=False,convert_enums=False,as_values=False,exclude=None), json(self,**kwargs), to_json alias.
- datamodel/parsers/json.pyx:85-107 — JSONContent.__call__, default(self,object obj); Decimal becomes float.
- tests/test_json.py:46-102 — Decimal extremes, datetime options, custom isoformat and UUID tests.
- datamodel/models.py:216-220 — exclusion-set mutation and dataclasses.asdict copying are observable.
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

Do not equate equal JSON on the Employee happy path with parity. Existing asdict traversal can invoke observable hooks.

Use the existing paths and behavior described in the contract, not the illustrative placeholders in the generic task template. Read §2–§5 of the specification for dispatch semantics, measurement protocol and acceptance thresholds.

### Key Constraints

- Preserve reference behavior, including legacy quirks; do not migrate consumers to Pydantic, weaken checks, change public/cpdef return contracts, or require model rebuild calls.
- Reference: d932c720e9e36bbacdaca2b1a2af0688f2636c40 (0.10.21), rebuilt in isolation. Candidate targets 0.11.0 and preserves FEAT-001 Linux/Windows × CPython 3.10–3.14 support.
- Use deterministic offline inputs. No production database writes, release publication, new backend packaging, or service credentials are authorized by this task.
- Rebuild affected Cython/Rust artifacts before testing. Separate diagnostic instrumentation from release timings; benchmark runs and shared extension builds require exclusive execution.
- Do not count missing dependencies, platforms, failed builds or unfinished measurements as successful verification or a completed negative experiment.
- Work in the per-spec feature worktree. You are not alone in the codebase: preserve others' edits and coordinate shared files rather than reverting their work.

### References in Codebase

The verified contract above is the source for existing behavior. New interfaces from `TASK-16` must be documented with their actual definitions, never inferred from proposed filenames.

## Acceptance Criteria

- [ ] Custom hooks, identity/copy relationships and output options match reference exactly.
- [ ] No mutable encoder instance is globally reused and public to_dict copy behavior is unchanged.
- [ ] AC10 promotion or retain-current decision is supported by raw cold/warm measurements and parity.
- [ ] Construction/assignment behavior is unchanged by the serialization edit.
- [ ] Required tests and evidence are recorded with actual commands/results; no new reference-relative regression is hidden.
- [ ] Only scoped files and task/index state change; AC2, AC6, AC7, AC10, AC11 evidence is linked in the completion note.

## Test Specification

- Run `python -m pytest tests/test_json.py tests/compatibility/test_serialization_parity.py -q`.
- Include custom deepcopy/encoder cases, nested dataclasses, Decimal extremes, datetime options, exclusion-set mutation and asyncdb model serialization.
- Use the common full measurement protocol for final promotion eligibility.

Tests are behavioral specifications, not permission to change the oracle. Verify import paths of new test-support modules after their dependency tasks land. A quick smoke run is not a substitute for the full acceptance protocol.

## Agent Instructions

1. Read the full spec and this task before acting; use `sdd/tasks/index/compatible-model-performance.json`, never the historical monolithic index.
2. Confirm dependencies are done/verified in that index and their task files are in `sdd/tasks/completed/`. Read their completion notes and newly implemented contracts.
3. Verify every relevant contract with `rg` and source reads before writing code. Record changed/new definitions first; do not guess imports or attributes.
4. Update only this task's assignment, start timestamp and status to `in-progress` in the per-spec index.
5. Implement only the declared scope, preserving other contributors' work. Respect the parallelism notes and serialize shared build/timing resources.
6. Run the scoped tests plus appropriate rebuilt-artifact differential checks. Record commands, artifact identities and raw evidence. If a prerequisite or required gate fails, keep the task incomplete and report it; do not waive it.
7. Fill the completion note, then use `scripts/sdd/close_task.sh TASK-20 compatible-model-performance verified` only when all required criteria are met. Verify the active copy is gone and the per-spec index points to the completed file.
8. Commit the scoped changes and task/index state in the feature worktree following the task-execution skill. Do not publish or merge the feature as part of this task.

## Completion Note

**Completed by**: sdd-worker (Claude Opus 5)
**Date**: 2026-09-08
**Decision**: **RETAIN THE CURRENT SERIALIZATION PATH.** AC10 is not met.
**Production changed**: **none.**
**Evidence**: `benchmarks/results/compatible-model-performance/serialization.md`
and `serialization.json`.

### Where the time actually goes

`Employee(native).json()`, warm — this breakdown is the most useful thing the
task produced:

| component | ns | share |
|---|---|---|
| **`dataclasses.asdict`** recursive deep copy | 10,825 | **77.4%** |
| `orjson.dumps` via the encoder | 1,138 | 8.2% |
| **`JSONContent()` construction** | 53 | **0.38%** |
| total | 14,079 | |

Cold and warm measured separately as the task requires: `json()` **20,998 ns
cold** / 14,079 ns warm; `to_dict()` likewise recorded.

### Candidate A — reuse one encoder instead of building one per call

**REJECTED on measurement.** `json()` does `self.__encoder__(**kwargs)` every
call. Reusing a single instance was measured end to end:

| model | current | candidate | improvement |
|---|---|---|---|
| `Employee` | 13,704 ns | 13,472 ns | **+1.69%** |
| `UnconstrainedScalars` | 12,393 ns | 12,368 ns | **+0.20%** |

Outputs identical. Against a required **10%** this is nowhere near — encoder
construction is 0.38% of the call, so that was always the ceiling.

Worth recording that it would have been **safe**: `JSONContent` is a `cdef`
class with **no instance state at all** (no `__dict__`), so a shared instance is
not the "mutable encoder instance globally reused" the acceptance criteria warn
against. It simply buys nothing. `test_json_content_is_stateless` now fails if
instance state is ever added, which would invalidate that reasoning.

### Candidate B — skip `asdict`'s deep copy inside `json()`

**REJECTED on compatibility, demonstrated.** This is the only candidate that
could reach 10% — 77.4% is available — and the copy *looks* like pure waste,
since the intermediate dict is handed to `orjson` and discarded immediately.

But the copying is **observable**. A value with a custom `__deepcopy__` has it
invoked exactly once during `json()`, verified on **both** builds:

```
to_dict()  -> __deepcopy__ calls: 1
json()     -> __deepcopy__ calls: 1
```

Removing the copy would silently stop running user code — precisely the "custom
encoders, `__deepcopy__` and exclusion/null side effects" the task requires be
preserved. Pinned by `test_json_still_invokes_deepcopy_on_values`.

### Parity — zero divergences

Every scenario run in **two separate processes** bound to their own compiled
artifacts, with the 0.10.21 reference as the oracle: scalars, Decimal extremes
(28-digit, 1e-28, large negative, zero), Unicode (accents, CJK, emoji, embedded
quotes), nulls/defaults/`remove_nulls`, containers, **copy independence**,
**exclusion-set mutation across calls**, nested dataclasses, custom field
encoders, enums and `convert_enums`, `__deepcopy__` side effects, per-call
options — plus **every OK case in the benchmark corpus** and **every OK case in
the real asyncdb 2.16.0 consumer corpus**. **0 divergences.**

### A pre-existing quirk found and characterized, not fixed

**`json(**kwargs)` silently ignores per-call options.** The kwargs are forwarded
to the encoder's *constructor* (`self.__encoder__(**kwargs)`), never to
`encode()`; `JSONContent` accepts and discards them. So
`json(option=OPT_SORT_KEYS)` and `json(indent=2)` both return compact,
declaration-ordered output and raise nothing. Verified identical on 0.10.21, so
it is **not a regression**. Correcting it would be new JSON semantics, which
spec §1 puts out of scope, so it is pinned by
`test_per_call_json_options_are_silently_ignored` rather than fixed.

**Flagged for the maintainer**: a caller passing `indent=2` today silently gets
compact output. That is a defect worth its own ticket, outside this feature.

### Verification commands/results

- `.venv/bin/python -m pytest tests/test_json.py
  tests/compatibility/test_serialization_parity.py -q` -> **31 passed**.
- `.venv/bin/python -m pytest tests/ -q` -> **755 passed, 2 skipped, 0 failed**
  (743 before this task + 12 new).
- `.venv/bin/python -m ruff check --select F,E9` on both test files -> clean.
- Reference/candidate probe of `json(**kwargs)` -> identical on both builds.

### Evidence and acceptance coverage

- **AC10** (promotion or retain decision from raw cold/warm measurements and
  parity): `serialization.json` -> `promotion_gate`, `candidates`,
  `cold_vs_warm`, `cost_breakdown`;
  `test_serialization_report_exists_and_retains_the_current_path` requires every
  candidate to carry a `REJECTED` verdict *and* a measurement, and
  `test_the_report_records_where_the_time_actually_goes` fails if the report
  stops recording that `asdict` is the dominant cost — so a future attempt
  cannot start from the wrong end.
- **AC2/AC6** (exact output, no regression): the parity scenarios above;
  TASK-16's acceptance run already had `json_warm` and `to_dict` inconclusive.
- **AC7** (public copy behaviour, no globally reused mutable encoder):
  `test_to_dict_returns_independent_copies`,
  `test_each_json_call_builds_its_own_encoder`,
  `test_json_content_is_stateless`, plus the `to_dict_copy_independence` and
  `exclusion_set_is_not_mutated_across_calls` parity scenarios.
- **AC11**: both report files, including "what would change the answer".
- Construction/assignment unchanged by this task: trivially, since no production
  file was modified — and the full suite confirms it.

### Deviations from spec

One, flagged.

1. **`datamodel/models.py` and `datamodel/parsers/json.pyx` are listed as MODIFY
   but were left UNCHANGED.** That is the outcome the task itself prescribes:
   *"otherwise remove experimental runtime changes and retain the original path
   with evidence."* Candidate A was measured by faithfully simulating the change
   at runtime rather than editing production files, so there was never an
   experimental edit to remove; candidate B was rejected before implementation
   once `__deepcopy__` was shown to run. Editing either file to match the file
   table would have meant shipping a change worth 1.69% against a 10% gate.
2. No `.pyx` changed, so no rebuild and no manifest regeneration was required.
