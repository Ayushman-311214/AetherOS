from __future__ import annotations

import asyncio
from typing import Any

from ..core.errors.voice_error import VoiceError as VoiceErrorException
from ..core.interfaces.speech_to_text import SpeechToText
from ..core.interfaces.text_to_speech import TextToSpeech
from ..core.interfaces.voice_activator import VoiceActivator
from ..core.logging.logging import get_logger
from ..runtime.events.event_bus import EventBus
from .activation import create_activator
from .audio import AudioCapture, AudioPlayer, microphone_available
from .config import VoiceConfig
from .events import VoiceServiceStarted, VoiceServiceStopped
from .pipeline import TurnResult, VoicePipeline, VoiceReasoner
from .state import VoiceState
from .stt import create_stt
from .stt.null_stt import NullSTT
from .tts import fallback_chain
from .tts.null_tts import NullTTS


class VoiceService:
    """
    Owns the voice subsystem's lifecycle.

    Assembles capture, recognition, synthesis, activation and the
    pipeline, then starts and stops them as one unit. Everything it
    touches is injectable, so the same service runs unchanged in tests
    with no audio hardware.

    Failure is contained rather than propagated. No microphone means
    recognition is replaced by a null provider and typed input still
    works; no working synthesizer means replies stay text-only. In
    both cases AetherOS keeps running.
    """

    def __init__(
        self,
        *,
        config: VoiceConfig | None = None,
        event_bus: EventBus | None = None,
        container: Any = None,
        reasoner: VoiceReasoner | None = None,
        stt: SpeechToText | None = None,
        tts: TextToSpeech | None = None,
        activator: VoiceActivator | None = None,
    ) -> None:

        self._config = config or VoiceConfig.from_env()
        self._bus = event_bus
        self._container = container

        self._logger = get_logger("voice.service")

        self._reasoner = reasoner
        self._stt = stt
        self._tts = tts
        self._activator = activator

        self._player = AudioPlayer(self._config)
        self._capture = AudioCapture(self._config)

        self._pipeline: VoicePipeline | None = None

        self._running = False
        self._warmup: asyncio.Task[None] | None = None
        self._activation: asyncio.Task[TurnResult] | None = None

        #: Why listening is unavailable, when it is.
        self._listen_blocked: str | None = None

    # ==========================================================
    # State
    # ==========================================================

    @property
    def is_running(self) -> bool:
        return self._running

    @property
    def config(self) -> VoiceConfig:
        return self._config

    @property
    def state(self) -> VoiceState:

        if self._pipeline is None:
            return VoiceState.IDLE

        return self._pipeline.state

    @property
    def pipeline(self) -> VoicePipeline | None:
        return self._pipeline

    @property
    def can_listen(self) -> bool:
        return self._running and self._listen_blocked is None

    def status(self) -> dict[str, Any]:
        """
        A flat snapshot for the CLI.
        """

        return {
            "running": self._running,
            "state": str(self.state),
            "can_listen": self.can_listen,
            "blocked": self._listen_blocked,
            "stt": self._stt.name if self._stt else None,
            "tts": self._tts.name if self._tts else None,
            "activator": (
                self._activator.name if self._activator else None
            ),
            "hotkey": (
                self._config.hotkey
                if self._activator is not None
                and getattr(self._activator, "is_running", False)
                else None
            ),
            "microphone_disabled": self._config.microphone_disabled,
            "stt_model": self._config.stt_model,
            "stt_device": self._config.resolved_stt_device,
            "tts_voice": self._config.tts_voice,
        }

    # ==========================================================
    # Lifecycle
    # ==========================================================

    async def start(self) -> None:
        """
        Bring the voice subsystem up.
        """

        if self._running:
            self._logger.debug("Voice service already running.")
            return

        self._logger.info("Starting voice service...")

        self._listen_blocked = None

        await self._start_recognition()
        await self._start_synthesis()

        self._pipeline = VoicePipeline(
            config=self._config,
            capture=self._capture,
            stt=self._require_stt(),
            tts=self._require_tts(),
            reasoner=self._resolve_reasoner(),
            event_bus=self._bus,
        )

        await self._start_activation()

        self._running = True

        if self._bus is not None:
            await self._bus.publish(
                VoiceServiceStarted(
                    stt_provider=self._require_stt().name,
                    tts_provider=self._require_tts().name,
                    activator=(
                        self._activator.name
                        if self._activator
                        else "manual"
                    ),
                )
            )

        self._logger.info(
            f"Voice service ready (stt={self._require_stt().name}, "
            f"tts={self._require_tts().name}, "
            f"activation={self._activator.name if self._activator else 'manual'})."
        )

    async def stop(self) -> None:
        """
        Take the voice subsystem down and release every resource.

        Ordering matters: activation first so nothing new can start,
        then the in-flight turn, then the devices.
        """

        if not self._running and self._pipeline is None:
            return

        self._logger.info("Stopping voice service...")

        # ------------------------------------------------------
        # Stop accepting new work
        # ------------------------------------------------------

        if self._activator is not None:
            try:
                await self._activator.stop()

            except Exception:
                self._logger.opt(exception=True).debug(
                    "Ignoring error while stopping activation."
                )

        await self._cancel(self._activation)
        self._activation = None

        await self._cancel(self._warmup)
        self._warmup = None

        # ------------------------------------------------------
        # Abandon any turn in flight
        # ------------------------------------------------------

        if self._pipeline is not None:
            try:
                await self._pipeline.cancel()

            except Exception:
                self._logger.opt(exception=True).debug(
                    "Ignoring error while cancelling turn."
                )

        # ------------------------------------------------------
        # Release devices
        # ------------------------------------------------------

        await self._player.stop()

        for component in (self._tts, self._stt):

            if component is None:
                continue

            try:
                await component.shutdown()

            except Exception:
                self._logger.opt(exception=True).debug(
                    f"Ignoring error while shutting down {type(component).__name__}."
                )

        self._pipeline = None
        self._running = False

        if self._bus is not None:
            await self._bus.publish(VoiceServiceStopped())

        self._logger.info("Voice service stopped.")

    async def restart(self) -> None:
        """
        Stop and start again.
        """

        await self.stop()
        await self.start()

    # ==========================================================
    # Interaction
    # ==========================================================

    async def listen(self) -> TurnResult:
        """
        Run one microphone-driven turn.
        """

        pipeline = self._require_pipeline()

        if self._listen_blocked is not None:
            self._logger.warning(f"Listening unavailable: {self._listen_blocked}")

            return TurnResult(error=self._listen_blocked)

        return await pipeline.listen_once()

    async def say(self, text: str) -> TurnResult:
        """
        Run one turn from typed text.

        Works with no microphone at all, which makes it both the
        fallback input path and the way the full Voice -> LLM -> Tool
        -> speech flow is verified end to end.
        """

        return await self._require_pipeline().say(text)

    async def speak(self, text: str) -> None:
        """
        Speak `text` without reasoning about it.
        """

        await self._require_pipeline().speak(text)

    async def cancel(self) -> None:
        """
        Abandon whatever the pipeline is doing.
        """

        if self._pipeline is not None:
            await self._pipeline.cancel()

    def stop_listening(self) -> None:
        """
        End the current recording early.
        """

        if self._pipeline is not None:
            self._pipeline.request_stop_listening()

    # ==========================================================
    # Recognition
    # ==========================================================

    async def _start_recognition(self) -> None:
        """
        Choose and prepare a speech-recognition provider.
        """

        if self._stt is not None:
            await self._stt.initialize()
            return

        # ------------------------------------------------------
        # Privacy and availability gates
        # ------------------------------------------------------

        if self._config.microphone_disabled:

            self._block(
                "The microphone is disabled "
                "(AETHEROS_MICROPHONE_DISABLED=true)."
            )

            self._stt = NullSTT(
                reason="The microphone is disabled by configuration.",
                sample_rate=self._config.sample_rate,
            )

            await self._stt.initialize()

            return

        if not microphone_available(self._config.input_device):

            self._block(
                "No microphone was found. Use 'voice say <text>' "
                "to talk to AetherOS by typing."
            )

            self._stt = NullSTT(
                reason="No capture device is available.",
                sample_rate=self._config.sample_rate,
            )

            await self._stt.initialize()

            return

        # ------------------------------------------------------
        # Real provider
        # ------------------------------------------------------

        provider = create_stt(self._config)

        if isinstance(provider, NullSTT):
            self._block(provider.reason)

        self._stt = provider

        # Whisper takes several seconds to load, and the first run has
        # to download the model. Warm it up in the background so
        # startup is not held hostage to it; the first transcription
        # awaits the same idempotent initialize().
        self._warmup = asyncio.create_task(
            self._warm_recognition(provider),
            name="aetheros-stt-warmup",
        )

    async def _warm_recognition(
        self,
        provider: SpeechToText,
    ) -> None:

        try:
            await provider.initialize()

        except asyncio.CancelledError:
            raise

        except VoiceErrorException as exc:

            self._logger.warning(f"Speech recognition unavailable: {exc.message}")

            self._block(exc.message)

        except Exception as exc:

            self._logger.warning(f"Speech recognition unavailable: {exc}")

            self._block(str(exc))

    # ==========================================================
    # Synthesis
    # ==========================================================

    async def _start_synthesis(self) -> None:
        """
        Initialize the first synthesis provider that works.
        """

        if self._tts is not None:
            await self._tts.initialize()
            return

        for provider in fallback_chain(self._config, self._player):

            try:
                await provider.initialize()

                self._tts = provider

                return

            except Exception as exc:

                self._logger.warning(
                    f"Speech synthesis provider '{provider.name}' unavailable: {exc}"
                )

        # fallback_chain always ends in NullTTS, so this is only
        # reachable if that too somehow failed.
        self._tts = NullTTS(
            reason="No speech-synthesis provider is available.",
        )

        await self._tts.initialize()

    # ==========================================================
    # Activation
    # ==========================================================

    async def _start_activation(self) -> None:
        """
        Arm the activation source, if listening is possible at all.
        """

        if self._listen_blocked is not None:

            self._logger.info(f"Skipping voice activation: {self._listen_blocked}")

            return

        if self._activator is None:
            self._activator = create_activator(self._config)

        await self._activator.start(self._on_activated)

    def _on_activated(self) -> None:
        """
        Handle an activation signal.

        Runs on the event loop: activators marshal their callbacks
        there before calling this.
        """

        pipeline = self._pipeline

        if pipeline is None:
            return

        # A second press while recording ends the utterance instead of
        # being swallowed.
        if pipeline.state is VoiceState.LISTENING:
            pipeline.request_stop_listening()
            return

        if pipeline.is_busy:
            self._logger.debug(f"Ignoring activation while {pipeline.state}.")
            return

        self._activation = asyncio.create_task(
            self.listen(),
            name="aetheros-voice-turn",
        )

    # ==========================================================
    # Internals
    # ==========================================================

    def _block(self, reason: str) -> None:
        """
        Record why listening is unavailable.
        """

        if self._listen_blocked is None:
            self._listen_blocked = reason

    def _resolve_reasoner(self) -> VoiceReasoner:
        """
        Find something that can answer an utterance.
        """

        if self._reasoner is not None:
            return self._reasoner

        from .reasoner import LLMLoopReasoner

        container = self._container

        if container is None:
            from ..core.container import container as global_container

            container = global_container

        try:
            self._reasoner = LLMLoopReasoner.from_container(
                self._config,
                container,
            )

        except Exception as exc:
            raise VoiceErrorException(
                code="030",
                message="No LLM provider is available for voice.",
                hint=(
                    "Voice reuses the configured LLM provider. Check "
                    "the LLM configuration and that bootstrap "
                    "completed."
                ),
                cause=exc,
            ) from exc

        return self._reasoner

    def _require_pipeline(self) -> VoicePipeline:

        pipeline = self._pipeline

        if pipeline is None:
            raise VoiceErrorException(
                code="031",
                message="The voice service is not running.",
                hint="Start it with 'voice start'.",
            )

        return pipeline

    def _require_stt(self) -> SpeechToText:

        if self._stt is None:
            raise VoiceErrorException(
                code="032",
                message="Speech recognition was not initialized.",
            )

        return self._stt

    def _require_tts(self) -> TextToSpeech:

        if self._tts is None:
            raise VoiceErrorException(
                code="033",
                message="Speech synthesis was not initialized.",
            )

        return self._tts

    async def _cancel(
        self,
        task: asyncio.Task[Any] | None,
    ) -> None:
        """
        Cancel a background task and wait for it to finish.
        """

        if task is None or task.done():
            return

        task.cancel()

        try:
            await task

        except (asyncio.CancelledError, Exception):
            pass


__all__ = ["VoiceService"]
