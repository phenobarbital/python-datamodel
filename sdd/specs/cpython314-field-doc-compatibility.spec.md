---
type: hotfix
base_branch: main
---

# Bug Specification: CPython 3.14 Field initialization omits required doc argument

**Identity**: `cpython314-field-doc-compatibility` (standalone hotfix; no Jira key assigned)
**Date**: 2026-09-08
**Author**: Codex, based on Jesus Lara's request and FEAT-2 evidence
**Status**: draft
**Severity / Priority**: Critical compatibility defect / P0 for a release advertising CPython 3.14
**Target version**: Next corrective release; exact number to be assigned by the maintainer
**Related work**: FEAT-001 platform support; FEAT-2 TASK-21 `BLOCKER-1`

## 1. Motivation & Business Requirements

### Problem Statement

`datamodel.fields.Field` subclasses `dataclasses.Field` and calls its initializer
without `doc`. CPython 3.14 added this required initializer argument. Consequently,
`Field()`, `Column()`, explicit field declarations, and model initialization routes
that create a Field raise:

```text
TypeError: Field.__init__() missing 1 required positional argument: 'doc'
```

The package already accepts `Field(doc=None)` and stores `self.doc`; the missing
piece is forwarding that value to the superclass on interpreters that require it.
Supplying `doc` as a user does today does not avoid the error.

This predates FEAT-2. The FEAT-2 platform report records the same failure on the
0.10.21 engineering reference and 29 collection errors in the candidate's Linux
3.14 cell. The initializer argument block is identical in reference commit
`d932c720e9e36bbacdaca2b1a2af0688f2636c40`, current main `ab953c1`, and the
FEAT-2 worktree at `55dc55c`.

The release matrix advertises Linux x86_64 and Windows AMD64 on CPython 3.10–3.14,
but its wheel test only imports `datamodel.rs_parsers` and asserts `HAS_RUST`.
That check can pass without constructing a Field or a working model.

### Evidence and qualification of the reported claim

- **Reproduced during this specification**: CPython 3.14.2, the existing isolated
  0.10.21 build in `/tmp/py314ref/.venv`, importing from the detached reference
  worktree. `Field()`, `Column(doc="identifier")`, and an explicit Field model
  declaration raise the exact error above. Probes ran from `/tmp` to avoid source
  checkout imports shadowing the installed extension.
- **Verified upstream**: the [CPython 3.14.0 implementation](https://github.com/python/cpython/blob/v3.14.0/Lib/dataclasses.py#L273)
  requires `doc` in `Field.__init__`. The [3.14 dataclasses documentation](https://docs.python.org/3.14/library/dataclasses.html#dataclasses.field)
  documents the new optional `doc` argument to the public `field()` factory.
  The factory argument is optional; the underlying initializer argument is required.
- **Recorded, not rerun here**: candidate suite counts and platform results in
  FEAT-2 `benchmarks/results/compatible-model-performance/platforms.json` and
  `platforms.md`. The temporary candidate 3.14 environment named there no longer
  exists. The reference environment remains available.
- **Wording correction**: “every model definition” is too broad. An empty model
  can be declared. A normal bare-annotation model on the reference also declared,
  but had an empty `__columns__` registry and retained `"7"` as a string for an
  `int` field. `ModelMeta.__new__` reads `attrs.get('__annotations__', {})`;
  annotation discovery needs separate investigation on 3.14. This is an additional
  compatibility blocker, not proof that those models work correctly. An explicit
  `__annotations__` dictionary takes the Field path and reproduces the doc error.

### Goals

- Restore Field and Column initialization on CPython 3.14 while preserving
  behavior on CPython 3.10–3.13.
- Preserve the existing `doc` value, defaults, factories, metadata, flags and
  dataclass integration; introduce no new public parameter.
- Add regression coverage and a wheel test that actually exercises Field-backed
  model construction, so import success cannot conceal this failure again.
- Track this correction independently from FEAT-2's compatibility-preserving
  performance work and its unmodified historical reference.

### Non-Goals (explicitly out of scope)

- Performance optimization, Rust backend changes, new serialization semantics,
  or changing the public Field signature.
- Removing advertised 3.14 support or reducing the supported platform matrix.
- Repairing editable-install Rust staging or providing all asyncdb artifacts.
- Repairing the separately observed annotation-discovery defect in this narrow
  hotfix. It must remain a tracked release blocker until separately resolved.
- Certifying FEAT-2 or choosing between its 0.11.0 target and the 0.12.0 version
  in its worktree. Main currently declares 0.11.0; this spec authorizes no bump.

## 2. Architectural Design

### Overview

Use the existing `from sys import version_info` import in `fields.pyx`. Immediately
before calling `ff.__init__`, add `doc` to the existing argument dictionary when
`version_info >= (3, 14)`, passing the caller's existing `doc` value, including
`None`. Leave the superclass call's other arguments and initialization order intact.
On 3.10–3.13 do not pass `doc` to the superclass; retain the existing `self.doc`
assignment. This also preserves `Column(doc=...)`, which already forwards kwargs.

Do not inspect signatures for every Field, catch and retry arbitrary `TypeError`,
patch the stdlib, or rename/remove slots as part of this fix. The subclass already
declares a `doc` slot; verify its observable value after superclass initialization.

### Component Diagram

```text
Field(...) / Column(...) / ModelMeta._initialize_fields(...)
    -> Field.__init__(..., doc=None, ...)
        -> version-aware superclass arguments
            -> dataclasses.Field.__init__(...[, doc=doc])
                -> unchanged model conversion / validation
```

### Integration Points

| Component | Change | Purpose |
|---|---|---|
| `datamodel/fields.pyx` | Add version-aware forwarding | Repair the stdlib constructor boundary |
| `tests/test_field.py` | Extend existing tests | Pin doc, factory and dataclass behavior |
| New `tests/test_field_runtime_compatibility.py` | Focused model regression tests | Prove initialization reaches model conversion |
| New `scripts/smoke_installed_model.py` | Installed-wheel smoke script | Exercise Field, Column and a model without pytest dependencies |
| `.github/workflows/release.yml` | Extend `CIBW_TEST_COMMAND` | Run the smoke on each installed wheel and keep the Rust assertion |
| `CHANGELOG.md` | Corrective entry | Describe the specific fix and remaining certification limits |

### Data Models / New Public Interfaces

No new public interfaces. The test-only model must use a deterministic eager
annotation dictionary to isolate this initializer fix from annotation discovery:

```python
from datamodel import BaseModel, Column, Field

class FieldDocSmoke(BaseModel):
    __annotations__ = {"value": int}
    value = Column(default=0, doc="Example value")

assert Field(doc="Standalone").doc == "Standalone"
model = FieldDocSmoke(value="7")
assert type(model.value) is int and model.value == 7
assert "value" in FieldDocSmoke.__columns__
assert FieldDocSmoke.__columns__["value"].doc == "Example value"
```

This is a targeted regression fixture, not a proposed annotation style for users
or evidence that ordinary Python 3.14 annotation discovery has been repaired.

## 3. Module Breakdown

| Module | Ownership | Responsibility / Dependencies |
|---|---|---|
| M1 | `datamodel/fields.pyx` | Conditional `doc` forwarding; independent of FEAT-2 changes |
| M2 | `tests/test_field.py`, new `tests/test_field_runtime_compatibility.py` | Regression coverage against freshly compiled M1 |
| M3 | New `scripts/smoke_installed_model.py`, `.github/workflows/release.yml` | Installed-wheel model smoke; retain `HAS_RUST`; depends on M1 |
| M4 | `CHANGELOG.md` | Record verified correction and validation evidence after M2/M3 |

## 4. Test Specification

### Unit Tests

Names below are planned additions, not existing functions.

| Test / family | Required observation |
|---|---|
| `test_field_doc_values` | Parameterize omitted doc, explicit None, empty string and text; initialization succeeds and the exact value remains accessible |
| `test_column_doc_forwarding` | Same doc cases through Column; it returns a Field with the requested value |
| Existing Field defaults/metadata tests | Default, factory, required/nullable and metadata behavior remain unchanged |
| `test_doc_with_default_factory` | List factory produces independent instance values and doc survives; conflicting factory arguments retain their existing ValueError |
| `test_dataclass_field_doc` | Plain stdlib dataclass using Field/Column works; `dataclasses.fields()` exposes the existing doc value; `asdict` and `replace` retain expected behavior |
| `test_model_field_initialization` | Model with explicit eager annotations and Field/Column declares, registers fields, converts `"7"` to int, and instantiates |
| `test_inherited_field_doc` | An inherited field and an overridden field retain their respective doc values and default behavior |

Use ordinary scalar values in the focused tests so missing optional temporal
parser binaries cannot obscure the constructor regression. Use distinct model
names to avoid unrelated metaclass cache interactions.

### Integration Tests

- Freshly build and install the Cython extension for each interpreter. A 3.13
  binary or an editable checkout shadowing the wheel is not valid 3.14 evidence.
- Execute the smoke script against each installed wheel using cibuildwheel's
  project-path placeholder. Do not add the source checkout to `PYTHONPATH`.
  Print interpreter, package version and imported extension path for provenance.
- Keep the existing Rust assertion and add standalone Field/Column doc checks,
  model registry and converted-value assertions. A bare import is insufficient.
- Run focused regressions on Linux x86_64 and Windows AMD64 for CPython
  3.10, 3.11, 3.12, 3.13 and 3.14; all ten cells require passing evidence.
- Run the repository suite with `rs_parsers` staged as required. Record failures
  separately, including annotation discovery; do not xfail this doc defect or
  claim overall 3.14 certification from the focused smoke.

### Minimal pre-fix reproduction

With a fresh package installed in a CPython 3.14 environment, run outside the
source checkout:

```bash
python -c "from datamodel import Field; Field()"
python -c "from datamodel import Column; Column(doc='identifier')"
```

Both fail before the correction and must exit successfully afterward. Existing
reference reproduction during spec research used `/tmp/py314ref/.venv/bin/python`.
No full suite or new build was run as part of writing this spec.

## 5. Acceptance Criteria

- [ ] AC1. Fresh CPython 3.14 builds initialize Field and Column with all specified
  doc values; the missing-doc TypeError is eliminated.
- [ ] AC2. Field-backed models using eager annotations register their fields,
  construct and convert scalar input, with doc values intact.
- [ ] AC3. CPython 3.10–3.13 receive no unsupported superclass keyword and pass
  the same regression tests; defaults, factories, metadata and flags retain behavior.
- [ ] AC4. Stdlib dataclass introspection, construction, asdict and replace, plus
  inherited/overridden field docs, pass the specified tests.
- [ ] AC5. All ten supported OS/interpreter wheel cells run and pass the new
  installed-model smoke and focused regressions; `HAS_RUST` checks remain present.
- [ ] AC6. Full-suite outcomes are recorded against fresh builds. No new failure
  is hidden as a baseline defect; unresolved annotation-discovery and other
  platform/consumer gaps remain explicit blockers to general 3.14 certification.
- [ ] AC7. The changelog identifies a pre-existing constructor incompatibility,
  with reference/candidate provenance and passing fix evidence attached to the
  implementation review. Historical FEAT-2 evidence remains unchanged.
- [ ] AC8. No new dependency, public signature change, runtime monkeypatch,
  performance backend change or unrequested release-version change is introduced.

No speedup threshold applies: this is a correctness fix at field creation time,
not an instance-construction optimization.

## 6. Codebase Contract

Verified on main `ab953c1` unless explicitly attributed to FEAT-2.

### Verified Imports

```python
from sys import version_info                 # datamodel/fields.pyx:4
from dataclasses import Field as ff          # datamodel/fields.pyx:18
from datamodel import BaseModel, Field, Column  # datamodel/__init__.py:6-8; reference import probe passed
```

### Existing Signatures and Integration Points

| Symbol / contract | Verified location |
|---|---|
| `class Field(ff)`; existing `doc` slot | `datamodel/fields.pyx:70`, `:87` |
| `Field.__init__(self, default=None, nullable=True, required=False, factory=None, min=None, max=None, validator=None, pattern=None, alias=None, kw_only=False, metadata=None, doc=None, **kwargs)` | `datamodel/fields.pyx:128` |
| `self.doc = doc`; existing superclass argument dictionary and call without doc | `datamodel/fields.pyx:172`, `:233`, `:241` |
| `Column(default=None, nullable=True, required=False, factory=None, min=None, max=None, validator=None, kw_only=False, alias=None, **kwargs)` returns `Field(..., **kwargs)` | `datamodel/fields.pyx:319` |
| `ModelMeta._initialize_fields(attrs, annotations, strict)` constructs Field | `datamodel/abstract.py:180`, `:215`, `:223` |
| `ModelMeta.__new__(cls, name, bases, attrs, **kwargs)` reads `attrs.get('__annotations__', {})` | `datamodel/abstract.py:352` |
| `BaseModel.__post_init__(self) -> None` calls `processing_fields(self, columns)` | `datamodel/base.py:35`, `:43` |
| Existing Field tests and stdlib dataclass fixture | `tests/test_field.py:8`, `:17`, `:34`, `:47` |
| Extension `datamodel.fields` compiles `datamodel/fields.pyx` | `setup.py:29` |
| Ten-cell release matrix; installed-wheel test only asserts Rust availability | `.github/workflows/release.yml:14`, `:62` |
| 3.14 classifier | `pyproject.toml:33` |

### Evidence from the FEAT-2 branch

These files exist at `55dc55c` in
`.claude/worktrees/feat-FEAT-2-compatible-model-performance/`, not on main:

- `docs/performance.md`, “Rollout prerequisites”.
- `benchmarks/results/compatible-model-performance/platforms.md`, BLOCKER-1.
- `benchmarks/results/compatible-model-performance/platforms.json`,
  `analysis.release_blockers` and `cells["linux-x86_64/3.14"]`.

### Does NOT Exist (Anti-Hallucination)

- A separate Column class or separate Column superclass initializer: Column is
  a factory forwarding to Field.
- A missing public `doc` parameter: Field already exposes it.
- The two proposed test/smoke files: they are new deliverables.
- Passing Windows 3.14 evidence or complete 3.14 model support established by this
  investigation. The existing platform report does not certify either.

## 7. Implementation Notes & Constraints

### Patterns to Follow

Keep the fix adjacent to the existing superclass argument dictionary. Rebuild
Cython outputs through the existing build system; do not hand-edit generated C++
or commit local compiled binaries. No additional package dependency is needed.

### Known Risks / Gotchas

- Unconditionally passing doc fixes 3.14 but breaks earlier interpreters.
- Passing `None` instead of the supplied doc would erase documentation on 3.14.
- CPython annotation discovery is a distinct issue: source inspection suggests
  the eager namespace lookup misses deferred annotations. The observed empty
  registry is confirmed; a full causal investigation and repair are follow-up work.
- Closing this narrowly scoped bug does not certify the FEAT-001/FEAT-2 matrix.
- Rebuilding the immutable 0.10.21 reference with this fix would invalidate its
  role as FEAT-2's historical oracle. Validate this correction as an intentional
  compatibility repair with separate artifacts.

### External Dependencies

Existing CPython stdlib, Cython build toolchain, pytest and cibuildwheel only;
retain repository version constraints. The constructor change is confirmed from
upstream CPython and the local 3.14.2 stdlib signature.

### Worktree Strategy

`resolve_flow(kind="bug")` resolves to `type: hotfix`, `base_branch: main`.
Use a dedicated hotfix worktree based on main for implementation; this spec does
not reserve a FEAT identifier. Keep ownership to M1–M4 and integrate the eventual
fix into dev and the FEAT-2 branch through the normal hotfix process. Coordinate
the `fields.pyx` hunk with FEAT-2's policy additions. No task decomposition or
implementation is performed by this specification request.

## 8. Open Questions

- [x] Is this a FEAT-2 regression? No: independently reproduced in the existing
  0.10.21 reference, with identical initializer argument blocks.
- [x] Is a new public doc parameter needed? No: preserve and forward the existing one.
- [x] Does repairing doc prove all 3.14 models work? No: annotation discovery
  and the remaining platform/consumer evidence need separate resolution.
- [ ] Assign a Jira key if external tracking is desired. — Owner: maintainer.
- [ ] Assign the corrective release number before publishing. — Owner: maintainer.
- [ ] Create/link the companion annotation-discovery issue and require it for
  full CPython 3.14 certification. — Owner: maintainer / implementation review.

## Revision History

| Version | Date | Author | Change |
|---|---|---|---|
| 0.1 | 2026-09-08 | Codex | Initial bug spec; reproduced reference failure, qualified scope, specified compatibility fix and installed-wheel regression gate |
