# TASK-4: Add cross-platform Rust extension staging

**Feature**: FEAT-001 - Optional uvloop, Python 3.14 build, Windows wheels
**Spec**: `sdd/specs/new-infra-spec-uvloop-py314-windows.spec.md`
**Status**: pending
**Priority**: high
**Estimated effort**: M (2-4h)
**Depends-on**: none
**Assigned-to**: unassigned

---

## Context

The current staging path is embedded twice: a Linux/bash-only extractor in
`release.yml` and a Makefile recipe that recognizes only `.so`. Windows
needs `_rs_parsers*.pyd\), while Linux must preserve `--manylinux off`. This
task implements Module 4, including the resolved default to ignore local
`*.pyd` artifacts.

## Scope

- Create `scripts/stage_rust_ext.py` with reusable `main()` and CLI entrypoint.
- Run Maturin with an explicit target interpreter and optional manylinux policy.
- Select the newest wheel, copy matching `_rs_parsers*.so/.pyd` to the package.
- Return non-zero when Maturin fails, no wheel exists, or no extension is found.
- Replace Makefile extraction with the script.
- Add `*.pyd` to `.gitignore`.
- Add fake-wheel and subprocess CLI tests.

**NOT in scope**: GitHub matrix changes (TASK-5), compiler flags (TASK-3), or
Rust source changes.

## Files to Create / Modify

| File | Action | Description |
|---|---|---|
| `scripts/stage_rust_ext.py` | CREATE | Portable Maturin/build-wheel staging CLI |
| `Makefile` | MODIFY | Delegate `stage-rust` |
| `.gitignore` | MODIFY | Ignore local `*.pyd` artifacts |
| `tests/test_stage_rust_ext.py` | CREATE | Fake-wheel and CLI tests |

## Codebase Contract (Anti-Hallucination)

### Verified Existing Blocks

```makefile
# Makefile:57-66
stage-rust:
\t$(MATURIN) build --release -i python --manifest-path rust/rs_parsers/Cargo.toml --out $(RUST_WHEEL_OUT)
\t@whl=$$(ls -t $(RUST_WHEEL_OUT)/rs_parsers-*.whl | head -1); \
\t  ... unzip ...; \
\t  find "$$tmp" -name '_rs_parsers*.so' -exec cp {} datamodel/rs_parsers/ \; ; \
\t  ...
```

```gitignore
# .gitignore:6-7
*.so
```

```toml
# rust/rs_parsers/pyproject.toml
module-name = "datamodel.rs_parsers._rs_parsers"
```

### Does NOT Exist

- ~~`scripts/stage_rust_ext.py`~~ — this task creates it.
- ~~`CIBW_BEFORE_BUILD_LINUX`/ `CIBW_BEFORE_BUILD_WINDOWS`~~ — TASK-5 wires them.
- ~~`.pyd` ignore rule~~ — currently only `*.so` is ignored.

## Implementation Notes

Use `subprocess.run`, `tempfile.TemporaryDirectory()`, `zipfile.ZipFile`,
and `pathlib.Path`; never assume `/tmp` or bash:

```python
def main(manifest="rust/rs_parsers/Cargo.toml",
         dest="datamodel/rs_parsers",
         out_dir="rust/target/wheels",
         interpreter="python",
         manylinux=None) -> int:
    command = ["maturin", "build", "--release", "--interpreter", interpreter,
               "--manifest-path", manifest, "--out", out_dir]
    if manylinux is not None:
        command.extend(["--manylinux", manylinux])
    completed = subprocess.run(command, check=False)
    if completed.returncode != 0:
        return completed.returncode
    wheels = sorted(Path(out_dir).glob("rs_parsers-*.whl"),
                    key=lambda path: path.stat().st_mtime, reverse=True)
    if not wheels:
        return 1
    with tempfile.TemporaryDirectory() as temp:
        with zipfile.ZipFile(wheels[0]) as archive:
            names = [name for name in archive.namelist()
                     if Path(name).name.startswith("_rs_parsers")
                     and Path(name).suffix in {".so", ".pyd"}]
            if not names:
                return 1
            ...
    return 0


if __name__ == "__main__":
    raise SystemExit(main(**parse_args()))
```

The final implementation must normalize archive paths before copying, avoid
directory traversal, preserve native filenames, and expose CLI flags for
`--manifest`, `--dest`, `--out-dir`, `--interpreter`, and `--manylinux`.

### Key Constraints

- Linux release invocation passes `--manylinux off`; Windows omits it.
- Make invocation preserves `-i python` through the interpreter default.
- Do not commit generated native binaries.

### References in Codebase

- `Makefile:57-66` — current Rust staging.
- `.github/workflows/release.yml:46-54` — current Linux extractor.
- `rust/rs_parsers/Cargo.toml:9-12` — native library output.
- `pyproject.toml:94` — package data accepts `.so` and `.pyd`.

## Acceptance Criteria

- [ ] Fake `.so` and `.pyd` wheels stage correctly.
- [ ] Missing extension, wheel, and failed Maturin return non-zero.
- [ ] CLI reaches `main()` and forwards build-policy options.
- [ ] Makefile no longer contains archive extraction logic.
- [ ] `.gitignore` contains both `*.so` and `*.pyd`.
- [ ] No shared-script bash-only path or `/tmp` assumption remains.

## Test Specification

```python
def test_stage_pyd(tmp_path, monkeypatch):
    wheel = tmp_path / "rs_parsers-0.1-cp312-win_amd64.whl"
    with zipfile.ZipFile(wheel, "w") as archive:
        archive.writestr(
            "datamodel/rs_parsers/_rs_parsers.cp312-win_amd64.pyd", b"pyd"
        )
    monkeypatch.setattr(stage, "build_wheel", lambda *args, **kwargs: 0)
    assert stage.main(out_dir=str(tmp_path), dest=str(tmp_path / "dest")) == 0
    assert (tmp_path / "dest" / "_rs_parsers.cp312-win_amd64.pyd").read_bytes() == b"pyd"


def test_cli_entrypoint():
    result = subprocess.run(
        [sys.executable, "scripts/stage_rust_ext.py", "--help"],
        check=False,
    )
    assert result.returncode == 0
```

The tests must not require Rust or network access.

## Agent Instructions

1. Verify the Makefile and current workflow extractor before editing.
2. Keep the implementation portable to PowerShell and POSIX environments.
3. Run focused tests and `make -n stage-rust`.
4. Do not modify `.github/workflows/release.yml`; TASK-5 owns the hooks.

## Completion Note

**Completed by**: <session or agent ID>
**Date**: YYYY-MM-DD
**Notes**: <implementation and verification summary>
**Deviations from spec**: none | describe if any
