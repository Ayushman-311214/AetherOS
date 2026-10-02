"""
Tests for the short-lived screen-frame cache.

The clock is injected so time advances deterministically instead of via
``sleep``. The contract, from §8 of the vision-optimisation spec:

- within the TTL a read-only op reuses the cached frame (one capture, not two);
- past the TTL, or after ``invalidate``, the next op captures fresh;
- ``force=True`` (grounded actions) always captures fresh AND refreshes the
  cache, so acting can never land on a stale frame and a following read still
  benefits;
- a TTL of 0 disables reuse entirely;
- concurrent misses coalesce: the first captures, the rest reuse that result
  rather than launching parallel captures (which §9 forbids for the detector).
"""

from __future__ import annotations

import asyncio

import numpy as np
import pytest

from aetheros.vision.frame_cache import FrameCache
from aetheros.vision.image import Image


class _Clock:
    """A hand-cranked monotonic clock, in seconds."""

    def __init__(self) -> None:
        self.t = 0.0

    def __call__(self) -> float:
        return self.t

    def advance_ms(self, ms: float) -> None:
        self.t += ms / 1000.0


def _make_capture():
    """
    A capture function that returns a fresh, distinct Image each call and counts
    invocations, so a test can tell reuse from a real grab.
    """

    state = {"n": 0}

    async def capture() -> Image:
        state["n"] += 1
        data = np.zeros((4, 4, 3), dtype=np.uint8)
        data[:, :, 0] = state["n"]  # stamp the call number so frames differ
        return Image.from_numpy(data, source=f"cap-{state['n']}", color_space="bgr")

    return capture, state


@pytest.mark.asyncio
class TestReuseWithinTtl:

    async def test_second_call_within_ttl_reuses(self) -> None:
        clock = _Clock()
        cache = FrameCache(ttl_ms=300, clock=clock)
        capture, state = _make_capture()

        img1, from_cache1 = await cache.get_or_capture(capture)
        clock.advance_ms(100)  # still inside the 300ms window
        img2, from_cache2 = await cache.get_or_capture(capture)

        assert from_cache1 is False
        assert from_cache2 is True
        assert state["n"] == 1          # only one real capture
        assert img2 is img1             # the very same frame object

    async def test_capture_after_ttl_expires(self) -> None:
        clock = _Clock()
        cache = FrameCache(ttl_ms=300, clock=clock)
        capture, state = _make_capture()

        await cache.get_or_capture(capture)
        clock.advance_ms(301)           # just past the ceiling
        _, from_cache = await cache.get_or_capture(capture)

        assert from_cache is False
        assert state["n"] == 2

    async def test_ttl_boundary_is_inclusive(self) -> None:
        clock = _Clock()
        cache = FrameCache(ttl_ms=300, clock=clock)
        capture, state = _make_capture()

        await cache.get_or_capture(capture)
        clock.advance_ms(300)           # exactly at the ceiling still reuses
        _, from_cache = await cache.get_or_capture(capture)

        assert from_cache is True
        assert state["n"] == 1


@pytest.mark.asyncio
class TestInvalidate:

    async def test_invalidate_forces_a_recapture(self) -> None:
        clock = _Clock()
        cache = FrameCache(ttl_ms=300, clock=clock)
        capture, state = _make_capture()

        await cache.get_or_capture(capture)
        cache.invalidate()
        _, from_cache = await cache.get_or_capture(capture)

        assert from_cache is False
        assert state["n"] == 2


@pytest.mark.asyncio
class TestForce:

    async def test_force_always_captures_even_within_ttl(self) -> None:
        clock = _Clock()
        cache = FrameCache(ttl_ms=300, clock=clock)
        capture, state = _make_capture()

        await cache.get_or_capture(capture)
        _, from_cache = await cache.get_or_capture(capture, force=True)

        assert from_cache is False
        assert state["n"] == 2

    async def test_force_refreshes_the_cache_for_following_reads(self) -> None:
        clock = _Clock()
        cache = FrameCache(ttl_ms=300, clock=clock)
        capture, state = _make_capture()

        forced, _ = await cache.get_or_capture(capture, force=True)
        # A subsequent read within the TTL reuses the forced frame, not a
        # third capture -- the action's fresh grab primed the cache.
        reused, from_cache = await cache.get_or_capture(capture)

        assert from_cache is True
        assert reused is forced
        assert state["n"] == 1


@pytest.mark.asyncio
class TestDisabled:

    async def test_zero_ttl_never_reuses(self) -> None:
        clock = _Clock()
        cache = FrameCache(ttl_ms=0, clock=clock)
        capture, state = _make_capture()

        await cache.get_or_capture(capture)
        _, from_cache = await cache.get_or_capture(capture)  # no time advanced

        assert from_cache is False
        assert state["n"] == 2

    async def test_negative_ttl_is_clamped_to_zero(self) -> None:
        cache = FrameCache(ttl_ms=-100)
        assert cache.ttl_ms == 0


@pytest.mark.asyncio
class TestConcurrentCoalescing:

    async def test_simultaneous_misses_capture_once(self) -> None:
        clock = _Clock()
        cache = FrameCache(ttl_ms=300, clock=clock)

        started = {"n": 0}

        async def slow_capture() -> Image:
            started["n"] += 1
            # Yield control so all waiters are queued on the lock before the
            # first capture completes -- the exact race the lock guards.
            await asyncio.sleep(0.01)
            return Image.from_numpy(
                np.zeros((4, 4, 3), dtype=np.uint8),
                source="slow",
                color_space="bgr",
            )

        results = await asyncio.gather(
            *(cache.get_or_capture(slow_capture) for _ in range(5))
        )

        # Exactly one real capture; four callers reused its result.
        assert started["n"] == 1
        from_cache_flags = [from_cache for _, from_cache in results]
        assert from_cache_flags.count(False) == 1
        assert from_cache_flags.count(True) == 4
