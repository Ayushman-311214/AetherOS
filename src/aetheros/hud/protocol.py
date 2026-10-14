from __future__ import annotations

from typing import Any, Protocol

from .state import HUDSnapshot

# ==============================================================
# Message types
# ==============================================================

# Application -> renderer
MSG_SNAPSHOT = "snapshot"
MSG_CONFIG = "config"
MSG_QUIT = "quit"

# Renderer -> application
MSG_READY = "ready"
MSG_CLOSED = "closed"
MSG_ERROR = "error"
MSG_STATS = "stats"

#: Every message is a plain dict so it survives pickling between
# processes without either side importing the other's types.
Message = dict[str, Any]


class MessageQueue(Protocol):
    """
    The slice of multiprocessing.Queue the HUD actually uses.

    Typed as a protocol so tests can substitute a plain queue.Queue
    and exercise the whole service without spawning a process.
    """

    def put(self, item: Any) -> None: ...

    def get(self, block: bool = ..., timeout: float | None = ...) -> Any: ...

    def get_nowait(self) -> Any: ...

    def empty(self) -> bool: ...


# ==============================================================
# Builders
# ==============================================================


def snapshot_message(snapshot: HUDSnapshot) -> Message:
    """
    Wrap a snapshot for transport.
    """

    return {"type": MSG_SNAPSHOT, "snapshot": snapshot.to_dict()}


def config_message(config: dict[str, Any]) -> Message:
    return {"type": MSG_CONFIG, "config": dict(config)}


def quit_message() -> Message:
    return {"type": MSG_QUIT}


def ready_message(pid: int) -> Message:
    return {"type": MSG_READY, "pid": pid}


def closed_message(reason: str = "user") -> Message:
    return {"type": MSG_CLOSED, "reason": reason}


def error_message(message: str) -> Message:
    return {"type": MSG_ERROR, "message": message}


def stats_message(fps: float, quality: str) -> Message:
    return {"type": MSG_STATS, "fps": round(fps, 1), "quality": quality}


# ==============================================================
# Readers
# ==============================================================


def message_type(message: Any) -> str:
    """
    Extract a message's type, tolerating anything malformed.

    The render loop must never die because something unexpected
    arrived on the queue.
    """

    if not isinstance(message, dict):
        return ""

    value = message.get("type")

    return "" if value is None else str(value)


def read_snapshot(message: Any) -> HUDSnapshot | None:
    """
    Decode a snapshot message, or None if it is not one.
    """

    if message_type(message) != MSG_SNAPSHOT:
        return None

    payload = message.get("snapshot")

    if not isinstance(payload, dict):
        return None

    return HUDSnapshot.from_dict(payload)


def read_config(message: Any) -> dict[str, Any] | None:
    """
    Decode a config message, or None if it is not one.
    """

    if message_type(message) != MSG_CONFIG:
        return None

    payload = message.get("config")

    return dict(payload) if isinstance(payload, dict) else None


def drain(queue: MessageQueue, limit: int = 64) -> list[Message]:
    """
    Take everything currently queued, newest last.

    Bounded so a flood cannot stall the caller, and tolerant of the
    races inherent in multiprocessing queues: empty() is advisory, so
    the Empty exception is the real terminator.
    """

    messages: list[Message] = []

    for _ in range(max(1, limit)):

        try:
            messages.append(queue.get_nowait())

        except Exception:
            # queue.Empty, or a closed queue during shutdown.
            break

    return messages


__all__ = [
    "MSG_CLOSED",
    "MSG_CONFIG",
    "MSG_ERROR",
    "MSG_QUIT",
    "MSG_READY",
    "MSG_SNAPSHOT",
    "MSG_STATS",
    "Message",
    "MessageQueue",
    "closed_message",
    "config_message",
    "drain",
    "error_message",
    "message_type",
    "quit_message",
    "read_config",
    "read_snapshot",
    "ready_message",
    "snapshot_message",
    "stats_message",
]
