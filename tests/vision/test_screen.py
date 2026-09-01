"""
Tests for the screen capture layer.

Screen capture is where the vision pipeline's colour-space invariant starts: mss
hands back BGRA over a buffer it reuses, and every frame the vision engine sees
comes through here. The backend is exercised against a fake mss session rather
than a real display, so the conversion and lifetime rules are checked on a
headless machine too — the alternative is a suite that only runs on a developer's
desktop.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
import pytest

from aetheros.core.errors.vision_error import VisionError
from aetheros.core.interfaces.screen_controller import ScreenController
from aetheros.desktop.screen import mss_backend
from aetheros.desktop.screen.controller import ScreenService
from aetheros.desktop.screen.mss_backend import MSSScreen
from aetheros.vision.image import Image


# ============================================================================
# Fake mss session
# ============================================================================


_MONITORS: list[dict[str, int]] = [
    # Index 0 is the virtual bounding box of every screen, not a monitor.
    {"left": 0, "top": 0, "width": 3520, "height": 1080},
    {"left": 0, "top": 0, "width": 1920, "height": 1080},
    {"left": 1920, "top": 0, "width": 1600, "height": 900},
]


class FakeSCT:
    """
    Stands in for an ``mss.mss()`` session.

    Returns BGRA, the way mss does, so the backend's alpha handling is the real
    thing under test.
    """

    def __init__(
        self,
        frame: np.ndarray | None = None,
        *,
        error: Exception | None = None,
        monitors: list[dict[str, int]] | None = None,
    ) -> None:

        if frame is None:
            frame = np.zeros((4, 6, 4), dtype=np.uint8)
            frame[:, :, 0] = 10   # blue
            frame[:, :, 1] = 20   # green
            frame[:, :, 2] = 30   # red
            frame[:, :, 3] = 255  # alpha

        self._frame = frame
        self._error = error

        self.monitors = monitors if monitors is not None else list(_MONITORS)

        self.grabbed: list[dict[str, Any]] = []
        self.closed = False

    def grab(self, monitor: dict[str, Any]) -> np.ndarray:

        if self._error is not None:
            raise self._error

        self.grabbed.append(dict(monitor))

        return self._frame

    def close(self) -> None:
        self.closed = True


@pytest.fixture
def fake_sct() -> FakeSCT:
    return FakeSCT()


@pytest.fixture
def mss_screen(monkeypatch, fake_sct: FakeSCT) -> MSSScreen:
    """
    A real MSSScreen backed by a fake session instead of a display.
    """

    monkeypatch.setattr(mss_backend.mss, "mss", lambda: fake_sct)

    return MSSScreen()


# ============================================================================
# Backend
# ============================================================================


class TestMSSBackendInitialisation:
    def test_implements_the_interface(self, mss_screen: MSSScreen):
        assert isinstance(mss_screen, ScreenController)

    def test_headless_failure_is_translated(self, monkeypatch):
        """
        mss raises on construction without a display, so the DI container would
        otherwise cache a half-built object — or fail bootstrap outright on a
        machine that can still run the trading-analysis core.
        """

        def explode():
            raise RuntimeError("no display name and no $DISPLAY")

        monkeypatch.setattr(mss_backend.mss, "mss", explode)

        with pytest.raises(VisionError) as excinfo:
            MSSScreen()

        assert excinfo.value.code == "VISION_SCREEN_UNAVAILABLE"
        assert excinfo.value.hint is not None
        assert isinstance(excinfo.value.cause, RuntimeError)


class TestMSSCapture:
    def test_capture_returns_bgr(
        self,
        mss_screen: MSSScreen,
        fake_sct: FakeSCT,
    ):
        frame = mss_screen.capture()

        assert frame.shape == (4, 6, 3)
        assert frame.dtype == np.uint8
        # Alpha dropped, channel order untouched: B=10, G=20, R=30.
        assert tuple(int(v) for v in frame[0, 0]) == (10, 20, 30)

    def test_capture_uses_the_primary_monitor(
        self,
        mss_screen: MSSScreen,
        fake_sct: FakeSCT,
    ):
        mss_screen.capture()

        # Index 1, not index 0 — index 0 spans every screen.
        assert fake_sct.grabbed[0]["width"] == 1920

    def test_capture_is_not_a_view_on_the_shared_buffer(
        self,
        mss_screen: MSSScreen,
        fake_sct: FakeSCT,
    ):
        """
        ``np.asarray`` over an mss ScreenShot aliases a buffer mss reuses, so the
        next grab would mutate a frame the caller still holds.
        """

        frame = mss_screen.capture()

        fake_sct._frame[:, :, 0] = 200

        assert int(frame[0, 0, 0]) == 10
        assert frame.flags["C_CONTIGUOUS"]

    def test_capture_region_passes_the_rectangle_through(
        self,
        mss_screen: MSSScreen,
        fake_sct: FakeSCT,
    ):
        mss_screen.capture_region(left=5, top=7, width=6, height=4)

        assert fake_sct.grabbed[0] == {
            "left": 5,
            "top": 7,
            "width": 6,
            "height": 4,
        }

    @pytest.mark.parametrize(
        "width, height",
        [(0, 10), (10, 0), (-1, 10)],
    )
    def test_capture_region_rejects_empty_rectangles(
        self,
        mss_screen: MSSScreen,
        width,
        height,
    ):
        with pytest.raises(VisionError) as excinfo:
            mss_screen.capture_region(
                left=0,
                top=0,
                width=width,
                height=height,
            )

        assert excinfo.value.code == "VISION_INVALID_REGION"

    def test_grab_failure_is_translated(self, monkeypatch):
        session = FakeSCT(error=RuntimeError("gdi failure"))

        monkeypatch.setattr(mss_backend.mss, "mss", lambda: session)

        with pytest.raises(VisionError) as excinfo:
            MSSScreen().capture()

        assert excinfo.value.code == "VISION_CAPTURE_FAILED"
        assert isinstance(excinfo.value.cause, RuntimeError)


class TestMSSInformation:
    def test_size_is_the_primary_monitor(self, mss_screen: MSSScreen):
        assert mss_screen.size() == (1920, 1080)

    def test_monitors_excludes_the_virtual_screen(self, mss_screen: MSSScreen):
        monitors = mss_screen.monitors()

        assert len(monitors) == 2
        assert monitors[0]["width"] == 1920

    def test_monitors_are_copies(
        self,
        mss_screen: MSSScreen,
        fake_sct: FakeSCT,
    ):
        mss_screen.monitors()[0]["width"] = 1

        assert fake_sct.monitors[1]["width"] == 1920

    def test_capture_monitor_rejects_an_unknown_index(
        self,
        mss_screen: MSSScreen,
    ):
        with pytest.raises(VisionError) as excinfo:
            mss_screen.capture_monitor(9)

        assert excinfo.value.code == "VISION_INVALID_MONITOR"

    def test_capture_monitor_grabs_the_requested_screen(
        self,
        mss_screen: MSSScreen,
        fake_sct: FakeSCT,
    ):
        mss_screen.capture_monitor(2)

        assert fake_sct.grabbed[0]["left"] == 1920


class TestMSSSave:
    def test_writes_a_readable_file(
        self,
        mss_screen: MSSScreen,
        tmp_path: Path,
    ):
        target = tmp_path / "shot.png"

        mss_screen.save(mss_screen.capture(), target)

        assert target.is_file()
        assert target.stat().st_size > 0

    def test_saved_colours_are_not_swapped(
        self,
        mss_screen: MSSScreen,
        tmp_path: Path,
    ):
        """
        cv2.imwrite expects BGR, which is what capture() returns. Passing the
        frame through an RGB-oriented encoder would swap red and blue in every
        saved screenshot — invisible until someone looks at one.
        """

        target = tmp_path / "colour.png"

        mss_screen.save(mss_screen.capture(), target)

        reloaded = Image.open(target)

        assert tuple(
            int(v) for v in reloaded.data[0, 0]
        ) == (10, 20, 30)

    def test_missing_directory_is_reported(
        self,
        mss_screen: MSSScreen,
        tmp_path: Path,
    ):
        with pytest.raises(VisionError) as excinfo:
            mss_screen.save(
                mss_screen.capture(),
                tmp_path / "absent" / "shot.png",
            )

        assert excinfo.value.code == "VISION_SAVE_FAILED"


class TestMSSLifecycle:
    def test_close_releases_the_session(
        self,
        mss_screen: MSSScreen,
        fake_sct: FakeSCT,
    ):
        mss_screen.close()

        assert fake_sct.closed is True


# ============================================================================
# Service
# ============================================================================


class TestScreenService:
    @pytest.mark.asyncio
    async def test_capture_delegates_to_the_controller(self, make_fake_screen):
        screen = make_fake_screen(size=(64, 32))

        frame = await ScreenService(screen).capture()

        assert screen.captures == 1
        assert frame.shape == (32, 64, 3)

    @pytest.mark.asyncio
    async def test_capture_region_forwards_every_argument(
        self,
        make_fake_screen,
    ):
        screen = make_fake_screen(size=(64, 32))

        region = await ScreenService(screen).capture_region(
            left=4,
            top=8,
            width=10,
            height=6,
        )

        assert screen.regions == [(4, 8, 10, 6)]
        assert region.shape == (6, 10, 3)

    @pytest.mark.asyncio
    async def test_capture_failure_propagates(self, make_fake_screen):
        """
        A capture failure must surface, not be turned into an empty frame that
        OCR would happily report no text for.
        """

        failure = VisionError(
            code="CAPTURE_FAILED",
            message="display went away",
        )

        with pytest.raises(VisionError) as excinfo:
            await ScreenService(
                make_fake_screen(error=failure)
            ).capture()

        assert excinfo.value is failure

    @pytest.mark.asyncio
    async def test_save_delegates(self, make_fake_screen, tmp_path: Path):
        screen = make_fake_screen()

        service = ScreenService(screen)

        target = tmp_path / "out.png"

        await service.save(
            image=await service.capture(),
            path=target,
        )

        assert screen.saved == [target]

    @pytest.mark.asyncio
    async def test_size(self, make_fake_screen):
        assert await ScreenService(
            make_fake_screen(size=(800, 600))
        ).size() == (800, 600)

    @pytest.mark.asyncio
    async def test_monitors(self, make_fake_screen):
        monitors = await ScreenService(make_fake_screen()).monitors()

        assert monitors[0]["width"] == 320

    @pytest.mark.asyncio
    async def test_shutdown_releases_the_backend(self, make_fake_screen):
        """
        Without this, the process keeps an OS capture handle open for its whole
        lifetime — and on Windows that can block teardown outright.
        """

        screen = make_fake_screen()

        await ScreenService(screen).shutdown()

        assert screen.closed is True
