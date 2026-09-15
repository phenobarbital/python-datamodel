# HOTFIX-CPY314DOC-1: Fix Field.__init__ doc forwarding for CPython 3.14

**Feature**: cpython314-field-doc-compatibility (hotfix; no Jira key)
**Spec**: `sdd/specs/cpython314-field-doc-compatibility.spec.md`
**Status**: pending
**Priority**: high
**Estimated effort**: S (< 2h)
**Depends-on**: none
**Assigned-to**: unassigned

---

## Context

> CPython 3.14 added a required `doc` argument to `dataclasses.Field.__init__`.
> `datamodel.fields.Field` subclasses it and calls `ff.__init__()` without `doc`,
> causing a `TypeError` on every Field/Column construction on 3.14.
> This task implements the version-aware forwarding described in spec §2.

---

## Scope

- Add a version guard that includes `doc` in the superclass argument dictionary
  when `version_info >= (3, 14)`.
- Preserve existing `self.doc = doc` assignment (line 172) — the caller's value
  must reach both the subclass slot and the superclass.
- Do not pass `doc` on 3.10–3.13 (they reject unknown kwargs).
- Rebuild the Cython extension and verify the fix with a minimal smoke:
  `python -c "from datamodel.fields import Field; Field()"` and
  `python -c "from datamodel.fields import Field; Field(doc='test')"`.

**NOT in scope**: tests (HOTFIX-CPY314DOC-2), CI smoke (HOTFIX-CPY314DOC-3),
changelog (HOTFIX-CPY314DOC-4).

---

## Files to Create / Modify

| File | Action | Description |
|---|---|---|
| `datamodel/fields.pyx` | MODIFY | Add version-aware `doc` forwarding to superclass args |

---

## Codebase Contract (Anti-Hallucination)

### Verified Imports
```python
from sys import version_info                 # verified: datamodel/fields.pyx:4
from dataclasses import Field as ff          # verified: datamodel/fields.pyx:18
```

### Existing Signatures to Use
```python
# datamodel/fields.pyx:70
class Field(ff):
    __slots__ = (..., 'doc', ...)             # line 87

# datamodel/fields.pyx:128
def __init__(self, default=None, nullable=True, required=False,
             factory=None, min=None, max=None, validator=None,
             pattern=None, alias=None, kw_only=False,
             metadata=None, doc=None, **kwargs):

# datamodel/fields.pyx:172
    self.doc = doc

# datamodel/fields.pyx:233-246 — superclass call block:
    args = {
        "init": self.init,
        "repr": self.repr,
        "hash": self.hash,
        "compare": self.compare,
        "metadata": self._meta,
        "kw_only": self.kw_only
    }
    ff.__init__(
        self,
        default=self.default,
        default_factory=self.default_factory,
        **args
    )
```

### Does NOT Exist
- ~~`args["doc"]`~~ — not currently in the args dict; this task adds it conditionally
- ~~`try/except TypeError`~~ — the spec explicitly forbids catch-and-retry
- ~~A separate Column superclass call~~ — Column is a factory that delegates to Field

---

## Implementation Blueprint

### Steps (in order)
1. Insert a version guard between the `args` dict and the `ff.__init__()` call — *why*: CPython 3.14 requires `doc` in `Field.__init__`; earlier versions reject it.
2. Rebuild: `python setup.py build_ext --inplace` — *why*: `.pyx` changes require recompilation.
3. Smoke-test: `python -c "from datamodel.fields import Field; Field()"` and `python -c "from datamodel.fields import Field; Field(doc='hello')"` — *why*: confirms the fix doesn't raise on the current interpreter.

### `datamodel/fields.pyx` (MODIFY)
```python
# occurrences: 1 (verified: grep -c '"kw_only": self.kw_only' datamodel/fields.pyx)
# AFTER — insert below `            "kw_only": self.kw_only` (verified: datamodel/fields.pyx:239)
# The two new lines go between the closing `}` of `args` (line 240) and `ff.__init__(` (line 241).
        if version_info >= (3, 14):
            args["doc"] = doc
```
**Why this shape**: `version_info` is already imported at line 4. The guard is a
one-time check at field creation time (not per-instance), adds zero overhead on
3.10–3.13, and forwards the caller's existing `doc` value (including `None`)
exactly as the spec requires. The `self.doc = doc` assignment on line 172
remains — both paths must set the slot.

### FILL IN checklist
- [ ] Verify the insertion point: the two lines must appear after `}` (line 240) and before `ff.__init__(` (line 241)

---

## Acceptance Criteria

- [ ] `Field()` succeeds on CPython 3.14 (no TypeError)
- [ ] `Field(doc="test")` succeeds and `f.doc == "test"` on 3.14
- [ ] `Field(doc=None)` succeeds and `f.doc is None` on 3.14
- [ ] `Column(doc="x")` succeeds on 3.14 (delegates to Field)
- [ ] CPython 3.10–3.13 receive no unsupported `doc` keyword in superclass call
- [ ] Existing `pytest tests/test_field.py` passes after rebuild

---

## Test Specification

> Minimal smoke only — full tests are HOTFIX-CPY314DOC-2.

```python
# Quick manual verification (not a pytest file):
from datamodel.fields import Field, Column
f1 = Field()
assert f1.doc is None
f2 = Field(doc="hello")
assert f2.doc == "hello"
c = Column(doc="col doc")
assert c.doc == "col doc"
```

---

## Agent Instructions

When you pick up this task:

1. **Read the spec** at the path listed above for full context
2. **Check dependencies** — none for this task
3. **Verify the Codebase Contract** — confirm `version_info` import at line 4, `args` dict at lines 233–240, and `ff.__init__` at line 241
4. **Update status** in `sdd/tasks/index/cpython314-field-doc-compatibility.json` → `"in-progress"`
5. **Implement** — insert the two-line version guard per the blueprint
6. **Rebuild**: `python setup.py build_ext --inplace`
7. **Verify** all acceptance criteria are met
8. **Move this file** to `sdd/tasks/completed/HOTFIX-CPY314DOC-1-field-doc-forwarding.md`
9. **Update index** → `"done"`
10. **Fill in the Completion Note** below

---

## Completion Note

*(Agent fills this in when done)*

**Completed by**: <session or agent ID>
**Date**: YYYY-MM-DD
**Notes**: What was implemented, any deviations from scope, issues encountered.

**Deviations from spec**: none | describe if any
