from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal

import cv2
import numpy as np
from PIL import Image as PILImage

from ..core.errors.base_error import ErrorContext
from ..core.errors.vision_error import VisionError

# Which channel order ``Image.data`` is actually in.
#
# Without this the conversion helpers cannot be correct: `cvtColor(BGR2RGB)` and
# `cvtColor(RGB2BGR)` are the *same* permutation, so a helper that only looks at
# the channel count will happily swap red and blue a second time and report
# success. Every consumer in the engine (OpenCV, PaddleOCR, PaddleX) treats a
# bare numpy array as BGR, so BGR is the default and the pipeline's invariant.
ColorSpace = Literal["bgr", "rgb", "gray"]

_VALID_COLOR_SPACES: frozenset[str] = frozenset({"bgr", "rgb", "gray"})


@dataclass(slots=True)
class Image:
    """
    Universal image model for AetherOS.

    Every vision module should consume and return this class.

    Invariants, enforced at construction
    ------------------------------------
    - ``data`` is a non-empty ``numpy.ndarray``
    - ``data.ndim`` is 2 (single channel) or 3 (1, 3 or 4 channels)
    - ``color_space`` describes ``data``'s channel order and agrees with its
      channel count; when omitted it is inferred from the channel count

    Construction raises :class:`VisionError` rather than allowing a malformed
    image to travel down the pipeline and fail later inside OpenCV, where the
    message no longer says which capture or file was at fault.
    """

    data: np.ndarray

    source: str = "unknown"

    # Defaults to None, which means "infer": single-channel data has no channel
    # order to declare, so requiring the caller to spell out "gray" would be
    # ceremony — and would make Image.from_numpy(cv2.imread(p, 0)) fail. Never
    # None after construction; __post_init__ resolves it to a real ColorSpace.
    color_space: ColorSpace | None = None

    timestamp: datetime = field(
        default_factory=lambda: datetime.now(UTC)
    )

    metadata: dict[str, Any] = field(
        default_factory=dict
    )

    # ==========================================================
    # Validation
    # ==========================================================

    def __post_init__(self) -> None:

        if self.data is None:
            raise VisionError(
                code="INVALID_IMAGE",
                message="Image data is None.",
                hint="A capture or file load returned nothing.",
                context=self._context("validate"),
            )

        if not isinstance(self.data, np.ndarray):
            raise VisionError(
                code="INVALID_IMAGE",
                message=(
                    f"Image data must be a numpy array, "
                    f"got {type(self.data).__name__}."
                ),
                hint="Use Image.open() for files or Image.from_numpy() for arrays.",
                context=self._context("validate"),
            )

        if self.data.ndim not in (2, 3):
            raise VisionError(
                code="INVALID_IMAGE",
                message=(
                    f"Image data must be 2- or 3-dimensional, "
                    f"got shape {self.data.shape}."
                ),
                context=self._context("validate"),
            )

        if self.data.size == 0:
            raise VisionError(
                code="EMPTY_IMAGE",
                message=f"Image has no pixels (shape {self.data.shape}).",
                context=self._context("validate"),
            )

        if self.data.ndim == 3 and self.data.shape[2] not in (1, 3, 4):
            raise VisionError(
                code="INVALID_IMAGE",
                message=(
                    f"Unsupported channel count {self.data.shape[2]}; "
                    f"expected 1, 3 or 4."
                ),
                context=self._context("validate"),
            )

        if self.color_space is None:
            # Only the 3/4-channel case is genuinely ambiguous, and BGR is the
            # pipeline's documented default there.
            self.color_space = (
                "gray"
                if self.channels == 1
                else "bgr"
            )

        if self.color_space not in _VALID_COLOR_SPACES:
            raise VisionError(
                code="INVALID_COLOR_SPACE",
                message=(
                    f"Unknown color space {self.color_space!r}; "
                    f"expected one of {sorted(_VALID_COLOR_SPACES)}."
                ),
                context=self._context("validate"),
            )

        if self.color_space == "gray" and self.channels != 1:
            raise VisionError(
                code="INVALID_COLOR_SPACE",
                message=(
                    f"color_space='gray' requires a single channel, "
                    f"got {self.channels}."
                ),
                context=self._context("validate"),
            )

        if self.color_space in ("bgr", "rgb") and self.channels == 1:
            raise VisionError(
                code="INVALID_COLOR_SPACE",
                message=(
                    f"color_space={self.color_space!r} requires 3 or 4 "
                    f"channels; use 'gray' for single-channel data."
                ),
                context=self._context("validate"),
            )

    # ==========================================================
    # Properties
    # ==========================================================

    @property
    def width(self) -> int:
        return int(self.data.shape[1])

    @property
    def height(self) -> int:
        return int(self.data.shape[0])

    @property
    def channels(self) -> int:
        if self.data.ndim == 2:
            return 1

        return int(self.data.shape[2])

    @property
    def shape(self) -> tuple[int, ...]:
        return self.data.shape

    @property
    def has_alpha(self) -> bool:
        return self.channels == 4

    # ==========================================================
    # Color Space
    # ==========================================================

    def rgb(self) -> "Image":
        """
        Return this image with RGB channel order.

        Idempotent: an image already in RGB, or single-channel data with no
        channel order to swap, is returned unchanged.
        """

        if self.color_space != "bgr":
            return self

        code = (
            cv2.COLOR_BGRA2RGB
            if self.has_alpha
            else cv2.COLOR_BGR2RGB
        )

        return self._derive(
            cv2.cvtColor(self.data, code),
            color_space="rgb",
        )

    def bgr(self) -> "Image":
        """
        Return this image with BGR channel order — the pipeline default.

        Idempotent, for the same reason as :meth:`rgb`.
        """

        if self.color_space != "rgb":
            return self

        code = (
            cv2.COLOR_RGBA2BGR
            if self.has_alpha
            else cv2.COLOR_RGB2BGR
        )

        return self._derive(
            cv2.cvtColor(self.data, code),
            color_space="bgr",
        )

    def gray(self) -> "Image":
        """
        Return a single-channel copy.
        """

        if self.color_space == "gray":
            return self

        code = _GRAY_CONVERSIONS[(self.color_space, self.has_alpha)]

        return self._derive(
            cv2.cvtColor(self.data, code),
            color_space="gray",
        )

    def without_alpha(self) -> "Image":
        """
        Drop the alpha channel, keeping the channel order.

        PaddleOCR and most OpenCV operations reject 4-channel input, so a
        screenshot or PNG carrying transparency has to be flattened before it
        reaches them.
        """

        if not self.has_alpha:
            return self

        return self._derive(
            np.ascontiguousarray(self.data[:, :, :3]),
            color_space=self.color_space,
        )

    # ==========================================================
    # Resize
    # ==========================================================

    def resize(
        self,
        width: int,
        height: int,
    ) -> "Image":

        if width <= 0 or height <= 0:
            raise VisionError(
                code="INVALID_ARGUMENT",
                message=(
                    f"Resize target must be positive, got {width}x{height}."
                ),
                context=self._context("resize"),
            )

        return self._derive(
            cv2.resize(self.data, (width, height))
        )

    # ==========================================================
    # Crop
    # ==========================================================

    def crop(
        self,
        x: int,
        y: int,
        width: int,
        height: int,
    ) -> "Image":

        if width <= 0 or height <= 0:
            raise VisionError(
                code="INVALID_ARGUMENT",
                message=(
                    f"Crop size must be positive, got {width}x{height}."
                ),
                context=self._context("crop"),
            )

        # Checked here rather than left to numpy: slicing out of bounds returns
        # a silently empty array, and the resulting error would name neither the
        # requested rectangle nor the image it came from.
        if (
            x < 0
            or y < 0
            or x + width > self.width
            or y + height > self.height
        ):
            raise VisionError(
                code="INVALID_ARGUMENT",
                message=(
                    f"Crop ({x},{y},{width},{height}) falls outside a "
                    f"{self.width}x{self.height} image."
                ),
                context=self._context("crop"),
            )

        return self._derive(
            self.data[y:y + height, x:x + width]
        )

    # ==========================================================
    # Copy
    # ==========================================================

    def copy(self) -> "Image":

        return self._derive(self.data.copy())

    # ==========================================================
    # Save
    # ==========================================================

    def save(
        self,
        path: str | Path,
    ) -> None:
        """
        Write the image to disk with its colours intact.
        """

        target = Path(path)

        if not target.parent.exists():
            raise VisionError(
                code="SAVE_FAILED",
                message=f"Directory does not exist: {target.parent}",
                context=self._context("save"),
            )

        try:
            self.to_pillow().save(target)

        except OSError as exc:
            raise VisionError(
                code="SAVE_FAILED",
                message=f"Could not write image to {target}.",
                context=self._context("save"),
                cause=exc,
            ) from exc

    # ==========================================================
    # Conversion
    # ==========================================================

    def to_numpy(self) -> np.ndarray:

        return self.data

    def to_pillow(self) -> PILImage.Image:
        """
        Convert to a Pillow image.

        Pillow interprets arrays as RGB(A) or L, so BGR data is reordered
        first — otherwise every saved or displayed frame has red and blue
        swapped.
        """

        if self.color_space == "gray":
            return PILImage.fromarray(
                self.data
                if self.data.ndim == 2
                else self.data[:, :, 0]
            )

        return PILImage.fromarray(self.rgb().data)

    # ==========================================================
    # Constructors
    # ==========================================================

    @classmethod
    def from_numpy(
        cls,
        array: np.ndarray,
        source: str = "numpy",
        color_space: ColorSpace | None = None,
    ) -> "Image":
        """
        Wrap a raw array.

        ``color_space`` is inferred when omitted: single channel becomes
        ``"gray"``, and anything wider becomes BGR — matching what screen-capture
        backends and ``cv2.imread`` produce. Pass ``"rgb"`` explicitly for
        anything that came out of Pillow.
        """

        return cls(
            data=array,
            source=source,
            color_space=color_space,
        )

    @classmethod
    def open(
        cls,
        path: str | Path,
    ) -> "Image":
        """
        Load an image file, normalised to 3-channel BGR ``uint8``.

        Pillow decodes to RGB, palette, greyscale or RGBA depending on the file,
        and returns 16-bit data for some PNGs. Every one of those reaches the
        rest of the engine as BGR uint8 so no consumer has to branch on what the
        file happened to contain.
        """

        target = Path(path)

        if not target.exists():
            raise VisionError(
                code="IMAGE_NOT_FOUND",
                message=f"Image file does not exist: {target}",
                context=ErrorContext(
                    module="vision",
                    operation="open",
                    details={"path": str(target)},
                ),
            )

        try:
            with PILImage.open(target) as handle:
                # PIL is lazy; load() forces the decode while the handle is
                # open, and converting normalises palette/greyscale/16-bit.
                rgb = handle.convert("RGB")
                array = np.asarray(rgb, dtype=np.uint8)

        except VisionError:
            raise

        except Exception as exc:
            raise VisionError(
                code="IMAGE_LOAD_FAILED",
                message=f"Could not decode image file: {target}",
                hint="The file may be truncated or not an image.",
                context=ErrorContext(
                    module="vision",
                    operation="open",
                    details={"path": str(target)},
                ),
                cause=exc,
            ) from exc

        return cls(
            data=cv2.cvtColor(array, cv2.COLOR_RGB2BGR),
            source=str(target),
            color_space="bgr",
        )

    # ==========================================================
    # Internal
    # ==========================================================

    def _derive(
        self,
        data: np.ndarray,
        color_space: ColorSpace | None = None,
    ) -> "Image":
        """
        Build a new Image from transformed pixels, carrying provenance over.
        """

        return Image(
            data=data,
            source=self.source,
            color_space=color_space or self.color_space,
            metadata=self.metadata.copy(),
        )

    def _context(
        self,
        operation: str,
    ) -> ErrorContext:

        return ErrorContext(
            module="vision",
            operation=operation,
            details={"source": self.source},
        )

    # ==========================================================
    # Representation
    # ==========================================================

    def __repr__(self) -> str:

        return (
            f"Image("
            f"{self.width}x{self.height}, "
            f"channels={self.channels}, "
            f"color_space='{self.color_space}', "
            f"source='{self.source}')"
        )


# (color_space, has_alpha) -> OpenCV conversion code.
_GRAY_CONVERSIONS: dict[tuple[str, bool], int] = {
    ("bgr", False): cv2.COLOR_BGR2GRAY,
    ("bgr", True): cv2.COLOR_BGRA2GRAY,
    ("rgb", False): cv2.COLOR_RGB2GRAY,
    ("rgb", True): cv2.COLOR_RGBA2GRAY,
}
