# TASK-6: Document the install path and publish version metadata

**Feature**: FEAT-001 - Optional uvloop, Python 3.14 build, Windows wheels
**Spec**: `sdd/specs/new-infra-spec-uvloop-py314-windows.spec.md`
**Status**: pending
**Priority**: medium
**Estimated effort**: M (2-4h)
**Depends-on**: TASK-1, TASK-5
**Assigned-to**: unassigned

---

## Context

Removing uvloop from the base dependency changes installation behavior, while
Windows wheels and Python 3.14 become supported release targets. Users need the
optional extra and explicit helper call, and the repository needs an initial
changelog because `CHANGELOG.md` does not exist. This task implements Module 6
and AC12-AC13.

## Scope

- Update README with base install, optional extra, explicit helper call,
  Windows wheel, and Python 3.14 documentation.
- Replace stale `setuptools-rust` in `INSTALL.md` with Maturin instructions.
- Create `CHANGELOG.md` with a 0.11.0 section and breaking install note.
- Bump `datamodel/version.py` from `0.10.21` to `0.11.0`.

**NOT in scope**: changing public imports beyond the helper module, adding a new
documentation site, or modifying workflow behavior.

## Files to Create / Modify

| File | Action | Description |
|---|---|---|
| `README.md` | MODIFY | Installation and platform support |
| `INSTALL.md` | MODIFY | Maturin-based development setup |
| `CHANGELOG.md` | CREATE | Initial 0.11.0 release notes |
| `datamodel/version.py` | MODIFY | Version bump |

## Codebase Contract (Anti-Hallucination)

### Verified Imports

```python
from datamodel.libs.uvloop import HAS_UVLOOP, install_uvloop  # TASK-1
```

### Existing Signatures to Use

```markdown
# README.md:17-25
## Installation
pip install python-datamodel
```

```text
# INSTALL.md:16-17
# Install Setup dependencies:
pip install cython maturin sdist setuptools wheel setuptools-rust
```

```python
# datamodel/version.py:9
__version__ = '0.10.21'
```

### Does NOT Exist

- ~~`CHANGELOG.md`~~ — create it with a 0.11.0 section.
- ~~`datamodel.install_uvloop`~~ — document only
  `datamodel.libs.uvloop.install_uvloop`.
- ~~macOS/ARM support statements~~ — document only approved Windows support.

## Implementation Notes

Use concise examples that reflect the actual public surface:

```markdown
### Optional uvloop acceleration

Install the optional dependency on supported non-Windows platforms:

    pip install "python-datamodel[uvloop]"

Opt in explicitly from application startup:

    from datamodel.libs.uvloop import install_uvloop
    install_uvloop()

Importing `datamodel` never changes the application's event-loop policy.
```

The changelog must state that applications which previously relied on datamodel
to install uvloop transitively must now request the extra or install uvloop
themselves. Do not claim automatic activation, macOS wheels, or ARM wheels.

### Key Constraints

- Keep examples compatible with Python 3.10+.
- Do not document a root-level re-export.
- Keep the version source at `datamodel/version.py`; pyproject reads it
  dynamically.
- Mention `win_amd64` and Python 3.14 without promising unsupported targets.

### References in Codebase

- `README.md:13-25` — requirements and installation.
- `INSTALL.md:1-17` — Rust/compiler/setup instructions.
- `datamodel/version.py:4-12` — version metadata.
- `pyproject.toml:99-100` — dynamic version source.

## Acceptance Criteria

- [ ] README documents base install, optional extra, explicit helper, Windows
  wheels, and Python 3.14.
- [ ] INSTALL no longer mentions `setuptools-rust`.
- [ ] `CHANGELOG.md` exists with a 0.11.0 entry and breaking install note.
- [ ] `__version__` is exactly `0.11.0`.
- [ ] Documentation does not claim automatic activation, macOS wheels, or ARM.
- [ ] Version assertion passes.

## Test Specification

```bash
! rg -n 'setuptools-rust|datamodel\.install_uvloop|macOS wheels|ARM wheels' \
  README.md INSTALL.md CHANGELOG.md
rg -n 'python-datamodel\[uvloop\]|install_uvloop|win_amd64|3\.14|0\.11\.0' \
  README.md INSTALL.md CHANGELOG.md datamodel/version.py
python -c 'from datamodel.version import __version__; assert __version__ == "0.11.0"'
```

## Agent Instructions

1. Verify TASK-1 and TASK-5 are complete before editing.
2. Preserve the existing concise README style.
3. Treat the changelog as a new tracked file.
4. Run the grep checks and version assertion.

## Completion Note

**Completed by**: <session or agent ID>
**Date**: YYYY-MM-DD
**Notes**: <implementation and verification summary>
**Deviations from spec**: none | describe if any
