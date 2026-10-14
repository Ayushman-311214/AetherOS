"""
Backwards-compatible location for the HUD test double.

The double itself moved to ``tests/hud_support.py`` so the bootstrap wiring
tests could reach it: ``tests/`` has no ``__init__.py``, so a module under
``tests/hud/`` is only importable once pytest has inserted that directory into
``sys.path``, which does not happen until collection reaches it — after
``tests/bootstrap/``. The tests root is on the path from the moment the root
conftest loads, so the shared double lives there.

Nothing imports this module any more; it re-exports rather than duplicating so
there is exactly one implementation.
"""

from __future__ import annotations

from hud_support import FakeHUDProcess

__all__ = ["FakeHUDProcess"]
