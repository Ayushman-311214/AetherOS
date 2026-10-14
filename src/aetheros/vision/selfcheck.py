"""
Deterministic images for verifying the vision pipeline.

The OCR path cannot be trusted on the strength of "it imported successfully" —
the provider previously returned an empty list for every image while raising no
error at all. Proving the pipeline works needs an image whose text is known in
advance, and generating it in code rather than committing a PNG keeps the check
reproducible and reviewable.

Used by both ``python -m aetheros.vision.main`` and the integration tests, so
the two agree on exactly what "working" means.
"""

from __future__ import annotations

import cv2
import numpy as np

from .image import Image

# High-contrast black-on-white block capitals in a stroke font: the easiest case
# any OCR engine has, chosen so a failure means the pipeline is broken rather
# than that the image was hard to read.
REFERENCE_LINES: tuple[str, ...] = (
    "AETHEROS",
    "VISION TEST",
    "HELLO WORLD",
)


def render_text_image(
    lines: tuple[str, ...] | list[str] = REFERENCE_LINES,
    width: int = 640,
    line_height: int = 90,
    font_scale: float = 1.6,
    thickness: int = 3,
) -> Image:
    """
    Render lines of text onto a white background.

    Returns a BGR :class:`Image`. Output depends only on the arguments and the
    OpenCV version, so the same call always produces the same pixels.
    """

    if not lines:
        raise ValueError("At least one line of text is required.")

    height = line_height * len(lines) + line_height // 2

    canvas = np.full(
        (height, width, 3),
        255,
        dtype=np.uint8,
    )

    for index, line in enumerate(lines):

        baseline = line_height * (index + 1)

        cv2.putText(
            canvas,
            line,
            (30, baseline),
            cv2.FONT_HERSHEY_SIMPLEX,
            font_scale,
            (0, 0, 0),
            thickness,
            cv2.LINE_AA,
        )

    return Image.from_numpy(
        canvas,
        source="selfcheck",
        color_space="bgr",
    )


def reference_image() -> Image:
    """
    The canonical verification image containing :data:`REFERENCE_LINES`.
    """

    return render_text_image(REFERENCE_LINES)


def expected_words() -> set[str]:
    """
    Every word the reference image contains, upper-cased.
    """

    return {
        word
        for line in REFERENCE_LINES
        for word in line.split()
    }


def recognised_words(text: str) -> set[str]:
    """
    Normalise recognised text for comparison against :func:`expected_words`.

    Case and punctuation are dropped. OCR output varies in both between engine
    versions, and an assertion that pins them would fail for a reason that has
    nothing to do with whether the pipeline works.
    """

    cleaned = "".join(
        character if character.isalnum() else " "
        for character in text.upper()
    )

    return {word for word in cleaned.split() if word}
