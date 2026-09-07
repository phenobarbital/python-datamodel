# TASK-1: Add the optional uvloop helper and packaging constraints

**Feature**: FEAT-001 - Optional uvloop, Python 3.14 build, Windows wheels
**Spec**: `sdd/specs/new-infra-spec-uvloop-py314-windows.spec.md`
**Status**: pending
**Priority**: high
**Estimated effort**: M (2-4h)
**Depends-on**: none
**Assigned-to**: unassigned

---

## Context

The package currently installs uvloop as a non-Windows hard dependency even
though no package module imports it. The approved spec moves it to an optional
extra, adds an explicit opt-in helper, and fixes packaging so the helper is
present in built wheels. This task implements Module 1 and AC1, AC2, AC4,
AC10, and AC14.

## Scope

- Remove uvloop from `[project].dependencies`.
- Add `[project.optional-dependencies].uvloop` with
  `uvloop>=0.21.0; sys_platform != 'win32'`.
- Add `datamodel.libs` to the explicit setuptools package list.
- Align build-system and dev-extra Cython constraints at `>=3.2.8`.
- Create `datamodel/libs/uvloop.py` with `HAS_UVLOOP` and explicit,
  idempotent `install_uvloop()`.
- Do not import the helper from `datamodel/__init__.py`.
- Regenerate `uv.lock` with `uv lock`.

**NOT in scope**: helper tests (TASK-2), compiler flags (TASK-3), Rust staging
(TASK-4), release workflow (TASK-5), or documentation/version changes (TASK-6).

## Files to Create / Modify

| File | Action | Description |
|---|---|---|
| `pyproject.toml` | MODIFY | Optional extra, Cython floors, package inclusion |
| `uv.lock` | MODIFY | Lock metadata after dependency graph changes |
| `datamodel/libs/uvloop.py` | CREATE | Lazy optional import and policy installer |
| `datamodel/__init__.py` | VERIFY ONLY | Confirm no eager helper import |

## Codebase Contract (Anti-Hallucination)

### Verified Imports

```python
from datamodel.libs import ClassDict, ClassDictConfig  # datamodel/libs/__init__.py:1
from datamodel.rs_parsers import HAS_RUST              # datamodel/rs_parsers/__init__.py:8,28
```

### Existing Signatures to Use

```python
# datamodel/rs_parsers/__init__.py:8-30
HAS_RUST = False
try:
    from ._rs_parsers import (...)  # optional native import
    HAS_RUST = True
except ImportError:
    pass

# pyproject.toml:79-82
[tool.setuptools]
packages = ["datamodel"]
include-package-data = true
```

### Does NOT Exist

- ~~`datamodel/libs/uvloop.py`~~ — this task creates it.
- ~~`datamodel.libs.uvloop.HAS_UVLOOP`~~ — new symbol.
- ~~`datamodel.libs.uvloop.install_uvloop`~~ — new symbol.
- ~~`datamodel.libs` in the setuptools package list~~ — currently absent.

## Implementation Notes

### Pattern to Follow

```python
import sys

HAS_UVLOOP = False
try:
    import uvloop
    HAS_UVLOOP = True
except ImportError:
    uvloop = None


def install_uvloop() -> bool:
    """Install uvloop's policy when available on a supported platform."""
    if sys.platform == "win32" or not HAS_UVLOOP:
        return False
    uvloop.install()
    return True
```

The implementation may use a more precise optional type annotation, but it must
preserve false-without-raising when unavailable or on Windows, true after
installation, and no call from `datamodel/__init__.py`. Do not re-export the
helper from `datamodel.libs`; that default was resolved in the spec.

### Key Constraints

- Keep uvloop out of base dependencies and retain the Windows marker.
- Include `datamodel.libs` in the wheel without broad package discovery.
- Keep both Cython constraints synchronized at `>=3.2.8`.

### References in Codebase

- `datamodel/rs_parsers/__init__.py:8-30` — optional import pattern.
- `datamodel/__init__.py:6-14` — must remain uvloop-free.
- `pyproject.toml:42-69,79-94` — dependencies and package data.
- `uv.lock:1324-1367,1594-1605` — current lock metadata.

## Acceptance Criteria

- [ ] uvloop appears only in the optional extra.
- [ ] A built wheel contains `datamodel/libs/__init__.py` and the helper.
- [ ] Importing the helper without uvloop succeeds with `HAS_UVLOOP is False`.
- [ ] Build-system and dev-extra Cython constraints both read `>=3.2.8`.
- [ ] `uv.lock` is regenerated and reflects the optional dependency.

## Test Specification

```bash
uv lock
python - <<'PY'
import tomllib
from pathlib import Path

data = tomllib.loads(Path("pyproject.toml").read_text())
assert all("uvloop" not in item for item in data["project"]["dependencies"])
assert data["project"]["optional-dependencies"]["uvloop"] == [
    "uvloop>=0.21.0; sys_platform != 'win32'"
]
assert "datamodel.libs" in data["tool"]["setuptools"]["packages"]
assert "Cython>=3.2.8" in data["build-system"]["requires"]
assert "Cython>=3.2.8" in data["project"]["optional-dependencies"]["dev"]
PY
```

The wheel-content assertion is completed by TASK-2.

## Agent Instructions

1. Read the approved spec and verify the contract before editing.
2. Make only the files in this task's scope.
3. Run the TOML assertions and `uv lock`.
4. Do not add tests to `tests/`; TASK-2 owns them.

## Completion Note

**Completed by**: <session or agent ID>
**Date**: YYYY-MM-DD
**Notes**: <implementation and verification summary>
**Deviations from spec**: none | describe if any
