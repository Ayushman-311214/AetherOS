"""
Unit tests for the vision Image model.

Image is the type every other vision component consumes, so its invariants are
tested first: a malformed image that gets past construction fails much later,
inside OpenCV or a model, with an error that names neither the capture nor the
file it came from.

The colour-space tests are the important ones. ``cvtColor(BGR2RGB)`` and
``cvtColor(RGB2BGR)`` are the same permutation, so a conversion helper that
branches on channel count alone will swap red and blue twice and report success.
Only a test that checks actual pixel values catches that.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from aetheros.core.errors.vision_error import VisionError
from aetheros.vision.image import Image


# ============================================================================
# Construction and validation
# ============================================================================


class TestImageValidation:
    def test_rejects_none_data(self):
        with pytest.raises(VisionError) as excinfo:
            Image(data=None)  # type: ignore[arg-type]

        assert excinfo.value.code == "VISION_INVALID_IMAGE"

    def test_rejects_non_array(self):
        with pytest.raises(VisionError) as excinfo:
            Image(data=[[1, 2], [3, 4]])  # type: ignore[arg-type]

        assert excinfo.value.code == "VISION_INVALID_IMAGE"
        assert "numpy" in excinfo.value.message

    def test_rejects_one_dimensional_data(self):
        with pytest.raises(VisionError) as excinfo:
            Image(data=np.zeros(10, dtype=np.uint8))

        assert excinfo.value.code == "VISION_INVALID_IMAGE"

    def test_rejects_four_dimensional_data(self):
        with pytest.raises(VisionError) as excinfo:
            Image(data=np.zeros((2, 2, 2, 3), dtype=np.uint8))

        assert excinfo.value.code == "VISION_INVALID_IMAGE"

    def test_rejects_empty_image(self):
        with pytest.raises(VisionError) as excinfo:
            Image(data=np.zeros((0, 10, 3), dtype=np.uint8))

        assert excinfo.value.code == "VISION_EMPTY_IMAGE"

    def test_rejects_unsupported_channel_count(self):
        with pytest.raises(VisionError) as excinfo:
            Image(data=np.zeros((4, 4, 2), dtype=np.uint8))

        assert excinfo.value.code == "VISION_INVALID_IMAGE"

    def test_rejects_unknown_color_space(self):
        with pytest.raises(VisionError) as excinfo:
            Image(
                data=np.zeros((4, 4, 3), dtype=np.uint8),
                color_space="hsv",  # type: ignore[arg-type]
            )

        assert excinfo.value.code == "VISION_INVALID_COLOR_SPACE"

    def test_rejects_gray_with_three_channels(self):
        with pytest.raises(VisionError) as excinfo:
            Image(
                data=np.zeros((4, 4, 3), dtype=np.uint8),
                color_space="gray",
            )

        assert excinfo.value.code == "VISION_INVALID_COLOR_SPACE"

    def test_rejects_bgr_with_one_channel(self):
        with pytest.raises(VisionError) as excinfo:
            Image(
                data=np.zeros((4, 4), dtype=np.uint8),
                color_space="bgr",
            )

        assert excinfo.value.code == "VISION_INVALID_COLOR_SPACE"

    def test_error_context_names_the_source(self):
        with pytest.raises(VisionError) as excinfo:
            Image(
                data=np.zeros((0, 0, 3), dtype=np.uint8),
                source="screen",
            )

        assert excinfo.value.context.details["source"] == "screen"


class TestColorSpaceInference:
    """
    A single-channel array has no channel order, so it should not need one
    spelled out. Anything wider defaults to BGR, the pipeline's invariant.
    """

    def test_two_dimensional_data_infers_gray(self):
        image = Image(data=np.zeros((4, 4), dtype=np.uint8))

        assert image.color_space == "gray"

    def test_single_channel_three_dimensional_infers_gray(self):
        image = Image(data=np.zeros((4, 4, 1), dtype=np.uint8))

        assert image.color_space == "gray"

    def test_three_channel_data_infers_bgr(self):
        image = Image(data=np.zeros((4, 4, 3), dtype=np.uint8))

        assert image.color_space == "bgr"

    def test_from_numpy_infers_too(self):
        assert Image.from_numpy(
            np.zeros((4, 4), dtype=np.uint8)
        ).color_space == "gray"

    def test_explicit_color_space_is_respected(self):
        image = Image(
            data=np.zeros((4, 4, 3), dtype=np.uint8),
            color_space="rgb",
        )

        assert image.color_space == "rgb"


# ============================================================================
# Geometry
# ============================================================================


class TestImageGeometry:
    def test_properties(self, bgr_image: Image):
        assert bgr_image.width == 12
        assert bgr_image.height == 8
        assert bgr_image.channels == 3
        assert bgr_image.shape == (8, 12, 3)
        assert bgr_image.has_alpha is False

    def test_alpha_detection(self):
        image = Image(data=np.zeros((4, 4, 4), dtype=np.uint8))

        assert image.channels == 4
        assert image.has_alpha is True

    def test_resize_rejects_zero(self, bgr_image: Image):
        with pytest.raises(VisionError) as excinfo:
            bgr_image.resize(0, 10)

        assert excinfo.value.code == "VISION_INVALID_ARGUMENT"

    def test_resize_rejects_negative(self, bgr_image: Image):
        with pytest.raises(VisionError):
            bgr_image.resize(10, -1)

    def test_crop_rejects_out_of_bounds(self, bgr_image: Image):
        # numpy would return a silently empty array here rather than raising.
        with pytest.raises(VisionError) as excinfo:
            bgr_image.crop(x=10, y=0, width=10, height=4)

        assert excinfo.value.code == "VISION_INVALID_ARGUMENT"
        assert "12x8" in excinfo.value.message

    def test_crop_rejects_negative_origin(self, bgr_image: Image):
        with pytest.raises(VisionError):
            bgr_image.crop(x=-1, y=0, width=2, height=2)

    def test_crop_rejects_zero_size(self, bgr_image: Image):
        with pytest.raises(VisionError):
            bgr_image.crop(x=0, y=0, width=0, height=2)

    def test_crop_at_exact_boundary_is_allowed(self, bgr_image: Image):
        cropped = bgr_image.crop(x=2, y=1, width=10, height=7)

        assert (cropped.width, cropped.height) == (10, 7)

    def test_derived_image_keeps_provenance(self, bgr_image: Image):
        resized = bgr_image.resize(4, 4)

        assert resized.source == bgr_image.source
        assert resized.color_space == bgr_image.color_space


# ============================================================================
# Colour space conversion
# ============================================================================


class TestColorConversion:
    def test_bgr_to_rgb_swaps_channels(self, bgr_image: Image):
        converted = bgr_image.rgb()

        assert converted.color_space == "rgb"
        # Source was B=10, G=20, R=30.
        assert converted.data[0, 0, 0] == 30
        assert converted.data[0, 0, 1] == 20
        assert converted.data[0, 0, 2] == 10

    def test_rgb_is_idempotent(self, bgr_image: Image):
        """
        The double-swap regression: calling rgb() twice must not swap back.
        """

        once = bgr_image.rgb()
        twice = once.rgb()

        assert twice.color_space == "rgb"
        assert np.array_equal(once.data, twice.data)

    def test_bgr_is_idempotent(self, bgr_image: Image):
        assert np.array_equal(
            bgr_image.bgr().data,
            bgr_image.data,
        )

    def test_round_trip_restores_original(self, bgr_image: Image):
        restored = bgr_image.rgb().bgr()

        assert restored.color_space == "bgr"
        assert np.array_equal(restored.data, bgr_image.data)

    def test_gray_from_bgr(self, bgr_image: Image):
        gray = bgr_image.gray()

        assert gray.channels == 1
        assert gray.color_space == "gray"

    def test_gray_is_idempotent(self, bgr_image: Image):
        once = bgr_image.gray()

        assert once.gray() is once

    def test_gray_respects_channel_order(self, bgr_image: Image):
        """
        Luminance is weighted per channel, so a BGR array read as RGB produces a
        different grey. The two must not agree.
        """

        as_bgr = bgr_image.gray()

        as_rgb = Image(
            data=bgr_image.data.copy(),
            color_space="rgb",
        ).gray()

        assert as_bgr.data[0, 0] != as_rgb.data[0, 0]

    def test_without_alpha_drops_the_channel(self):
        data = np.zeros((4, 4, 4), dtype=np.uint8)
        data[:, :, 3] = 255

        flattened = Image(data=data).without_alpha()

        assert flattened.channels == 3
        assert flattened.color_space == "bgr"

    def test_without_alpha_is_a_noop_for_three_channels(
        self,
        bgr_image: Image,
    ):
        assert bgr_image.without_alpha() is bgr_image

    def test_rgb_from_bgra_drops_alpha(self):
        data = np.zeros((4, 4, 4), dtype=np.uint8)
        data[:, :, 2] = 200

        converted = Image(data=data).rgb()

        assert converted.channels == 3
        assert converted.data[0, 0, 0] == 200


# ============================================================================
# Copying
# ============================================================================


class TestImageCopy:
    def test_copy_is_independent(self, bgr_image: Image):
        duplicate = bgr_image.copy()
        duplicate.data[0, 0, 0] = 255

        assert bgr_image.data[0, 0, 0] == 10

    def test_copy_keeps_color_space(self):
        image = Image(
            data=np.zeros((4, 4, 3), dtype=np.uint8),
            color_space="rgb",
        )

        assert image.copy().color_space == "rgb"


# ============================================================================
# Disk round trip
# ============================================================================


class TestImageDisk:
    def test_open_missing_file(self, tmp_path: Path):
        with pytest.raises(VisionError) as excinfo:
            Image.open(tmp_path / "nope.png")

        assert excinfo.value.code == "VISION_IMAGE_NOT_FOUND"

    def test_open_malformed_file(self, tmp_path: Path):
        target = tmp_path / "broken.png"
        target.write_bytes(b"this is not a PNG")

        with pytest.raises(VisionError) as excinfo:
            Image.open(target)

        assert excinfo.value.code == "VISION_IMAGE_LOAD_FAILED"
        assert excinfo.value.cause is not None

    def test_save_to_missing_directory(
        self,
        bgr_image: Image,
        tmp_path: Path,
    ):
        with pytest.raises(VisionError) as excinfo:
            bgr_image.save(tmp_path / "absent" / "out.png")

        assert excinfo.value.code == "VISION_SAVE_FAILED"

    def test_round_trip_preserves_colours(
        self,
        bgr_image: Image,
        tmp_path: Path,
    ):
        """
        The end-to-end check for the colour-space contract.

        Pillow writes RGB, so a save that skips the reorder — or an open that
        skips it — comes back with red and blue exchanged. PNG is lossless, so
        the comparison can be exact.
        """

        target = tmp_path / "round_trip.png"

        bgr_image.save(target)
        reloaded = Image.open(target)

        assert reloaded.color_space == "bgr"
        assert np.array_equal(reloaded.data, bgr_image.data)

    def test_open_normalises_grayscale_file(self, tmp_path: Path):
        target = tmp_path / "gray.png"

        Image(
            data=np.full((6, 6), 128, dtype=np.uint8),
        ).save(target)

        reloaded = Image.open(target)

        # Normalised to 3-channel BGR so no downstream consumer has to branch on
        # what the file happened to contain.
        assert reloaded.channels == 3
        assert reloaded.color_space == "bgr"

    def test_to_pillow_uses_rgb(self, bgr_image: Image):
        pillow = bgr_image.to_pillow()

        assert pillow.mode == "RGB"
        assert pillow.size == (12, 8)
        # B=10, G=20, R=30 in the source -> R first for Pillow.
        assert pillow.getpixel((0, 0)) == (30, 20, 10)

    def test_to_pillow_handles_gray(self):
        pillow = Image(
            data=np.full((4, 4), 90, dtype=np.uint8),
        ).to_pillow()

        assert pillow.mode == "L"

    def test_to_numpy_returns_the_buffer(self, bgr_image: Image):
        assert bgr_image.to_numpy() is bgr_image.data


def test_repr_is_informative(bgr_image: Image):
    text = repr(bgr_image)

    assert "12x8" in text
    assert "bgr" in text
    assert "fixture" in text
