"""
Vision engine verification entry point.

Run with::

    python -m aetheros.vision.main

Exercises the real pipeline through the real bootstrap path — DI container,
tool registry, providers — and reports each stage as PASS, FAIL or SKIP. Display
and OCR-model checks are reported as SKIP rather than FAIL when the hardware or
the optional package is absent, so a headless machine gets a truthful result
instead of a misleading failure.

Exit code is 0 only when nothing failed.
"""

from __future__ import annotations

import asyncio
import sys
from dataclasses import dataclass

from ..bootstrap.bootstrapper import Bootstrapper
from ..core.container import container
from ..core.errors.vision_error import VisionError
from ..tools.registry import tool_registry
from .controller import VisionService
from .selfcheck import (
    expected_words,
    recognised_words,
    reference_image,
)

PASS = "PASS"
FAIL = "FAIL"
SKIP = "SKIP"

VISION_TOOLS = (
    "read_screen_text",
    "read_image_text",
    "detect_screen_objects",
    "find_text",
    "analyze_screen",
)


@dataclass(slots=True)
class Check:
    name: str
    status: str
    detail: str = ""


class VisionVerifier:
    """
    Runs the verification stages and collects their results.
    """

    def __init__(self) -> None:
        self._checks: list[Check] = []

    # ==========================================================
    # Reporting
    # ==========================================================

    def record(
        self,
        name: str,
        status: str,
        detail: str = "",
    ) -> None:

        self._checks.append(
            Check(name=name, status=status, detail=detail)
        )

    @property
    def failed(self) -> bool:

        return any(
            check.status == FAIL
            for check in self._checks
        )

    def report(self) -> str:

        width = max(len(check.name) for check in self._checks)

        lines = [
            "",
            "AetherOS Vision Engine Verification",
            "=" * (width + 30),
        ]

        for check in self._checks:
            lines.append(
                f"{check.name.ljust(width)}  {check.status:4}  {check.detail}"
            )

        lines.extend(
            [
                "=" * (width + 30),
                (
                    "Vision Engine verification FAILED."
                    if self.failed
                    else "Vision Engine verification passed."
                ),
                "",
            ]
        )

        return "\n".join(lines)

    # ==========================================================
    # Stages
    # ==========================================================

    async def run(self) -> None:

        bootstrapper = Bootstrapper()

        try:
            await bootstrapper.start()
            self.record("AetherOS startup", PASS)

        except Exception as exc:
            self.record(
                "AetherOS startup",
                FAIL,
                f"{type(exc).__name__}: {exc}",
            )
            return

        try:
            self._check_registration()
            self._check_tools()

            vision = container.resolve(VisionService)

            await self._check_image_processing(vision)
            await self._check_ocr(vision)
            await self._check_error_handling(vision)
            await self._check_screenshot()
            await self._check_end_to_end()

        finally:
            try:
                await bootstrapper.shutdown()
                self.record("Clean shutdown", PASS)

            except Exception as exc:
                self.record(
                    "Clean shutdown",
                    FAIL,
                    f"{type(exc).__name__}: {exc}",
                )

    # ------------------------------------------------------
    # DI
    # ------------------------------------------------------

    def _check_registration(self) -> None:

        if container.has(VisionService):
            self.record(
                "Vision service registered",
                PASS,
                "resolved from the DI container",
            )
        else:
            self.record(
                "Vision service registered",
                FAIL,
                "VisionService missing from the container",
            )

    # ------------------------------------------------------
    # Tools
    # ------------------------------------------------------

    def _check_tools(self) -> None:

        missing = [
            name
            for name in VISION_TOOLS
            if not tool_registry.exists(name)
        ]

        if missing:
            self.record(
                "Vision tools registered",
                FAIL,
                f"missing: {', '.join(missing)}",
            )
        else:
            self.record(
                "Vision tools registered",
                PASS,
                f"{len(VISION_TOOLS)} tools in the registry",
            )

        discovered = [
            definition.name
            for definition in tool_registry.by_category("vision")
        ]

        if set(VISION_TOOLS).issubset(discovered):
            self.record(
                "Vision tools discoverable",
                PASS,
                "category 'vision'",
            )
        else:
            self.record(
                "Vision tools discoverable",
                FAIL,
                f"category 'vision' held {discovered}",
            )

    # ------------------------------------------------------
    # Image processing
    # ------------------------------------------------------

    async def _check_image_processing(
        self,
        vision: VisionService,
    ) -> None:

        try:
            image = reference_image()

            gray = await vision.grayscale(image)
            edges = await vision.edges(image)
            small = await vision.resize(image, 64, 64)

            assert gray.channels == 1
            assert edges.channels == 1
            assert (small.width, small.height) == (64, 64)

            self.record(
                "Image processing",
                PASS,
                f"{image.width}x{image.height} -> grayscale, edges, resize",
            )

        except Exception as exc:
            self.record(
                "Image processing",
                FAIL,
                f"{type(exc).__name__}: {exc}",
            )

    # ------------------------------------------------------
    # OCR
    # ------------------------------------------------------

    async def _check_ocr(
        self,
        vision: VisionService,
    ) -> None:

        if not vision.has_ocr:
            self.record(
                "OCR",
                SKIP,
                "PaddleOCR is not installed",
            )
            return

        try:
            blocks = await vision.read_text(reference_image())

        except VisionError as exc:
            # A missing model cache with no network is an environment problem,
            # not a defect in the engine, so it is reported as a skip.
            status = (
                SKIP
                if exc.code.endswith(("OCR_UNAVAILABLE", "OCR_INIT_FAILED"))
                else FAIL
            )

            self.record("OCR", status, f"{exc.code}: {exc.message}")
            return

        except Exception as exc:
            self.record("OCR", FAIL, f"{type(exc).__name__}: {exc}")
            return

        recognised = recognised_words(
            " ".join(block.text for block in blocks)
        )

        found = expected_words() & recognised

        if found:
            self.record(
                "OCR",
                PASS,
                (
                    f"{len(blocks)} blocks, matched "
                    f"{len(found)}/{len(expected_words())} expected words"
                ),
            )
        else:
            self.record(
                "OCR",
                FAIL,
                f"expected {sorted(expected_words())}, read {sorted(recognised)}",
            )

    # ------------------------------------------------------
    # Error handling
    # ------------------------------------------------------

    async def _check_error_handling(
        self,
        vision: VisionService,
    ) -> None:

        try:
            await vision.read_text(None)  # type: ignore[arg-type]

        except VisionError:
            self.record(
                "Error handling",
                PASS,
                "invalid input raises VisionError",
            )

        except Exception as exc:
            self.record(
                "Error handling",
                FAIL,
                f"raised {type(exc).__name__} instead of VisionError",
            )

        else:
            self.record(
                "Error handling",
                FAIL,
                "invalid input was accepted",
            )

    # ------------------------------------------------------
    # Screenshot
    # ------------------------------------------------------

    async def _check_screenshot(self) -> None:

        from ..desktop.screen.controller import ScreenService

        if not container.has(ScreenService):
            self.record(
                "Screenshot",
                SKIP,
                "no display available",
            )
            return

        try:
            frame = await container.resolve(ScreenService).capture()

            self.record(
                "Screenshot",
                PASS,
                f"{frame.shape[1]}x{frame.shape[0]}, {frame.shape[2]} channels",
            )

        except Exception as exc:
            self.record(
                "Screenshot",
                FAIL,
                f"{type(exc).__name__}: {exc}",
            )

    # ------------------------------------------------------
    # End to end
    # ------------------------------------------------------

    async def _check_end_to_end(self) -> None:
        """
        Drive OCR through the tool registry, the way an agent would.
        """

        from ..tools.executor import ToolExecutor

        vision = container.resolve(VisionService)

        if not vision.has_ocr:
            self.record(
                "End-to-end vision flow",
                SKIP,
                "PaddleOCR is not installed",
            )
            return

        import tempfile
        from pathlib import Path

        with tempfile.TemporaryDirectory() as directory:

            path = Path(directory) / "vision_selfcheck.png"

            reference_image().save(path)

            # A plain ToolExecutor now: the 180s override this used to pass was
            # working around a 30s global default that cancelled every OCR call.
            # The vision tools declare VISION_TOOL_TIMEOUT_SECONDS themselves, so
            # the selfcheck exercises the same budget an agent gets — which is
            # the point of an end-to-end check.
            result = await ToolExecutor().execute_safe(
                "read_image_text",
                {"path": str(path)},
            )

        if not result.ok:
            detail = result.error or ""

            status = (
                SKIP
                if "OCR_UNAVAILABLE" in detail or "OCR_INIT_FAILED" in detail
                else FAIL
            )

            self.record("End-to-end vision flow", status, detail[:160])
            return

        recognised = recognised_words(result.value["text"])

        if expected_words() & recognised:
            self.record(
                "End-to-end vision flow",
                PASS,
                (
                    f"tool returned {result.value['count']} blocks in "
                    f"{result.duration_ms:.0f}ms"
                ),
            )
        else:
            self.record(
                "End-to-end vision flow",
                FAIL,
                f"tool read {sorted(recognised)}",
            )


async def start() -> VisionVerifier:
    """
    Run every verification stage.
    """

    verifier = VisionVerifier()

    await verifier.run()

    return verifier


def main() -> int:

    verifier = asyncio.run(start())

    print(verifier.report())

    return 1 if verifier.failed else 0


if __name__ == "__main__":
    sys.exit(main())
