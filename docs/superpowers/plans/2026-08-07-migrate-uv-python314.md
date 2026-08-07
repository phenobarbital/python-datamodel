# Migrate python-datamodel to uv + Python 3.14 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Migrate python-datamodel to uv package management, upgrade PyO3 for Python 3.14 support, and restructure Rust extensions to follow the querysource maturin pattern.

**Architecture:** Keep setuptools as the build backend for Cython extensions. Move Rust code to `rust/` with a Cargo workspace and separate maturin config (following querysource's dual-build strategy). Use uv for dependency management, lockfile, virtualenvs, and CI. The Rust `.so` is built by maturin, staged into the source tree, then bundled by setuptools into the final wheel.

**Tech Stack:** uv, setuptools, maturin, Cython 3.x, PyO3 0.24, cibuildwheel, GitHub Actions

## Global Constraints

- Python >=3.10, supports 3.10/3.11/3.12/3.13/3.14
- Rust edition 2021, minimum 1.84.0
- PyO3 0.24 (first version with Python 3.14 support; querysource uses this)
- uv for all dependency management (no raw pip)
- `link-mode = "copy"` in `[tool.uv]` (prevents native extension hardlink issues)
- setuptools remains the build backend (handles Cython); maturin is a dev/CI tool only
- Only `rs_parsers` is actively built; `rs_core` and `rs_validators` live in `rust/` for future work
- Template: `/home/jesuslara/proyectos/querysource/` (proven working pattern)

---

### Task 1: Restructure Rust Code into `rust/` Directory

**Files:**
- Create: `rust/Cargo.toml` (workspace root)
- Create: `rust/rs_parsers/Cargo.toml` (crate config, PyO3 0.24)
- Create: `rust/rs_parsers/pyproject.toml` (maturin config)
- Move: `datamodel/rs_parsers/src/lib.rs` → `rust/rs_parsers/src/lib.rs` (with edits)
- Move: `datamodel/rs_core/Cargo.toml` → `rust/rs_core/Cargo.toml`
- Move: `datamodel/rs_core/src/lib.rs` → `rust/rs_core/src/lib.rs`
- Move: `datamodel/rs_validators/Cargo.toml` → `rust/rs_validators/Cargo.toml`
- Move: `datamodel/rs_validators/src/lib.rs` → `rust/rs_validators/src/lib.rs`
- Delete: `Cargo.toml` (root workspace — replaced by `rust/Cargo.toml`)
- Delete: `Cargo.lock` (root — will be regenerated under `rust/`)
- Delete: `src/lib.rs` (root — empty placeholder)

**Interfaces:**
- Produces: Rust workspace at `rust/` with `rs_parsers` as the only active member
- Produces: maturin-buildable crate producing `datamodel.rs_parsers._rs_parsers` module
- Produces: compiled `_rs_parsers.cpython-3XX.so` via `maturin develop`

- [ ] **Step 1: Create the `rust/` directory structure**

```bash
mkdir -p rust/rs_parsers/src
mkdir -p rust/rs_core/src
mkdir -p rust/rs_validators/src
```

- [ ] **Step 2: Create `rust/Cargo.toml` (workspace root)**

```toml
[workspace]
members = [
    "rs_parsers",
]
resolver = "2"
edition = "2021"

[workspace.dependencies]
pyo3 = { version = "0.24", features = ["extension-module"] }
rayon = "1.10"
```

Note: `rs_core` and `rs_validators` are NOT in workspace members — they use the old PyO3 API and need separate upgrading. They live under `rust/` for future work.

- [ ] **Step 3: Create `rust/rs_parsers/Cargo.toml`**

```toml
[package]
name = "rs_parsers"
version = "0.1.0"
edition = "2021"
authors = ["Jesus Lara <jesuslarag@gmail.com>"]
description = "Parallel DataModel Parser and validator using Rust"
license = "MIT"
repository = "https://github.com/phenobarbital/python-datamodel"

[lib]
name = "_rs_parsers"
crate-type = ["cdylib"]

[dependencies]
pyo3 = { workspace = true }
rayon = { workspace = true }
chrono = "0.4.39"
speedate = "0.15.0"
uuid = "1.11.0"
fastuuid = "0.3.0"
rust_decimal = "1.36"
rust_decimal_macros = "1.36"

[features]
default = ["extension-module"]
extension-module = ["pyo3/extension-module"]

[profile.release]
opt-level = 3
lto = true
codegen-units = 1
```

Key differences from old config:
- `[lib] name` is `_rs_parsers` (underscore prefix, matching querysource's `_qs_parsers`)
- Uses workspace dependency for `pyo3` (0.24)
- Removed `generate-import-lib` feature (only needed by setuptools-rust on Windows)
- Added release profile optimizations
- Feature gate for `extension-module` (allows `cargo test --no-default-features`)

- [ ] **Step 4: Create `rust/rs_parsers/pyproject.toml` (maturin config)**

```toml
[build-system]
requires = ["maturin>=1.7,<2.0"]
build-backend = "maturin"

[project]
name = "rs_parsers"
version = "0.1.0"
requires-python = ">=3.10"

[tool.maturin]
module-name = "datamodel.rs_parsers._rs_parsers"
bindings = "pyo3"
features = ["pyo3/extension-module"]
```

- [ ] **Step 5: Move and update `rust/rs_parsers/src/lib.rs`**

Copy `datamodel/rs_parsers/src/lib.rs` to `rust/rs_parsers/src/lib.rs`, then apply these changes:

1. Rename the module function from `rs_parsers` to `_rs_parsers`:

```rust
// OLD (line 573-574):
#[pymodule]
fn rs_parsers(_py: Python, m: &Bound<'_, PyModule>) -> PyResult<()> {

// NEW:
#[pymodule]
fn _rs_parsers(_py: Python, m: &Bound<'_, PyModule>) -> PyResult<()> {
```

2. Remove `PyTypeInfo` import (line 3) — not used in this file:

```rust
// OLD (line 3):
use pyo3::PyTypeInfo;

// Remove this line entirely
```

3. Remove `wrap_pyfunction` import (line 4) — PyO3 0.24 re-exports it from prelude:

```rust
// OLD (line 4):
use pyo3::wrap_pyfunction;

// Remove this line — wrap_pyfunction! is in pyo3::prelude::*
```

The rest of the code uses the modern `Bound` API and should compile with PyO3 0.24 as-is.

- [ ] **Step 6: Move rs_core and rs_validators**

```bash
# Move rs_core
cp datamodel/rs_core/Cargo.toml rust/rs_core/Cargo.toml
cp datamodel/rs_core/src/lib.rs rust/rs_core/src/lib.rs

# Move rs_validators
cp datamodel/rs_validators/Cargo.toml rust/rs_validators/Cargo.toml
cp datamodel/rs_validators/src/lib.rs rust/rs_validators/src/lib.rs
```

Do NOT add these to the workspace yet — `rs_core` uses old PyO3 GIL-ref API and needs separate migration. They are stored here for future development.

- [ ] **Step 7: Delete old Rust artifacts from project root**

```bash
rm Cargo.toml
rm Cargo.lock
rm -rf src/
rm -rf datamodel/rs_parsers/Cargo.toml datamodel/rs_parsers/src/
rm -rf datamodel/rs_core/
rm -rf datamodel/rs_validators/
```

- [ ] **Step 8: Verify Rust compilation**

```bash
cd rust && cargo check --manifest-path rs_parsers/Cargo.toml && cd ..
```

If there are PyO3 0.24 compilation errors, fix them. Expected issues:
- `PyList::new()` might need `?` (already has it in current code — should be fine)
- `type_object()` may emit deprecation warnings — fix if they become errors

- [ ] **Step 9: Commit**

```bash
git add rust/ 
git add -u  # stages deletions
git commit -m "refactor: move Rust code to rust/ directory with Cargo workspace

- Move rs_parsers, rs_core, rs_validators to rust/
- Upgrade PyO3 from 0.23.3 to 0.24
- Add maturin config for rs_parsers
- Only rs_parsers in workspace (rs_core/rs_validators for future)
- Rename module to _rs_parsers (maturin convention)"
```

---

### Task 2: Create Python Glue Module for rs_parsers

**Files:**
- Create: `datamodel/rs_parsers/__init__.py`

**Interfaces:**
- Consumes: `_rs_parsers` compiled Rust module (from Task 1)
- Produces: `datamodel.rs_parsers` Python package with `HAS_RUST` flag and re-exported functions
- Produces: transparent compatibility — `import datamodel.rs_parsers as rc; rc.to_date(...)` still works

- [ ] **Step 1: Create `datamodel/rs_parsers/__init__.py`**

This is the glue module following querysource's `qs_parsers/__init__.py` pattern:

```python
"""Rust-accelerated parsers for python-datamodel.

Provides type conversion functions (to_date, to_datetime, to_integer, etc.)
implemented in Rust via PyO3 for performance. Falls back gracefully if the
Rust extension is not compiled.
"""

HAS_RUST = False

try:
    from ._rs_parsers import (  # type: ignore[import-not-found]
        to_string,
        strtobool,
        to_boolean,
        to_date,
        to_datetime,
        to_timestamp,
        slugify_camelcase,
        to_uuid_str,
        to_uuid_obj,
        to_uuid,
        to_integer,
        to_float,
        to_decimal,
        to_list,
    )

    HAS_RUST = True
except ImportError:
    pass
```

The `converters.pyx` import (`import datamodel.rs_parsers as rc`) continues working transparently. When the Rust extension is compiled and installed, `rc.to_date(...)` calls the Rust implementation.

- [ ] **Step 2: Verify import compatibility**

The existing `converters.pyx` line 36 does:
```python
import datamodel.rs_parsers as rc
```
Then uses: `rc.to_timestamp()`, `rc.to_date()`, `rc.to_datetime()`, `rc.to_list()`

With the new `__init__.py` re-exporting these names, this import path is preserved exactly.

- [ ] **Step 3: Commit**

```bash
git add datamodel/rs_parsers/__init__.py
git commit -m "feat: add Python glue module for rs_parsers

Follows querysource's qs_parsers pattern: __init__.py re-exports
all functions from the compiled Rust _rs_parsers extension and
sets HAS_RUST=True/False for diagnostics."
```

---

### Task 3: Update Build Configuration

**Files:**
- Modify: `pyproject.toml`
- Modify: `setup.py`
- Modify: `MANIFEST.in`

**Interfaces:**
- Consumes: Rust workspace at `rust/` (from Task 1)
- Consumes: `datamodel/rs_parsers/__init__.py` glue module (from Task 2)
- Produces: Working build config that compiles Cython extensions only (Rust handled separately by maturin)
- Produces: uv-compatible project with lockfile support

- [ ] **Step 1: Update `pyproject.toml`**

Replace the entire file with:

```toml
[build-system]
requires = [
    "setuptools>=74.0.0",
    "setuptools_scm[toml]>=8.0",
    "Cython>=3.0.11",
    "wheel>=0.44.0",
]
build-backend = "setuptools.build_meta"

[project]
name = "python-datamodel"
dynamic = ["version"]
description = "simple library based on python +3.10 to use Dataclass-syntax for interacting with Data"
authors = [
    {name = "Jesus Lara", email = "jesuslarag@gmail.com"}
]
readme = "README.md"
license = {text = "BSD"}
requires-python = ">=3.10.0"
keywords = ["asyncio", "dataclass", "dataclasses", "data models"]
classifiers = [
    "Development Status :: 4 - Beta",
    "Intended Audience :: Developers",
    "Intended Audience :: System Administrators",
    "Topic :: Software Development :: Build Tools",
    "Topic :: Software Development :: Libraries :: Python Modules",
    "Programming Language :: Python :: 3",
    "Programming Language :: Python :: 3 :: Only",
    "Programming Language :: Python :: 3.10",
    "Programming Language :: Python :: 3.11",
    "Programming Language :: Python :: 3.12",
    "Programming Language :: Python :: 3.13",
    "Programming Language :: Python :: 3.14",
    "Framework :: AsyncIO",
    "License :: OSI Approved :: BSD License",
    "Operating System :: OS Independent",
    "Topic :: System :: Systems Administration",
    "Topic :: Utilities",
    "Environment :: Web Environment",
]

dependencies = [
    "numpy>=1.26.4",
    "uvloop>=0.21.0; sys_platform != 'win32'",
    "faust-cchardet>=2.1.19",
    "ciso8601>=2.3.2",
    "objectpath>=0.6.1",
    "orjson>=3.10.11",
    "typing_extensions>=4.9.0",
    "asyncpg>=0.29.0",
    "python-dateutil>=2.8.2",
    "python-slugify>=8.0.1",
    "psycopg[binary]>=3.2.0",
    "msgspec>=0.19.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=7.0.0",
    "pytest-asyncio>=0.21.0",
    "coverage>=7.0",
    "ruff>=0.6.0",
    "mypy>=1.0",
    "maturin>=1.7,<2.0",
]

[project.urls]
Homepage = "https://github.com/phenobarbital/python-datamodel"
Source = "https://github.com/phenobarbital/python-datamodel"
Tracker = "https://github.com/phenobarbital/python-datamodel/issues"
Documentation = "https://datamodel.readthedocs.io/en/latest/"
Funding = "https://paypal.me/phenobarbital"
"Say Thanks!" = "https://saythanks.io/to/phenobarbital"

[tool.setuptools]
license-files = ["LICENSE"]
packages = ["datamodel"]
include-package-data = true

[tool.setuptools.package-data]
"datamodel.fields" = ["*.pyx"]
"datamodel.converters" = ["*.pyx"]
"datamodel.validation" = ["*.pyx"]
"datamodel.exceptions" = ["*.pxd", "*.pyx"]
"datamodel.functions" = ["*.pxd", "*.pyx"]
"datamodel.libs.mapping" = ["*.pxd", "*.pyx"]
"datamodel.typedefs.singleton" = ["*.pxd", "*.pyx"]
"datamodel.typedefs.types" = ["*.pxd", "*.pyx"]
"datamodel.parsers.json" = ["*.pyx"]
"datamodel.rs_parsers" = ["*.so", "*.pyd"]

[tool.setuptools.exclude-package-data]
"*" = ["*.c", "*.cpp"]

[tool.setuptools.dynamic]
version = {attr = "datamodel.version.__version__"}

[tool.pytest.ini_options]
addopts = [
    "--strict-config",
    "--strict-markers",
]
testpaths = ["tests"]
python_files = "test_*.py"
python_functions = "test_*"
log_cli = true
log_cli_level = "DEBUG"
log_cli_format = "%(asctime)s [%(levelname)8s] %(message)s (%(filename)s:%(lineno)s)"
log_cli_date_format = "%Y-%m-%d %H:%M:%S"
filterwarnings = [
    "error",
]
markers = [
    "asyncio: mark a test as a coroutine that should be run by pytest-asyncio",
]

[tool.black]
line-length = 120
include = '\.pyi?$'
exclude = '''
/(
    \.git
  | \.hg
  | \.mypy_cache
  | \.tox
  | \.venv
  | _build
  | buck-out
  | build
  | dist
)/
'''

# ---------------------------------------------------------------------------
# uv install settings
# ---------------------------------------------------------------------------
[tool.uv]
link-mode = "copy"
```

Key changes:
- Removed `setuptools-rust` and `pip` from `[build-system] requires`
- Removed `asyncio==3.4.3` (stdlib since Python 3.4)
- Replaced `psycopg2-binary==2.9.10` with `psycopg[binary]>=3.2.0`
- Relaxed all hard-pinned versions to `>=` floors
- Added Python 3.14 classifier
- Added `[project.optional-dependencies] dev` group
- Added `"datamodel.rs_parsers" = ["*.so", "*.pyd"]` to package-data
- Added `[tool.setuptools.exclude-package-data]` for Cython build artifacts
- Added `[tool.uv] link-mode = "copy"` (prevents native extension hardlink issues)

- [ ] **Step 2: Update `setup.py` (remove Rust, keep Cython)**

```python
#!/usr/bin/env python
"""DataModels.

    Dataclass Reimplementation with true inheritance (without decorators.)
See:
https://github.com/phenobarbital/DataModel
"""

from Cython.Build import cythonize
from setuptools import Extension, setup

COMPILE_ARGS = ["-O3"]
EXTRA_LINK_ARGS = ["-lstdc++"]

extensions = [
    Extension(
        name='datamodel.fields',
        sources=['datamodel/fields.pyx'],
        extra_compile_args=COMPILE_ARGS,
        extra_link_args=EXTRA_LINK_ARGS,
        language="c++"
    ),
    Extension(
        name='datamodel.converters',
        sources=['datamodel/converters.pyx'],
        extra_compile_args=COMPILE_ARGS,
        language="c",
    ),
    Extension(
        name='datamodel.validation',
        sources=['datamodel/validation.pyx'],
        extra_compile_args=COMPILE_ARGS,
        language="c"
    ),
    Extension(
        name='datamodel.functions',
        sources=['datamodel/functions.pyx'],
        extra_compile_args=COMPILE_ARGS,
        extra_link_args=EXTRA_LINK_ARGS,
        language="c++"
    ),
    Extension(
        name='datamodel.exceptions',
        sources=['datamodel/exceptions.pyx'],
        extra_compile_args=COMPILE_ARGS,
        language="c"
    ),
    Extension(
        name='datamodel.types',
        sources=['datamodel/types.pyx'],
        extra_compile_args=COMPILE_ARGS,
        language="c"
    ),
    Extension(
        name='datamodel.parsers.json',
        sources=['datamodel/parsers/json.pyx'],
        extra_compile_args=COMPILE_ARGS,
        extra_link_args=EXTRA_LINK_ARGS,
        language="c++"
    ),
    Extension(
        name='datamodel.libs.mapping',
        sources=['datamodel/libs/mapping.pyx'],
        extra_compile_args=COMPILE_ARGS,
        language="c"
    ),
    Extension(
        name='datamodel.typedefs.singleton',
        sources=['datamodel/typedefs/singleton.pyx'],
        extra_compile_args=COMPILE_ARGS,
        language="c"
    ),
    Extension(
        name='datamodel.typedefs.types',
        sources=['datamodel/typedefs/types.pyx'],
        extra_compile_args=COMPILE_ARGS,
        language="c"
    ),
]

setup(
    ext_modules=cythonize(extensions, annotate=True),
    package_data={
        "datamodel.rs_parsers": ["*.so", "*.pyd"],
    },
    zip_safe=False,
)
```

Changes: removed `from setuptools_rust import RustExtension`, removed `rust_extensions` list and `rust_extensions=rust_extensions` from `setup()`. Added `package_data` for rs_parsers compiled extensions.

- [ ] **Step 3: Update `MANIFEST.in`**

```
include LICENSE
include CHANGELOG.md
include CONTRIBUTING.md
include SECURITY.md
include README.md
include Makefile

graft datamodel
graft tests

recursive-include datamodel *.pxd *.pyx

global-exclude *.pyc
prune docs
prune settings
prune env
prune examples
prune bin
prune rust/rs_parsers/target
prune rust/rs_core/target
prune rust/rs_validators/target
recursive-exclude */__pycache__
prune */__pycache__
```

Changes: removed `recursive-include datamodel/rs_parsers *` (Rust source no longer under `datamodel/`). Added prune rules for `rust/*/target`.

- [ ] **Step 4: Commit**

```bash
git add pyproject.toml setup.py MANIFEST.in
git commit -m "build: update config for uv + maturin

- Remove setuptools-rust (Rust now built via maturin separately)
- Replace psycopg2-binary with psycopg[binary] 3.x
- Remove asyncio==3.4.3 (stdlib)
- Relax hard-pinned dependency versions
- Add Python 3.14 classifier
- Add [tool.uv] config with link-mode=copy
- Add dev optional dependencies
- Update MANIFEST.in for new Rust directory"
```

---

### Task 4: Rewrite Makefile with uv

**Files:**
- Modify: `Makefile`

**Interfaces:**
- Consumes: `rust/rs_parsers/Cargo.toml` for maturin builds (from Task 1)
- Produces: `make venv`, `make install`, `make develop`, `make build`, `make build-rust`, `make stage-rust`, `make build-inplace`, `make test`, `make clean`

- [ ] **Step 1: Rewrite `Makefile`**

```makefile
# python-datamodel Makefile
# Follows querysource's dual-build pattern: maturin (Rust) + setuptools (Cython)

.PHONY: venv install develop build build-rust stage-rust build-inplace \
        format lint test clean distclean lock sync release help

# Python version to use
PYTHON_VERSION := 3.12

# maturin is a dev dependency — run via the venv so it always targets
# the project virtualenv. Do NOT use `uv run --with maturin` (creates
# an ephemeral environment and installs the extension there instead).
MATURIN := .venv/bin/maturin

# Rust wheel staging directory
RUST_WHEEL_OUT := rust/target/wheels

# ---- Environment ----

venv:
	uv venv --python $(PYTHON_VERSION) .venv
	@echo 'run `source .venv/bin/activate` to start develop DataModel'

lock:
	uv lock

sync:
	uv sync --frozen --extra dev

# ---- Install ----

install: build-rust
	uv sync --frozen --no-dev

develop: build-rust
	uv sync --frozen --extra dev
	$(MAKE) build-inplace

develop-fast:
	uv pip install -e .[dev]

# ---- Rust ----

# Build and install Rust extension into the venv (for development)
build-rust:
	$(MATURIN) develop --release --manifest-path rust/rs_parsers/Cargo.toml

# Stage the compiled Rust extension (.so) INTO the source tree so that
# `uv build` (setuptools backend) bundles it into the wheel. setuptools
# only packages a pre-existing artifact via package-data; it never
# invokes maturin. `maturin develop` installs into site-packages, NOT
# the source tree, so the wheel would otherwise ship without the Rust
# extension.
stage-rust:
	$(MATURIN) build --release -i python --manifest-path rust/rs_parsers/Cargo.toml --out $(RUST_WHEEL_OUT)
	@whl=$$(ls -t $(RUST_WHEEL_OUT)/rs_parsers-*.whl | head -1); \
	  test -n "$$whl" || { echo "ERROR: maturin produced no wheel in $(RUST_WHEEL_OUT)"; exit 1; }; \
	  echo "Staging Rust extension from $$whl"; \
	  tmp=$$(mktemp -d); \
	  unzip -o -q "$$whl" -d "$$tmp"; \
	  find "$$tmp" -name '_rs_parsers*.so' -exec cp {} datamodel/rs_parsers/ \; ; \
	  rm -rf "$$tmp"; \
	  ls -la datamodel/rs_parsers/_rs_parsers*.so

# ---- Cython ----

build-cython:
	@echo "Compiling Cython extensions..."
	python setup.py build_ext

build-inplace:
	@echo "Building Cython extensions in place..."
	python setup.py build_ext --inplace

# ---- Build ----

# Full build: clean → stage Rust → build wheel with uv
build: clean
	$(MAKE) stage-rust
	@echo "Building package with uv..."
	uv build

release: lint test clean
	uv build
	uv publish

# ---- Quality ----

format:
	uv run black datamodel

lint:
	uv run pylint --rcfile .pylintrc datamodel/*.py
	uv run black --check datamodel

test:
	uv run pytest tests/ -v

# ---- Maintenance ----

update:
	uv lock --upgrade

info:
	uv tree

clean:
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info/
	find . -name "*.pyc" -delete
	find . -name "*.pyo" -delete
	find datamodel -name "*.so" -delete
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	@echo "Clean complete."

distclean: clean
	rm -rf .venv

# ---- Version ----

bump-patch:
	@python -c "import re; \
	content = open('datamodel/version.py').read(); \
	version = re.search(r'__version__ = .(.+).', content).group(1); \
	parts = version.split('.'); \
	parts[2] = str(int(parts[2]) + 1); \
	new_version = '.'.join(parts); \
	new_content = re.sub(r'__version__ = .(.+).', f'__version__ = \"{new_version}\"', content); \
	open('datamodel/version.py', 'w').write(new_content); \
	print(f'Version bumped to {new_version}')"

bump-minor:
	@python -c "import re; \
	content = open('datamodel/version.py').read(); \
	version = re.search(r'__version__ = .(.+).', content).group(1); \
	parts = version.split('.'); \
	parts[1] = str(int(parts[1]) + 1); \
	parts[2] = '0'; \
	new_version = '.'.join(parts); \
	new_content = re.sub(r'__version__ = .(.+).', f'__version__ = \"{new_version}\"', content); \
	open('datamodel/version.py', 'w').write(new_content); \
	print(f'Version bumped to {new_version}')"

help:
	@echo "Available targets:"
	@echo "  venv          - Create virtual environment (Python $(PYTHON_VERSION))"
	@echo "  install       - Install production dependencies"
	@echo "  develop       - Install dev dependencies + build extensions"
	@echo "  build         - Full build (stage Rust + uv build)"
	@echo "  build-rust    - Build Rust extension via maturin (dev mode)"
	@echo "  stage-rust    - Stage Rust .so into source tree for wheel packaging"
	@echo "  build-inplace - Build Cython extensions in place"
	@echo "  release       - Build and publish package"
	@echo "  test          - Run tests"
	@echo "  format        - Format code with black"
	@echo "  lint          - Lint code"
	@echo "  clean         - Clean build artifacts"
	@echo "  distclean     - Clean everything including .venv"
```

- [ ] **Step 2: Commit**

```bash
git add Makefile
git commit -m "build: rewrite Makefile with uv commands

Follow querysource pattern: build-rust, stage-rust, build-inplace.
All commands use uv for dependency/env management."
```

---

### Task 5: Update CI Workflow

**Files:**
- Modify: `.github/workflows/release.yml`

**Interfaces:**
- Consumes: `rust/rs_parsers/Cargo.toml` for maturin builds in container
- Produces: cp310/cp311/cp312/cp313/cp314 manylinux wheels published to PyPI

- [ ] **Step 1: Rewrite `.github/workflows/release.yml`**

Follow querysource's release.yml pattern:

```yaml
name: Python package build and publish

on:
  release:
    types: [created]

jobs:
  build:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: ["3.10", "3.11", "3.12", "3.13", "3.14"]
        include:
          - python-version: "3.10"
            cibw-build: "cp310-*"
          - python-version: "3.11"
            cibw-build: "cp311-*"
          - python-version: "3.12"
            cibw-build: "cp312-*"
          - python-version: "3.13"
            cibw-build: "cp313-*"
          - python-version: "3.14"
            cibw-build: "cp314-*"
    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.12"

      - name: Install Rust
        uses: dtolnay/rust-toolchain@stable

      - name: Add Rust to PATH
        run: echo "$HOME/.cargo/bin" >> $GITHUB_PATH

      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install cibuildwheel maturin twine cython

      - name: Build wheels
        env:
          CIBW_ARCHS: x86_64
          CIBW_BEFORE_BUILD: >-
            curl https://sh.rustup.rs -sSf | sh -s -- -y &&
            export PATH=/root/.cargo/bin:$PATH &&
            pip install maturin &&
            cd {project}/rust && rm -rf target/wheels &&
            maturin build --release --manylinux off --interpreter python3
            --manifest-path rs_parsers/Cargo.toml &&
            python3 -c "import zipfile,glob,os,shutil;whl=glob.glob('target/wheels/*.whl')[0];zf=zipfile.ZipFile(whl);so=[n for n in zf.namelist() if n.endswith('.so') and '_rs_parsers' in n][0];zf.extract(so,'/tmp/_rs');shutil.copy2(os.path.join('/tmp/_rs',so),'{project}/datamodel/rs_parsers/')" &&
            cd {project}
          CIBW_ENVIRONMENT: "PATH=/root/.cargo/bin:$PATH"
          CIBW_BUILD: ${{ matrix.cibw-build }}
        run: |
          cibuildwheel --platform linux --output-dir dist

      - name: Upload wheel artifacts
        uses: actions/upload-artifact@v4
        with:
          name: wheels-py${{ matrix.python-version }}
          path: dist/*.whl

  deploy:
    needs: build
    runs-on: ubuntu-latest
    if: github.event_name == 'release'
    environment:
      name: pypi
      url: https://pypi.org/p/python-datamodel
    permissions:
      contents: read
      id-token: write
    steps:
      - uses: actions/checkout@v4

      - name: Download all artifacts
        uses: actions/download-artifact@v4.1.7
        with:
          pattern: wheels-py*
          path: dist-artifacts
          merge-multiple: true

      - name: Move wheel files to dist directory
        run: |
          mkdir -p dist
          find dist-artifacts -name '*.whl' -exec mv {} dist/ \;

      - name: Build sdist
        run: |
          pip install build
          python -m build --sdist --outdir dist

      - name: Check for wheel types
        id: check_wheels
        run: |
          echo "Checking for wheel types..."
          if ls dist/*-manylinux*.whl 1> /dev/null 2>&1; then
            echo "Found manylinux wheels."
            echo "HAS_MANYLINUX_WHEELS=true" >> $GITHUB_ENV
          fi

      - name: List files in dist
        run: ls -l dist

      - name: Install uv
        uses: astral-sh/setup-uv@v4
        with:
          version: "latest"

      - name: Publish wheels and sdist to PyPI
        run: |
          uv tool install twine
          uv tool run twine upload dist/*.whl dist/*.tar.gz --username __token__ --password ${{ secrets.PYTHON_DATAMODEL_PYPI_API_TOKEN }}
```

Key changes from old CI:
- `actions/setup-python@v5` (was v4)
- `dtolnay/rust-toolchain@stable` (was deprecated `actions-rs/toolchain@v1`)
- Removed Windows build job (Linux-only for now — can add back later)
- Added Python 3.14 to matrix
- `CIBW_BEFORE_BUILD` builds maturin inside container, extracts `.so` into source tree
- Deploy uses `astral-sh/setup-uv@v4` + `uv tool run twine`
- Uses `merge-multiple: true` for artifact downloads (cleaner)
- Added GitHub environment for PyPI

- [ ] **Step 2: Commit**

```bash
git add .github/workflows/release.yml
git commit -m "ci: update release workflow for maturin + uv + Python 3.14

- Add cp314 to build matrix
- Use dtolnay/rust-toolchain (replaces deprecated actions-rs)
- Use actions/setup-python@v5
- Build Rust via maturin inside cibuildwheel container
- Deploy with uv-managed twine
- Add GitHub environment for pypi"
```

---

### Task 6: Update Tests for psycopg3

**Files:**
- Modify: `tests/test_json.py` (line 7)

**Interfaces:**
- Consumes: `psycopg[binary]>=3.2.0` (new dependency from Task 3)
- Produces: Tests that work with psycopg 3.x

- [ ] **Step 1: Update psycopg2 import in `tests/test_json.py`**

Change line 7 from:
```python
from psycopg2 import Binary
```

To a compatible import with fallback:
```python
try:
    from psycopg2 import Binary
except ImportError:
    # psycopg 3.x — use bytes directly as binary adapter
    Binary = bytes
```

psycopg 3.x doesn't have a `Binary` wrapper class — it accepts `bytes` natively for binary data. The `Binary = bytes` assignment preserves the test's semantics: `Binary(b"data")` still produces a bytes object that JSON serialization can handle.

- [ ] **Step 2: Run the test to verify**

```bash
uv run pytest tests/test_json.py -v
```

Expected: all tests pass, including `test_binary`.

- [ ] **Step 3: Commit**

```bash
git add tests/test_json.py
git commit -m "test: update test_json.py for psycopg 3.x

Replace psycopg2.Binary import with fallback to bytes
for psycopg 3.x compatibility."
```

---

### Task 7: End-to-End Verification

**Files:**
- None created/modified — verification only

**Interfaces:**
- Consumes: all changes from Tasks 1-6
- Produces: verified working build with Rust + Cython extensions

- [ ] **Step 1: Generate uv lockfile**

```bash
uv lock
```

Expected: `uv.lock` is created with resolved dependencies including `psycopg[binary]>=3.2.0`.

- [ ] **Step 2: Create venv and sync**

```bash
make venv
source .venv/bin/activate
make develop
```

Expected: virtualenv created, dependencies installed, Rust and Cython extensions compiled.

- [ ] **Step 3: Verify Rust extension loads**

```bash
python -c "from datamodel.rs_parsers import HAS_RUST; print(f'HAS_RUST={HAS_RUST}')"
python -c "from datamodel.rs_parsers import to_date; print(to_date('2026-08-07'))"
```

Expected: `HAS_RUST=True` and a valid `datetime.date` object.

- [ ] **Step 4: Verify Cython extensions load**

```bash
python -c "from datamodel.fields import Field; print('Cython fields OK')"
python -c "from datamodel.converters import to_string; print('Cython converters OK')"
```

Expected: both imports succeed.

- [ ] **Step 5: Run full test suite**

```bash
make test
```

Expected: all tests pass.

- [ ] **Step 6: Test wheel build**

```bash
make build
ls -la dist/*.whl
```

Expected: a wheel in `dist/` containing both Cython `.so` files and `_rs_parsers*.so`.

- [ ] **Step 7: Verify wheel contents**

```bash
python -c "import zipfile; z=zipfile.ZipFile(list(__import__('pathlib').Path('dist').glob('*.whl'))[0]); [print(n) for n in sorted(z.namelist()) if n.endswith('.so') or 'rs_parsers' in n]"
```

Expected: output includes `_rs_parsers*.so` alongside the Cython `.so` files.

- [ ] **Step 8: Commit lockfile**

```bash
git add uv.lock
git commit -m "chore: add uv.lock for reproducible dependencies"
```

- [ ] **Step 9: Final commit — version bump (optional)**

If all verification passes and a release is desired:

```bash
make bump-minor  # or bump-patch
git add datamodel/version.py
git commit -m "release: bump version for Python 3.14 + uv migration"
```
