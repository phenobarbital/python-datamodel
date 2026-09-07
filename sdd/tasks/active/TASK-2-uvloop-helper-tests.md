# TASK-2: Test uvloop fallback, activation, and wheel packaging

**Feature**: FEAT-001 - Optional uvloop, Python 3.14 build, Windows wheels
**Spec**: `sdd/specs/new-infra-spec-uvloop-py314-windows.spec.md`
**Status**: pending
**Priority**: high
**Estimated effort**: M (2-4h)
**Depends-on**: TASK-1
**Assigned-to**: unassigned

---

## Context

TASK-1 changes dependency resolution and adds the public helper. This task
proves behavior in both dependency states and protects against the packaging
regression where a helper works in a checkout but is absent from the wheel.
It implements Module 2 and the helper tests in the approved spec.

## Scope

- Create the flat-suite test module `tests/test_uvloop_helper.py`.
- Test absence of uvloop without requiring uvloop to be installed.
- Test Windows gating by monkeypatching `sys.platform`.
- Test Linux activation and idempotency with `pytest.importorskip("uvloop")`.
- Test that importing `datamodel` does not import uvloop.
- Add a wheel/package smoke assertion for `datamodel.libs.uvloop`.
- Restore the event-loop policy after every activation test.

**NOT in scope**: changing helper behavior, dependency declarations, release
workflow, or staging script implementation.

## Files to Create / Modify

| File | Action | Description |
|---|---|---|
| `tests/test_uvloop_helper.py` | CREATE | Unit and subprocess tests |
| `tests/test_valid_callables.py` | VERIFY ONLY | Existing event-loop pattern |

## Codebase Contract (Anti-Hallucination)

### Verified Imports

```python
import asyncio                         # tests/test_valid_callables.py:2,38-40
import pytest                           # tests/test_valid_callables.py:4
from datamodel.libs.uvloop import HAS_UVLOOP, install_uvloop  # TASK-1
```

### Existing Signatures to Use

```python
# tests/test_valid_callables.py:38-40
loop = asyncio.new_event_loop()
result = loop.run_until_complete(instance.async_result)
loop.close()
```

```ini
# pytest.ini:1-2
[pytest]
filterwarnings = ignore::DeprecationWarning
```

### Does NOT Exist

- ~~`tests/conftest.py`~~ — keep the policy fixture in this module.
- ~~`tests/unit/`~~ and ~~`tests/integration/`~~ — the suite is flat.
- ~~`datamodel.libs.uvloop`~~ before TASK-1 completes.

## Implementation Notes

Use a fixture that restores the exact policy object. Use a subprocess for the
no-eager-import assertion so the parent import cache cannot affect the result:

```python
@pytest.fixture
def restore_event_loop_policy():
    previous = asyncio.get_event_loop_policy()
    try:
        yield
    finally:
        asyncio.set_event_loop_policy(previous)


def test_install_uvloop_without_uvloop_returns_false(monkeypatch):
    import datamodel.libs.uvloop as helper
    monkeypatch.setattr(helper, "HAS_UVLOOP", False)
    assert helper.install_uvloop() is False


def test_import_datamodel_does_not_import_uvloop():
    result = subprocess.run(
        [sys.executable, "-c",
         "import datamodel, sys; assert 'uvloop' not in sys.modules"],
        check=False,
    )
    assert result.returncode == 0
```

For activation, skip when uvloop is unavailable, call the helper, assert that
`asyncio.new_event_loop()` is a `uvloop.Loop`, close the loop, and restore
the policy. The Windows test must return false even when the optional module is
available.

### Key Constraints

- Missing uvloop is a supported state, not a test failure.
- Never leak a uvloop policy into unrelated tests.
- Do not import the helper in the no-eager-import subprocess test.
- Keep tests compatible with the existing flat pytest layout.

### References in Codebase

- `tests/test_valid_callables.py:38-40` — loop lifecycle.
- `datamodel/rs_parsers/__init__.py:8-30` — optional capability pattern.
- `pyproject.toml:102-119` and `pytest.ini:1-2` — test configuration.

## Acceptance Criteria

- [ ] Fallback, Windows gating, activation, and idempotency tests exist.
- [ ] Activation tests skip cleanly when uvloop is absent.
- [ ] `import datamodel` leaves uvloop out of `sys.modules`.
- [ ] A built wheel imports `datamodel.libs.uvloop`.
- [ ] Focused and full test suites pass.

## Test Specification

```python
import asyncio
import subprocess
import sys

import pytest


def test_install_uvloop_on_win32_returns_false(monkeypatch):
    import datamodel.libs.uvloop as helper
    monkeypatch.setattr(helper.sys, "platform", "win32")
    assert helper.install_uvloop() is False


def test_install_uvloop_activates_policy():
    uvloop = pytest.importorskip("uvloop")
    import datamodel.libs.uvloop as helper
    previous = asyncio.get_event_loop_policy()
    try:
        assert helper.install_uvloop() is True
        loop = asyncio.new_event_loop()
        try:
            assert isinstance(loop, uvloop.Loop)
        finally:
            loop.close()
    finally:
        asyncio.set_event_loop_policy(previous)


def test_install_uvloop_idempotent():
    pytest.importorskip("uvloop")
    import datamodel.libs.uvloop as helper
    previous = asyncio.get_event_loop_policy()
    try:
        assert helper.install_uvloop() is True
        assert helper.install_uvloop() is True
    finally:
        asyncio.set_event_loop_policy(previous)
```

## Agent Instructions

1. Verify TASK-1 is complete before editing tests.
2. Keep tests deterministic on Linux and Windows.
3. Run the focused file, then `pytest tests/ -v`.
4. Do not change production behavior solely to satisfy a test without updating
   the approved spec contract.

## Completion Note

**Completed by**: <session or agent ID>
**Date**: YYYY-MM-DD
**Notes**: <implementation and verification summary>
**Deviations from spec**: none | describe if any
