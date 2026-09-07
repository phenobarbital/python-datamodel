"""Tests for the platform-conditional compiler flags selected in setup.py.

`setup.py` guards its `setup(...)` call behind `if __name__ == "__main__":`
so this module can be imported safely without triggering a build.
"""
import setup


def test_windows_flags(monkeypatch):
    monkeypatch.setattr(setup.sys, "platform", "win32")
    assert setup._compiler_flags() == (["/O2"], [])


def test_posix_flags(monkeypatch):
    monkeypatch.setattr(setup.sys, "platform", "linux")
    assert setup._compiler_flags() == (["-O3"], ["-lstdc++"])
