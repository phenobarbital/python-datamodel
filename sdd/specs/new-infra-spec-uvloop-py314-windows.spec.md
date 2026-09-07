---
# SDD flow type and base branch (FEAT-145).
# - type: feature  (default)  → base_branch: dev (or any non-main branch)
# - type: hotfix              → base_branch MUST be: main
type: feature
base_branch: dev
---

# Feature Specification: Optional uvloop, Python 3.14 build, Windows wheels

**Feature ID**: FEAT-001
**Date**: 2026-09-07
**Author**: Jesus Lara (spec drafted by Claude from `sdd/proposals/new-infra-spec-uvloop-py314-windows.proposal.md`)
**Status**: draft
**Target version**: 0.11.0 (current `datamodel/version.py` is `0.10.21`; a dependency removal and a new platform justify a minor bump)
**Proposal**: `sdd/proposals/new-infra-spec-uvloop-py314-windows.proposal.md` · research audit `sdd/state/FEAT-001/`

---

## 1. Motivation & Business Requirements

### Problem Statement

python-datamodel declares `uvloop>=0.21.0; sys_platform != 'win32'` as a hard
runtime dependency, yet no module in the package imports it and the library
never creates or configures an event loop (research findings F001, F005). Every
non-Windows user pays for a compiled dependency the library does not use.

Python 3.14 is already listed in the classifiers and in the release matrix
(`cp314-*`), and the locked toolchain (Cython 3.2.9, PyO3 0.29) supports it,
but no 3.14 wheel has ever been built and verified end to end (F002, F004,
F007, F011).

Windows users cannot install binary wheels at all: `release.yml` runs
cibuildwheel on `ubuntu-latest` only, and `setup.py` passes GCC-only flags
(`-O3`, `-lstdc++`) that MSVC rejects (F003, F004). The Rust extension has no
platform-specific code and the package-data already accepts `*.pyd`, so the
gap is confined to build flags and CI (F002, F007, F013).

### Goals

- G1. Remove `uvloop` from `[project].dependencies`; offer it as the optional
  extra `python-datamodel[uvloop]` (proposal U2).
- G2. Provide an explicit, opt-in `install_uvloop()` helper that activates
  uvloop only when it is importable and the platform is not Windows. No
  import-time side effect (proposal U1).
- G3. Produce and verify Python 3.14 wheels for every platform in the release
  matrix.
- G4. Publish `win_amd64` wheels for cp310–cp314 that **contain the Rust
  extension** (`_rs_parsers*.pyd`); the release fails if the Rust build fails
  (proposal U3).
- G5. Keep the release matrix to manylinux x86_64 + win_amd64 (proposal U4).
- G6. Make `release.yml` runnable as a dry run (`workflow_dispatch`) so a broken
  Windows or 3.14 build is caught before a release is cut (F014).

### Non-Goals (explicitly out of scope)

- macOS wheels (resolved U4: Windows only; no macOS wheels exist today).
- Shipping Windows wheels without the Rust extension (resolved U3). The
  `HAS_RUST=False` runtime fallback stays only as a safety net for source
  installs.
- Activating uvloop automatically at `import datamodel` (resolved U1).
- Removing other heavy dependencies (numpy, asyncpg, psycopg).
- A full PR-time test matrix or rewriting the obsolete `tox.ini` (F014). A
  `workflow_dispatch` trigger on the release workflow is the only CI addition.
- ARM / aarch64 wheels on either platform.
- Changing the Rust crate sources or the PyO3 version (already 0.29).

---

## 2. Architectural Design

### Overview

Three independent workstreams touch three surfaces.

**Packaging (uvloop).** `uvloop` moves from `dependencies` to a new
`[project.optional-dependencies].uvloop` extra, keeping the
`sys_platform != 'win32'` marker so the extra is a harmless no-op on Windows.
A new pure-Python module `datamodel/libs/uvloop.py` mirrors the optional-import
pattern of `datamodel/rs_parsers/__init__.py`: a `try/except ImportError` sets
`HAS_UVLOOP`, and `install_uvloop()` installs the uvloop event-loop policy and
returns `True`, or returns `False` without raising when uvloop is unavailable
or the platform is `win32`. Nothing in `datamodel/__init__.py` imports this
module, so importing the library has no effect on the caller's loop.

**Build flags (Windows).** `setup.py` selects compiler flags by platform:
`/O2` and no extra link args under MSVC (`sys.platform == "win32"`), the
current `-O3` / `-lstdc++` elsewhere. Cython sources are unchanged.

**Release workflow (3.14 + Windows).** `release.yml` gains an `os` dimension
(`ubuntu-latest`, `windows-latest`) crossed with the existing five Python
versions. cibuildwheel runs without `--platform` (auto-detect), with
per-platform archs (`CIBW_ARCHS_LINUX=x86_64`, `CIBW_ARCHS_WINDOWS=AMD64`) and
per-platform pre-build hooks. The Rust extension staging (build wheel with
maturin, extract `_rs_parsers*.so|.pyd` into `datamodel/rs_parsers/`) moves
from an inline shell one-liner into a small cross-platform Python script,
`scripts/stage_rust_ext.py`, invoked by both `CIBW_BEFORE_BUILD_LINUX` and
`CIBW_BEFORE_BUILD_WINDOWS` and by the Makefile. A `CIBW_TEST_COMMAND` imports
`datamodel.rs_parsers` and asserts `HAS_RUST is True` inside every built
wheel; this is what enforces G4 on both platforms. Artifact names become
`wheels-<os>-py<version>` so the two OS legs no longer collide, and the deploy
job downloads `wheels-*`.

### Component Diagram

```
pip install python-datamodel[uvloop]
        │
        ▼
pyproject.toml ── optional-dependencies.uvloop ──► uvloop (non-win32 only)
        │
        ▼
datamodel/libs/uvloop.py
   HAS_UVLOOP: bool            (try/except ImportError, like rs_parsers.HAS_RUST)
   install_uvloop() -> bool    (opt-in; caller invokes explicitly)

release.yml  (on: release created | workflow_dispatch)
  build[os × py] ──► cibuildwheel
        │   CIBW_BEFORE_BUILD_{LINUX,WINDOWS} ──► scripts/stage_rust_ext.py
        │            └─ maturin build rust/rs_parsers ─► copy .so/.pyd → datamodel/rs_parsers/
        │   setup.py (platform flags) ──► 10 Cython extensions
        │   CIBW_TEST_COMMAND: assert datamodel.rs_parsers.HAS_RUST
        └─► upload wheels-<os>-py<ver>
  deploy ──► download wheels-* ──► sdist ──► PyPI
```

### Integration Points

| Existing Component | Integration Type | Notes |
|---|---|---|
| `pyproject.toml` `[project].dependencies` (lines 42-55) | modifies | drop `uvloop` line 44 |
| `pyproject.toml` `[project.optional-dependencies]` (line 57) | extends | add `uvloop = [...]` extra next to `dev` |
| `pyproject.toml` `[build-system].requires` (lines 2-7) | modifies | raise `Cython>=3.0.11` to a 3.14-capable floor (`>=3.1.0`) |
| `datamodel/libs/__init__.py` (line 1) | untouched | helper lives in `datamodel.libs.uvloop`; not re-exported to avoid eager import |
| `datamodel/rs_parsers/__init__.py` `HAS_RUST` (lines 8-30) | pattern reuse + CI assertion | template for `HAS_UVLOOP`; `HAS_RUST` is asserted by `CIBW_TEST_COMMAND` |
| `setup.py` `COMPILE_ARGS` / `EXTRA_LINK_ARGS` (lines 12-13) | modifies | platform-conditional values |
| `.github/workflows/release.yml` `jobs.build` (lines 8-64) | restructures | os matrix, per-OS CIBW env, artifact names, staging script |
| `.github/workflows/release.yml` `jobs.deploy` (lines 66-116) | modifies | `pattern: wheels-*` |
| `Makefile` `stage-rust` (lines 57-66) | modifies | delegate to `scripts/stage_rust_ext.py` (handles `.pyd`) |
| `README.md` (line 22), `INSTALL.md` (line 17), `CHANGELOG.md` | documents | extra, Windows wheels, 3.14; fix stale `setuptools-rust` |
| `datamodel/version.py` (line 9) | bumps | `0.10.21` → `0.11.0` |

### Data Models

No new data structures. The only new state is a module-level boolean.

### New Public Interfaces

```python
# datamodel/libs/uvloop.py  (new)
HAS_UVLOOP: bool
"""True when `import uvloop` succeeded at module import time."""

def install_uvloop() -> bool:
    """Install uvloop as the asyncio event-loop policy.

    Returns True when the policy was installed (or was already uvloop's).
    Returns False, without raising, when uvloop is not importable or when
    sys.platform == "win32". Idempotent. Never called implicitly by datamodel.
    """
```

```python
# scripts/stage_rust_ext.py  (new, build tooling — not part of the wheel)
def main(manifest: str = "rust/rs_parsers/Cargo.toml",
         dest: str = "datamodel/rs_parsers",
         out_dir: str = "rust/target/wheels") -> int:
    """Run `maturin build --release` for the manifest, then copy every
    `_rs_parsers*.so` / `_rs_parsers*.pyd` found in the newest wheel into
    `dest`. Exit non-zero if maturin fails or no extension file was found."""
```

Command-line surface added to the package: `pip install python-datamodel[uvloop]`.

---

## 3. Module Breakdown

### Module 1: uvloop optional extra + helper
- **Path**: `pyproject.toml`, `datamodel/libs/uvloop.py` (new)
- **Responsibility**: remove the hard dependency; add the `uvloop` extra with the
  `sys_platform != 'win32'` marker; implement `HAS_UVLOOP` and
  `install_uvloop()` following the `rs_parsers` optional-import pattern.
  Regenerate `uv.lock` (`uv lock`).
- **Depends on**: nothing.

### Module 2: uvloop helper tests
- **Path**: `tests/test_uvloop_helper.py` (new)
- **Responsibility**: `install_uvloop()` returns `False` and does not raise when
  uvloop is absent (simulate via `monkeypatch` on the module's `HAS_UVLOOP` /
  `sys.platform`); returns `True` and `asyncio.new_event_loop()` yields a
  `uvloop.Loop` when uvloop is present (`pytest.importorskip("uvloop")`);
  `import datamodel` does not import `uvloop` (`"uvloop" not in sys.modules`
  after a fresh import in a subprocess).
- **Depends on**: Module 1.

### Module 3: MSVC-compatible build flags
- **Path**: `setup.py`
- **Responsibility**: choose `extra_compile_args` / `extra_link_args` per
  platform: `["/O2"]` and `[]` on `win32`; `["-O3"]` and `["-lstdc++"]`
  otherwise. Applies to all ten extensions; the three `language="c++"`
  extensions keep the C++ language flag on both platforms.
- **Depends on**: nothing.

### Module 4: Cross-platform Rust staging script
- **Path**: `scripts/stage_rust_ext.py` (new), `Makefile` `stage-rust`
- **Responsibility**: replace the inline `python3 -c "import zipfile,..."`
  one-liner in `release.yml` and the `find … '_rs_parsers*.so'` in the Makefile
  with one script that handles both `.so` and `.pyd`, uses `tempfile` instead
  of `/tmp/_rs`, and exits non-zero when nothing was staged. Makefile
  `stage-rust` calls it.
- **Depends on**: nothing (Module 5 consumes it).

### Module 5: Release workflow — OS matrix, Windows leg, 3.14 verification
- **Path**: `.github/workflows/release.yml`
- **Responsibility**: add `workflow_dispatch` trigger; matrix
  `os: [ubuntu-latest, windows-latest]` × `python-version` (five entries,
  `cibw-build` includes unchanged); `runs-on: ${{ matrix.os }}`;
  `cibuildwheel --output-dir dist` (no `--platform`);
  `CIBW_ARCHS_LINUX: x86_64`, `CIBW_ARCHS_WINDOWS: AMD64`;
  `CIBW_BEFORE_BUILD_LINUX` (rustup via curl as today, then
  `pip install maturin && python scripts/stage_rust_ext.py`);
  `CIBW_BEFORE_BUILD_WINDOWS` (`pip install maturin && python scripts/stage_rust_ext.py`,
  relying on the runner's preinstalled MSVC Rust toolchain);
  `CIBW_TEST_COMMAND: python -c "import datamodel.rs_parsers as r; assert r.HAS_RUST"`;
  artifact `name: wheels-${{ matrix.os }}-py${{ matrix.python-version }}`;
  deploy `pattern: wheels-*`; deploy step listing `dist/` must show both
  `manylinux` and `win_amd64` wheels for cp310–cp314 (a shell check fails the
  job otherwise).
- **Depends on**: Module 3, Module 4.

### Module 6: Docs, version, changelog
- **Path**: `README.md`, `INSTALL.md`, `CHANGELOG.md`, `datamodel/version.py`
- **Responsibility**: document `pip install python-datamodel[uvloop]` and the
  `install_uvloop()` call; state Windows (`win_amd64`) and Python 3.14
  support; replace the stale `setuptools-rust` instruction with maturin;
  changelog entry noting the removed hard dependency (breaking for anyone who
  relied on datamodel to pull uvloop); bump version to `0.11.0`.
- **Depends on**: Modules 1, 5.

---

## 4. Test Specification

### Unit Tests
| Test | Module | Description |
|---|---|---|
| `test_install_uvloop_without_uvloop_returns_false` | 2 | With `HAS_UVLOOP` monkeypatched to `False`, `install_uvloop()` returns `False`, raises nothing, policy unchanged |
| `test_install_uvloop_on_win32_returns_false` | 2 | With `sys.platform` monkeypatched to `"win32"`, returns `False` even if uvloop is importable |
| `test_install_uvloop_activates_policy` | 2 | `pytest.importorskip("uvloop")`; after the call `asyncio.new_event_loop()` is a `uvloop.Loop`; restores the default policy in teardown |
| `test_install_uvloop_idempotent` | 2 | Calling twice returns `True` twice and does not stack policies |
| `test_import_datamodel_does_not_import_uvloop` | 2 | Subprocess `python -c "import datamodel, sys; assert 'uvloop' not in sys.modules"` exits 0 |
| `test_setup_flags_per_platform` | 3 | Import `setup.py` flag selection with `sys.platform` patched to `win32` / `linux`; assert `/O2` + no link args vs `-O3` + `-lstdc++` (only if flag selection is factored into an importable function; otherwise verified by CI build) |
| `test_stage_rust_ext_copies_pyd_and_so` | 4 | Given a fake wheel zip containing `_rs_parsers.cp312-win_amd64.pyd` (and one with `.so`), the script copies it into a temp `dest` and returns 0; returns non-zero for a wheel with neither |

### Integration Tests
| Test | Description |
|---|---|
| CI dry run (`workflow_dispatch`) | All 10 matrix legs (2 os × 5 py) green; every wheel passes `CIBW_TEST_COMMAND` (HAS_RUST true) |
| Wheel inventory check in `deploy` | `dist/` contains `*-manylinux*_x86_64.whl` and `*-win_amd64.whl` for each of cp310..cp314 (10 wheels) plus the sdist |
| Fresh-venv install without uvloop | `uv venv && uv pip install dist/<linux cp312 wheel>` then `python -c "import datamodel; from datamodel.libs.uvloop import install_uvloop, HAS_UVLOOP; assert HAS_UVLOOP is False"` |
| Fresh-venv install with extra | `uv pip install "dist/<wheel>[uvloop]"` then `install_uvloop()` returns `True` |
| Existing suite | `pytest tests/ -v` passes on 3.12 locally and on 3.14 in CI (`CIBW_TEST_COMMAND` may additionally run a smoke subset) |

### Test Data / Fixtures
```python
# tests/test_uvloop_helper.py — fixture sketch (design only)
@pytest.fixture
def restore_event_loop_policy():
    """Snapshot asyncio's policy before the test and restore it after,
    so uvloop activation cannot leak into other tests."""
```
There is no `tests/conftest.py` today (F012); the fixture lives in the test
module unless a conftest is introduced by the implementer.

---

## 5. Acceptance Criteria

> This feature is complete when ALL of the following are true:

- [ ] AC1. `grep -n uvloop pyproject.toml` matches only inside
  `[project.optional-dependencies]` under the `uvloop` extra, with marker
  `sys_platform != 'win32'`; no match under `dependencies`.
- [ ] AC2. In a fresh venv without uvloop, `python -c "import datamodel"` and
  `python -c "from datamodel.libs.uvloop import install_uvloop, HAS_UVLOOP"`
  both succeed; `HAS_UVLOOP is False`; `install_uvloop()` returns `False`.
- [ ] AC3. With `python-datamodel[uvloop]` installed on Linux,
  `install_uvloop()` returns `True` and `asyncio.new_event_loop()` returns a
  `uvloop.Loop`. Calling it twice is safe.
- [ ] AC4. `python -c "import datamodel, sys; assert 'uvloop' not in sys.modules"`
  exits 0 (no import-time activation).
- [ ] AC5. `setup.py` passes no `-lstdc++` and no `-O3` when
  `sys.platform == "win32"`; Linux flags are unchanged (`-O3`, `-lstdc++` on
  the three C++ extensions).
- [ ] AC6. `release.yml` has `workflow_dispatch`; matrix is exactly
  `{ubuntu-latest, windows-latest} × {3.10, 3.11, 3.12, 3.13, 3.14}`; no
  macOS entry.
- [ ] AC7. A `workflow_dispatch` dry run is green on all 10 legs, and each
  wheel passes `CIBW_TEST_COMMAND` asserting `datamodel.rs_parsers.HAS_RUST`
  is `True` (Rust `.pyd` present in every Windows wheel).
- [ ] AC8. The deploy job's inventory step fails unless `dist/` contains ten
  wheels (5 manylinux x86_64 + 5 win_amd64) and one sdist; artifact names are
  unique per (os, python).
- [ ] AC9. `scripts/stage_rust_ext.py` is the single staging path used by
  `CIBW_BEFORE_BUILD_LINUX`, `CIBW_BEFORE_BUILD_WINDOWS` and `make stage-rust`;
  it handles `.so` and `.pyd` and exits non-zero when nothing is staged.
- [ ] AC10. `[build-system].requires` pins `Cython>=3.1.0` (or later) and
  `uv.lock` is regenerated and committed.
- [ ] AC11. `pytest tests/ -v` passes locally (3.12) with the new
  `tests/test_uvloop_helper.py`; uvloop-dependent tests skip cleanly when
  uvloop is absent.
- [ ] AC12. README, INSTALL and CHANGELOG document the extra, Windows wheels
  and 3.14; INSTALL no longer mentions `setuptools-rust`; version is `0.11.0`.
- [ ] AC13. No change to the public API of `datamodel` other than the new
  `datamodel.libs.uvloop` module.

---

## 6. Codebase Contract

> **CRITICAL — Anti-Hallucination Anchor**
> Verified 2026-09-07 against `dev` @ `ab95f81`. Implementation agents MUST
> NOT reference imports, attributes, or methods not listed here without first
> verifying they exist via `grep` or `read`.

### Verified Imports
```python
from datamodel.rs_parsers import HAS_RUST          # verified: datamodel/rs_parsers/__init__.py:8,28
from datamodel.libs import ClassDict, ClassDictConfig  # verified: datamodel/libs/__init__.py:1 (only export)
from datamodel import Field, Column, fields, Model, BaseModel, ValidationError  # verified: datamodel/__init__.py:6-14
import asyncio  # used once in datamodel/validation.pyx:7 (iscoroutinefunction at :524); no loop is created anywhere
```

### Existing Signatures / Blocks
```python
# datamodel/rs_parsers/__init__.py  (pattern to replicate)
HAS_RUST = False                          # line 8
try:                                      # line 10
    from ._rs_parsers import (to_string, strtobool, to_boolean, to_date, to_datetime,
        to_timestamp, slugify_camelcase, to_uuid_str, to_uuid_obj, to_uuid,
        to_integer, to_float, to_decimal, to_list)   # lines 11-26
    HAS_RUST = True                       # line 28
except ImportError:                       # line 29
    pass
```
```python
# setup.py
COMPILE_ARGS = ["-O3"]                    # line 12
EXTRA_LINK_ARGS = ["-lstdc++"]            # line 13
# C++ extensions using EXTRA_LINK_ARGS: datamodel.fields (15-22),
# datamodel.functions (36-42), datamodel.parsers.json (60-66)
# setup(ext_modules=cythonize(extensions, annotate=True), package_data={"datamodel.rs_parsers": ["*.so", "*.pyd"]}, zip_safe=False)  # lines 96-102
```
```toml
# pyproject.toml
[build-system]                            # line 1
requires = [ ... "Cython>=3.0.11", ... ]  # lines 2-7 (Cython at line 5)
requires-python = ">=3.10.0"              # line 19
"Programming Language :: Python :: 3.14"  # line 31 (already present)
dependencies = [ ... ]                    # lines 42-55; uvloop at line 44
[project.optional-dependencies]           # line 57
dev = [ ... ]                             # lines 58-69 (pytest, pytest-asyncio, maturin>=1.7,<2.0, Cython>=3.0.11 at 65)
"datamodel.rs_parsers" = ["*.so", "*.pyd"] # package-data, line ~90
[tool.pytest.ini_options] filterwarnings = ["error"]  # lines ~111-122 — INERT: pytest.ini takes precedence (F012)
[tool.uv] link-mode = "copy"              # line 141
```
```yaml
# .github/workflows/release.yml (current)
on: release: types: [created]             # lines 3-5
jobs.build: runs-on: ubuntu-latest        # lines 8-9
matrix.python-version: ["3.10","3.11","3.12","3.13","3.14"] + include cibw-build cp310..cp314  # lines 12-23
CIBW_ARCHS: x86_64 / CIBW_BEFORE_BUILD (curl rustup, /root/.cargo, maturin, inline .so extraction to /tmp/_rs) / CIBW_BUILD  # lines 44-56
run: cibuildwheel --platform linux --output-dir dist   # line 58
upload-artifact name: wheels-py${{ matrix.python-version }}  # lines 60-64
jobs.deploy: download-artifact pattern: wheels-py*, merge-multiple: true  # lines 66-84
sdist build, "Check for wheel types", twine publish via uv tool  # lines 91-116
```
```makefile
# Makefile
PYTHON_VERSION := 3.12                    # line 8
build-rust:                               # line 48  (maturin develop --release)
stage-rust:                               # line 57  (maturin build → unzip → find '_rs_parsers*.so' → cp)  lines 57-66
build: clean                              # line 81  ($(MAKE) stage-rust; uv build)
release: lint test build                  # line 86
```
```toml
# rust/Cargo.toml — pyo3 = { version = "0.29", features = ["extension-module"] }  (lines 1-12; 3.14-capable, no change)
# rust/rs_parsers/Cargo.toml — [lib] name = "_rs_parsers", crate-type = ["cdylib"]  (lines 9-12)
# rust/rs_parsers/pyproject.toml — module-name = "datamodel.rs_parsers._rs_parsers", python-source = "../.."
```
```python
# tests/test_valid_callables.py — only event-loop use in the suite
loop = asyncio.new_event_loop()           # line 38
result = loop.run_until_complete(instance.async_result)  # line 39
loop.close()                              # line 40
```
```ini
# pytest.ini (authoritative pytest config; pyproject block is ignored)
[pytest]
filterwarnings = ignore::DeprecationWarning
```

### Integration Points
| New Component | Connects To | Via | Verified At |
|---|---|---|---|
| `datamodel/libs/uvloop.py` | `datamodel.libs` package | new sibling module; **not** added to `__init__.py` exports | `datamodel/libs/__init__.py:1` |
| `pyproject` extra `uvloop` | `[project.optional-dependencies]` | new key beside `dev` | `pyproject.toml:57-69` |
| `scripts/stage_rust_ext.py` | `Makefile stage-rust`, `release.yml CIBW_BEFORE_BUILD_*` | subprocess `maturin build --release --manifest-path rust/rs_parsers/Cargo.toml --out rust/target/wheels` then copy into `datamodel/rs_parsers/` | `Makefile:57-66`, `release.yml:46-54` |
| `CIBW_TEST_COMMAND` | `datamodel.rs_parsers.HAS_RUST` | `python -c` assertion inside each wheel's test env | `datamodel/rs_parsers/__init__.py:8,28` |
| `setup.py` platform flags | ten `Extension(...)` entries | `extra_compile_args` / `extra_link_args` | `setup.py:12-13, 15-94` |

### Does NOT Exist (Anti-Hallucination)
- ~~`datamodel/libs/uvloop.py`~~, ~~`datamodel.libs.uvloop.install_uvloop`~~, ~~`HAS_UVLOOP`~~ — to be created by Module 1; no `uvloop` import exists anywhere in `datamodel/` or `tests/` today.
- ~~`scripts/stage_rust_ext.py`~~ — to be created by Module 4. `scripts/` currently holds only `scripts/sdd/` tooling.
- ~~`tests/conftest.py`~~, ~~`tests/unit/`~~, ~~`tests/integration/`~~ — the suite is flat under `tests/` (`test_*.py`); the template's `pytest tests/unit/` commands do not apply.
- ~~`CIBW_BEFORE_BUILD_WINDOWS`~~, ~~`CIBW_ARCHS_WINDOWS`~~, ~~`CIBW_TEST_COMMAND`~~, ~~`workflow_dispatch`~~ — none present in `release.yml` yet.
- ~~`.github/workflows/ci.yml`~~ or any PR/test workflow — only `release.yml` and `dependabot.yml` exist.
- ~~any `sys.platform` / `os.name` check~~ in `setup.py` or `datamodel/` — none exists (F013).
- ~~`datamodel/rs_parsers/*.pyd`~~ — no Windows binary has ever been built; only `__init__.py` is git-tracked (`*.so` is gitignored).
- ~~`asyncio.set_event_loop_policy` / `uvloop.install` calls~~ anywhere in the package — none.
- ~~`uvloop` inside the `dev` extra~~ — the `dev` extra has no uvloop; tests never needed it.
- ~~`tox.ini` targets~~ — obsolete (py35–py311, `src/` paths); not used by Makefile or CI; do not extend it.
- ~~`pyproject [tool.pytest.ini_options]` being active~~ — `pytest.ini` wins; do not rely on `filterwarnings = ["error"]`.

---

## 7. Implementation Notes & Constraints

### Patterns to Follow
- **Optional native import behind a flag**: copy the structure of
  `datamodel/rs_parsers/__init__.py:8-30` for `datamodel/libs/uvloop.py`.
- **Environment marker on the extra**: keep `; sys_platform != 'win32'` so
  `pip install python-datamodel[uvloop]` is a no-op on Windows instead of a
  resolution failure.
- **cibuildwheel per-platform env vars** (`CIBW_*_LINUX` / `CIBW_*_WINDOWS`)
  rather than branching inside a single `CIBW_BEFORE_BUILD` string.
- **Library hygiene**: nothing in `datamodel/__init__.py` may import
  `datamodel.libs.uvloop`; activation is always the caller's explicit choice
  (resolved U1).
- **Pure-Python helper**: `datamodel/libs/uvloop.py` stays `.py` (not `.pyx`);
  it is not on any hot path and must import on interpreters without a
  compiler.
- Follow `.claude/rules/cython-development.md` for any `.pyx` touch (none
  expected).

### Known Risks / Gotchas
- **MSVC compilation of the Cython sources is untested** (proposal C7,
  confidence low). `functions.pyx` cimports `libcpp.bool`; `fields.pyx` and
  `parsers/json.pyx` are compiled as C++ only via `language="c++"`. If MSVC
  surfaces errors beyond flags, fix them in the `.pyx` sources within this
  feature; do not downgrade to Cython-only Windows wheels (U3 forbids
  shipping without Rust, and the Cython layer is mandatory anyway).
- **Rust `.pyd` build on `windows-latest`** (C4, medium). GitHub Windows
  runners ship rustup with the `stable-x86_64-pc-windows-msvc` toolchain;
  cibuildwheel's Windows build runs on the host, not in a container, so
  `cargo` is on PATH without the `curl | sh` step. `maturin build
  --interpreter python` must target the cibuildwheel-provided interpreter
  (use `-i python` from the build env, as `Makefile:58` does).
- **Python 3.14 deprecates the asyncio policy system** (`set_event_loop_policy`
  emits `DeprecationWarning` on 3.14). `install_uvloop()` should call
  `uvloop.install()` and let it handle version specifics; `pytest.ini` already
  ignores `DeprecationWarning`. Document in the helper docstring that on 3.12+
  callers may prefer `asyncio.run(main(), loop_factory=uvloop.new_event_loop)`.
- **Breaking change for downstream installs**: projects that implicitly
  received uvloop through datamodel will lose it. Call this out in
  `CHANGELOG.md` and bump the minor version (0.11.0).
- **Artifact-name collision**: with two OS legs, `wheels-py3.12` would be
  uploaded twice and fail; the `<os>` segment in the name is mandatory.
- **Windows path handling in staging**: the current inline extractor uses
  `/tmp/_rs` and filters `.endswith('.so')`; on Windows the extension is
  `_rs_parsers.cp3XX-win_amd64.pyd`. `scripts/stage_rust_ext.py` must match
  `_rs_parsers*` with either suffix and use `tempfile.mkdtemp()`.
- **`git status` noise**: the staged `.so`/`.pyd` files are gitignored (`*.so`)
  — confirm `*.pyd` is also ignored or add it to `.gitignore`.
- **Stale worktree**: `.claude/worktrees/migrate-uv-python314` is fully merged
  and 8 commits behind (F010); remove it (`/remove-worktree`) before creating
  the FEAT-001 worktree to avoid duplicate grep hits.
- **No PR-time CI**: until a dispatch dry run is executed, none of AC6–AC8 can
  be verified locally. Plan one `workflow_dispatch` run on the feature branch
  (or a fork) before merging.

### External Dependencies
| Package | Version | Reason |
|---|---|---|
| `uvloop` | `>=0.21.0; sys_platform != 'win32'` | moves to optional extra `uvloop` (0.22.1 currently locked) |
| `Cython` | `>=3.1.0` (build-system) | first line with Python 3.14 support; lock already at 3.2.9 |
| `maturin` | `>=1.7,<2.0` | unchanged; builds `rs_parsers` on both OS legs |
| `cibuildwheel` | latest (CI only) | Windows + manylinux wheels |
| `pyo3` (Rust) | `0.29` | unchanged; already 3.14-capable |
| `pytest-asyncio` | `>=0.21.0` (dev) | unchanged; new tests use plain `asyncio` + `importorskip` |

---

## 8. Open Questions

> Resolved items were answered during the proposal phase (2026-09-07) and are
> carried forward verbatim; they are not to be re-asked.

- [x] Where should "automatic usage" of uvloop take effect? — *Resolved in proposal*: an explicit `install_uvloop()` helper that callers invoke; no import-time side effect. (→ §2 Overview, §3 Module 1, AC2–AC4)
- [x] Should uvloop be exposed as a pip extra, and under what name? — *Resolved in proposal*: yes, `python-datamodel[uvloop]`. (→ §2 Integration Points, AC1)
- [x] Must the Rust `.pyd` ship in Windows wheels? — *Resolved in proposal*: yes, ship the Rust extension for Windows; the release job must fail if the Rust build fails. (→ §3 Module 5 `CIBW_TEST_COMMAND`, AC7)
- [x] Add macOS wheels while the matrix is being restructured? — *Resolved in proposal*: Windows only; matrix stays manylinux x86_64 + win_amd64. (→ §1 Non-Goals, AC6)
- [ ] Should `install_uvloop()` also be re-exported from `datamodel.libs` for discoverability, or stay reachable only as `datamodel.libs.uvloop.install_uvloop`? Default: stay in the submodule (keeps `datamodel.libs` import cheap). — *Owner: Jesus* (decide during implementation; non-blocking)
- [ ] Should `*.pyd` be added to `.gitignore` alongside `*.so`? Default: yes. — *Owner: implementer* (non-blocking)
- [ ] Should the `workflow_dispatch` dry run also upload wheels as artifacts for manual inspection without publishing? Default: yes, deploy job stays gated on `github.event_name == 'release'`. — *Owner: implementer* (non-blocking)

---

## Worktree Strategy

- **Default isolation unit**: `per-spec` — one worktree
  (`.claude/worktrees/feat-FEAT-001-new-infra-spec-uvloop-py314-windows`),
  tasks executed sequentially. The feature is small and several modules edit
  `pyproject.toml`, so parallel worktrees would merge-conflict on that file.
- **Parallelizable in principle** (if `/sdd-task` chooses a mixed layout):
  Module 1+2 (uvloop, touches `pyproject.toml`, `datamodel/libs/`, `tests/`)
  is independent of Module 3+4 (`setup.py`, `scripts/`, `Makefile`). Module 5
  depends on 3 and 4; Module 6 depends on 1 and 5.
- **Recommended task order**: M4 → M3 → M5 (CI dry run) → M1 → M2 → M6, so the
  riskiest, unverifiable-locally work (Windows CI) surfaces first.
- **Cross-feature dependencies**: none. Prerequisite housekeeping: remove the
  stale `migrate-uv-python314` worktree.

---

## Revision History

| Version | Date | Author | Change |
|---|---|---|---|
| 0.1 | 2026-09-07 | Claude (for Jesus Lara) | Initial draft from FEAT-001 proposal; all four proposal unknowns carried forward as resolved |
