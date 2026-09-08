# TASK-21: Verify consumer compatibility across the FEAT-001 platform matrix

**Feature**: FEAT-2 - Compatible model execution performance
**Spec**: `sdd/specs/compatible-model-performance.spec.md`
**Status**: pending
**Priority**: high
**Estimated effort**: M (4h active engineering time; external evidence wait excluded)
**Depends-on**: TASK-10, TASK-19, TASK-20
**Parallel**: false
**Parallelism notes**: Final integrated code/artifact verification after native and serialization changes; no concurrent production edits.
**Assigned-to**: unassigned

---

## Context

Implements M8 / AC12 of the approved specification; contributes to AC1, AC2, AC4, AC7, AC12. Constructor/ORM hydration performance is the priority, with strict compatibility for repository schema examples and real `asyncdb.models`. Rust, parallel execution and serialization are measured experiments, not automatic backend migrations.

Approval is recorded in spec frontmatter and resolved requirements in §8. Its older body status/release placeholders do not override those decisions.

## Scope

- Implement a development runner/report aggregator for isolated wheel/interpreter verification, reusing the existing FEAT-001 build/staging commands without replacing its workflow.
- Verify Linux x86_64 and Windows AMD64 for CPython3.10–3.14 with fresh artifacts, full applicable repository/differential tests and required asyncdb/example cases.
- Record source/artifact/dependency hashes, backend availability, exact command/log evidence and baseline-only failures for every cell.
- Test absence of the new experimental native module without breaking default construction; characterize existing rs_parsers-absent behavior separately.
- Use available local/authorized CI environments. Missing platform or real asyncdb evidence is incomplete certification, never a skipped pass; do not publish release artifacts.

**NOT in scope**: New platform support, workflow rewrites, altered native loader/package policy, production service writes or publishing version0.11.0.

## Files to Create / Modify

Ownership is restricted to these implementation/test/report files, plus this task's completion note and per-spec index state. Expand scope only through an explicit task/spec update.

| File | Action | Responsibility |
|---|---|---|
| `tests/compatibility/matrix.py` | CREATE | Compatibility fixtures, test support or regression tests |
| `tests/compatibility/test_matrix_runner.py` | CREATE | Compatibility fixtures, test support or regression tests |
| `benchmarks/results/compatible-model-performance/platforms.json` | CREATE | Reproducible evidence and decision report |
| `benchmarks/results/compatible-model-performance/platforms.md` | CREATE | Reproducible evidence and decision report |

## Codebase Contract (Anti-Hallucination)

References were re-read against the current `dev` tree after FEAT-001 integration and before task creation (runtime baseline `1d578ab`; reservation `4d5f97d`). Verify freshness again before implementation. Planned dependency outputs are not yet existing contracts.

### Verified Imports

```python
from datamodel import BaseModel, Field, Column
from datamodel.exceptions import ValidationError
```

### Existing Signatures to Use

- setup.py:15-29,98-106 — _compiler_flags() selects /O2 on Windows and -O3 on POSIX; guarded setup invocation and existing Cython extensions.
- pyproject.toml:1-8,19,57-74 — Cython>=3.2.8, Python>=3.10, optional uvloop and dev dependencies after FEAT-001.
- scripts/stage_rust_ext.py:30-59 — build_wheel(manifest: str, out_dir: str, interpreter: str, manylinux: str | None, maturin_bin: str = 'maturin') -> int; builds rs_parsers through maturin, not the experimental rs_core loader.
- .github/workflows/release.yml:13-25,49-65 — Ubuntu/Windows × CPython3.10–3.14, Linux x86_64/Windows AMD64, skips musllinux; current wheel test only asserts HAS_RUST.
- datamodel/version.py:9 — current version is already 0.11.0; do not bump it again.
- datamodel/base.py:35-55 — errors/state observable at construction.
- datamodel/models.py:134-152,209-226,304-308 — reset_values/old_value, to_dict and json.
- datamodel/abstract.py:66-145 — assignment history and parser-only assignment validation.
- tests/test_descriptors.py:6-80 — descriptors execute through normal attribute access; tests/test_field.py:8-70 — fields/defaults/metadata.
- datamodel/__init__.py:6-9 — existing public exports.
- datamodel/base.py:29-55 — BaseModel.__post_init__(self) -> None snapshots columns, calls processing_fields, and handles strict/non-strict validity.
- datamodel/exceptions.pyx:24-38 — ValidationError(message, payload=None); string output includes ordered payload field names.

### Does NOT Exist

- Files marked CREATE below are planned artifacts, not existing interfaces. Read completed dependencies to verify their newly introduced APIs before using them.
- No existing production per-field validation policy, compatible rs_core backend loader, or public batch-construction API is established by this contract.
- `_validate_constraints` is a Cython cdef interface, not a Python-importable function. Do not invent Python imports for it.

## Implementation Notes

### Pattern to Follow

FEAT-001 is merged. Cython>=3.2.8, compiler flags and Rust staging must remain intact. Current CIBW_TEST_COMMAND only checks HAS_RUST, which is insufficient evidence for this feature. Runtime artifact tests must not accidentally import source checkout modules.

Use the existing paths and behavior described in the contract, not the illustrative placeholders in the generic task template. Read §2–§5 of the specification for dispatch semantics, measurement protocol and acceptance thresholds.

### Key Constraints

- Preserve reference behavior, including legacy quirks; do not migrate consumers to Pydantic, weaken checks, change public/cpdef return contracts, or require model rebuild calls.
- Reference: d932c720e9e36bbacdaca2b1a2af0688f2636c40 (0.10.21), rebuilt in isolation. Candidate targets 0.11.0 and preserves FEAT-001 Linux/Windows × CPython 3.10–3.14 support.
- Use deterministic offline inputs. No production database writes, release publication, new backend packaging, or service credentials are authorized by this task.
- Rebuild affected Cython/Rust artifacts before testing. Separate diagnostic instrumentation from release timings; benchmark runs and shared extension builds require exclusive execution.
- Do not count missing dependencies, platforms, failed builds or unfinished measurements as successful verification or a completed negative experiment.
- Work in the per-spec feature worktree. You are not alone in the codebase: preserve others' edits and coordinate shared files rather than reverting their work.

### References in Codebase

The verified contract above is the source for existing behavior. New interfaces from `TASK-10`, `TASK-19`, `TASK-20` must be documented with their actual definitions, never inferred from proposed filenames.

## Acceptance Criteria

- [ ] All ten required platform/interpreter cells have actual test evidence from matching artifacts, not inferred success from import-only wheel smoke tests.
- [ ] Real asyncdb.models/example compatibility and public contracts are verified; no new failures are hidden behind skips.
- [ ] Matrix aggregator rejects missing/failed required cells and stale/different artifact references.
- [ ] AC12 release certification remains blocked if any required external evidence is unavailable; this task is not marked verified until complete.
- [ ] Required tests and evidence are recorded with actual commands/results; no new reference-relative regression is hidden.
- [ ] Only scoped files and task/index state change; AC1, AC2, AC4, AC7, AC12 evidence is linked in the completion note.

## Test Specification

- Run `python -m pytest tests/compatibility/test_matrix_runner.py -q` for missing-cell, wrong-hash and failed-case rejection.
- Execute the runner for actual Linux/Windows wheels and interpreters; aggregate the full matrix including real integration cases.
- Full suite: `python -m pytest tests/ -q` inside each properly installed artifact environment; record the actual config selection.

Tests are behavioral specifications, not permission to change the oracle. Verify import paths of new test-support modules after their dependency tasks land. A quick smoke run is not a substitute for the full acceptance protocol.

## Agent Instructions

1. Read the full spec and this task before acting; use `sdd/tasks/index/compatible-model-performance.json`, never the historical monolithic index.
2. Confirm dependencies are done/verified in that index and their task files are in `sdd/tasks/completed/`. Read their completion notes and newly implemented contracts.
3. Verify every relevant contract with `rg` and source reads before writing code. Record changed/new definitions first; do not guess imports or attributes.
4. Update only this task's assignment, start timestamp and status to `in-progress` in the per-spec index.
5. Implement only the declared scope, preserving other contributors' work. Respect the parallelism notes and serialize shared build/timing resources.
6. Run the scoped tests plus appropriate rebuilt-artifact differential checks. Record commands, artifact identities and raw evidence. If a prerequisite or required gate fails, keep the task incomplete and report it; do not waive it.
7. Fill the completion note, then use `scripts/sdd/close_task.sh TASK-21 compatible-model-performance verified` only when all required criteria are met. Verify the active copy is gone and the per-spec index points to the completed file.
8. Commit the scoped changes and task/index state in the feature worktree following the task-execution skill. Do not publish or merge the feature as part of this task.

## Completion Note

**STATUS: INCOMPLETE — BLOCKED. Certification is NOT granted.**

The task's own criteria are explicit: *"AC12 release certification remains
blocked if any required external evidence is unavailable; this task is not
marked verified until complete."* One of ten required cells has passing
evidence, so the task stays open.

**Run by**: sdd-worker (Claude Opus 5) | **Date**: 2026-09-08
**Evidence**: `benchmarks/results/compatible-model-performance/platforms.md`
and `platforms.json`.

### The matrix

| platform | CPython | status | tests | rs_parsers | asyncdb |
|---|---|---|---|---|---|
| linux-x86_64 | 3.10 | fail | 1 collection error | absent | unverified |
| linux-x86_64 | 3.11 | fail | 1 collection error | absent | unverified |
| linux-x86_64 | 3.12 | fail | 1 collection error | absent | unverified |
| linux-x86_64 | **3.13** | **PASS** | **772 passed, 0 failed** | built | **verified** |
| linux-x86_64 | 3.14 | fail | 29 collection errors | absent | unverified |
| windows-amd64 | 3.10–3.14 | **unavailable** | — | — | — |

### The qualifier that matters most

**No failure found here is attributable to FEAT-2.** Every one reproduces on the
0.10.21 reference. But a cell that fails for a pre-existing reason still has no
passing evidence, so it still blocks AC12. "Not our fault" is not "certified",
and the aggregator does not let those two be confused.

### BLOCKER-1 (high) — CPython 3.14 does not work at all

`dataclasses.Field.__init__` gained a required `doc` parameter in Python 3.14;
`datamodel/fields.pyx` does not pass it, so **every model definition** raises
`TypeError: Field.__init__() missing 1 required positional argument: 'doc'`.
29 test modules fail at collection.

I verified this is **pre-existing** rather than assuming: the `ff.__init__` call
site is byte-identical between the reference and the candidate, and I built the
**0.10.21 reference against CPython 3.14** and reproduced the identical failure.

The consequence is a release-facing one: **the FEAT-001 release matrix claims
CPython 3.10–3.14 support, and on 3.14 no model can be declared.** Wheels may
build and import; the library is unusable. This needs its own ticket against
`fields.pyx` — fixing it is outside FEAT-2's scope and would be exactly the kind
of unrelated repair the cardinal rules forbid here.

### Other blockers

* **BLOCKER-2 (medium)** — Windows AMD64 evidence entirely absent (5 of 10
  cells). Needs the FEAT-001 release workflow or an authorized CI runner.
* **BLOCKER-3 (medium)** — the pinned asyncdb 2.16.0 artifact is the **cp313**
  wheel, so real consumer compatibility is verified on one interpreter only;
  AC12 requires it per cell.
* **BLOCKER-4 (low)** — `uv pip install -e .` does not build `rs_parsers`, so
  `converters.pyx:199,236` dereference `rc.to_date`/`rc.to_datetime` against
  `HAS_RUST = False`. This is TASK-7's characterized gap, confirmed shared with
  the reference, and is why 3.10/3.11/3.12 show a collection error rather than a
  clean run.

### What the one passing cell actually demonstrates

`linux-x86_64 / CPython 3.13`, source fingerprint `fde1d97b71c0…`:
**772 passed, 0 failed, 2 skipped** — the full repository suite, not an import
smoke test; `rs_parsers` present; real **asyncdb 2.16.0** installed with its
compatibility suite green; and the **experimental native module absent** from a
normally installed environment, confirming the TASK-17/19 `rs_core` work did not
leak into the package and that default construction works without it.

### The aggregator cannot be talked into a green tick

This is as much the deliverable as the numbers. It refuses to certify on: a cell
never run (each of the ten checked individually), an `unavailable` cell
("incomplete certification, not a skip"), a failed cell, an **import-only smoke
test** (`tests_passed == 0` is treated as no evidence, per the acceptance
criteria), a **stale artifact reference** (source-fingerprint mismatch), or a
cell that did not verify the real asyncdb consumer. An empty report yields
exactly ten problems — and a fully clean matrix *does* certify, so the positive
control exists and `certified` is not hard-wired to False.

### Verification commands/results

- `.venv/bin/python -m pytest tests/compatibility/test_matrix_runner.py -q`
  -> **17 passed**.
- `.venv/bin/python -m pytest tests/ -q` -> **772 passed, 2 skipped, 0 failed**.
- Matrix sweep: `run_cell()` for CPython 3.10/3.11/3.12/3.13/3.14 in throwaway
  virtualenvs built from source; results above.
- Reference-on-3.14 probe: `uv pip install -e <ref-worktree>` under CPython
  3.14.2 -> `TypeError: Field.__init__() missing 1 required positional
  argument: 'doc'`.
- `.venv/bin/python -m ruff check --select F,E9` on both new files -> clean.

### Evidence and acceptance coverage

- **AC12**: `platforms.json` -> `certified: false`, `problems`,
  `analysis.release_blockers`;
  `test_the_platform_report_exists_and_is_honest` fails if the report ever
  claims certification while listing problems, or denies it without a reason.
- **AC1** (artifact provenance): every cell records a source fingerprint;
  mismatches are rejected as stale.
- **AC2/AC4/AC7**: the passing cell runs the entire suite, including the
  differential corpus, adversarial parity and asyncdb consumer tests.
- Experimental native absence without breaking default construction:
  recorded per cell as `experimental_native_absent`, true in the passing cell.
- rs_parsers-absent behaviour characterized separately: `baseline_only_failures`
  on the affected cells, cross-referenced to TASK-7/TASK-8.

### Required next steps

1. Fix CPython 3.14 (`Field.__init__` must pass `doc`) **or** remove 3.14 from
   the declared support matrix — currently it promises something non-functional.
2. Run the Windows AMD64 cells on the FEAT-001 release workflow.
3. Provide asyncdb artifacts per interpreter so consumer compatibility is
   verified per cell.
4. Build `rs_parsers` in each test environment so 3.10–3.12 run clean.
