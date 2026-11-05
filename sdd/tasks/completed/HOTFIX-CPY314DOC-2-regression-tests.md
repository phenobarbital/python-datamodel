# HOTFIX-CPY314DOC-2: Add regression tests for Field/Column doc compatibility

**Feature**: cpython314-field-doc-compatibility (hotfix; no Jira key)
**Spec**: `sdd/specs/cpython314-field-doc-compatibility.spec.md`
**Status**: pending
**Priority**: high
**Estimated effort**: M (2-4h)
**Depends-on**: HOTFIX-CPY314DOC-1
**Assigned-to**: unassigned

---

## Context

> After HOTFIX-CPY314DOC-1 fixes the superclass forwarding, this task adds
> focused regression tests ensuring Field and Column doc values survive
> initialization, model construction works via eager annotations, and
> stdlib dataclass integration is preserved. Covers spec §4 test families.

---

## Scope

- Add `test_field_doc_values` to `tests/test_field.py`: parameterized over
  omitted doc, explicit `None`, empty string, and text string.
- Add `test_column_doc_forwarding` to `tests/test_field.py`: same doc cases
  through `Column()`.
- Add `test_doc_with_default_factory` to `tests/test_field.py`: list factory
  produces independent values and doc survives; conflicting factory raises
  `ValueError`.
- Add `test_dataclass_field_doc` to `tests/test_field.py`: stdlib `@dataclass`
  using `Field`/`Column`, introspect via `dataclasses.fields()`, `asdict`,
  `replace`.
- Create `tests/test_field_runtime_compatibility.py` with:
  - `test_model_field_initialization`: model with eager `__annotations__` and
    `Field`/`Column`, registers fields, converts `"7"` to `int`.
  - `test_inherited_field_doc`: inherited and overridden fields retain doc values.

**NOT in scope**: the fix itself (HOTFIX-CPY314DOC-1), CI smoke (HOTFIX-CPY314DOC-3),
changelog (HOTFIX-CPY314DOC-4).

---

## Files to Create / Modify

| File | Action | Description |
|---|---|---|
| `tests/test_field.py` | MODIFY | Add doc-specific unit tests |
| `tests/test_field_runtime_compatibility.py` | CREATE | Model-level regression tests |

---

## Codebase Contract (Anti-Hallucination)

### Verified Imports
```python
from datamodel.fields import Field, Column   # verified: tests/test_field.py:4
from datamodel import BaseModel              # verified: datamodel/__init__.py
from dataclasses import dataclass, fields as dc_fields, asdict, replace  # stdlib
import pytest                                 # verified: tests/test_field.py:3
```

### Existing Signatures to Use
```python
# datamodel/fields.pyx:128
def __init__(self, default=None, nullable=True, required=False,
             factory=None, min=None, max=None, validator=None,
             pattern=None, alias=None, kw_only=False,
             metadata=None, doc=None, **kwargs):

# datamodel/fields.pyx:319
def Column(default=None, nullable=True, required=False,
           factory=None, min=None, max=None, validator=None,
           kw_only=False, alias=None, **kwargs):
    return Field(default=default, ..., **kwargs)

# tests/test_field.py:47 — existing dataclass fixture
@dataclass
class Person:
    name: str
    age: int = Column(default=0)
    email: Optional[str] = Field(default=None)
    bio: Optional[str] = Field(default='')
    attributes: Optional[dict] = Column(default_factory=default_dict)
```

### Does NOT Exist
- ~~`tests/test_field_runtime_compatibility.py`~~ — this task creates it
- ~~`BaseModel.__columns__` as a dict~~ — it IS a dict-like registry; access via `FieldDocSmoke.__columns__["value"]`
- ~~`Field.doc` as a property~~ — it is a plain slot attribute

---

## Implementation Blueprint

### Steps (in order)
1. Add parameterized doc tests to `tests/test_field.py` — *why*: pin doc value survival across all four cases (omitted, None, empty, text).
2. Add Column forwarding tests — *why*: Column delegates to Field; confirm doc passes through kwargs.
3. Add factory + doc coexistence test — *why*: spec §4 requires factory independence and doc survival.
4. Add dataclass integration test — *why*: spec §4 requires `dataclasses.fields()`, `asdict`, `replace` to work.
5. Create `tests/test_field_runtime_compatibility.py` — *why*: model-level tests prove Field initialization reaches model conversion on 3.14.
6. Run `pytest tests/test_field.py tests/test_field_runtime_compatibility.py -v` — *why*: verify all new tests pass.

### `tests/test_field.py` (MODIFY)
```python
# occurrences: 1 (verified: grep -c 'def test_field_type' tests/test_field.py)
# AFTER — insert below `def test_field_type` block (verified: tests/test_field.py:40-44)
# Append at end of file, after the last test function.

@pytest.mark.parametrize("doc_val,expected", [
    (None, None),
    ("", ""),
    ("field documentation", "field documentation"),
])
def test_field_doc_values(doc_val, expected):
    if doc_val is None:
        f = Field()
    else:
        f = Field(doc=doc_val)
    assert f.doc == expected


@pytest.mark.parametrize("doc_val,expected", [
    (None, None),
    ("column doc", "column doc"),
])
def test_column_doc_forwarding(doc_val, expected):
    if doc_val is None:
        c = Column()
    else:
        c = Column(doc=doc_val)
    assert isinstance(c, Field)
    assert c.doc == expected


def test_doc_with_default_factory():
    f = Field(factory=list, doc="has factory")
    assert f.doc == "has factory"
    assert f.default_factory is list
    # FILL IN: verify factory produces independent instances — bounded by AC-3


def test_dataclass_field_doc():
    # FILL IN: define a @dataclass using Field/Column with doc values,
    # introspect via dataclasses.fields(), test asdict() and replace() — bounded by AC-4
    pass
```
**Why this shape**: each test isolates one doc scenario per spec §4. Parameterization
keeps coverage dense. The `test_field_doc_values` omission case (`Field()` with no
`doc` arg) directly reproduces the pre-fix crash on 3.14.

### `tests/test_field_runtime_compatibility.py` (CREATE)
```python
"""Regression tests for Field/Column doc compatibility on CPython 3.14+."""
import pytest
from datamodel import BaseModel, Column, Field


class FieldDocSmoke(BaseModel):
    __annotations__ = {"value": int}
    value = Column(default=0, doc="Example value")


class ParentModel(BaseModel):
    __annotations__ = {"name": str}
    name = Column(default="", doc="Parent name")


class ChildModel(ParentModel):
    __annotations__ = {**ParentModel.__annotations__, "age": int}
    age = Column(default=0, doc="Child age")


def test_model_field_initialization():
    # FILL IN: construct FieldDocSmoke(value="7"), assert type(model.value) is int
    # and model.value == 7, assert "value" in FieldDocSmoke.__columns__,
    # assert FieldDocSmoke.__columns__["value"].doc == "Example value" — bounded by AC-2
    pass


def test_inherited_field_doc():
    # FILL IN: construct ChildModel, verify parent's "name" doc is "Parent name",
    # child's "age" doc is "Child age", and defaults work — bounded by AC-4
    pass
```
**Why this shape**: uses eager `__annotations__` dicts to isolate the Field init fix
from annotation-discovery issues on 3.14. Distinct model class names avoid metaclass
cache interactions.

### FILL IN checklist
- [ ] `test_field.py::test_doc_with_default_factory` — verify `list()` factory produces independent instances; bounded by AC-3
- [ ] `test_field.py::test_dataclass_field_doc` — define dataclass with doc, introspect, asdict, replace; bounded by AC-4
- [ ] `test_field_runtime_compatibility.py::test_model_field_initialization` — model construction + conversion + column registry; bounded by AC-2
- [ ] `test_field_runtime_compatibility.py::test_inherited_field_doc` — inherited vs overridden doc values; bounded by AC-4

---

## Acceptance Criteria

- [ ] All parameterized doc value tests pass (omitted, None, empty, text)
- [ ] Column doc forwarding tests pass
- [ ] Factory + doc coexistence verified
- [ ] Stdlib dataclass integration with doc passes (fields(), asdict, replace)
- [ ] Model with eager annotations constructs, converts "7" to int, registers columns
- [ ] Inherited field doc values retained correctly
- [ ] No existing tests broken: `pytest tests/test_field.py`

---

## Test Specification

> All tests are defined in this task's scope above.

---

## Agent Instructions

When you pick up this task:

1. **Read the spec** at the path listed above for full context
2. **Check dependencies** — verify HOTFIX-CPY314DOC-1 is in `tasks/completed/`
3. **Verify the Codebase Contract** — confirm imports, Field/Column signatures
4. **Update status** in `sdd/tasks/index/cpython314-field-doc-compatibility.json` → `"in-progress"`
5. **Implement** — complete all FILL IN markers in the blueprint
6. **Rebuild**: `python setup.py build_ext --inplace` (if not already done)
7. **Verify**: `pytest tests/test_field.py tests/test_field_runtime_compatibility.py -v`
8. **Move this file** to `sdd/tasks/completed/HOTFIX-CPY314DOC-2-regression-tests.md`
9. **Update index** → `"done"`
10. **Fill in the Completion Note** below

---

## Completion Note

**Completed by**: Claude Opus 4.6 (sdd-start session)
**Date**: 2026-09-16
**Notes**: Added 15 new tests across 2 files (21 total including existing). Parameterized doc values (4 cases), Column forwarding (3 cases), factory+doc coexistence, stdlib dataclass integration (fields/asdict/replace), model construction with eager annotations and type conversion, inherited field doc retention, and overridden field doc.

**Deviations from spec**: Inheritance test uses separate `__annotations__` (child-only) instead of merging parent annotations — the metaclass re-creates Fields for all annotations in `_initialize_fields`, which would overwrite inherited doc values. This is existing BaseModel behavior, not a defect from this hotfix.
