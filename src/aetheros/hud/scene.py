from __future__ import annotations

import math
import random
from dataclasses import dataclass, fields
from typing import Iterable

from .config import QUALITY_LEVELS, HUDConfig
from .state import HUDSnapshot, HUDState
from .theme import StateStyle, Theme, get_theme

#: Seconds to cross-fade between two states' styles. Long enough to
# read as a transition, short enough to feel responsive.
TRANSITION_SECONDS = 0.45

#: Radial waveform resolution. Doubles as the amplitude history depth,
# so the wave visibly travels around the ring as audio arrives.
WAVEFORM_BINS = 56

#: Particle budget at "high". Lower tiers use a fraction of this.
PARTICLE_BUDGET = 104

#: How long an expanding pulse ring takes to reach the outer edge.
PULSE_LIFETIME = 1.7

#: Hard cap on concurrent pulses, so a fast state cannot grow the
# list without bound.
MAX_PULSES = 14

#: An ERROR snapshot with no follow-up decays to IDLE after this long.
# The pipeline already resets itself; this only guards against a
# dropped message leaving the overlay stuck showing a fault.
ERROR_HOLD_SECONDS = 4.5

#: Quality multipliers: particle fraction, glow passes, waveform bins.
_QUALITY_PROFILE = {
    "low": (0.35, 1, WAVEFORM_BINS // 2),
    "medium": (0.65, 2, WAVEFORM_BINS),
    "high": (1.0, 3, WAVEFORM_BINS),
}


@dataclass(slots=True)
class Particle:
    """
    One orbiting mote.

    Motion is a closed-form function of time rather than an integrated
    velocity, so the field cannot drift or accumulate error, and a
    dropped frame changes nothing.
    """

    #: Starting angle, radians.
    angle: float

    #: Base orbit as a fraction of the half-width.
    orbit: float

    #: Angular speed multiplier, signed so the field counter-rotates.
    speed: float

    #: Radial oscillation rate and phase.
    wobble: float
    phase: float

    #: Dot radius in logical pixels at scale 1.
    size: float

    #: Per-particle brightness, 0..1.
    brightness: float


def _build_particles(count: int) -> list[Particle]:
    """
    Generate a deterministic particle field.

    Seeded so every process and every run produces the same field:
    the HUD should look identical each launch, and tests need it to be
    reproducible.
    """

    rng = random.Random(0x4E7A)

    particles: list[Particle] = []

    for index in range(count):

        # Bias the distribution outward so the centre stays legible
        # and the core is not lost behind dots.
        radial = 0.28 + 0.52 * math.sqrt(rng.random())

        particles.append(
            Particle(
                angle=rng.uniform(0.0, math.tau),
                orbit=radial,
                speed=rng.choice((1.0, -1.0))
                * rng.uniform(0.35, 1.25),
                wobble=rng.uniform(0.4, 1.6),
                phase=rng.uniform(0.0, math.tau),
                size=rng.uniform(0.9, 2.4),
                brightness=rng.uniform(0.35, 1.0),
            )
        )

    # Draw dim particles first so bright ones land on top.
    particles.sort(key=lambda item: item.brightness)

    return particles


@dataclass(slots=True)
class Pulse:
    """
    An expanding ring emitted from the core.
    """

    born: float

    def progress(self, now: float) -> float:
        return (now - self.born) / PULSE_LIFETIME


class Scene:
    """
    The animation state of the overlay.

    Holds everything that changes over time: the current snapshot, the
    style being cross-faded toward, smoothed amplitude, orbital phases,
    live pulses and the quality governor. Contains no Qt types, so the
    entire animation system is testable without a display.
    """

    def __init__(
        self,
        config: HUDConfig,
        theme: Theme | None = None,
    ) -> None:

        self._config = config
        self._theme = theme or get_theme(config.theme)

        self._snapshot = HUDSnapshot()

        #: Style we are fading from, and the target.
        self._from_style = self._theme.style(str(self._snapshot.state))
        self._to_style = self._from_style
        self._style = self._from_style

        #: Seconds since the scene started, and since the last change.
        self._time = 0.0
        self._transition = TRANSITION_SECONDS
        self._state_age = 0.0

        # ------------------------------------------------------
        # Audio
        # ------------------------------------------------------

        self._amplitude = 0.0
        self._target_amplitude = 0.0
        self._peak = 0.0

        self._history = [0.0] * WAVEFORM_BINS
        self._head = 0

        #: Accumulator so history advances at a fixed rate regardless
        # of frame rate.
        self._history_clock = 0.0

        # ------------------------------------------------------
        # Motion
        # ------------------------------------------------------

        self._rotation = 0.0
        self._counter_rotation = 0.0
        self._orbit = 0.0

        self._particles = _build_particles(PARTICLE_BUDGET)
        self._pulses: list[Pulse] = []
        self._pulse_debt = 0.0

        # ------------------------------------------------------
        # Quality governor
        # ------------------------------------------------------

        self._quality = config.initial_quality
        self._frame_ema = 0.0
        self._pressure = 0.0
        self._fps = float(config.fps)

    # ==========================================================
    # Accessors
    # ==========================================================

    @property
    def config(self) -> HUDConfig:
        return self._config

    @property
    def theme(self) -> Theme:
        return self._theme

    @property
    def snapshot(self) -> HUDSnapshot:
        return self._snapshot

    @property
    def state(self) -> HUDState:
        return self._snapshot.state

    @property
    def style(self) -> StateStyle:
        """
        The interpolated style for this frame.
        """

        return self._style

    @property
    def time(self) -> float:
        return self._time

    @property
    def amplitude(self) -> float:
        """
        Smoothed audio level, 0..1.
        """

        return self._amplitude

    @property
    def peak(self) -> float:
        """
        Slowly decaying peak, used for the outer bloom.
        """

        return self._peak

    @property
    def rotation(self) -> float:
        return self._rotation

    @property
    def counter_rotation(self) -> float:
        return self._counter_rotation

    @property
    def orbit_phase(self) -> float:
        return self._orbit

    @property
    def pulses(self) -> list[Pulse]:
        return self._pulses

    @property
    def quality(self) -> str:
        return self._quality

    @property
    def fps(self) -> float:
        return self._fps

    @property
    def glow_passes(self) -> int:
        return _QUALITY_PROFILE[self._quality][1]

    @property
    def waveform_bins(self) -> int:
        return _QUALITY_PROFILE[self._quality][2]

    def visible_particles(self) -> Iterable[Particle]:
        """
        The particles this frame should draw.

        Intensity and quality both trim from the front of the list,
        which is sorted dim-first, so what drops out is what would
        have been least visible anyway.
        """

        fraction = _QUALITY_PROFILE[self._quality][0]

        count = int(
            len(self._particles)
            * fraction
            * max(0.0, min(1.0, self._style.particle_intensity))
        )

        if count <= 0:
            return ()

        return self._particles[len(self._particles) - count :]

    def waveform(self) -> list[float]:
        """
        Amplitude history ordered so index 0 is the oldest bin.
        """

        bins = self.waveform_bins
        step = max(1, WAVEFORM_BINS // bins)

        return [
            self._history[(self._head + offset) % WAVEFORM_BINS]
            for offset in range(0, WAVEFORM_BINS, step)
        ]

    # ==========================================================
    # Input
    # ==========================================================

    def apply(self, snapshot: HUDSnapshot) -> None:
        """
        Adopt a new snapshot, starting a style transition if the state
        changed.
        """

        changed = snapshot.state is not self._snapshot.state

        self._snapshot = snapshot

        if changed:
            # Fade from whatever is on screen right now, not from the
            # previous target, so an interrupted transition does not
            # jump.
            self._from_style = self._style
            self._to_style = self._theme.style(str(snapshot.state))

            self._transition = 0.0
            self._state_age = 0.0

            # A new state starts its own pulse rhythm.
            self._pulse_debt = 0.0

        self._target_amplitude = (
            snapshot.amplitude if snapshot.is_audio_reactive else 0.0
        )

    def set_amplitude(self, level: float) -> None:
        """
        Update the live audio level without changing state.
        """

        clamped = max(0.0, min(1.0, level))

        self._snapshot = HUDSnapshot(
            state=self._snapshot.state,
            amplitude=clamped,
            transcript=self._snapshot.transcript,
            action=self._snapshot.action,
            response=self._snapshot.response,
            message=self._snapshot.message,
            sequence=self._snapshot.sequence,
        )

        self._target_amplitude = (
            clamped if self._snapshot.is_audio_reactive else 0.0
        )

    def apply_config(self, config: HUDConfig) -> None:
        """
        Adopt new configuration, rebuilding theme-derived state.
        """

        self._config = config
        self._theme = get_theme(config.theme)

        self._quality = config.initial_quality

        self._to_style = self._theme.style(str(self._snapshot.state))
        self._from_style = self._to_style
        self._style = self._to_style

    # ==========================================================
    # Advance
    # ==========================================================

    def advance(self, delta: float) -> None:
        """
        Step the animation forward by `delta` seconds.
        """

        # Clamp: a stalled window (dragged, or the machine slept) must
        # not teleport the animation.
        step = max(0.0, min(0.1, delta))

        self._time += step
        self._state_age += step

        self._advance_style(step)
        self._advance_audio(step)
        self._advance_motion(step)
        self._advance_pulses(step)

    def _advance_style(self, step: float) -> None:
        """
        Cross-fade toward the target style.
        """

        if self._transition >= TRANSITION_SECONDS:
            self._style = self._to_style
            return

        self._transition = min(
            TRANSITION_SECONDS,
            self._transition + step,
        )

        progress = self._transition / TRANSITION_SECONDS

        self._style = _blend(
            self._from_style,
            self._to_style,
            _smoothstep(progress),
        )

    def _advance_audio(self, step: float) -> None:
        """
        Smooth the amplitude and advance the waveform history.
        """

        target = self._target_amplitude

        # Fast attack, slow release: speech transients should be
        # visible, but the geometry should not flicker on every gap
        # between syllables.
        rate = 22.0 if target > self._amplitude else 6.5

        self._amplitude += (target - self._amplitude) * min(
            1.0,
            rate * step,
        )

        if self._amplitude < 0.001:
            self._amplitude = 0.0

        self._peak = max(
            self._amplitude,
            self._peak - step * 0.55,
        )

        # Advance history at a fixed 60 Hz regardless of render rate,
        # so the travelling wave keeps the same apparent speed when
        # quality drops.
        self._history_clock += step

        while self._history_clock >= 1.0 / 60.0:
            self._history_clock -= 1.0 / 60.0

            self._head = (self._head + 1) % WAVEFORM_BINS
            self._history[self._head] = self._amplitude

    def _advance_motion(self, step: float) -> None:
        """
        Advance rotations, wrapping to keep the numbers small.
        """

        speed = self._style.ring_speed

        self._rotation = (self._rotation + speed * step) % 360.0

        # Counter-rotation at an unrelated ratio so the rings never
        # visually lock together.
        self._counter_rotation = (
            self._counter_rotation - speed * 0.618 * step
        ) % 360.0

        self._orbit = (
            self._orbit + self._style.particle_speed * step
        ) % math.tau

    def _advance_pulses(self, step: float) -> None:
        """
        Emit and retire expanding rings.
        """

        now = self._time

        self._pulses = [
            pulse
            for pulse in self._pulses
            if pulse.progress(now) < 1.0
        ]

        rate = self._style.pulse_rate

        if rate <= 0.0:
            return

        # Louder input emits faster, which makes LISTENING respond to
        # the voice rather than just to the clock.
        if self._style.amplitude_response > 0.0:
            rate *= 1.0 + self._amplitude * 1.4

        self._pulse_debt += rate * step

        while self._pulse_debt >= 1.0 and len(self._pulses) < MAX_PULSES:
            self._pulse_debt -= 1.0
            self._pulses.append(Pulse(born=now))

        # Never let debt accumulate past one emission.
        self._pulse_debt = min(self._pulse_debt, 1.0)

    # ==========================================================
    # Derived geometry
    # ==========================================================

    def core_radius(self, half: float) -> float:
        """
        Core radius in pixels, including breathing and audio response.
        """

        style = self._style

        breath = math.sin(self._time * style.breath_rate * math.tau)

        scale = 1.0 + breath * style.breath_depth

        if style.amplitude_response > 0.0:
            scale += self._amplitude * style.amplitude_response * 0.34

        return max(2.0, half * style.core_scale * scale)

    def glow_radius(self, half: float) -> float:
        """
        Outer bloom radius in pixels.
        """

        base = self.core_radius(half) * 3.0

        return min(half * 0.98, base * (1.0 + self._peak * 0.3))

    def should_return_to_idle(self) -> bool:
        """
        Whether a stale ERROR should decay to IDLE on its own.
        """

        return (
            self._snapshot.state is HUDState.ERROR
            and self._state_age >= ERROR_HOLD_SECONDS
        )

    # ==========================================================
    # Quality governor
    # ==========================================================

    def record_frame(self, duration: float) -> None:
        """
        Feed one frame's render time to the quality governor.

        Sustained overrun steps quality down; sustained headroom steps
        it back up, but never above what was configured. This is how
        the 60 FPS target degrades to a smooth 30 instead of
        stuttering.
        """

        if duration > 0.0:
            self._frame_ema = (
                duration
                if self._frame_ema <= 0.0
                else self._frame_ema * 0.9 + duration * 0.1
            )

        if self._frame_ema > 0.0:
            self._fps = min(
                float(self._config.fps),
                1.0 / self._frame_ema,
            )

        if not self._config.adaptive_quality:
            return

        budget = self._config.frame_interval_ms / 1000.0

        if self._frame_ema > budget * 0.85:
            self._pressure += 1.0

        elif self._frame_ema < budget * 0.45:
            self._pressure -= 0.5

        else:
            self._pressure *= 0.9

        # ~1 second of consistent evidence before changing tier, so a
        # single slow frame never causes a visible downgrade.
        if self._pressure >= 45.0:
            self._pressure = 0.0
            self._step_quality(-1)

        elif self._pressure <= -60.0:
            self._pressure = 0.0
            self._step_quality(1)

    def _step_quality(self, direction: int) -> None:

        levels = list(QUALITY_LEVELS)
        index = levels.index(self._quality)

        ceiling = levels.index(self._config.initial_quality)

        target = max(0, min(ceiling, index + direction))

        if target != index:
            self._quality = levels[target]

    def force_quality(self, quality: str) -> None:
        """
        Pin the quality tier, e.g. after a render failure.
        """

        if quality in QUALITY_LEVELS:
            self._quality = quality
            self._pressure = 0.0


# ==============================================================
# Helpers
# ==============================================================

#: The colour fields, and every numeric field, of a StateStyle.
# Listed explicitly rather than derived from field.type: under
# `from __future__ import annotations` those types are strings, and
# matching on them would break silently the moment a field is renamed
# or re-annotated.
_STYLE_COLOURS = ("primary", "secondary", "glow")

_STYLE_NUMBERS = tuple(
    field.name
    for field in fields(StateStyle)
    if field.name not in _STYLE_COLOURS and field.name != "label"
)


def _smoothstep(t: float) -> float:
    """
    Ease in and out.
    """

    clamped = max(0.0, min(1.0, t))

    return clamped * clamped * (3.0 - 2.0 * clamped)


def _mix(a: float, b: float, t: float) -> float:
    return a + (b - a) * t


def _mix_colour(
    a: tuple[int, int, int],
    b: tuple[int, int, int],
    t: float,
) -> tuple[int, int, int]:

    return (
        int(round(_mix(a[0], b[0], t))),
        int(round(_mix(a[1], b[1], t))),
        int(round(_mix(a[2], b[2], t))),
    )


def _blend(
    a: StateStyle,
    b: StateStyle,
    t: float,
) -> StateStyle:
    """
    Interpolate two styles.

    Colours and every numeric quantity blend; the label switches at
    the halfway point so text does not appear to melt.
    """

    values: dict[str, object] = {
        name: _mix(
            getattr(a, name),
            getattr(b, name),
            t,
        )
        for name in _STYLE_NUMBERS
    }

    for name in _STYLE_COLOURS:
        values[name] = _mix_colour(
            getattr(a, name),
            getattr(b, name),
            t,
        )

    values["label"] = b.label if t >= 0.5 else a.label

    return StateStyle(**values)  # type: ignore[arg-type]


__all__ = [
    "ERROR_HOLD_SECONDS",
    "MAX_PULSES",
    "PARTICLE_BUDGET",
    "PULSE_LIFETIME",
    "TRANSITION_SECONDS",
    "WAVEFORM_BINS",
    "Particle",
    "Pulse",
    "Scene",
]
