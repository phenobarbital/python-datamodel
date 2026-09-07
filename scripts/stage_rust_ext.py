#!/usr/bin/env python
"""Cross-platform staging of the compiled Rust extension.

Builds `rust/rs_parsers` with Maturin, then copies the resulting
`_rs_parsers*.so` (Linux/macOS) or `_rs_parsers*.pyd` (Windows) extension
module out of the newest built wheel and into `datamodel/rs_parsers/`, so
that `setup.py` (via `package_data`) bundles it into the final wheel.

This replaces the previous inline bash/`python3 -c` extractors used by
`.github/workflows/release.yml` (Linux-only, `/tmp/_rs`, `.so`-only) and by
the Makefile's `stage-rust` target. It is the single staging path shared by
`CIBW_BEFORE_BUILD_LINUX`, `CIBW_BEFORE_BUILD_WINDOWS`, and
`make stage-rust`.

Exit status is non-zero when Maturin fails, no wheel is produced, or no
matching extension file is found inside the wheel.
"""
from __future__ import annotations

import argparse
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

EXTENSION_SUFFIXES = {".so", ".pyd"}


def build_wheel(
    manifest: str,
    out_dir: str,
    interpreter: str,
    manylinux: str | None,
) -> int:
    """Run `maturin build --release` for `manifest`, writing to `out_dir`."""
    command = [
        "maturin",
        "build",
        "--release",
        "--interpreter",
        interpreter,
        "--manifest-path",
        manifest,
        "--out",
        out_dir,
    ]
    if manylinux is not None:
        command.extend(["--manylinux", manylinux])
    completed = subprocess.run(command, check=False)
    return completed.returncode


def _newest_wheel(out_dir: str) -> Path | None:
    wheels = sorted(
        Path(out_dir).glob("rs_parsers-*.whl"),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )
    return wheels[0] if wheels else None


def _stage_from_wheel(wheel: Path, dest: Path) -> bool:
    """Copy every `_rs_parsers*.so`/`.pyd` member of `wheel` into `dest`.

    Returns True when at least one extension file was staged.
    """
    dest.mkdir(parents=True, exist_ok=True)
    staged = False
    with tempfile.TemporaryDirectory() as tmp_name:
        tmp = Path(tmp_name)
        with zipfile.ZipFile(wheel) as archive:
            for member in archive.namelist():
                # Normalize and use only the filename: never honor archive
                # paths that could escape the staging directory.
                name = Path(member).name
                if not name.startswith("_rs_parsers"):
                    continue
                if Path(name).suffix not in EXTENSION_SUFFIXES:
                    continue
                extracted = archive.extract(member, path=tmp)
                target = dest / name
                target.write_bytes(Path(extracted).read_bytes())
                staged = True
    return staged


def main(
    manifest: str = "rust/rs_parsers/Cargo.toml",
    dest: str = "datamodel/rs_parsers",
    out_dir: str = "rust/target/wheels",
    interpreter: str = "python",
    manylinux: str | None = None,
) -> int:
    """Build the Rust extension and stage it into `dest`.

    Returns 0 on success. Returns non-zero when Maturin fails, no wheel is
    produced, or no `_rs_parsers*.so`/`.pyd` member is found in the wheel.
    """
    return_code = build_wheel(manifest, out_dir, interpreter, manylinux)
    if return_code != 0:
        print(f"ERROR: maturin build failed (exit {return_code})", file=sys.stderr)
        return return_code

    wheel = _newest_wheel(out_dir)
    if wheel is None:
        print(f"ERROR: no rs_parsers-*.whl found in {out_dir}", file=sys.stderr)
        return 1

    print(f"Staging Rust extension from {wheel}")
    if not _stage_from_wheel(wheel, Path(dest)):
        print(
            f"ERROR: no _rs_parsers*.so/.pyd member found in {wheel}",
            file=sys.stderr,
        )
        return 1

    return 0


def parse_args(argv: list[str] | None = None) -> dict:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--manifest",
        default="rust/rs_parsers/Cargo.toml",
        help="Path to the Rust crate's Cargo.toml (default: %(default)s)",
    )
    parser.add_argument(
        "--dest",
        default="datamodel/rs_parsers",
        help="Directory the compiled extension is copied into (default: %(default)s)",
    )
    parser.add_argument(
        "--out-dir",
        default="rust/target/wheels",
        help="Directory maturin writes the built wheel into (default: %(default)s)",
    )
    parser.add_argument(
        "--interpreter",
        default="python",
        help="Target interpreter forwarded to `maturin build -i` (default: %(default)s)",
    )
    parser.add_argument(
        "--manylinux",
        default=None,
        help="Value forwarded to `maturin build --manylinux` (e.g. 'off'); omitted when unset",
    )
    args = parser.parse_args(argv)
    return {
        "manifest": args.manifest,
        "dest": args.dest,
        "out_dir": args.out_dir,
        "interpreter": args.interpreter,
        "manylinux": args.manylinux,
    }


if __name__ == "__main__":
    raise SystemExit(main(**parse_args()))
