"""
Verification strategies — the eight ways AetherOS reads state back.

Every desktop action tool ends with a read-back through one of these. The point
is not defensiveness for its own sake: pyautogui, the Win32 API and the Windows
clipboard all fail *silently*. ``pyautogui.moveTo(9999, 9999)`` clamps to the
screen edge and returns None. ``SetForegroundWindow`` returns 0 when the calling
process does not own the foreground and pywin32 raises nothing useful.
``pyperclip.copy`` succeeds while another process holds the clipboard open and
the data never lands. In each case the action reports success and the state is
wrong, so the only trustworthy signal is a separate read.

Services are resolved lazily, inside ``check``, rather than injected at
construction. Two reasons, both load-bearing:

* The window and process services are themselves built on top of these
  strategies' sibling modules, so constructor injection would close an import
  cycle.
* On a headless machine the screen and window services are never registered at
  all. A strategy that resolved them eagerly would fail at import and take the
  whole tool registry with it; resolving late turns the same situation into an
  honest per-check ``ERROR`` result.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Any, ClassVar

from ...config.config_loader import get_settings
from ...core.errors.desktop_error import DesktopError
from ...core.logging import get_logger
from .result import VerificationResult


class MatchMode(str, Enum):
    """
    How ``expected`` should be compared against what was read back.

    Shared across strategies so ``contains`` means the same thing whether it is
    applied to clipboard text or OCR output.
    """

    EQUALS = "equals"
    CONTAINS = "contains"
    NOT_CONTAINS = "not_contains"
    EXISTS = "exists"
    ABSENT = "absent"
    CHANGED = "changed"
    UNCHANGED = "unchanged"


@dataclass(frozen=True, slots=True)
class VerificationRequest:
    """
    One verification to perform.

    A single request object rather than per-strategy signatures, so the
    ``verify_action`` tool can dispatch on ``method`` without a match statement
    over eight different call shapes, and so a workflow step can carry its
    verification as plain data.
    """

    method: str
    mode: MatchMode = MatchMode.EQUALS
    expected: Any = None
    target: str | None = None
    tolerance: float = 0.0
    region: tuple[int, int, int, int] | None = None
    baseline: Any = None
    condition: str | None = None

    def describe(self) -> str:
        """
        Human-readable condition, used when the caller did not supply one.
        """

        if self.condition:
            return self.condition

        subject = self.target or self.method

        if self.mode in (MatchMode.EXISTS, MatchMode.ABSENT):
            return f"{subject} {self.mode.value}"

        if self.mode in (MatchMode.CHANGED, MatchMode.UNCHANGED):
            return f"{subject} {self.mode.value}"

        return f"{subject} {self.mode.value} {self.expected!r}"

    @classmethod
    def from_spec(cls, spec: dict[str, Any]) -> VerificationRequest:
        """
        Build a request from a plain dict, as a workflow step carries it.

        Unknown keys are rejected rather than ignored: a step that says
        ``{"method": "file", "path": "x"}`` meant ``target``, and silently
        dropping the key would produce a check that passes for the wrong reason.
        """

        if not isinstance(spec, dict):
            raise DesktopError(
                code="VERIFICATION_SPEC_INVALID",
                message=(
                    "A verification spec must be an object, got "
                    f"{type(spec).__name__}."
                ),
                hint='Example: {"method": "file", "mode": "exists", "target": "C:/tmp/a.txt"}',
            )

        allowed = {
            "method",
            "mode",
            "expected",
            "target",
            "tolerance",
            "region",
            "condition",
        }

        unknown = sorted(set(spec) - allowed)

        if unknown:
            raise DesktopError(
                code="VERIFICATION_SPEC_INVALID",
                message=f"Unknown verification field(s): {', '.join(unknown)}.",
                hint=f"Supported fields: {', '.join(sorted(allowed))}.",
            )

        method = spec.get("method")

        if not method:
            raise DesktopError(
                code="VERIFICATION_SPEC_INVALID",
                message="A verification spec needs a 'method'.",
                hint=f"Available methods: {', '.join(sorted(STRATEGIES))}.",
            )

        return cls(
            method=str(method).strip().lower(),
            mode=parse_mode(spec.get("mode", "equals")),
            expected=spec.get("expected"),
            target=(
                None if spec.get("target") is None else str(spec["target"])
            ),
            tolerance=float(spec.get("tolerance") or 0.0),
            region=parse_region(spec.get("region")),
            condition=spec.get("condition"),
        )


def parse_mode(value: str) -> MatchMode:
    """
    Parse a caller-supplied comparison mode.

    Shared by the ``verify_action`` tool and the workflow parser so a mode name
    means the same thing whether it arrived as a tool argument or inside a
    workflow step.
    """

    try:
        return MatchMode(str(value).strip().lower())

    except ValueError as exc:
        supported = ", ".join(sorted(item.value for item in MatchMode))

        raise DesktopError(
            code="VERIFICATION_MODE_INVALID",
            message=f"'{value}' is not a comparison mode.",
            hint=f"Use one of: {supported}.",
            cause=exc,
        ) from exc


def parse_region(value: Any) -> tuple[int, int, int, int] | None:
    """
    Parse a ``[left, top, width, height]`` screen region.
    """

    if value is None:
        return None

    if not isinstance(value, (list, tuple)) or len(value) != 4:
        raise DesktopError(
            code="VERIFICATION_REGION_INVALID",
            message=(
                "A screen region needs exactly 4 values, got "
                f"{len(value) if isinstance(value, (list, tuple)) else type(value).__name__}."
            ),
            hint="Pass region as [left, top, width, height].",
        )

    try:
        left, top, width, height = (int(item) for item in value)

    except (TypeError, ValueError) as exc:
        raise DesktopError(
            code="VERIFICATION_REGION_INVALID",
            message="Region values must be whole numbers of pixels.",
            hint="Pass region as [left, top, width, height].",
            cause=exc,
        ) from exc

    if width <= 0 or height <= 0:
        raise DesktopError(
            code="VERIFICATION_REGION_INVALID",
            message=(
                f"Region width and height must be positive, got {width}x{height}."
            ),
            hint="Pass region as [left, top, width, height].",
        )

    return left, top, width, height


class VerificationStrategy(ABC):
    """
    Base class for a single way of reading state back.
    """

    method: ClassVar[str]
    description: ClassVar[str]
    supported_modes: ClassVar[frozenset[MatchMode]]

    def __init__(self) -> None:
        self._logger = get_logger(f"desktop.verify.{self.method}")

    # ==========================================================
    # Public
    # ==========================================================

    async def check(self, request: VerificationRequest) -> VerificationResult:
        """
        Run this strategy, converting an unexpected failure into an ERROR result.

        The wrapper exists so a broken *check* can never be mistaken for a failed
        *action*: an unavailable window backend produces ``ERROR``, which leaves
        ``success`` intact and ``verified`` false, where ``FAILED`` would claim
        the action itself did not happen.

        :class:`DesktopError` is deliberately allowed through. It signals a
        malformed request (unknown mode, missing target), which is a caller bug
        the model must see as an error rather than as a verification outcome.
        """

        self._require_mode(request.mode)

        try:
            return await self._check(request)

        except DesktopError:
            raise

        except Exception as exc:
            self._logger.bind(
                method=self.method,
                error_type=type(exc).__name__,
            ).warning("Verification attempt failed to complete.")

            return VerificationResult.errored(
                request.describe(),
                method=self.method,
                detail=f"{type(exc).__name__}: {exc}",
            )

    # ==========================================================
    # Subclass contract
    # ==========================================================

    @abstractmethod
    async def _check(self, request: VerificationRequest) -> VerificationResult:
        """Read state back and compare it. May raise; ``check`` handles that."""

    # ==========================================================
    # Shared helpers
    # ==========================================================

    def _require_mode(self, mode: MatchMode) -> None:

        if mode not in self.supported_modes:

            supported = ", ".join(sorted(m.value for m in self.supported_modes))

            raise DesktopError(
                code="VERIFICATION_MODE_UNSUPPORTED",
                message=(
                    f"The '{self.method}' verification method does not support "
                    f"mode '{mode.value}'."
                ),
                hint=f"Supported modes: {supported}.",
            )

    def _require_target(self, request: VerificationRequest) -> str:

        if not request.target:
            raise DesktopError(
                code="VERIFICATION_TARGET_REQUIRED",
                message=(
                    f"The '{self.method}' verification method requires a target."
                ),
                hint="Supply the path, window title, or process name to check.",
            )

        return request.target

    def _compare_text(
        self,
        request: VerificationRequest,
        actual: str | None,
    ) -> VerificationResult:
        """
        Apply a text-oriented mode to a string that was just read back.

        Shared by the clipboard and OCR strategies so "contains" behaves
        identically in both, including the case folding.
        """

        condition = request.describe()
        expected = request.expected

        def outcome(passed: bool, detail: str | None = None) -> VerificationResult:

            builder = (
                VerificationResult.passed if passed else VerificationResult.failed
            )

            return builder(
                condition,
                method=self.method,
                expected=expected,
                actual=actual,
                detail=detail,
            )

        if request.mode is MatchMode.EXISTS:
            return outcome(bool(actual))

        if request.mode is MatchMode.ABSENT:
            return outcome(not actual)

        if request.mode is MatchMode.CHANGED:
            return outcome(
                actual != request.baseline,
                detail="compared against the value captured before the action",
            )

        if request.mode is MatchMode.UNCHANGED:
            return outcome(actual == request.baseline)

        if actual is None:
            return outcome(False, detail="nothing was read back")

        expected_text = "" if expected is None else str(expected)

        if request.mode is MatchMode.EQUALS:
            return outcome(actual == expected_text)

        # Case-insensitive for the substring modes. OCR routinely disagrees with
        # the source on case ("Save" read as "SAVE"), and a case-sensitive
        # contains check would report a visible button as missing.
        haystack = actual.casefold()
        needle = expected_text.casefold()

        if request.mode is MatchMode.CONTAINS:
            return outcome(needle in haystack)

        return outcome(needle not in haystack)

    def _compare_presence(
        self,
        request: VerificationRequest,
        present: bool,
        *,
        actual: Any = None,
        detail: str | None = None,
    ) -> VerificationResult:
        """
        Apply EXISTS / ABSENT to a boolean read-back.
        """

        wanted = request.mode is MatchMode.EXISTS

        builder = (
            VerificationResult.passed
            if present is wanted
            else VerificationResult.failed
        )

        return builder(
            request.describe(),
            method=self.method,
            expected=request.mode.value,
            actual=actual if actual is not None else present,
            detail=detail,
        )


# ==============================================================
# 1 — State
# ==============================================================


class StateStrategy(VerificationStrategy):
    """
    Compare a value the caller already read back.

    The workhorse for services that can observe their own effect cheaply — a
    window state after ``minimize_window``, a volume level after ``set_volume``.
    The read happens in the service, which knows how; this only judges it.
    """

    method = "state"
    description = "Compare an observed value against the expected value."
    supported_modes = frozenset(
        {
            MatchMode.EQUALS,
            MatchMode.CONTAINS,
            MatchMode.NOT_CONTAINS,
            MatchMode.EXISTS,
            MatchMode.ABSENT,
            MatchMode.CHANGED,
            MatchMode.UNCHANGED,
        }
    )

    async def _check(self, request: VerificationRequest) -> VerificationResult:

        # ``target`` carries the observed value for this strategy. It is the one
        # method where the caller performs the read-back and this class only
        # judges it, so there is nothing to query here.
        return self._compare_text(request, request.target)


# ==============================================================
# 2 — Position
# ==============================================================


class PositionStrategy(VerificationStrategy):
    """
    Read the cursor position back and compare it within a tolerance.

    Tolerance is not optional slack. Windows applies pointer acceleration and
    per-monitor DPI scaling, so a move to (800, 600) can legitimately settle on
    (799, 600); an exact-match check reports a perfectly working mouse as broken
    roughly one time in ten.

    The tolerance also stays small on purpose. The failure this catches is
    coordinate clamping — asking for (785, 2000) on a 1080p display lands on
    (785, 1079) — and a generous tolerance would wave that through.
    """

    method = "position"
    description = "Confirm the mouse cursor is at the expected coordinates."
    supported_modes = frozenset({MatchMode.EQUALS, MatchMode.CHANGED})

    async def _check(self, request: VerificationRequest) -> VerificationResult:

        from ...core.container import container
        from ..mouse.controller import MouseService

        service: MouseService = container.resolve(MouseService)

        actual = await service.position()

        condition = request.describe()

        if request.mode is MatchMode.CHANGED:

            baseline = self._as_point(request.baseline)

            return (
                VerificationResult.passed
                if baseline is None or tuple(actual) != baseline
                else VerificationResult.failed
            )(
                condition,
                method=self.method,
                expected="a position different from the one before the action",
                actual=list(actual),
                detail=(
                    "no baseline was supplied, so any position is accepted"
                    if baseline is None
                    else None
                ),
            )

        expected = self._as_point(request.expected)

        if expected is None:
            raise DesktopError(
                code="VERIFICATION_EXPECTED_REQUIRED",
                message="Position verification needs an expected (x, y) pair.",
                hint="Pass expected as [x, y].",
            )

        tolerance = (
            request.tolerance
            if request.tolerance > 0
            else get_settings().DESKTOP_POSITION_TOLERANCE
        )

        dx = abs(actual[0] - expected[0])
        dy = abs(actual[1] - expected[1])

        within = dx <= tolerance and dy <= tolerance

        builder = (
            VerificationResult.passed if within else VerificationResult.failed
        )

        return builder(
            condition,
            method=self.method,
            expected=list(expected),
            actual=list(actual),
            detail=(
                f"offset ({dx}, {dy}) against a tolerance of {tolerance}px"
            ),
        )

    def _as_point(self, value: Any) -> tuple[int, int] | None:
        """
        Coerce the many shapes a coordinate pair arrives in.

        The model sends ``[800, 600]``; internal callers pass a tuple; JSON
        round-trips can produce floats. Rejecting any of those would be a
        pointless failure.
        """

        if value is None:
            return None

        if isinstance(value, dict):
            try:
                return int(value["x"]), int(value["y"])
            except (KeyError, TypeError, ValueError):
                return None

        if isinstance(value, (list, tuple)) and len(value) == 2:
            try:
                return int(value[0]), int(value[1])
            except (TypeError, ValueError):
                return None

        return None


# ==============================================================
# 3 — Clipboard
# ==============================================================


class ClipboardStrategy(VerificationStrategy):
    """
    Read the clipboard back.

    The strongest verification available for keyboard input: after typing into a
    field, ``Ctrl+A Ctrl+C`` and a clipboard read confirms what actually landed
    in the control, which no keyboard API can report. It is also the only way to
    catch a ``copy`` that was silently lost to another process holding the
    Windows clipboard open.
    """

    method = "clipboard"
    description = "Confirm the clipboard holds the expected text."
    supported_modes = frozenset(
        {
            MatchMode.EQUALS,
            MatchMode.CONTAINS,
            MatchMode.NOT_CONTAINS,
            MatchMode.EXISTS,
            MatchMode.ABSENT,
            MatchMode.CHANGED,
            MatchMode.UNCHANGED,
        }
    )

    async def _check(self, request: VerificationRequest) -> VerificationResult:

        from ...core.container import container
        from ..clipboard.controller import ClipboardService

        service: ClipboardService = container.resolve(ClipboardService)

        return self._compare_text(request, await service.paste_text())


# ==============================================================
# 4 — Process
# ==============================================================


class ProcessStrategy(VerificationStrategy):
    """
    Confirm a process is running, or gone.

    ``target`` is a PID, an executable name, or a substring of either — matching
    is delegated to the process service, which owns that policy.
    """

    method = "process"
    description = "Confirm a process is running or has exited."
    supported_modes = frozenset({MatchMode.EXISTS, MatchMode.ABSENT})

    async def _check(self, request: VerificationRequest) -> VerificationResult:

        from ...core.container import container
        from ..process.controller import ProcessService

        service: ProcessService = container.resolve(ProcessService)

        target = self._require_target(request)

        matches = await service.find(target)

        return self._compare_presence(
            request,
            bool(matches),
            actual=[
                {"pid": item.pid, "name": item.name}
                for item in matches[:5]
            ],
            detail=(
                f"{len(matches)} matching process(es)"
                if matches
                else "no matching process"
            ),
        )


# ==============================================================
# 5 — Window
# ==============================================================


class WindowStrategy(VerificationStrategy):
    """
    Confirm a window exists, is focused, or is in a given state.

    ``expected`` selects what to check: ``"exists"`` / ``"active"`` /
    ``"minimized"`` / ``"maximized"`` / ``"normal"``. This is the verification
    that matters most in practice, because ``SetForegroundWindow`` genuinely
    fails when the calling process does not own the foreground, returns a falsy
    value nobody checks, and leaves keystrokes going to whatever *was* focused.
    """

    method = "window"
    description = "Confirm a window exists, is focused, or is in a given state."
    supported_modes = frozenset({MatchMode.EXISTS, MatchMode.ABSENT, MatchMode.EQUALS})

    async def _check(self, request: VerificationRequest) -> VerificationResult:

        from ...core.container import container
        from ..window.controller import WindowService

        service: WindowService = container.resolve(WindowService)

        target = self._require_target(request)

        matches = await service.find(target)

        if request.mode in (MatchMode.EXISTS, MatchMode.ABSENT):

            return self._compare_presence(
                request,
                bool(matches),
                actual=[window.title for window in matches[:5]],
                detail=(
                    f"{len(matches)} matching window(s)"
                    if matches
                    else "no matching window"
                ),
            )

        # EQUALS — check a specific attribute of the matched window.
        condition = request.describe()
        wanted = str(request.expected or "active").lower()

        if not matches:
            return VerificationResult.failed(
                condition,
                method=self.method,
                expected=wanted,
                actual=None,
                detail=f"no window matched '{target}'",
            )

        window = matches[0]

        if wanted == "active":
            active = await service.active()
            observed = "active" if active and active.handle == window.handle else "inactive"

        else:
            observed = window.state

        builder = (
            VerificationResult.passed
            if observed == wanted
            else VerificationResult.failed
        )

        return builder(
            condition,
            method=self.method,
            expected=wanted,
            actual=observed,
            detail=f"window '{window.title}'",
        )


# ==============================================================
# 6 — File
# ==============================================================


class FileStrategy(VerificationStrategy):
    """
    Confirm a path exists, is gone, or holds the expected content.

    The cheapest and most reliable strategy here: the filesystem answers
    truthfully and immediately, with no timing window. Where a workflow can be
    arranged to leave a file behind as evidence, that beats reading the screen.
    """

    method = "file"
    description = "Confirm a file or folder exists, is absent, or holds given text."
    supported_modes = frozenset(
        {
            MatchMode.EXISTS,
            MatchMode.ABSENT,
            MatchMode.EQUALS,
            MatchMode.CONTAINS,
            MatchMode.NOT_CONTAINS,
        }
    )

    async def _check(self, request: VerificationRequest) -> VerificationResult:

        import asyncio

        from ..safety.paths import PathAccess, path_guard

        target = self._require_target(request)

        path = path_guard.ensure(target, PathAccess.READ)

        exists = await asyncio.to_thread(path.exists)

        if request.mode in (MatchMode.EXISTS, MatchMode.ABSENT):

            return self._compare_presence(
                request,
                exists,
                actual=str(path),
                detail=(
                    f"{'directory' if path.is_dir() else 'file'} present"
                    if exists
                    else "path does not exist"
                ),
            )

        if not exists:
            return VerificationResult.failed(
                request.describe(),
                method=self.method,
                expected=request.expected,
                actual=None,
                detail=f"'{path}' does not exist, so its content cannot match",
            )

        settings = get_settings()

        def read() -> str:
            # Bounded read: a content check against a multi-gigabyte log must not
            # pull the whole file into memory to answer a substring question.
            with path.open("r", encoding="utf-8", errors="replace") as handle:
                return handle.read(settings.DESKTOP_MAX_READ_BYTES)

        return self._compare_text(request, await asyncio.to_thread(read))


# ==============================================================
# 7 — Screen
# ==============================================================


class ScreenStrategy(VerificationStrategy):
    """
    Confirm the screen changed, or did not.

    A blunt instrument, and the right one when nothing else is queryable: after
    a click that should open a menu, "did those pixels change?" is answerable
    where "is the menu open?" is not.

    Compares mean absolute pixel difference against a threshold rather than
    requiring exact equality, because a live desktop is never pixel-identical
    twice — a clock, a caret, an animated tray icon all guarantee drift.
    """

    method = "screen"
    description = "Confirm the screen (or a region) changed after an action."
    supported_modes = frozenset({MatchMode.CHANGED, MatchMode.UNCHANGED})

    #: Mean absolute difference, in 8-bit levels, above which two captures are
    #: considered different. 2.0 sits above caret blink and clock ticks and well
    #: below any real UI transition.
    DEFAULT_THRESHOLD: ClassVar[float] = 2.0

    async def _check(self, request: VerificationRequest) -> VerificationResult:

        import numpy as np

        from ...core.container import container
        from ..screen.controller import ScreenService

        service: ScreenService = container.resolve(ScreenService)

        if request.region:
            left, top, width, height = request.region
            current = await service.capture_region(
                left=left,
                top=top,
                width=width,
                height=height,
            )
        else:
            current = await service.capture()

        baseline = request.baseline

        if baseline is None:
            return VerificationResult.errored(
                request.describe(),
                method=self.method,
                detail=(
                    "screen comparison needs a baseline capture taken before "
                    "the action"
                ),
            )

        baseline_array = np.asarray(baseline)

        if baseline_array.shape != current.shape:
            # A resolution or region change between captures. Reported as a
            # genuine change rather than an error: the screen did change, and
            # saying so is more useful than refusing to answer.
            difference = float("inf")

        else:
            difference = float(
                np.mean(
                    np.abs(
                        baseline_array.astype(np.int16)
                        - current.astype(np.int16)
                    )
                )
            )

        threshold = (
            request.tolerance if request.tolerance > 0 else self.DEFAULT_THRESHOLD
        )

        changed = difference > threshold
        wanted_change = request.mode is MatchMode.CHANGED

        builder = (
            VerificationResult.passed
            if changed is wanted_change
            else VerificationResult.failed
        )

        return builder(
            request.describe(),
            method=self.method,
            expected=request.mode.value,
            actual="changed" if changed else "unchanged",
            detail=(
                f"mean pixel difference {difference:.2f} "
                f"against a threshold of {threshold:.2f}"
                if difference != float("inf")
                else "capture dimensions differ between baseline and current"
            ),
        )


# ==============================================================
# 8 — OCR
# ==============================================================


class OcrStrategy(VerificationStrategy):
    """
    Read the screen with OCR and check for expected text.

    The last resort, and treated as such. It is slow (tens of seconds for a
    full-screen PaddleOCR pass on CPU), it is the only strategy that can produce
    a false negative from a working action — small or anti-aliased text simply is
    not read — and it depends on a model that may not be installed.

    Use it when nothing else can see the result: a dialog with no queryable
    state, a rendered chart, a web page in a browser AetherOS does not control.
    Never use it for something the filesystem or clipboard could confirm.
    """

    method = "ocr"
    description = "Confirm expected text is visible on screen, using OCR."
    supported_modes = frozenset(
        {
            MatchMode.CONTAINS,
            MatchMode.NOT_CONTAINS,
            MatchMode.EQUALS,
            MatchMode.EXISTS,
            MatchMode.ABSENT,
        }
    )

    async def _check(self, request: VerificationRequest) -> VerificationResult:

        from ...core.container import container
        from ..screen.controller import ScreenService
        from ...vision.controller import VisionService
        from ...vision.image import Image

        vision: VisionService = container.resolve(VisionService)

        if not vision.has_ocr:
            return VerificationResult.errored(
                request.describe(),
                method=self.method,
                detail="the OCR provider is not available on this machine",
            )

        screen: ScreenService = container.resolve(ScreenService)

        if request.region:
            left, top, width, height = request.region
            frame = await screen.capture_region(
                left=left,
                top=top,
                width=width,
                height=height,
            )
        else:
            frame = await screen.capture()

        image = Image.from_numpy(frame, source="screen", color_space="bgr")

        blocks = await vision.read_text(image)

        text = " ".join(block.text for block in blocks)

        result = self._compare_text(request, text)

        # OCR text can be a full screen of prose; the detail is truncated so a
        # failure stays readable in a log line and in the model's context.
        excerpt = text if len(text) <= 300 else f"{text[:300]}…"

        return VerificationResult(
            status=result.status,
            condition=result.condition,
            method=self.method,
            expected=result.expected,
            actual=excerpt,
            detail=f"{len(blocks)} text block(s) recognised",
        )


#: Every strategy, keyed by the ``method`` name the ``verify_action`` tool and
#: workflow steps use. Built from the classes rather than hand-listed so a new
#: strategy cannot be added without becoming reachable.
STRATEGIES: dict[str, type[VerificationStrategy]] = {
    strategy.method: strategy
    for strategy in (
        StateStrategy,
        PositionStrategy,
        ClipboardStrategy,
        ProcessStrategy,
        WindowStrategy,
        FileStrategy,
        ScreenStrategy,
        OcrStrategy,
    )
}
