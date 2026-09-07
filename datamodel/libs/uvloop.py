# -*- coding: utf-8 -*-
"""Optional uvloop activation helper.

This module mirrors the optional-import pattern used by
`datamodel.rs_parsers` (see `HAS_RUST`): `HAS_UVLOOP` reports whether the
`uvloop` package is importable, and `install_uvloop()` is an explicit,
opt-in helper that installs uvloop's event-loop policy.

Nothing in `datamodel/__init__.py` imports this module, so importing
`datamodel` never has any effect on the caller's event loop. Callers must
invoke `install_uvloop()` themselves, typically at application startup.

On Python 3.12+, callers may prefer
`asyncio.run(main(), loop_factory=uvloop.new_event_loop)` instead of the
process-wide policy installed by this helper.
"""
import sys
from typing import Optional

HAS_UVLOOP = False
uvloop: Optional[object] = None

try:
    import uvloop  # type: ignore[no-redef]

    HAS_UVLOOP = True
except ImportError:
    uvloop = None


def install_uvloop() -> bool:
    """Install uvloop as the asyncio event-loop policy.

    Returns `True` when the policy was installed (or was already uvloop's).
    Returns `False`, without raising, when uvloop is not importable or when
    `sys.platform == "win32"`. Idempotent: calling it more than once is
    always safe. Never called implicitly by `datamodel`.
    """
    if sys.platform == "win32" or not HAS_UVLOOP:
        return False
    uvloop.install()
    return True
