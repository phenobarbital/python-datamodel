---
id: F007
query_id: Q007
type: read
intent: Inspect Rust workspace + maturin config (PyO3 version for 3.14, platform cfg)
executed_at: 2026-09-07T21:31:00Z
duration_ms: 300
parent_id: null
depth: 0
---

# F007 — Rust side is already 3.14-capable and platform-agnostic

## Summary

The Cargo workspace pins `pyo3 = "0.29"` (Python 3.14 support landed in
PyO3 0.26, so this is sufficient). `rs_parsers` is a `cdylib` built with
maturin as a mixed project (`python-source = "../.."`, module
`datamodel.rs_parsers._rs_parsers`). No `#[cfg(...)]` platform conditionals
exist in `rs_parsers` or `rs_core` sources, and the dependency set (chrono,
speedate, uuid, rust_decimal, rayon) is pure Rust, so a Windows MSVC build
is expected to work without source changes. The Makefile's `stage-rust`
target only copies `_rs_parsers*.so`, so it would miss a `.pyd`.

## Citations

- path: `rust/Cargo.toml`
  lines: 1-12
  symbol: `[workspace]`, `[workspace.dependencies]`
  excerpt: |
    members = [ "rs_parsers", "rs_core", "rs_validators", ]
    resolver = "2"
    [workspace.dependencies]
    pyo3 = { version = "0.29", features = ["extension-module"] }
    rayon = "1.10"

- path: `rust/rs_parsers/Cargo.toml`
  lines: 9-12
  symbol: `[lib]`
  excerpt: |
    [lib]
    name = "_rs_parsers"
    crate-type = ["cdylib"]

- path: `rust/rs_parsers/pyproject.toml`
  lines: 1-15
  symbol: `[tool.maturin]`
  excerpt: |
    requires = ["maturin>=1.7,<2.0"]
    [tool.maturin]
    module-name = "datamodel.rs_parsers._rs_parsers"
    python-source = "../.."
    bindings = "pyo3"

- path: `Makefile`
  lines: 55-63
  symbol: `stage-rust`
  excerpt: |
    stage-rust:
    	$(MATURIN) build --release -i python --manifest-path rust/rs_parsers/Cargo.toml --out $(RUST_WHEEL_OUT)
    	...
    	  find "$$tmp" -name '_rs_parsers*.so' -exec cp {} datamodel/rs_parsers/ \; ; \

- path: `Makefile`
  lines: 8-9
  symbol: `PYTHON_VERSION`
  excerpt: |
    PYTHON_VERSION := 3.12
