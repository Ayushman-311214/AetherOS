from __future__ import annotations

from dataclasses import dataclass, replace

#: An 8-bit RGB triple. Deliberately not a QColor: the theme is
# imported by the parent process (and by tests) where Qt may not be
# loaded at all, so the renderer converts these at the boundary.
RGB = tuple[int, int, int]


@dataclass(frozen=True, slots=True)
class StateStyle:
    """
    How one state looks and moves.

    Every animated quantity a layer needs is a field here, so the
    difference between IDLE and THINKING is data rather than branching
    scattered through the renderer.
    """

    #: Text shown under the core.
    label: str

    #: Dominant energy colour.
    primary: RGB

    #: Warm counterpoint, used sparingly for highlights and ticks.
    secondary: RGB

    #: Colour of the outer bloom.
    glow: RGB

    # ----------------------------------------------------------
    # Core
    # ----------------------------------------------------------

    #: Core radius as a fraction of the half-width.
    core_scale: float = 0.17

    #: Breathing cycles per second, and how deep the breath is.
    breath_rate: float = 0.22
    breath_depth: float = 0.06

    #: Overall bloom strength, 0..1.
    glow_intensity: float = 0.55

    # ----------------------------------------------------------
    # Rings
    # ----------------------------------------------------------

    #: Base rotation speed in degrees per second.
    ring_speed: float = 8.0

    #: Opacity multiplier for the technical ring group.
    ring_intensity: float = 0.5

    #: Expanding pulse rings per second. Zero disables them.
    pulse_rate: float = 0.0

    # ----------------------------------------------------------
    # Particles
    # ----------------------------------------------------------

    #: Fraction of the particle budget that is visible, 0..1.
    particle_intensity: float = 0.35

    #: Orbital speed multiplier.
    particle_speed: float = 0.35

    #: How far particles drift outward from their base orbit.
    particle_spread: float = 0.08

    # ----------------------------------------------------------
    # Waveform
    # ----------------------------------------------------------

    #: Radial waveform strength, 0..1. Zero hides the waveform.
    waveform_gain: float = 0.0

    #: How much live amplitude modulates the core, 0..1.
    amplitude_response: float = 0.0


@dataclass(frozen=True, slots=True)
class Theme:
    """
    A complete visual identity for the overlay.
    """

    name: str

    #: Background wash. Alpha is applied separately so the window can
    # stay genuinely transparent at the corners.
    background: RGB

    #: Text colours.
    text: RGB
    text_dim: RGB

    #: Fallback used for any state without an explicit style.
    default: StateStyle

    #: Per-state overrides, keyed by state name.
    states: dict[str, StateStyle]

    def style(self, state: str) -> StateStyle:
        """
        Resolve the style for a state name.
        """

        return self.states.get(state.upper(), self.default)


# ==============================================================
# Palette
# ==============================================================

#: Cool energy: the system's resting identity.
_CYAN: RGB = (34, 211, 238)
_CYAN_BRIGHT: RGB = (125, 240, 255)
_BLUE: RGB = (56, 132, 255)
_INDIGO: RGB = (120, 116, 255)

#: Warm counterpoint. Used at low coverage, as accent only.
_AMBER: RGB = (255, 176, 74)
_GOLD: RGB = (255, 214, 140)

#: Fault colour: readable, not alarming.
_ROSE: RGB = (255, 106, 122)


_IDLE = StateStyle(
    label="IDLE",
    primary=_CYAN,
    secondary=_AMBER,
    glow=_BLUE,
    core_scale=0.155,
    breath_rate=0.20,
    breath_depth=0.075,
    glow_intensity=0.42,
    ring_speed=6.0,
    ring_intensity=0.34,
    particle_intensity=0.28,
    particle_speed=0.22,
    particle_spread=0.05,
)


_LISTENING = StateStyle(
    label="LISTENING",
    primary=_CYAN_BRIGHT,
    secondary=_GOLD,
    glow=_CYAN,
    core_scale=0.185,
    breath_rate=0.9,
    breath_depth=0.05,
    glow_intensity=0.82,
    ring_speed=16.0,
    ring_intensity=0.78,
    # Expanding rings read as "receiving".
    pulse_rate=1.15,
    particle_intensity=0.72,
    particle_speed=0.5,
    particle_spread=0.14,
    waveform_gain=1.0,
    amplitude_response=0.85,
)


_TRANSCRIBING = StateStyle(
    label="TRANSCRIBING",
    primary=(90, 200, 255),
    secondary=_GOLD,
    glow=_BLUE,
    core_scale=0.165,
    breath_rate=1.6,
    breath_depth=0.035,
    glow_intensity=0.58,
    ring_speed=34.0,
    ring_intensity=0.6,
    particle_intensity=0.45,
    particle_speed=0.7,
    particle_spread=0.07,
    waveform_gain=0.22,
)


_THINKING = StateStyle(
    label="THINKING",
    primary=_INDIGO,
    secondary=_AMBER,
    glow=(80, 96, 255),
    core_scale=0.17,
    breath_rate=0.7,
    breath_depth=0.055,
    glow_intensity=0.72,
    # Fast counter-rotating rings plus orbiting particles: the
    # reasoning state should look like machinery working.
    ring_speed=52.0,
    ring_intensity=0.88,
    pulse_rate=0.5,
    particle_intensity=0.95,
    particle_speed=1.25,
    particle_spread=0.2,
)


_EXECUTING = StateStyle(
    label="EXECUTING",
    primary=_AMBER,
    secondary=_CYAN_BRIGHT,
    glow=(255, 138, 44),
    core_scale=0.19,
    breath_rate=2.4,
    breath_depth=0.06,
    glow_intensity=0.95,
    ring_speed=96.0,
    ring_intensity=1.0,
    pulse_rate=2.1,
    particle_intensity=1.0,
    particle_speed=2.0,
    particle_spread=0.26,
)


_SPEAKING = StateStyle(
    label="SPEAKING",
    primary=_CYAN_BRIGHT,
    secondary=_GOLD,
    glow=_CYAN,
    core_scale=0.175,
    breath_rate=0.5,
    breath_depth=0.03,
    glow_intensity=0.85,
    ring_speed=22.0,
    ring_intensity=0.72,
    particle_intensity=0.6,
    particle_speed=0.6,
    particle_spread=0.12,
    waveform_gain=1.0,
    # Speech should visibly drive the geometry.
    amplitude_response=1.0,
)


_ERROR = StateStyle(
    label="ERROR",
    primary=_ROSE,
    secondary=_GOLD,
    glow=(200, 60, 90),
    core_scale=0.16,
    breath_rate=1.1,
    breath_depth=0.05,
    glow_intensity=0.6,
    ring_speed=10.0,
    ring_intensity=0.5,
    particle_intensity=0.2,
    particle_speed=0.2,
    particle_spread=0.04,
)


AETHER_THEME = Theme(
    name="aether",
    background=(4, 8, 16),
    text=(214, 242, 252),
    text_dim=(122, 158, 178),
    default=_IDLE,
    states={
        "IDLE": _IDLE,
        "LISTENING": _LISTENING,
        "TRANSCRIBING": _TRANSCRIBING,
        "THINKING": _THINKING,
        "EXECUTING": _EXECUTING,
        "SPEAKING": _SPEAKING,
        "ERROR": _ERROR,
        "OFFLINE": replace(
            _IDLE,
            label="OFFLINE",
            primary=(96, 122, 138),
            glow=(48, 66, 82),
            glow_intensity=0.2,
            particle_intensity=0.12,
            breath_rate=0.12,
        ),
    },
)


#: A colder, more monochrome variant for users who find the warm
# accents distracting.
ICE_THEME = Theme(
    name="ice",
    background=(3, 7, 12),
    text=(226, 246, 255),
    text_dim=(126, 160, 180),
    default=replace(_IDLE, secondary=_CYAN),
    states={
        name: replace(style, secondary=_CYAN_BRIGHT)
        for name, style in AETHER_THEME.states.items()
    },
)


THEMES: dict[str, Theme] = {
    AETHER_THEME.name: AETHER_THEME,
    ICE_THEME.name: ICE_THEME,
}


def get_theme(name: str) -> Theme:
    """
    Look up a theme, falling back to the default rather than failing.
    """

    return THEMES.get(name.strip().lower(), AETHER_THEME)


__all__ = [
    "AETHER_THEME",
    "ICE_THEME",
    "RGB",
    "THEMES",
    "StateStyle",
    "Theme",
    "get_theme",
]
