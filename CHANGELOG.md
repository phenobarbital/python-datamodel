# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/), and this
project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.11.0]

### Added
* Optional `python-datamodel[uvloop]` extra (`uvloop>=0.21.0; sys_platform != 'win32'`),
  and an explicit, opt-in `datamodel.libs.uvloop.install_uvloop()` helper. Importing
  `datamodel` never activates uvloop; callers invoke the helper themselves.
* Python 3.14 build target added to the release workflow (pending a live
  `workflow_dispatch` verification run before the first 0.11.0 release).
* Windows (`win_amd64`) wheels for cp310-cp314, built with the Rust extension
  (`_rs_parsers*.pyd`) included; the release job fails if the Rust build fails.
* `scripts/stage_rust_ext.py`, a cross-platform staging script (replaces the previous
  Linux-only inline extractor) used by both the release workflow and `make stage-rust`.
* A `workflow_dispatch` trigger on `.github/workflows/release.yml` so the full build
  matrix can be dry-run before cutting a release.

### Changed
* **Breaking**: `uvloop` is no longer installed automatically as a transitive dependency
  of `python-datamodel`. Applications that relied on datamodel to pull in `uvloop` must
  now request it explicitly via `pip install "python-datamodel[uvloop]"` (or install
  `uvloop` themselves) and call `install_uvloop()`.
* `setup.py` now selects MSVC-compatible compiler/link flags (`/O2`, no extra link args)
  on `win32`, and keeps the existing `-O3` / `-lstdc++` flags on other platforms.
* Both `[build-system].requires` and the `dev` extra now pin `Cython>=3.2.8`.

### Notes
* No macOS or ARM/aarch64 wheels are published; the release matrix remains manylinux
  x86_64 + win_amd64.

## [0.0.15] - 2022-09-15
* fixing building wheel for x86_64
* fixing behaviors over Meta class in Models with missing attributes

## [0.0.7] - 2022-09-14
* Added "from_dict" and "from_json" methods to create datamodels from json strings and dictionaries
* added a new json encoder, based on orjson
* "model()" method export a json version of Model (serialization).

## [0.0.1] - 2022-09-12
* First version
