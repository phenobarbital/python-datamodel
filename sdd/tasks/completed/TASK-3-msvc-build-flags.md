# TASK-3: Make Cython extension flags MSVC-compatible

**Feature**: FEAT-001 - Optional uvloop, Python 3.14 build, Windows wheels
**Spec**: `sdd/specs/new-infra-spec-uvloop-py314-windows.spec.md`
**Status**: pending
**Priority**: high
**Estimated effort**: S (< 2h)
**Depends-on**: none
**Assigned-to**: unassigned

---

## Context

`setup.py` sends GCC flags to every extension. MSVC rejects `-lstdc++`, and
`-O3` is not the correct MSVC optimization spelling. This task implements
Module 3 and AC5 without changing Cython sources or extension names.

## Scope

- Select `/O2` and no extra link arguments on `sys.platform == "win32"`.
- Preserve `-O3` and `-lstdc++` on non-Windows builds.
- Preserve the existing ten extension definitions and three C++ declarations.
- Add a small importable flag-selection function only if needed for tests.
- Add focused tests or a static verification for both branches.

**NOT in scope**: Windows CI orchestration (TASK-5), Rust staging (TASK-4), or
changes to `.pyx` sources.

## Files to Create / Modify

| File | Action | Description |
|---|---|---|
| `setup.py` | MODIFY | Platform-specific compile/link selection |
| `tests/test_setup_flags.py` | CREATE or MODIFY | Focused flag tests, if practical |

## Codebase Contract (Anti-Hallucination)

### Verified Imports

```python
from Cython.Build import cythonize  # setup.py:9
from setuptools import Extension, setup  # setup.py:10
```

### Existing Signatures to Use

```python
# setup.py:12-13
COMPILE_ARGS = ["-O3"]
EXTRA_LINK_ARGS = ["-lstdc++"]

# setup.py:15-79
extensions = [
    Extension(..., extra_compile_args=COMPILE_ARGS, ...),
    ...,
]
```

The current C++ extensions consuming `EXTRA_LINK_ARGS` are
`datamodel.fields` (lines 16-22), `datamodel.functions` (35-41), and
`datamodel.parsers.json` (54-60).

### Does NOT Exist

- ~~`_compiler_flags()`~~ — no flag-selection helper currently exists.
- ~~`sys.platform` checks in `setup.py`~~ — this task adds the first one.
- ~~MSVC-specific flags~~ — current definitions are GCC-style only.

## Implementation Notes

Keep the global variables available to existing `Extension` declarations:

```python
import sys


def _compiler_flags() -> tuple[list[str], list[str]]:
    if sys.platform == "win32":
        return ["/O2"], []
    return ["-O3"], ["-lstdc++"]


COMPILE_ARGS, EXTRA_LINK_ARGS = _compiler_flags()
```

If tests monkeypatch `sys.platform`, select values when the helper is called,
not permanently at import time. Existing C extensions should continue to omit
`extra_link_args`; the three C++ extensions should receive the selected list.

### Key Constraints

- Never pass `-lstdc++` to MSVC.
- Do not replace C++ extensions with C extensions.
- Keep non-Windows behavior equivalent.
- Do not add a Windows-only package dependency.

### References in Codebase

- `setup.py:12-79` — flags and all ten extensions.
- `pyproject.toml:1-8` — build-system Cython dependency.
- Spec AC5 — required platform behavior.

## Acceptance Criteria

- [ ] Windows selection returns `(["/O2"], [])`.
- [ ] Non-Windows selection returns `(["-O3"], ["-lstdc++"])`.
- [ ] The three C++ extensions remain `language="c++"`.
- [ ] No `.pyx` files are changed.
- [ ] Focused tests pass, or TASK-5 verifies the Windows build.

## Test Specification

```python
def test_windows_flags(monkeypatch):
    import setup
    monkeypatch.setattr(setup.sys, "platform", "win32")
    assert setup._compiler_flags() == (["/O2"], [])


def test_posix_flags(monkeypatch):
    import setup
    monkeypatch.setattr(setup.sys, "platform", "linux")
    assert setup._compiler_flags() == (["-O3"], ["-lstdc++"])
```

If importing `setup.py` triggers unacceptable build side effects, extract the
pure function into a small build helper module and retain the same globals.

## Agent Instructions

1. Verify all ten extension definitions before editing.
2. Keep this task independent from TASK-1 and TASK-4.
3. Run focused tests and document the Windows CI verification expected in TASK-5.
4. Do not modify Cython source files.

## Completion Note

**Completed by**: sdd-worker (Claude)
**Date**: 2026-09-08
**Notes**: Extracted a `_compiler_flags()` function selecting `(["/O2"], [])`
on `win32` and `(["-O3"], ["-lstdc++"])` elsewhere, assigning
`COMPILE_ARGS, EXTRA_LINK_ARGS = _compiler_flags()` at import time. Guarded
the trailing `setup(...)` call behind `if __name__ == "__main__":` so
`tests/test_setup_flags.py` can `import setup` and monkeypatch
`setup.sys.platform` without triggering a build (this guard is the only
deviation from the file's un-guarded original structure; behavior of
`python setup.py build_ext[...]` is unchanged since `__main__` is still true
when run as a script). Verified all ten extensions and the three
`language="c++"` extensions are untouched, and rebuilt in-place locally.
**Deviations from spec**: Added an `if __name__ == "__main__":` guard around
the `setup()` call (not explicitly listed in the task's file table) — the
task text anticipated this need: "If importing setup.py triggers
unacceptable build side effects, extract the pure function into a small
build helper module...". Guarding the call in place was simpler and kept
the change inside `setup.py` (already in scope) instead of adding a new
module.
