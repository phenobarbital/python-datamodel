---
id: F002
query_id: Q002
type: read
intent: Inspect declared dependencies, python_requires, classifiers, package-data
executed_at: 2026-09-07T21:30:00Z
duration_ms: 300
parent_id: null
depth: 0
---

# F002 — pyproject.toml: setuptools backend, Cython pin, 3.14 classifier already present

## Summary

setuptools is the build backend (`Cython>=3.0.11` in build requires). Python
3.14 is already listed as a classifier. Runtime deps are heavy (numpy,
asyncpg, psycopg[binary], msgspec, orjson, uvloop). There is no
`[project.optional-dependencies]` extra for uvloop; only a `dev` extra
exists. `rs_parsers` package-data already lists `*.pyd` alongside `*.so`,
so Windows Rust binaries would be packaged if staged.

## Citations

- path: `pyproject.toml`
  lines: 1-8
  symbol: `[build-system]`
  excerpt: |
    requires = [
        "setuptools>=74.0.0",
        "setuptools_scm[toml]>=8.0",
        "Cython>=3.0.11",
        "wheel>=0.44.0",
    ]
    build-backend = "setuptools.build_meta"

- path: `pyproject.toml`
  lines: 19,27-31
  symbol: `requires-python`, `classifiers`
  excerpt: |
    requires-python = ">=3.10.0"
    "Programming Language :: Python :: 3.13",
    "Programming Language :: Python :: 3.14",

- path: `pyproject.toml`
  lines: 42-55
  symbol: `[project].dependencies`
  excerpt: |
    dependencies = [
        "numpy>=1.26.4",
        "uvloop>=0.21.0; sys_platform != 'win32'",
        "faust-cchardet>=2.1.19",
        ...
        "msgspec>=0.19.0",
    ]

- path: `pyproject.toml`
  lines: 57-68
  symbol: `[project.optional-dependencies].dev`
  excerpt: |
    dev = [
        "pytest>=7.0.0",
        "pytest-asyncio>=0.21.0",
        ...
        "maturin>=1.7,<2.0",

- path: `pyproject.toml`
  lines: 81-92
  symbol: `[tool.setuptools.package-data]`
  excerpt: |
    "datamodel.rs_parsers" = ["*.so", "*.pyd"]

- path: `pyproject.toml`
  lines: 111-122
  symbol: `[tool.pytest.ini_options]`
  excerpt: |
    filterwarnings = [
        "error",
    ]
