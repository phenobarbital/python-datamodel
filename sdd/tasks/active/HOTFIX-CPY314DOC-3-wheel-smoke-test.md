# HOTFIX-CPY314DOC-3: Add installed-wheel smoke script and update release workflow

**Feature**: cpython314-field-doc-compatibility (hotfix; no Jira key)
**Spec**: `sdd/specs/cpython314-field-doc-compatibility.spec.md`
**Status**: pending
**Priority**: high
**Estimated effort**: M (2-4h)
**Depends-on**: HOTFIX-CPY314DOC-1
**Assigned-to**: unassigned

---

## Context

> The existing CIBW_TEST_COMMAND only asserts `HAS_RUST` — a bare import that
> can pass without constructing a Field or a working model. This task adds a
> standalone smoke script exercising Field, Column, and model construction so
> the release workflow rejects wheels that silently ship the doc-forwarding bug.
> Covers spec §3 M3 and §4 integration tests.

---

## Scope

- Create `scripts/smoke_installed_model.py`: a standalone script (no pytest
  dependency) that:
  - Prints interpreter version, package version, and imported extension path
  - Constructs `Field()`, `Field(doc="test")`, `Column(doc="col")`
  - Defines a model with eager `__annotations__` and `Column`
  - Asserts field registration, type conversion (`"7"` → `int`), and doc values
  - Retains the existing `HAS_RUST` assertion
  - Exits 0 on success, non-zero on any failure
- Modify `.github/workflows/release.yml` `CIBW_TEST_COMMAND` to run the smoke
  script instead of the inline `python -c` one-liner, while keeping `HAS_RUST`.

**NOT in scope**: the fix (HOTFIX-CPY314DOC-1), unit tests (HOTFIX-CPY314DOC-2),
changelog (HOTFIX-CPY314DOC-4).

---

## Files to Create / Modify

| File | Action | Description |
|---|---|---|
| `scripts/smoke_installed_model.py` | CREATE | Installed-wheel smoke test script |
| `.github/workflows/release.yml` | MODIFY | Update CIBW_TEST_COMMAND to run smoke script |

---

## Codebase Contract (Anti-Hallucination)

### Verified Imports
```python
from datamodel import BaseModel, Field, Column  # verified: datamodel/__init__.py
import datamodel.rs_parsers as r                 # verified: existing CIBW test at release.yml:63
```

### Existing Signatures to Use
```python
# .github/workflows/release.yml:62-63
CIBW_TEST_COMMAND: >-
    python -c "import datamodel.rs_parsers as r; assert r.HAS_RUST"

# cibuildwheel project-path placeholder: {project}
# The test command runs in a temp dir; source files are at {project}/
```

### Does NOT Exist
- ~~`scripts/smoke_installed_model.py`~~ — this task creates it
- ~~A pytest-based CI test step in the release workflow~~ — cibuildwheel uses
  `CIBW_TEST_COMMAND`, not pytest
- ~~`CIBW_TEST_REQUIRES`~~ — not currently set; the smoke must not need pytest

---

## Implementation Blueprint

### Steps (in order)
1. Create `scripts/smoke_installed_model.py` — *why*: standalone smoke that exercises Field/Column/model without pytest.
2. Update `CIBW_TEST_COMMAND` in `.github/workflows/release.yml` — *why*: replace the bare import with the comprehensive smoke.
3. Run the smoke locally: `python scripts/smoke_installed_model.py` — *why*: verify exit 0.

### `scripts/smoke_installed_model.py` (CREATE)
```python
#!/usr/bin/env python
"""Installed-wheel smoke test for Field, Column, and model construction.

Runs without pytest. Exits 0 on success, 1 on failure.
Prints interpreter, package version, and extension path for provenance.
"""
import sys


def main():
    print(f"Python: {sys.version}")

    import datamodel
    print(f"datamodel version: {datamodel.__version__}")
    print(f"datamodel path: {datamodel.__file__}")

    # Rust extension check (existing gate)
    import datamodel.rs_parsers as r
    assert r.HAS_RUST, "Rust extension not available"
    print("HAS_RUST: OK")

    from datamodel import BaseModel, Field, Column

    # Field doc forwarding
    f1 = Field()
    assert f1.doc is None, f"Field().doc should be None, got {f1.doc!r}"

    f2 = Field(doc="standalone")
    assert f2.doc == "standalone", f"Field(doc=...).doc mismatch: {f2.doc!r}"

    c = Column(doc="col doc")
    assert c.doc == "col doc", f"Column(doc=...).doc mismatch: {c.doc!r}"
    print("Field/Column doc: OK")

    # FILL IN: define a model class with eager __annotations__ and Column,
    # construct it with value="7", assert type conversion to int,
    # assert column registration and doc value — bounded by AC-2 / AC-5

    print("All smoke checks passed.")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"SMOKE FAILED: {e}", file=sys.stderr)
        sys.exit(1)
```
**Why this shape**: standalone script with no test framework dependency so
cibuildwheel can run it via `CIBW_TEST_COMMAND` without `CIBW_TEST_REQUIRES`.
Prints provenance first so CI logs identify exactly which interpreter and
package version ran.

### `.github/workflows/release.yml` (MODIFY)
```yaml
# occurrences: 1 (verified: grep -c 'CIBW_TEST_COMMAND' .github/workflows/release.yml)
# REPLACE the existing CIBW_TEST_COMMAND value (verified: .github/workflows/release.yml:62-63)
          CIBW_TEST_COMMAND: >-
            python {project}/scripts/smoke_installed_model.py
```
**Why**: `{project}` is cibuildwheel's placeholder for the source checkout path.
The smoke script includes the `HAS_RUST` assertion, so the inline one-liner is
fully superseded.

### FILL IN checklist
- [ ] `smoke_installed_model.py::main` — model class with eager annotations, construct with "7", assert int conversion + column registry + doc — bounded by AC-2 / AC-5

---

## Acceptance Criteria

- [ ] `scripts/smoke_installed_model.py` exits 0 after `build_ext --inplace`
- [ ] Smoke prints interpreter version, package version, extension path
- [ ] HAS_RUST assertion retained in the smoke
- [ ] Field doc assertions pass (None, explicit value, Column forwarding)
- [ ] Model construction with eager annotations and type conversion verified
- [ ] `CIBW_TEST_COMMAND` in release.yml references the smoke script
- [ ] No other release workflow changes (matrix, deploy, verification steps intact)

---

## Test Specification

> The smoke script IS the test — verify it exits 0.

```bash
source .venv/bin/activate
python setup.py build_ext --inplace
python scripts/smoke_installed_model.py
echo "Exit code: $?"
```

---

## Agent Instructions

When you pick up this task:

1. **Read the spec** at the path listed above for full context
2. **Check dependencies** — verify HOTFIX-CPY314DOC-1 is in `tasks/completed/`
3. **Verify the Codebase Contract** — confirm CIBW_TEST_COMMAND at line 62-63
4. **Update status** in `sdd/tasks/index/cpython314-field-doc-compatibility.json` → `"in-progress"`
5. **Implement** — complete the FILL IN marker in the smoke script
6. **Verify**: run `python scripts/smoke_installed_model.py` locally
7. **Move this file** to `sdd/tasks/completed/HOTFIX-CPY314DOC-3-wheel-smoke-test.md`
8. **Update index** → `"done"`
9. **Fill in the Completion Note** below

---

## Completion Note

*(Agent fills this in when done)*

**Completed by**: <session or agent ID>
**Date**: YYYY-MM-DD
**Notes**: What was implemented, any deviations from scope, issues encountered.

**Deviations from spec**: none | describe if any
