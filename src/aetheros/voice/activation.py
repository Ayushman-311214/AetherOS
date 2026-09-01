from __future__ import annotations

import asyncio
from typing import Any

from ..core.interfaces.voice_activator import VoiceActivator, WakeCallback
from ..core.logging.logging import get_logger
from .config import VoiceConfig


class NullActivator(VoiceActivator):
    """
    An activator that never fires.

    This is what "always-listening is off" looks like: nothing hooks
    the keyboard, nothing opens the microphone, and listening happens
    only when the user asks for it explicitly.
    """

    def __init__(
        self,
        *,
        reason: str = "Automatic voice activation is disabled.",
    ) -> None:

        self._reason = reason
        self._logger = get_logger("voice.activation.null")

    @property
    def name(self) -> str:
        return "manual"

    @property
    def is_running(self) -> bool:
        return False

    @property
    def reason(self) -> str:
        return self._reason

    async def start(self, on_activate: WakeCallback) -> None:
        self._logger.info(self._reason)

    async def stop(self) -> None:
        return None


class PushToTalkActivator(VoiceActivator):
    """
    Global hotkey activation.

    Push-to-talk is the default because it is deterministic and
    private: the microphone opens when the user presses a key and
    closes when they stop talking. Nothing listens in between.

    The hotkey is a convenience, not a requirement. If the `keyboard`
    package is missing, the hotkey string is empty, or the OS refuses
    the hook, the activator stays disarmed and logs why. Listening is
    still reachable from the CLI, so a failed hook never costs the
    user the voice subsystem.

    Threading: `keyboard` invokes the callback from its own daemon
    listener thread. The callback is marshalled onto the event loop
    that armed the activator, so callers always run on the loop.
    """

    def __init__(
        self,
        config: VoiceConfig,
    ) -> None:

        self._config = config
        self._logger = get_logger("voice.activation.hotkey")

        self._keyboard: Any = None
        self._handle: Any = None
        self._loop: asyncio.AbstractEventLoop | None = None
        self._running = False

    # ==========================================================
    # Provider Information
    # ==========================================================

    @property
    def name(self) -> str:
        return "push-to-talk"

    @property
    def is_running(self) -> bool:
        return self._running

    @property
    def hotkey(self) -> str:
        return self._config.hotkey

    # ==========================================================
    # Lifecycle
    # ==========================================================

    async def start(self, on_activate: WakeCallback) -> None:
        """
        Register the global hotkey.

        Never raises: a hotkey that cannot be registered is a degraded
        convenience, not a failure of the voice subsystem.
        """

        if self._running:
            return

        hotkey = self._config.hotkey.strip()

        if not hotkey:
            self._logger.info(
                "No voice hotkey configured; use the CLI to listen."
            )
            return

        try:
            import keyboard

        except Exception as exc:
            self._logger.warning(
                f"Global hotkey unavailable ({exc}); use the CLI to start listening."
            )
            return

        self._keyboard = keyboard
        self._loop = asyncio.get_running_loop()

        def fire() -> None:
            loop = self._loop

            if loop is None or loop.is_closed():
                return

            try:
                loop.call_soon_threadsafe(on_activate)

            except RuntimeError:
                # Loop shut down between the keypress and the callback.
                pass

        try:
            self._handle = keyboard.add_hotkey(
                hotkey,
                fire,
                suppress=False,
            )

        except Exception as exc:
            self._keyboard = None
            self._loop = None

            self._logger.warning(
                f"Could not register voice hotkey '{hotkey}' ({exc}); use the CLI to "
                f"start listening."
            )
            return

        self._running = True

        self._logger.info(f"Voice hotkey armed: {hotkey}")

    async def stop(self) -> None:
        """
        Release the keyboard hook.
        """

        keyboard = self._keyboard
        handle = self._handle

        self._running = False
        self._handle = None
        self._keyboard = None
        self._loop = None

        if keyboard is None or handle is None:
            return

        try:
            keyboard.remove_hotkey(handle)

            self._logger.debug("Voice hotkey released.")

        except Exception:
            self._logger.opt(exception=True).debug(
                "Ignoring error while releasing voice hotkey."
            )


class WakeWordActivator(VoiceActivator):
    """
    Placeholder for always-listening wake-word detection.

    The abstraction exists so a detector can be dropped in later
    without touching the pipeline. No detector ships today, and that
    is deliberate: always-listening means holding the microphone open
    indefinitely, which is a privacy decision the user should make
    knowingly rather than inherit from a default.

    Selecting this activator logs what is missing and leaves the
    microphone closed.
    """

    def __init__(
        self,
        config: VoiceConfig,
    ) -> None:

        self._config = config
        self._logger = get_logger("voice.activation.wake")

    @property
    def name(self) -> str:
        return "wake-word"

    @property
    def is_running(self) -> bool:
        return False

    @property
    def wake_word(self) -> str:
        return self._config.wake_word

    async def start(self, on_activate: WakeCallback) -> None:
        self._logger.warning(
            f"Wake-word activation ('{self._config.wake_word}') is not implemented; no "
            f"detector is bundled. Falling back to manual activation -- set "
            f"AETHEROS_VOICE_ACTIVATOR=push-to-talk for a global hotkey."
        )

    async def stop(self) -> None:
        return None


# ==============================================================
# Factory
# ==============================================================


#: Alias -> canonical activator name.
_ACTIVATORS = {
    "push-to-talk": "push-to-talk",
    "ptt": "push-to-talk",
    "hotkey": "push-to-talk",
    "wake-word": "wake-word",
    "wakeword": "wake-word",
    "manual": "manual",
    "none": "manual",
    "null": "manual",
    "disabled": "manual",
}


def create_activator(config: VoiceConfig) -> VoiceActivator:
    """
    Build the configured activation source.
    """

    logger = get_logger("voice.activation")

    requested = config.activator.strip().lower()

    resolved = _ACTIVATORS.get(requested)

    if resolved is None:
        logger.warning(
            f"Unknown voice activator '{config.activator}'; using push-to-talk. Valid "
            f"values: {', '.join(sorted(set(_ACTIVATORS)))}"
        )

        resolved = "push-to-talk"

    if resolved == "manual":
        return NullActivator(
            reason=(
                "Voice activation is set to manual; start listening "
                "from the CLI with 'voice listen'."
            ),
        )

    if resolved == "wake-word":
        return WakeWordActivator(config)

    return PushToTalkActivator(config)


__all__ = [
    "NullActivator",
    "PushToTalkActivator",
    "VoiceActivator",
    "WakeWordActivator",
    "create_activator",
]
