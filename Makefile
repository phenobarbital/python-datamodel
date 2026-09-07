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

install:
	uv sync --frozen --no-dev
	$(MAKE) build-rust
	$(MAKE) build-inplace

develop:
	uv sync --frozen --extra dev
	$(MAKE) build-rust
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
	python scripts/stage_rust_ext.py --manifest rust/rs_parsers/Cargo.toml \
	  --dest datamodel/rs_parsers --out-dir $(RUST_WHEEL_OUT) --interpreter python

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

release: lint test build
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
	find datamodel -name "*.so" -not -path "datamodel/rs_parsers/*" -delete
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
	@echo "  install       - Install production dependencies + build extensions"
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
