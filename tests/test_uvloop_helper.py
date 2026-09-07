"""Tests for `datamodel.libs.uvloop` (`HAS_UVLOOP`, `install_uvloop()`).

Missing uvloop is a supported state, not a test failure: activation tests
skip cleanly via `pytest.importorskip("uvloop")` rather than failing when
the optional dependency is absent.
"""
import asyncio
import subprocess
import sys

import pytest


@pytest.fixture
def restore_event_loop_policy():
    """Snapshot asyncio's policy before the test and restore it after,
    so uvloop activation cannot leak into other tests."""
    previous = asyncio.get_event_loop_policy()
    try:
        yield
    finally:
        asyncio.set_event_loop_policy(previous)


def test_install_uvloop_without_uvloop_returns_false(monkeypatch):
    import datamodel.libs.uvloop as helper

    monkeypatch.setattr(helper, "HAS_UVLOOP", False)
    assert helper.install_uvloop() is False


def test_install_uvloop_on_win32_returns_false(monkeypatch):
    import datamodel.libs.uvloop as helper

    monkeypatch.setattr(helper.sys, "platform", "win32")
    assert helper.install_uvloop() is False


def test_install_uvloop_activates_policy(restore_event_loop_policy):
    uvloop = pytest.importorskip("uvloop")
    import datamodel.libs.uvloop as helper

    assert helper.install_uvloop() is True
    loop = asyncio.new_event_loop()
    try:
        assert isinstance(loop, uvloop.Loop)
    finally:
        loop.close()


def test_install_uvloop_idempotent(restore_event_loop_policy):
    pytest.importorskip("uvloop")
    import datamodel.libs.uvloop as helper

    assert helper.install_uvloop() is True
    assert helper.install_uvloop() is True


def test_import_datamodel_does_not_import_uvloop():
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            "import datamodel, sys; assert 'uvloop' not in sys.modules",
        ],
        check=False,
    )
    assert result.returncode == 0


def test_wheel_package_imports_uvloop_helper():
    """Smoke-check that `datamodel.libs.uvloop` is importable as a package
    module (guards against the packaging regression where the helper works
    from a checkout but is absent from an installed wheel)."""
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            "from datamodel.libs.uvloop import install_uvloop, HAS_UVLOOP",
        ],
        check=False,
    )
    assert result.returncode == 0
