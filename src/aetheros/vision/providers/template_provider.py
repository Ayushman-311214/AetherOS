from __future__ import annotations

import cv2
import numpy as np

from ...core.errors.base_error import ErrorContext
from ...core.errors.vision_error import VisionError
from ..image import Image
from ..models.match import TemplateMatch
from .base import TemplateProvider


class OpenCVTemplateProvider(TemplateProvider):
    """
    Template matching using OpenCV.
    """

    @property
    def name(self) -> str:
        return "OpenCV Template Matching"

    @property
    def version(self) -> str:
        return cv2.__version__

    # ==========================================================
    # Template Matching
    # ==========================================================

    async def find(
        self,
        image: Image,
        template: Image,
        threshold: float = 0.90,
        method: int = cv2.TM_CCOEFF_NORMED,
    ) -> list[TemplateMatch]:
        """
        Find template in image using OpenCV.

        Args:
            image: Source image to search in
            template: Template image to find
            threshold: Confidence threshold (0.0 - 1.0)
            method: OpenCV matching method

        Returns:
            List of matches above threshold
        """

        if not 0.0 <= threshold <= 1.0:
            raise VisionError(
                code="INVALID_ARGUMENT",
                message=(
                    f"Match threshold must be within 0.0-1.0, got {threshold}."
                ),
                context=self._context("find"),
            )

        # matchTemplate requires the template to fit inside the source; it
        # raises a bare cv2.error naming neither image otherwise.
        if (
            template.width > image.width
            or template.height > image.height
        ):
            raise VisionError(
                code="TEMPLATE_TOO_LARGE",
                message=(
                    f"Template ({template.width}x{template.height}) is larger "
                    f"than the search image ({image.width}x{image.height})."
                ),
                context=self._context("find"),
            )

        # Grayscale for matching. Image.gray() picks the conversion from the
        # declared colour space and flattens alpha, so a 4-channel screenshot
        # cannot reach matchTemplate with a channel count the template lacks.
        img_gray = image.gray().data
        template_gray = template.gray().data

        # Perform template matching
        try:
            result = cv2.matchTemplate(
                img_gray,
                template_gray,
                method,
            )

        except cv2.error as exc:
            raise VisionError(
                code="TEMPLATE_MATCH_FAILED",
                message="Template matching failed.",
                context=self._context("find"),
                cause=exc,
            ) from exc

        # Find locations above threshold
        locations = np.where(result >= threshold)

        matches: list[TemplateMatch] = []

        template_height, template_width = template_gray.shape

        # Group nearby matches
        for y, x in zip(*locations):

            confidence = float(result[y, x])

            # Check if this match is too close to existing ones
            is_duplicate = False

            for existing in matches:

                dx = abs(existing.x - x)
                dy = abs(existing.y - y)

                # If within 10 pixels, consider duplicate
                if dx < 10 and dy < 10:
                    # Keep higher confidence match
                    if confidence > existing.confidence:
                        matches.remove(existing)
                    else:
                        is_duplicate = True
                    break

            if not is_duplicate:
                matches.append(
                    TemplateMatch(
                        x=int(x),
                        y=int(y),
                        width=template_width,
                        height=template_height,
                        confidence=confidence,
                    )
                )

        # Sort by confidence
        matches.sort(
            key=lambda m: m.confidence,
            reverse=True,
        )

        return matches

    # ==========================================================
    # Multi-scale Matching
    # ==========================================================

    async def find_multiscale(
        self,
        image: Image,
        template: Image,
        threshold: float = 0.90,
        scales: list[float] | None = None,
    ) -> list[TemplateMatch]:
        """
        Find template at multiple scales.

        Useful when template size might vary.
        """

        if scales is None:
            scales = [0.8, 0.9, 1.0, 1.1, 1.2]

        all_matches: list[TemplateMatch] = []

        for scale in scales:

            # Resize template
            new_width = int(template.width * scale)
            new_height = int(template.height * scale)

            if new_width < 10 or new_height < 10:
                continue

            if new_width > image.width or new_height > image.height:
                continue

            scaled_template = cv2.resize(
                template.data,
                (new_width, new_height),
                interpolation=cv2.INTER_LINEAR,
            )

            scaled_template_img = Image(
                data=scaled_template,
                source=template.source,
                color_space=template.color_space,
            )

            # Find matches at this scale
            matches = await self.find(
                image,
                scaled_template_img,
                threshold,
            )

            all_matches.extend(matches)

        # Remove duplicates and sort
        all_matches.sort(
            key=lambda m: m.confidence,
            reverse=True,
        )

        return all_matches

    # ==========================================================
    # Internal
    # ==========================================================

    @staticmethod
    def _context(operation: str) -> ErrorContext:

        return ErrorContext(
            module="vision.template",
            operation=operation,
            details={"provider": "opencv"},
        )
