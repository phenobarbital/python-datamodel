---
id: FEAT-001
title: Make uvloop an optional lazy-import speedup, finish the Python 3.14 build, add Windows wheels to release.yml
slug: new-infra-spec-uvloop-py314-windows
type: feature
mode: enrichment
status: review
source:
  kind: inline
  jira_key: null
  jira_url: null
  fetched_at: 2026-09-07
  summary_oneline: Make uvloop optional (lazy-import, auto-use), add Python 3.14 build, add Windows wheels in release.yml
overall_confidence: medium
base_branch: main
research_state: sdd/state/FEAT-001/
created: 2026-09-07
updated: 2026-09-07
---

# FEAT-001 — Optional uvloop, Python 3.14 build, Windows wheels

> **Mode**: enrichment
> **Confidence**: medium
> **Source**: `inline` (`/sdd-proposal new-infra-spec -- …`)
> **Audit**: [`sdd/state/FEAT-001/`](../state/FEAT-001/)

---

## 0. Origin

The original request, preserved verbatim. The full source is at
`sdd/state/FEAT-001/source.md`.

> python-datamodel requires uvloop as optional lazy-import, automatic usage if
> present but removing uvloop as hard dependency, add python 3.14 as new build
> and Windows compatibility on release.yml

**Initial signals** (extracted, not interpreted):
- Verbs: "requires … as optional", "removing … hard dependency", "add … new build", "Windows compatibility" → infrastructure/packaging feature, no bug language.
- Named entities: `uvloop`, Python 3.14, Windows, `release.yml`.
- Name hint: `new-infra-spec`.
- Acceptance criteria provided: no.

---

## 1. Synthesis Summary

The request bundles three packaging/CI changes. First, `uvloop` is a hard
runtime dependency on non-Windows platforms in `pyproject.toml`, yet it is
never imported anywhere in the package, so it is pure install weight; the fix
is to drop it from `dependencies`, expose it as an optional extra, and add a
small helper that installs the uvloop policy only when the module is
importable, mirroring the `HAS_RUST` fallback already used by
`datamodel/rs_parsers/__init__.py`. Second, Python 3.14 is already present in
the classifiers, the release matrix (`cp314-*`), and the locked toolchain
(Cython 3.2.9, PyO3 0.29); what remains is an end-to-end build verification
and a tighter Cython floor. Third, Windows is blocked by exactly two things:
GCC-only flags in `setup.py` (`-O3`, `-lstdc++`) and a Linux-only cibuildwheel
job in `.github/workflows/release.yml` whose Rust pre-build step assumes
bash, `/root/.cargo` and `.so` files. The Rust crate under `rust/` has no
platform-specific code. Recommendation: proceed straight to `/sdd-spec` with
three independent tasks.

---

## 2. Codebase Findings

> All entries are grounded in `sdd/state/FEAT-001/findings/`. Each cites the
> finding ID(s) that justify its inclusion.

### 2.1 Localization

| # | Path | Symbol | Lines | Role | Evidence |
|---|------|--------|-------|------|----------|
| 1 | `pyproject.toml` | `[project].dependencies` | 42-55 | remove uvloop hard dep; add `uvloop` extra | F001, F002 |
| 2 | `pyproject.toml` | `[build-system].requires` | 1-8 | raise `Cython>=3.0.11` to a 3.14-capable floor | F002, F011 |
| 3 | `datamodel/rs_parsers/__init__.py` | `HAS_RUST` | 8-30 | optional-import pattern to replicate for uvloop | F006 |
| 4 | `datamodel/validation.pyx` | asyncio usage | 7, 524 | only asyncio touchpoint; library creates no loop | F005 |
| 5 | `setup.py` | `COMPILE_ARGS`, `EXTRA_LINK_ARGS` | 12-13 | make flags compiler-conditional (MSVC vs GCC) | F003, F013 |
| 6 | `.github/workflows/release.yml` | `jobs.build` | 8-64 | OS matrix, per-OS `CIBW_BEFORE_BUILD`, `.pyd` extraction, artifact names | F004 |
| 7 | `.github/workflows/release.yml` | `jobs.deploy` | 66-116 | artifact download pattern must match new names | F004 |
| 8 | `Makefile` | `stage-rust`, `PYTHON_VERSION` | 8-9, 55-63 | copy `*.pyd` as well as `*.so`; 3.14 default | F007 |
| 9 | `rust/Cargo.toml` | `[workspace.dependencies].pyo3` | 1-12 | already 0.29 (3.14-capable); no change expected | F007 |
| 10 | `tests/test_valid_callables.py` | event loop usage | 38-40 | reference for a skip-if-missing uvloop test | F012 |
| 11 | `README.md` | install section | 22 | document the extra and Windows support | F015 |

### 2.2 Constraints Discovered

- **uvloop has no call site.** The package never imports uvloop nor
  configures an event loop; the only asyncio use is `iscoroutinefunction` in
  `validation.pyx`. *Implication*: "automatic usage" must be a **new,
  explicit helper**, not a change to existing code. *Evidence*: F001, F005

- **A library must not hijack the caller's loop policy.** datamodel is
  consumed by other asyncio applications (it depends on asyncpg). Setting a
  global event-loop policy at import time can break callers that already run
  a different loop. *Implication*: prefer an opt-in function (e.g.
  `install_uvloop()`), optionally gated by an env var; never auto-run at
  `import datamodel`. *Evidence*: F005, F002

- **GCC-only flags in setup.py.** `-O3` and `-lstdc++` are passed
  unconditionally to all ten Cython extensions (the three C++ ones link
  libstdc++). MSVC rejects `-lstdc++`. *Implication*: select flags per
  compiler (`/O2` and no libstdc++ link on `win32`). *Evidence*: F003, F013

- **Rust pre-build step is bash/Linux-specific.** `CIBW_BEFORE_BUILD` uses
  `curl | sh`, `/root/.cargo/bin`, `/tmp/_rs`, and extracts only `.so`.
  *Implication*: Windows needs its own `CIBW_BEFORE_BUILD_WINDOWS` (rustup is
  preinstalled on GitHub runners) and `.pyd` extraction; package-data already
  accepts `*.pyd`. *Evidence*: F004, F002, F007

- **Artifact naming collision.** Artifacts are named `wheels-py<version>`;
  a second OS in the matrix produces duplicate names. *Implication*: rename to
  `wheels-<os>-py<version>` and download with `wheels-*`. *Evidence*: F004

- **Python 3.14 is mostly done.** Classifier, `cp314-*` matrix entry, PyO3
  0.29 and Cython 3.2.9 are all in place. *Implication*: scope the 3.14 work
  as "finish and verify", not "add". *Evidence*: F002, F004, F007, F011

- **No PR-time CI.** `release.yml` is the only workflow, triggered on
  `release: created`. *Implication*: a broken Windows or 3.14 build is only
  discovered when a release is cut; add `workflow_dispatch` or a build-only
  PR workflow. *Evidence*: F014

- **Stale worktree.** `.claude/worktrees/migrate-uv-python314` is fully
  merged and 8 commits behind `main`. *Implication*: remove it before starting
  a new worktree. *Evidence*: F010

### 2.3 Recent History (Relevant)

| Commit | When | Author | Message | Touched files |
|--------|------|--------|---------|---------------|
| `9ab4e63` | 2026-08-28 | Jesus | security: fix all Dependabot vulnerabilities | `rust/Cargo.toml`, `rust/Cargo.lock`, `rust/rs_parsers/src/lib.rs` |
| `f90ea81` | 2026-08-07 | Jesus | fix: Makefile develop ordering and missing Cython/setuptools | `Makefile`, `pyproject.toml` |
| `3d2ee73` | 2026-08-07 | Jesus | ci: update release workflow for maturin + uv + Python 3.14 | `.github/workflows/release.yml` |
| `f6a863d` | 2026-08-07 | Jesus | build: update config for uv + maturin | `pyproject.toml`, `setup.py` |
| `a7fe091` | 2026-06-19 | Jesus Lara | fix: make uvloop a non-Windows-only dependency | `pyproject.toml` |

No commit has touched Windows CI or uvloop import behaviour. *Evidence*: F008

---

## 3. Probable Scope

### What's New

- **uvloop helper** (proposed `datamodel/libs/uvloop.py`) exposing
  `HAS_UVLOOP` and an explicit `install_uvloop()` that sets the uvloop policy
  only if the import succeeds and the platform is not Windows. No import-time
  side effect (U1).
- **`[project.optional-dependencies].uvloop` extra** (U2), keeping the
  `sys_platform != 'win32'` marker so the extra is a no-op on Windows.
- **`windows-latest` leg in the release matrix** producing cp310–cp314
  `win_amd64` wheels that **must** contain the Rust `_rs_parsers*.pyd`; the
  build job fails if maturin fails (U3). Matrix stays manylinux + Windows,
  no macOS (U4).
- **A skip-if-missing pytest** that exercises the helper.
- **Optional:** `workflow_dispatch` trigger on `release.yml` for dry runs.

### What Changes

- **`pyproject.toml`::`[project].dependencies`** — drop the uvloop line; add
  the extra; raise the Cython build floor. *Evidence*: F002, F011
- **`setup.py`::`COMPILE_ARGS` / `EXTRA_LINK_ARGS`** — `/O2` on MSVC and no
  `-lstdc++`; keep `-O3 -lstdc++` elsewhere. *Evidence*: F003
- **`.github/workflows/release.yml`::`jobs.build`** — matrix over os ×
  python; per-OS `CIBW_BEFORE_BUILD`; `.so`/`.pyd` extraction; `CIBW_ARCHS`
  per OS (`x86_64` / `AMD64`); OS-qualified artifact names. *Evidence*: F004
- **`.github/workflows/release.yml`::`jobs.deploy`** — download pattern
  `wheels-*`; sanity check that `win_amd64` wheels exist. *Evidence*: F004
- **`Makefile`::`stage-rust`** — copy `_rs_parsers*.so` **and**
  `_rs_parsers*.pyd`. *Evidence*: F007
- **`README.md` / `INSTALL.md` / `CHANGELOG.md`** — document
  `pip install python-datamodel[uvloop]`, Windows wheels and 3.14 support;
  fix the stale `setuptools-rust` mention. *Evidence*: F015

### What's Untouched (Non-Goals)

- macOS wheels: explicitly out of scope; release matrix is manylinux x86_64 +
  win_amd64 only (U4).
- Shipping Windows wheels without the Rust extension: rejected (U3). The
  `HAS_RUST=False` fallback stays only as a runtime safety net for source
  installs.
- Auto-installing uvloop at `import datamodel` time: rejected (U1).
- Removing other heavy dependencies (numpy, asyncpg, psycopg).
- Rewriting `tox.ini` or adding a full PR test matrix (recommended, but a
  separate change).

### Patterns to Follow

- Optional native import behind a boolean flag, as in
  `datamodel/rs_parsers/__init__.py`. *Evidence*: F006
- Environment markers already used for uvloop (`sys_platform != 'win32'`).
  *Evidence*: F002
- cibuildwheel matrix `include` blocks as in the current `release.yml`.
  *Evidence*: F004

---

## 4. Confidence Map

| ID | Claim | Confidence | Evidence |
|----|-------|------------|----------|
| C1 | uvloop is declared but never imported; removing it is safe for the library and its tests | high | F001, F005, F012 |
| C2 | Python 3.14 is already wired into classifiers, release matrix and locked toolchain; remaining work is verification | high | F002, F004, F007, F011 |
| C3 | The Windows blocker for the Cython layer is limited to the `-O3`/`-lstdc++` flags in `setup.py` | high | F003, F013 |
| C4 | The Rust extension builds on `windows-latest` with MSVC without source changes | medium | F007 |
| C5 | `release.yml` needs an OS matrix, a Windows pre-build step, `.pyd` handling and OS-qualified artifact names | high | F004, F002 |
| C6 | "Automatic usage" belongs in an opt-in helper, not an import-time side effect | medium | F005, F002 |
| C7 | All ten Cython extensions compile under MSVC once flags are fixed (no POSIX-only C calls) | low | F013 |
| C8 | The stale `migrate-uv-python314` worktree can be deleted safely | high | F010 |

**Overall confidence: medium.** Localization and the CI facts are directly
cited, and all four design unknowns were resolved by the user (§5). Still
bounded to medium because MSVC compilation of the Cython sources (C7) and the
Rust `.pyd` build on `windows-latest` (C4, now a hard requirement) are
untested.

---

## 5. Open Questions

### Resolved (during proposal phase, 2026-09-07)

- [x] **U1: Where should "automatic usage" of uvloop take effect?** — *Resolved*: an
  explicit `install_uvloop()` helper that callers invoke; no import-time side effect.
  *Resolves claims*: C6

- [x] **U2: Should uvloop be exposed as a pip extra, and under what name?** — *Resolved*:
  yes, `python-datamodel[uvloop]`.
  *Resolves claims*: C1

- [x] **U3: Must the Rust `.pyd` ship in Windows wheels?** — *Resolved*: yes, ship the
  Rust extension for Windows; the release job must fail if the Rust build fails.
  *Resolves claims*: C4 (now a hard requirement to verify on `windows-latest`)

- [x] **U4: Add macOS wheels while the matrix is being restructured?** — *Resolved*:
  Windows only. The release matrix stays manylinux x86_64 + win_amd64. No macOS
  wheels exist today (release.yml is Linux-only, F004), so nothing needs removing.

### Unresolved (defer to spec / implementation)

_None._

---

## 6. Recommended Next Step

**`/sdd-spec FEAT-001`** — *Rationale*: localization is high-confidence and
the work decomposes cleanly into three independent tasks (uvloop extra +
helper; MSVC flags + Windows CI leg; 3.14 verification). No architectural
fork warrants a brainstorm; the only open design question (U1) can be fixed
in the spec.

### Alternatives

- **`/sdd-brainstorm FEAT-001`** — if you want to compare uvloop integration
  strategies (helper vs env var vs import-time) before committing.
- **`/sdd-task FEAT-001`** — not recommended: three separate surfaces
  (packaging, build flags, CI) are too broad for a single task.
- **Manual review** — not needed; research was not truncated.

---

## 7. Research Audit

| Artifact | Path |
|----------|------|
| State checkpoints | `sdd/state/FEAT-001/state.json` |
| Source (raw) | `sdd/state/FEAT-001/source.md` |
| Research plan | `sdd/state/FEAT-001/research_plan.json` |
| Findings (digests) | `sdd/state/FEAT-001/findings/F001-*.md` … `F015-*.md` |
| Synthesis (JSON) | `sdd/state/FEAT-001/synthesis.json` |

**Budget consumed** (`default` profile):
- Files read: 16 / 40
- Grep calls: 14 / 25
- Git calls: 8 / 10
- Wall time: ~240s / 300s
- Truncated: **no**

**Mode determination**: `auto` → resolved to `enrichment` (infrastructure
additions, no failure/negation language in source).

**Gates**: the session ran unattended, so the plan gate and review gate were
auto-approved. The Q&A gate was completed afterwards: all four unknowns were
answered by the user on 2026-09-07 (§5).

---

## 8. Provenance

| Field | Value |
|-------|-------|
| Generated by | `/sdd-proposal v1.0` |
| Synthesis prompt | `sdd/templates/synthesis.prompt.md v1.0` |
| Plan prompt | `sdd/templates/research_plan.prompt.md v1.0` |
| Schema versions | state=1.0, synthesis=1.0, research_plan=1.0 |
| Operator | Claude (autonomous), on behalf of Jesus |
