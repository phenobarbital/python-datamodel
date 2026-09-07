---
id: F005
query_id: Q005
type: git_log
executed_at: 2026-09-08
depth: 0
---

# Baseline provenance

Current HEAD: `dbaac838117c615c17b7c12460ba6f3e21d5232e`, branch dev, ahead of origin/dev by four commits when inspected.

Pre-existing untracked files/directories: `.claude/worktrees/feat-FEAT-001-new-infra-spec-uvloop-py314-windows/`, `datamodel/converters_lt.pyx`, `examples/rust_benchmark.py`. These were not modified.

## Citations

Relevant git log for `datamodel/abstract.py`, `datamodel/converters.pyx`, `rust/rs_parsers`:

- `9ab4e63`, 2026-08-28: security: fix all Dependabot vulnerabilities.
- `cd7db78`, 2026-08-08: fix: resolve test failures across suite — metaclass cache, validation, and imports.
- `be9c058`, 2026-08-07: fix: correct maturin mixed-project layout for rs_parsers.
- `d9b808c`, 2026-08-07: refactor: move Rust code to rust/ directory with Cargo workspace.
- `c9b733f`, 2025-04-08: fix on nested lists.

`setup.py:15` builds Cython extensions with optimization flags; `pyproject.toml:19` declares Python >=3.10. Existing FEAT-001 artifacts concern infrastructure/platform support. Company deployed versions and compatibility platforms remain unspecified.
