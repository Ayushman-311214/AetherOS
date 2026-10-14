"""
Deterministic macro-release taxonomy for the economic calendar (spec sections 5, 9).

The spec's economic calendar tracks six named releases. This package gives them
a vocabulary: a pure, transparent, reproducible classifier
(:mod:`.macro`) that maps the *title* the calendar provider reported onto a
:class:`~..domain.event_calendar.MacroEventKind`, carrying the terms it matched.
It is deterministic-first by design, exactly like :mod:`..news`, and it neither
fetches anything nor claims anything about price -- it names a release, nothing
more.
"""

from __future__ import annotations

from .macro import MacroRead, classify

__all__ = ["MacroRead", "classify"]
