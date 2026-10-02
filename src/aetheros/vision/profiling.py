"""
Opt-in per-stage timing for the vision pipeline.

Vision is the one subsystem where a single request can take tens of seconds, and
the only way to optimise it responsibly is to know which stage -- capture,
preprocess, detection, OCR, grounding, format -- actually spent the time. This
module provides that instrument without paying for it when it is off:

- ``VISION_PROFILE`` false (the default): :meth:`VisionProfiler.stage` is a
  no-op context manager. It takes no clock reading and writes no log line, so
  production logging is byte-for-byte unchanged.
- ``VISION_PROFILE`` true: each stage's wall-clock is measured and logged at
  DEBUG under the ``vision.profile`` logger, and optionally accumulated into a
  :class:`StageTimings` the caller can attach to a tool result.

The enabled flag is read once from the single :class:`Settings` object rather
than from a scattered ``os.getenv`` -- see §12 of the vision optimisation spec.
"""

from __future__ import annotations

import time
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Iterator

from ..config.config_loader import get_settings
from ..core.logging import get_logger


@dataclass(slots=True)
class StageTimings:
    """
    Accumulated per-stage timings for one vision request.

    A plain name -> milliseconds map. ``record`` adds rather than overwrites so
    a stage entered more than once (e.g. two captures) sums correctly, which is
    exactly the duplicate-work the profiler exists to expose.
    """

    stages: dict[str, float] = field(default_factory=dict)

    def record(self, name: str, ms: float) -> None:
        self.stages[name] = self.stages.get(name, 0.0) + ms

    def as_dict(self) -> dict[str, float]:
        return {name: round(ms, 2) for name, ms in self.stages.items()}

    @property
    def total_ms(self) -> float:
        return round(sum(self.stages.values()), 2)


class VisionProfiler:
    """
    Times named stages when profiling is enabled, and is a no-op otherwise.

    Construct it with the resolved flag (``VisionProfiler(get_settings()
    .VISION_PROFILE)``) or via :func:`get_profiler`, which reads the flag from
    the shared settings object.
    """

    __slots__ = ("_enabled", "_logger")

    def __init__(self, enabled: bool) -> None:
        self._enabled = enabled
        self._logger = get_logger("vision.profile")

    @property
    def enabled(self) -> bool:
        return self._enabled

    @contextmanager
    def stage(
        self,
        name: str,
        timings: StageTimings | None = None,
    ) -> Iterator[None]:
        """
        Time the wrapped block.

        Used around an ``await`` -- ``with profiler.stage("ocr"): blocks = await
        ...`` -- the timing spans the awaited work because ``__exit__`` runs only
        after the await completes. When disabled it yields immediately, taking no
        clock reading.
        """

        if not self._enabled:
            yield
            return

        start = time.perf_counter()

        try:
            yield

        finally:
            elapsed_ms = (time.perf_counter() - start) * 1000.0

            if timings is not None:
                timings.record(name, elapsed_ms)

            self._logger.bind(
                stage=name,
                ms=round(elapsed_ms, 2),
            ).debug("Vision stage timing.")


def get_profiler() -> VisionProfiler:
    """
    A profiler configured from the shared settings object.

    ``get_settings`` is cached, so this reads the ``VISION_PROFILE`` flag from
    the one canonical config rather than re-parsing the environment.
    """

    return VisionProfiler(get_settings().VISION_PROFILE)


__all__ = ["StageTimings", "VisionProfiler", "get_profiler"]
