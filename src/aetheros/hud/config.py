from __future__ import annotations

import os
from dataclasses import MISSING, dataclass, fields
from functools import lru_cache
from typing import Any

from dotenv import load_dotenv

load_dotenv()


#: Render quality tiers.
#
# "auto" starts at high and steps down if frames are consistently
# late, which is how the 60 FPS target degrades gracefully to 30
# rather than stuttering.
QUALITY_LEVELS = ("low", "medium", "high")


# ==============================================================
# Coercion
# ==============================================================

# The config arrives from environment variables and across a process
# boundary, so any field may be the wrong type. These coerce rather
# than raise: a single bad value must not be able to stop the overlay
# from starting, and must never leave a half-valid config behind.


def _as_bool(value: object, default: bool) -> bool:

    if isinstance(value, bool):
        return value

    if isinstance(value, (int, float)):
        return bool(value)

    if isinstance(value, str):
        text = value.strip().lower()

        if text in ("1", "true", "yes", "on"):
            return True

        if text in ("0", "false", "no", "off"):
            return False

    return default


def _as_int(
    value: object,
    default: int,
    low: int | None = None,
    high: int | None = None,
) -> int:

    try:
        result = int(float(value))  # type: ignore[arg-type]

    except (TypeError, ValueError):
        result = default

    if low is not None:
        result = max(low, result)

    if high is not None:
        result = min(high, result)

    return result


def _as_float(
    value: object,
    default: float,
    low: float | None = None,
    high: float | None = None,
) -> float:

    try:
        result = float(value)  # type: ignore[arg-type]

    except (TypeError, ValueError):
        result = default

    # NaN fails every comparison, so it has to be caught explicitly.
    if result != result:
        result = default

    if low is not None:
        result = max(low, result)

    if high is not None:
        result = min(high, result)

    return result


def _as_text(value: object, default: str) -> str:

    if value is None:
        return default

    text = str(value).strip()

    return text or default


#: Environment variable suffix for each field, under AETHEROS_HUD_.
#
# Values arrive as strings and are coerced by __post_init__, so this
# only has to say which variable maps to which field.
_ENV_FIELDS = {
    "ENABLED": "enabled",
    "POSITION": "position",
    "SIZE": "size",
    "SCALE": "scale",
    "OPACITY": "opacity",
    "MARGIN": "margin",
    "ALWAYS_ON_TOP": "always_on_top",
    "CLICK_THROUGH": "click_through",
    "MOVABLE": "movable",
    "SHOW_TRANSCRIPT": "show_transcript",
    "SHOW_STATUS": "show_status",
    "MAX_TEXT_LENGTH": "max_text_length",
    "QUALITY": "animation_quality",
    "FPS": "fps",
    "THEME": "theme",
}



@dataclass(slots=True)
class HUDConfig:
    """
    Configuration for the JARVIS-style overlay.
    """

    # ----------------------------------------------------------
    # Feature flags
    # ----------------------------------------------------------

    enabled: bool = False

    # ----------------------------------------------------------
    # Placement
    # ----------------------------------------------------------

    #: One of the named anchors, or "x,y" in logical pixels.
    position: str = "bottom-right"

    #: Base size in logical pixels, before `scale`.
    size: int = 340

    scale: float = 1.0

    opacity: float = 0.94

    #: Gap from the screen edge for anchored positions.
    margin: int = 32

    # ----------------------------------------------------------
    # Behaviour
    # ----------------------------------------------------------

    always_on_top: bool = True

    #: Let clicks pass through to whatever is underneath.
    click_through: bool = False

    #: Allow dragging the overlay with the mouse.
    movable: bool = True

    # ----------------------------------------------------------
    # Content
    # ----------------------------------------------------------

    show_transcript: bool = True
    show_status: bool = True

    #: Longest transcript/response line before it is elided.
    max_text_length: int = 72

    # ----------------------------------------------------------
    # Rendering
    # ----------------------------------------------------------

    #: "auto", "low", "medium" or "high".
    animation_quality: str = "auto"

    fps: int = 60

    theme: str = "aether"

    def __post_init__(self) -> None:
        """
        Coerce and clamp every field.

        Runs on every construction path — defaults, `from_env`,
        `from_dict` and the CLI overrides — so nothing downstream has
        to defend against a string where a number belongs. Bounds are
        chosen to keep the overlay usable rather than to be permissive:
        a 4 FPS HUD or a 12-pixel one is not a working feature.
        """

        defaults = _defaults()

        self.enabled = _as_bool(self.enabled, defaults["enabled"])

        self.position = _as_text(self.position, defaults["position"])

        self.size = _as_int(self.size, defaults["size"], 120, 2048)

        self.scale = _as_float(self.scale, defaults["scale"], 0.25, 6.0)

        self.opacity = _as_float(
            self.opacity,
            defaults["opacity"],
            0.15,
            1.0,
        )

        self.margin = _as_int(self.margin, defaults["margin"], 0, 800)

        self.always_on_top = _as_bool(
            self.always_on_top,
            defaults["always_on_top"],
        )

        self.click_through = _as_bool(
            self.click_through,
            defaults["click_through"],
        )

        self.movable = _as_bool(self.movable, defaults["movable"])

        self.show_transcript = _as_bool(
            self.show_transcript,
            defaults["show_transcript"],
        )

        self.show_status = _as_bool(
            self.show_status,
            defaults["show_status"],
        )

        self.max_text_length = _as_int(
            self.max_text_length,
            defaults["max_text_length"],
            16,
            240,
        )

        self.animation_quality = _as_text(
            self.animation_quality,
            defaults["animation_quality"],
        ).lower()

        # Below 15 the animation stops reading as motion; above 144
        # there is nothing left to gain.
        self.fps = _as_int(self.fps, defaults["fps"], 15, 144)

        self.theme = _as_text(self.theme, defaults["theme"])

    @property
    def pixel_size(self) -> int:
        """
        Window edge length in logical pixels.
        """

        return max(160, int(round(self.size * self.scale)))

    @property
    def frame_interval_ms(self) -> int:
        """
        Timer interval for the render loop.
        """

        fps = max(15, min(144, self.fps))

        return max(1, int(round(1000.0 / fps)))

    @property
    def initial_quality(self) -> str:
        """
        Quality tier to start at.
        """

        requested = self.animation_quality.strip().lower()

        if requested in QUALITY_LEVELS:
            return requested

        return "high"

    @property
    def adaptive_quality(self) -> bool:
        """
        Whether quality may be reduced automatically.
        """

        return self.animation_quality.strip().lower() not in QUALITY_LEVELS

    # ==========================================================
    # Environment
    # ==========================================================

    @classmethod
    def from_env(
        cls,
        prefix: str = "AETHEROS_HUD_",
    ) -> HUDConfig:
        """
        Build a configuration from AETHEROS_HUD_* variables.

        Unset and blank variables are simply omitted, so each field
        falls back to its declared default; everything present is
        coerced by __post_init__. A malformed variable therefore
        degrades that one field rather than the whole overlay.
        """

        present: dict[str, str] = {}

        for suffix, name in _ENV_FIELDS.items():

            raw = os.getenv(prefix + suffix)

            if raw is not None and raw.strip():
                present[name] = raw.strip()

        return cls(**present)  # type: ignore[arg-type]

    # ==========================================================
    # Serialization
    # ==========================================================

    def to_dict(self) -> dict[str, object]:
        """
        Flatten for transport to the render process.
        """

        return {
            item.name: getattr(self, item.name)
            for item in fields(self)
        }

    @classmethod
    def from_dict(
        cls,
        data: dict[str, object],
    ) -> HUDConfig:
        """
        Rebuild from to_dict(), ignoring unknown keys.

        Values are coerced by __post_init__, so a malformed field falls
        back to its default instead of poisoning the config. That
        matters because this is a process boundary: the sender may be a
        different version, or a hand-edited environment.
        """

        known = _defaults()

        return cls(
            **{
                key: value
                for key, value in data.items()
                if key in known
            }  # type: ignore[arg-type]
        )


@lru_cache(maxsize=1)
def _defaults() -> dict[str, Any]:
    """
    Every field's declared default.

    Derived from the dataclass rather than written out again, so the
    coercion fallbacks cannot drift away from the declarations above.
    """

    return {
        item.name: item.default
        for item in fields(HUDConfig)
        if item.default is not MISSING
    }


__all__ = [
    "QUALITY_LEVELS",
    "HUDConfig",
]
