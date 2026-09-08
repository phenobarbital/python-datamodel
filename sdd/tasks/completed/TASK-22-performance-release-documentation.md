# TASK-22: Document performance decisions and 0.11.0 release readiness

**Feature**: FEAT-2 - Compatible model execution performance
**Spec**: `sdd/specs/compatible-model-performance.spec.md`
**Status**: pending
**Priority**: medium
**Estimated effort**: M (2h active engineering time; external evidence wait excluded)
**Depends-on**: TASK-16, TASK-18, TASK-19, TASK-20, TASK-21
**Parallel**: false
**Parallelism notes**: Final documentation consumes all completed verification/experiment artifacts; owns only documentation and aggregate evidence.
**Assigned-to**: unassigned

---

## Context

Implements M8 of the approved specification; contributes to AC11, AC12. Constructor/ORM hydration performance is the priority, with strict compatibility for repository schema examples and real `asyncdb.models`. Rust, parallel execution and serialization are measured experiments, not automatic backend migrations.

Approval is recorded in spec frontmatter and resolved requirements in §8. Its older body status/release placeholders do not override those decisions.

## Scope

- Explain measured Cython gains, remaining costs, mutation-safe behavior and fallback categories with reproducible commands and artifact provenance.
- Aggregate AC1–AC12 evidence, native/parallel/serialization decisions and full matrix/asyncdb coverage; distinguish experimental results from shipped behavior.
- Record resolved user requirements verbatim and target0.11.0; current version is already0.11.0, so no new bump is authorized.
- Document rollout prerequisites and any consumer baseline approvals without presenting absent evidence as complete.

**NOT in scope**: Runtime code edits, rerunning unresolved feature design choices, releases or bypassing failed acceptance criteria.

## Files to Create / Modify

Ownership is restricted to these implementation/test/report files, plus this task's completion note and per-spec index state. Expand scope only through an explicit task/spec update.

| File | Action | Responsibility |
|---|---|---|
| `docs/performance.md` | CREATE | User-facing performance documentation |
| `benchmarks/results/compatible-model-performance/summary.json` | CREATE | Reproducible evidence and decision report |
| `benchmarks/results/compatible-model-performance/README.md` | CREATE | Reproducible evidence and decision report |

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

### Does NOT Exist

- Files marked CREATE below are planned artifacts, not existing interfaces. Read completed dependencies to verify their newly introduced APIs before using them.
- No existing production per-field validation policy, compatible rs_core backend loader, or public batch-construction API is established by this contract.
- `_validate_constraints` is a Cython cdef interface, not a Python-importable function. Do not invent Python imports for it.

## Implementation Notes

### Pattern to Follow

User clarification: “The idea is not be a \"pydantic\" equivalent, is preserve current compatibility with asyncdb.models but adding speed up improvement.” Promotion reports do not by themselves authorize new package wiring.

Use the existing paths and behavior described in the contract, not the illustrative placeholders in the generic task template. Read §2–§5 of the specification for dispatch semantics, measurement protocol and acceptance thresholds.

### Key Constraints

- Preserve reference behavior, including legacy quirks; do not migrate consumers to Pydantic, weaken checks, change public/cpdef return contracts, or require model rebuild calls.
- Reference: d932c720e9e36bbacdaca2b1a2af0688f2636c40 (0.10.21), rebuilt in isolation. Candidate targets 0.11.0 and preserves FEAT-001 Linux/Windows × CPython 3.10–3.14 support.
- Use deterministic offline inputs. No production database writes, release publication, new backend packaging, or service credentials are authorized by this task.
- Rebuild affected Cython/Rust artifacts before testing. Separate diagnostic instrumentation from release timings; benchmark runs and shared extension builds require exclusive execution.
- Do not count missing dependencies, platforms, failed builds or unfinished measurements as successful verification or a completed negative experiment.
- Work in the per-spec feature worktree. You are not alone in the codebase: preserve others' edits and coordinate shared files rather than reverting their work.

### References in Codebase

The verified contract above is the source for existing behavior. New interfaces from `TASK-16`, `TASK-18`, `TASK-19`, `TASK-20`, `TASK-21` must be documented with their actual definitions, never inferred from proposed filenames.

## Acceptance Criteria

- [ ] Every acceptance criterion links to actual evidence and all required gates are satisfied before declaring release-ready.
- [ ] Documents explicitly preserve asyncdb.models compatibility and the FEAT-001 matrix; no remaining user question is reintroduced as unanswered when already resolved.
- [ ] Claims use matched-artifact measured ratios and explain retained legacy/native choices.
- [ ] Only reports/docs change; no package publication, PR merge or new backend promotion occurs.
- [ ] Required tests and evidence are recorded with actual commands/results; no new reference-relative regression is hidden.
- [ ] Only scoped files and task/index state change; AC11, AC12 evidence is linked in the completion note.

## Test Specification

- Validate aggregate JSON and all local evidence links, sample counts, artifact hashes and decision thresholds.
- Check documented commands against the real harness interfaces implemented by dependencies.
- Confirm summary rejects incomplete platform/consumer evidence and that runtime claimed version is0.11.0.

Tests are behavioral specifications, not permission to change the oracle. Verify import paths of new test-support modules after their dependency tasks land. A quick smoke run is not a substitute for the full acceptance protocol.

## Agent Instructions

1. Read the full spec and this task before acting; use `sdd/tasks/index/compatible-model-performance.json`, never the historical monolithic index.
2. Confirm dependencies are done/verified in that index and their task files are in `sdd/tasks/completed/`. Read their completion notes and newly implemented contracts.
3. Verify every relevant contract with `rg` and source reads before writing code. Record changed/new definitions first; do not guess imports or attributes.
4. Update only this task's assignment, start timestamp and status to `in-progress` in the per-spec index.
5. Implement only the declared scope, preserving other contributors' work. Respect the parallelism notes and serialize shared build/timing resources.
6. Run the scoped tests plus appropriate rebuilt-artifact differential checks. Record commands, artifact identities and raw evidence. If a prerequisite or required gate fails, keep the task incomplete and report it; do not waive it.
7. Fill the completion note, then use `scripts/sdd/close_task.sh TASK-22 compatible-model-performance verified` only when all required criteria are met. Verify the active copy is gone and the per-spec index points to the completed file.
8. Commit the scoped changes and task/index state in the feature worktree following the task-execution skill. Do not publish or merge the feature as part of this task.

## Completion Note

**Completed by**: sdd-worker (Claude Opus 5)
**Date**: 2026-09-08
**Documentation task complete. The FEATURE is NOT release-ready** —
`summary.json` records `release_ready: false`, blocked on AC12.

The distinction matters: this task's job was to aggregate the evidence and say
truthfully where things stand, and it does. It did **not** and could not clear
AC12, and it does not pretend to.

**Deliverables**: `docs/performance.md` (user-facing),
`benchmarks/results/compatible-model-performance/summary.json` (aggregate
AC1–AC12 roll-up), and `README.md` in that directory (evidence index).

### AC roll-up

| | status |
|---|---|
| AC1, AC2, AC3, AC4, AC5, AC6, AC7, AC11 | **pass** |
| AC8 (sequential Rust) | completed negative — retain Cython |
| AC9 (parallel) | completed negative — retain sequential |
| AC10 (serialization) | completed negative — retain current path |
| **AC12** (platform/consumer) | **BLOCKED — 1 of 10 cells** |

`release_ready` is *computed* from the gates rather than asserted, and a
consistency check confirms it follows from them.

### What the documentation is careful about

**It documents what did NOT ship at equal length to what did.** Four rejected
directions — the Rust executor, parallel execution, serialization changes, and
all six structural candidates — each get the measurement that rejected them and
a "what would change the answer" note, so the next attempt starts from evidence
instead of repeating the work.

**It records the remaining cost distribution**: `asdict`'s deep copy is 77.4% of
`json()`, per-field conversion and `_dc_method_setattr_` dominate construction,
and the generic validation dispatch is already fully eliminated for supported
scalars. That is the map for whoever picks this up.

**It explains the measurement discipline prominently**, including that the
same-source control has produced up to **three spurious "regression" verdicts
from provably identical code**, so a confidence interval excluding 1.0 is not by
itself evidence at these magnitudes. Nothing under ~2% is claimed anywhere.

**It states rollout prerequisites without dressing up absent evidence**: CPython
3.14 non-functional (pre-existing, own ticket), Windows evidence absent, asyncdb
verified on cp313 only, `rs_parsers` not built by an editable install. No
consumer baseline approval is supplied, and none is implied.

**It preserves the resolved user requirement verbatim** — `asyncdb.models`
compatibility is treated as a first-class requirement throughout, with the real
2.16.0 distribution pinned, installed against both builds, and compared
field-by-field. The FEAT-001 platform matrix is preserved as a requirement, with
its true status reported rather than assumed.

### The version discrepancy — recorded, not actioned

The task states *"current version is already 0.11.0, so no new bump is
authorized"*; `datamodel/version.py` actually reads **0.12.0**. I have flagged
this in every completion note since TASK-7. No bump is authorized either way, so
the file is untouched and `version.py` was never in any task's scope. Both
`summary.json` and `docs/performance.md` record the discrepancy explicitly and
**decline to choose** — the maintainer must reconcile which release carries this
work. Silently picking one would have been the easy and wrong thing.

### Verification commands/results

- Aggregate consistency check -> **37 path/hash references validated**, every
  evidence path resolves, every recorded sha256 matches the file on disk,
  `release_ready` agrees with the gate statuses, every command in `reproduce`
  names a file that exists, and the recorded current version matches
  `datamodel.version.__version__`.
- `.venv/bin/python -m pytest tests/ -q` -> **772 passed, 2 skipped, 0 failed**.
- No runtime code was edited; only the three declared documentation/report files
  changed.

### Evidence and acceptance coverage

- **AC11**: `docs/performance.md`, `summary.json`, `README.md` — gains,
  remaining costs, fallback categories, mutation-safe behaviour, every
  experiment decision, and reproducible commands checked against the real
  harness interfaces.
- **AC12**: `summary.json` -> `gates.AC12` carries the blocked status, the
  1-of-10 count and all four named blockers, and drives `release_ready: false`.
  Incomplete platform/consumer evidence is therefore *structurally* incapable of
  producing a release-ready summary.

### Deviations from spec

1. **No test file is in this task's declared scope**, yet its test specification
   asks to "validate aggregate JSON and all local evidence links, sample counts,
   artifact hashes and decision thresholds". I ran that validation as a
   scripted check (results above) rather than adding an unowned test file. A
   permanent regression test for the summary would be a sensible follow-up, and
   would need its own task to own the file.
2. **`docs/performance.md` states the feature is not release-ready.** That is
   deliberate: the task forbids "bypassing failed acceptance criteria", and
   publishing a performance document that implied readiness while AC12 is
   blocked would do exactly that.
3. No `.pyx` changed; no rebuild or manifest regeneration required. No package
   publication, no PR merge, no backend promotion.
