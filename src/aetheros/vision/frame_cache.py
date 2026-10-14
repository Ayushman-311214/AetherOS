"""
Short-lived screen-frame cache.

A desktop agent frequently runs several vision ops against the same screen
state in quick succession -- "find the Search box", then "read the results",
then "where is the Login button" -- and each one used to grab the screen again.
Capture is the cheapest stage, but a redundant capture also means a redundant
copy and, worse, invites a redundant *detector* pass on a frame that has not
changed.

This cache holds the most recent frame for a configurable TTL
(``VISION_FRAME_TTL_MS``, default 300ms). Within that window a read-only op
reuses the frame; after it, or when explicitly invalidated, the next op
captures fresh.

Two safety rules, both from §8 of the vision optimisation spec:

- **Actions never read the cache.** Grounded click/type must act on a frame
  captured at the moment of acting; a 300ms-old frame could place a click on an
  element that has since moved. Those call sites pass ``force=True``, which
  captures fresh *and* refreshes the cache for following reads.
- **TTL is a ceiling, not a promise of freshness.** A short TTL bounds how stale
  a reused frame can be; ``invalidate`` drops it immediately when the caller
  knows the screen changed.

An :class:`asyncio.Lock` coalesces concurrent callers so two tasks that miss at
the same instant do not both capture (and, downstream, do not launch two
simultaneous detector passes -- §9).
"""

from __future__ import annotations

import asyncio
import time
from typing import Awaitable, Callable

from ..config.config_loader import get_settings
from .image import Image


class FrameCache:
    """
    Caches the latest captured :class:`Image` for ``ttl_ms`` milliseconds.

    ``clock`` is injectable purely so tests can advance time deterministically;
    it defaults to :func:`time.monotonic`, which never goes backwards under a
    clock adjustment the way ``time.time`` can.
    """

    __slots__ = ("_ttl_ms", "_clock", "_frame", "_captured_at", "_lock")

    def __init__(
        self,
        ttl_ms: int,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._ttl_ms = max(0, ttl_ms)
        self._clock = clock
        self._frame: Image | None = None
        self._captured_at: float = 0.0
        self._lock = asyncio.Lock()

    # ------------------------------------------------------------------
    # State
    # ------------------------------------------------------------------

    @property
    def ttl_ms(self) -> int:
        return self._ttl_ms

    def _fresh_enough(self) -> bool:
        if self._ttl_ms <= 0 or self._frame is None:
            return False

        age_ms = (self._clock() - self._captured_at) * 1000.0
        return age_ms <= self._ttl_ms

    def invalidate(self) -> None:
        """Drop the cached frame so the next op captures fresh."""
        self._frame = None

    # ------------------------------------------------------------------
    # Capture-through
    # ------------------------------------------------------------------

    async def get_or_capture(
        self,
        capture: Callable[[], Awaitable[Image]],
        *,
        force: bool = False,
    ) -> tuple[Image, bool]:
        """
        Return a frame, reusing the cached one when it is fresh enough.

        Returns ``(image, from_cache)``. ``force=True`` always captures fresh
        (used by grounded actions) and refreshes the cache. The freshness check
        is repeated inside the lock so that when several callers miss together,
        the first captures and the rest reuse that result instead of piling up
        captures.
        """

        if not force and self._fresh_enough():
            assert self._frame is not None
            return self._frame, True

        async with self._lock:
            if not force and self._fresh_enough():
                assert self._frame is not None
                return self._frame, True

            image = await capture()
            self._frame = image
            self._captured_at = self._clock()
            return image, False


_default_cache: FrameCache | None = None


def get_frame_cache() -> FrameCache:
    """
    Process-wide frame cache, sized from the shared settings object.

    Built once from ``VISION_FRAME_TTL_MS`` so the TTL comes from the single
    canonical config rather than a scattered ``os.getenv``.
    """

    global _default_cache

    if _default_cache is None:
        _default_cache = FrameCache(get_settings().VISION_FRAME_TTL_MS)

    return _default_cache


def reset_frame_cache() -> None:
    """Drop the process-wide cache (used by tests and at shutdown)."""
    global _default_cache
    _default_cache = None


__all__ = ["FrameCache", "get_frame_cache", "reset_frame_cache"]
