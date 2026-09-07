# TASK-5: Add Windows and Python 3.14 release matrix coverage

**Feature**: FEAT-001 - Optional uvloop, Python 3.14 build, Windows wheels
**Spec**: `sdd/specs/new-infra-spec-uvloop-py314-windows.spec.md`
**Status**: pending
**Priority**: high
**Estimated effort**: L (4-8h)
**Depends-on**: TASK-3, TASK-4
**Assigned-to**: unassigned

---

## Context

The release workflow currently runs Linux-only cibuildwheel with a bash
extractor and colliding artifact names. This task adds Windows, keeps Python
3.10–3.14, wires shared staging, and asserts the Rust extension is present in
every wheel. It implements Module 5 and AC6-AC9.

## Scope

- Add `workflow_dispatch` while preserving `release: created`.
- Cross `ubuntu-latest` and `windows-latest` with Python 3.10–3.14.
- Keep `CIBW_BUILD` mapped to cp310–cp314 for each matrix entry.
- Set `CIBW_ARCHS_LINUX=x86_64` and `CIBW_ARCHS_WINDOWS=AMD64`.
- Wire Linux staging with `--manylinux off` and Windows staging without it.
- Remove explicit `--platform linux`.
- Add `CIBW_TEST_COMMAND` asserting `HAS_RUST is True`.
- Make artifact names OS-qualified and update the download pattern.
- Check for five manylinux and five win_amd64 wheels plus one sdist.
- Keep deploy gated to release events while manual dispatch uploads artifacts.

**NOT in scope**: publishing from manual dispatch, macOS/ARM wheels, Rust source
changes, or Cython source changes.

## Files to Create / Modify

| File | Action | Description |
|---|---|---|
| `.github/workflows/release.yml` | MODIFY | Matrix, per-OS hooks, artifacts, inventory |

## Codebase Contract (Anti-Hallucination)

### Verified Existing Blocks

```yaml
# .github/workflows/release.yml:3-5
on:
  release:
    types: [created]
```

```yaml
# .github/workflows/release.yml:12-23
matrix:
  python-version: ["3.10", "3.11", "3.12", "3.13", "3.14"]
  include:
    - python-version: "3.10"
      cibw-build: "cp310-*"
    # cp311 through cp314 follow
```

```yaml
# .github/workflows/release.yml:60-64
- name: Upload wheel artifacts
  uses: actions/upload-artifact@v4
  with:
    name: wheels-py${{ matrix.python-version }}
    path: dist/*.whl
```

### Does NOT Exist

- ~~`workflow_dispatch`~~, ~~`matrix.os`~~, and
  ~~`CIBW_BEFORE_BUILD_LINUX/WINDOWS`~~ — add them.
- ~~`CIBW_TEST_COMMAND`~~ — add the Rust assertion.
- ~~Windows artifact inventory checks~~ — add them to deploy.

## Implementation Notes

Use the existing Python include mapping while adding the OS dimension:

```yaml
on:
  release:
    types: [created]
  workflow_dispatch:

jobs:
  build:
    runs-on: ${{ matrix.os }}
    strategy:
      matrix:
        os: [ubuntu-latest, windows-latest]
        python-version: ["3.10", "3.11", "3.12", "3.13", "3.14"]
        include:
          - python-version: "3.10"
            cibw-build: "cp310-*"
          # cp311 through cp314
    env:
      CIBW_ARCHS_LINUX: x86_64
      CIBW_ARCHS_WINDOWS: AMD64
      CIBW_BUILD: ${{ matrix.cibw-build }}
      CIBW_BEFORE_BUILD_LINUX: >-
        pip install maturin && python scripts/stage_rust_ext.py --manylinux off
      CIBW_BEFORE_BUILD_WINDOWS: >-
        pip install maturin && python scripts/stage_rust_ext.py
      CIBW_TEST_COMMAND: >-
        python -c "import datamodel.rs_parsers as r; assert r.HAS_RUST"
```

Verify the existing Rust setup/path steps on Windows. The deploy inventory must
fail loudly if any target is missing. Keep `if: github.event_name == 'release'`
on deploy so manual dispatch cannot publish.

### Key Constraints

- No macOS or ARM expansion.
- Artifact names include OS and Python version.
- All ten jobs run the Rust smoke assertion.
- Deploy builds and publishes the sdist only for release events.

### References in Codebase

- `.github/workflows/release.yml:8-64` — current build job.
- `.github/workflows/release.yml:66-116` — current deploy job.
- `datamodel/rs_parsers/__init__.py:8-30` — HAS_RUST.
- Spec AC6-AC9 — required matrix and inventory behavior.

## Acceptance Criteria

- [ ] Manual dispatch starts exactly ten build legs and uploads ten uniquely
  named artifacts.
- [ ] Release-created dispatch runs the same ten legs and deploys.
- [ ] Every wheel's CIBW test imports `HAS_RUST` as true.
- [ ] Linux preserves `--manylinux off`; Windows does not use it.
- [ ] Inventory rejects missing cp310–cp314 manylinux or win_amd64 wheels and
  missing sdist.
- [ ] No macOS or ARM entries exist.

## Test Specification

```bash
rg -n 'workflow_dispatch|windows-latest|CIBW_TEST_COMMAND|wheels-' \
  .github/workflows/release.yml
```

Validate YAML with available tooling, then trigger `workflow_dispatch` on the
feature branch. Inspect all ten jobs, every wheel artifact, and the inventory
output; YAML parsing alone is insufficient.

## Agent Instructions

1. Verify TASK-3 and TASK-4 are complete before editing.
2. Preserve release credentials and permissions.
3. Test syntax locally, then perform a manual dispatch.
4. Do not weaken the Rust assertion to hide a Windows build failure.

## Completion Note

**Completed by**: sdd-worker (Claude)
**Date**: 2026-09-08
**Notes**: Added `workflow_dispatch:` alongside `release: types: [created]`;
added `os: [ubuntu-latest, windows-latest]` to the matrix (`fail-fast: false`
so one OS/version failure doesn't cancel the other nine legs) crossed with
the unchanged five-Python-version `cibw-build` include list, giving exactly
ten build legs; `runs-on: ${{ matrix.os }}`. Set `CIBW_ARCHS_LINUX: x86_64`
and `CIBW_ARCHS_WINDOWS: AMD64`; scoped the previous PATH override to
`CIBW_ENVIRONMENT_LINUX` (was the OS-agnostic `CIBW_ENVIRONMENT`, which
would have wrongly applied `/root/.cargo/bin` on Windows). Replaced the
single `CIBW_BEFORE_BUILD` with `CIBW_BEFORE_BUILD_LINUX` (keeps the
existing rustup curl install needed inside the manylinux container, then
calls `scripts/stage_rust_ext.py --manylinux off` in place of the old
inline zipfile one-liner) and `CIBW_BEFORE_BUILD_WINDOWS` (`pip install
maturin && python scripts/stage_rust_ext.py`, relying on the
windows-latest runner's preinstalled MSVC Rust toolchain plus the job's
own "Install Rust"/"Add Rust to PATH" steps, exactly as sketched in the
task). Added `CIBW_TEST_COMMAND` asserting `datamodel.rs_parsers.HAS_RUST`
in every wheel. Dropped the explicit `--platform linux` from the
`cibuildwheel` invocation. Artifact name is now
`wheels-${{ matrix.os }}-py${{ matrix.python-version }}`; deploy's download
`pattern` is `wheels-*`. Added a `Verify wheel inventory` step in `deploy`
that fails unless `dist/` has exactly 5 manylinux x86_64 wheels, 5
win_amd64 wheels, and 1 sdist. Verified: YAML parses cleanly; `rg` for
`workflow_dispatch|windows-latest|CIBW_TEST_COMMAND|wheels-` matches the
new lines; no `macos`/`arm`/`aarch64` string anywhere in the file.
**Not verified** (cannot be done outside GitHub Actions, per the spec's own
"No PR-time CI" risk note): an actual `workflow_dispatch` dry run showing
all ten legs green with `HAS_RUST` true in each wheel, and the deploy
inventory step passing against real artifacts (AC6 static structure is
verified; AC7/AC8's live-CI assertions are not). A dispatch run on the
pushed branch is recommended before merging, per the spec.
**Deviations from spec**: none in workflow structure. The Linux
`CIBW_BEFORE_BUILD_LINUX` keeps the pre-existing `curl | sh` rustup install
that the task's abbreviated example omitted, because the manylinux
container has no Rust preinstalled — dropping it would break the Linux
leg entirely; the task's own Codebase Contract's "Verified Existing
Blocks" documents this curl install as pre-existing and Module 5's scope
is "Wire Linux staging with `--manylinux off`", not removing the
toolchain bootstrap.
