"""Tests for `scripts/stage_rust_ext.py`.

These tests never invoke a real Maturin build or need network access: the
Maturin step is monkeypatched to a no-op, and a fake wheel zip is written
directly into the configured `out_dir`.
"""
import subprocess
import sys
import zipfile
from pathlib import Path

import scripts.stage_rust_ext as stage


def _write_fake_wheel(out_dir: Path, member_name: str, content: bytes = b"payload") -> Path:
    wheel = out_dir / "rs_parsers-0.1.0-cp312-cp312-linux_x86_64.whl"
    with zipfile.ZipFile(wheel, "w") as archive:
        archive.writestr(f"datamodel/rs_parsers/{member_name}", content)
    return wheel


def test_stage_rust_ext_copies_so(tmp_path, monkeypatch):
    out_dir = tmp_path / "wheels"
    out_dir.mkdir()
    dest = tmp_path / "dest"
    _write_fake_wheel(out_dir, "_rs_parsers.cpython-312-x86_64-linux-gnu.so", b"so-bytes")

    monkeypatch.setattr(stage, "build_wheel", lambda *args, **kwargs: 0)

    assert stage.main(out_dir=str(out_dir), dest=str(dest)) == 0
    staged = dest / "_rs_parsers.cpython-312-x86_64-linux-gnu.so"
    assert staged.read_bytes() == b"so-bytes"


def test_stage_rust_ext_copies_pyd(tmp_path, monkeypatch):
    out_dir = tmp_path / "wheels"
    out_dir.mkdir()
    dest = tmp_path / "dest"
    _write_fake_wheel(out_dir, "_rs_parsers.cp312-win_amd64.pyd", b"pyd-bytes")

    monkeypatch.setattr(stage, "build_wheel", lambda *args, **kwargs: 0)

    assert stage.main(out_dir=str(out_dir), dest=str(dest)) == 0
    staged = dest / "_rs_parsers.cp312-win_amd64.pyd"
    assert staged.read_bytes() == b"pyd-bytes"


def test_stage_rust_ext_no_matching_member_returns_nonzero(tmp_path, monkeypatch):
    out_dir = tmp_path / "wheels"
    out_dir.mkdir()
    dest = tmp_path / "dest"
    _write_fake_wheel(out_dir, "unrelated.txt", b"nope")

    monkeypatch.setattr(stage, "build_wheel", lambda *args, **kwargs: 0)

    assert stage.main(out_dir=str(out_dir), dest=str(dest)) != 0


def test_stage_rust_ext_no_wheel_returns_nonzero(tmp_path, monkeypatch):
    out_dir = tmp_path / "wheels"
    out_dir.mkdir()
    dest = tmp_path / "dest"

    monkeypatch.setattr(stage, "build_wheel", lambda *args, **kwargs: 0)

    assert stage.main(out_dir=str(out_dir), dest=str(dest)) != 0


def test_stage_rust_ext_maturin_failure_returns_nonzero(tmp_path, monkeypatch):
    out_dir = tmp_path / "wheels"
    out_dir.mkdir()
    dest = tmp_path / "dest"

    monkeypatch.setattr(stage, "build_wheel", lambda *args, **kwargs: 1)

    assert stage.main(out_dir=str(out_dir), dest=str(dest)) == 1


def test_stage_rust_ext_cli_invokes_main():
    result = subprocess.run(
        [sys.executable, "scripts/stage_rust_ext.py", "--help"],
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    assert "--manifest" in result.stdout
    assert "--dest" in result.stdout
    assert "--out-dir" in result.stdout
    assert "--interpreter" in result.stdout
    assert "--manylinux" in result.stdout


def test_parse_args_forwards_options():
    parsed = stage.parse_args(
        [
            "--manifest",
            "custom/Cargo.toml",
            "--dest",
            "custom/dest",
            "--out-dir",
            "custom/out",
            "--interpreter",
            "python3.14",
            "--manylinux",
            "off",
        ]
    )
    assert parsed == {
        "manifest": "custom/Cargo.toml",
        "dest": "custom/dest",
        "out_dir": "custom/out",
        "interpreter": "python3.14",
        "manylinux": "off",
    }
