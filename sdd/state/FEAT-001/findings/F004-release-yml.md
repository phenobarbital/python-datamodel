---
id: F004
query_id: Q004
type: read
intent: Inspect release workflow: OS matrix, Python matrix, cibuildwheel config
executed_at: 2026-09-07T21:30:00Z
duration_ms: 300
parent_id: null
depth: 0
---

# F004 — release.yml: Linux-only cibuildwheel, cp314 already in the matrix

## Summary

The `build` job runs on `ubuntu-latest` only, with `cibuildwheel --platform
linux` and `CIBW_ARCHS: x86_64`. The Python matrix already contains `"3.14"`
with `cibw-build: "cp314-*"`, so "add Python 3.14" is already partially done
at the workflow level. `CIBW_BEFORE_BUILD` is a Linux shell one-liner that
installs rustup via `curl | sh`, hardcodes `/root/.cargo/bin` and `/tmp/_rs`,
builds the Rust wheel with maturin, and extracts only files ending in `.so`
into `datamodel/rs_parsers/`. Every one of those steps breaks on Windows
(`.pyd`, no `/root`, no `curl | sh`). The `deploy` job merges `wheels-py*`
artifacts, builds an sdist, and pushes wheels plus sdist to PyPI with twine
(lines 113-116) using the `PYTHON_DATAMODEL_PYPI_API_TOKEN` secret.

## Citations

- path: `.github/workflows/release.yml`
  lines: 8-12
  symbol: `jobs.build`
  excerpt: |
    build:
      runs-on: ubuntu-latest
      strategy:
        matrix:
          python-version: ["3.10", "3.11", "3.12", "3.13", "3.14"]

- path: `.github/workflows/release.yml`
  lines: 22-23
  symbol: matrix include cp314
  excerpt: |
    - python-version: "3.14"
      cibw-build: "cp314-*"

- path: `.github/workflows/release.yml`
  lines: 44-58
  symbol: `Build wheels` step
  excerpt: |
    CIBW_ARCHS: x86_64
    CIBW_BEFORE_BUILD: >-
      curl https://sh.rustup.rs -sSf | sh -s -- -y &&
      export PATH=/root/.cargo/bin:$PATH &&
      ...
      python3 -c "...so=[n for n in zf.namelist() if n.endswith('.so') and '_rs_parsers' in n][0];zf.extract(so,'/tmp/_rs');..."
    CIBW_ENVIRONMENT: "PATH=/root/.cargo/bin:$PATH"
    CIBW_BUILD: ${{ matrix.cibw-build }}
    run: |
      cibuildwheel --platform linux --output-dir dist

- path: `.github/workflows/release.yml`
  lines: 60-64
  symbol: `Upload wheel artifacts`
  excerpt: |
    name: wheels-py${{ matrix.python-version }}
    path: dist/*.whl

- path: `.github/workflows/release.yml`
  lines: 66-69,79-84
  symbol: `jobs.deploy`
  excerpt: |
    deploy:
      needs: build
      runs-on: ubuntu-latest
      ...
      pattern: wheels-py*
      merge-multiple: true

- path: `.github/workflows/release.yml`
  lines: 113-116
  symbol: `Publish wheels and sdist to PyPI` step
  excerpt: |
    (installs twine via `uv tool install`, then pushes dist/*.whl and
     dist/*.tar.gz to PyPI with the __token__ user and the repo secret)

## Notes

Artifact names are keyed only by Python version (`wheels-py3.12`); adding a
Windows runner to the same matrix would collide on artifact names unless the
OS is added to the name.
