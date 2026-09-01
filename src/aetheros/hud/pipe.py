from __future__ import annotations

import json
import queue
import threading
from typing import Any, Callable, IO

from .protocol import Message

#: Longest single message accepted. Snapshots are a few hundred bytes;
# anything approaching this is a framing fault, not a message.
_MAX_LINE = 64 * 1024


def encode(message: Message) -> str:
    """
    Frame one message as a single line of JSON.

    Newline-delimited JSON rather than pickle: the two processes talk
    over stdio, and a text protocol means a stray write from Qt or a
    library cannot be mistaken for a payload.
    """

    return json.dumps(message, separators=(",", ":"), default=str)


def decode(line: str) -> Message | None:
    """
    Parse one line, or None if it is not a message.

    Junk is expected rather than exceptional: Qt and its plugins write
    warnings to the same streams, so anything unparseable is skipped
    silently.
    """

    text = line.strip()

    if not text or text[0] != "{" or len(text) > _MAX_LINE:
        return None

    try:
        value = json.loads(text)

    except (ValueError, TypeError):
        return None

    return value if isinstance(value, dict) else None


class PipeWriter:
    """
    Sends messages down a text stream.

    Satisfies the sending half of MessageQueue so callers cannot tell
    whether they are talking to a pipe or, in tests, to a plain queue.
    """

    def __init__(
        self,
        stream: IO[str],
        on_error: Callable[[str], None] | None = None,
    ) -> None:

        self._stream = stream
        self._on_error = on_error
        self._lock = threading.Lock()
        self._broken = False

    @property
    def broken(self) -> bool:
        """
        Whether the far end has gone away.
        """

        return self._broken

    def put(self, item: Any) -> None:
        """
        Write one message. Never raises.

        A broken pipe means the other process has exited, which is a
        normal shutdown race rather than an error worth propagating
        into a render loop or an event handler.
        """

        if self._broken:
            return

        try:
            line = encode(item)

        except Exception as exc:
            self._report(f"Could not encode HUD message: {exc}")

            return

        # Serialized because both the event loop and, in the child, Qt
        # timers may write; a torn line would desynchronize the stream.
        with self._lock:

            try:
                self._stream.write(line + "\n")
                self._stream.flush()

            except Exception:
                self._broken = True

    def close(self) -> None:

        self._broken = True

        try:
            self._stream.close()

        except Exception:
            pass

    def _report(self, message: str) -> None:

        if self._on_error is not None:
            try:
                self._on_error(message)

            except Exception:
                pass

    # ------------------------------------------------------
    # Unused halves of the protocol
    # ------------------------------------------------------

    def get(
        self,
        block: bool = True,
        timeout: float | None = None,
    ) -> Any:
        raise NotImplementedError("PipeWriter is send-only.")

    def get_nowait(self) -> Any:
        raise queue.Empty

    def empty(self) -> bool:
        return True


class PipeReader:
    """
    Receives messages from a text stream.

    Owns exactly one thread, because a pipe read blocks and neither an
    asyncio loop nor a Qt event loop may block on it. The thread is a
    daemon that ends when the far end closes the pipe, which is the
    normal way it finishes.
    """

    def __init__(
        self,
        stream: IO[str],
        name: str = "aetheros-hud-reader",
    ) -> None:

        self._stream = stream
        self._name = name

        self._queue: queue.Queue[Message] = queue.Queue()
        self._thread: threading.Thread | None = None
        self._stopping = threading.Event()

        #: Set once the stream ends, so callers can detect the far end
        #: closing without polling the process itself.
        self._closed = threading.Event()

    # ==========================================================
    # Lifecycle
    # ==========================================================

    def start(self) -> None:

        if self._thread is not None:
            return

        self._thread = threading.Thread(
            target=self._run,
            name=self._name,
            daemon=True,
        )

        self._thread.start()

    def stop(self, timeout: float = 1.0) -> None:
        """
        Stop reading, and release the stream if it is safe to.

        Deliberately does *not* close the stream to force the thread out
        of a blocking read. On Windows, closing a stream that another
        thread is reading does not interrupt the read — it blocks
        forever on the stream's own lock, taking the caller with it.
        That is a real hang, not a theoretical one: it deadlocked the
        overlay's shutdown until this was inverted.

        So the stream is closed only once the thread has actually
        finished. Otherwise the thread is left to end on its own when
        the far end closes; it is a daemon, so it cannot outlive the
        process, and the flag stops it queueing anything further.
        """

        self._stopping.set()

        thread = self._thread
        self._thread = None

        if thread is None:
            self._close_stream()

            return

        if thread.is_alive() and timeout > 0.0:
            thread.join(timeout=timeout)

        if not thread.is_alive():
            self._close_stream()

    def _close_stream(self) -> None:

        try:
            self._stream.close()

        except Exception:
            pass

    @property
    def closed(self) -> bool:
        return self._closed.is_set()

    @property
    def running(self) -> bool:

        thread = self._thread

        return thread is not None and thread.is_alive()

    # ==========================================================
    # Reading
    # ==========================================================

    def _run(self) -> None:

        try:
            for line in self._stream:

                if self._stopping.is_set():
                    break

                message = decode(line)

                if message is not None:
                    self._queue.put(message)

        except Exception:
            # The stream was closed underneath us, which is how
            # stop() unblocks this thread.
            pass

        finally:
            self._closed.set()

    # ==========================================================
    # MessageQueue
    # ==========================================================

    def put(self, item: Any) -> None:
        """
        Inject a message locally, as if it had arrived.
        """

        self._queue.put(item)

    def get(
        self,
        block: bool = True,
        timeout: float | None = None,
    ) -> Any:
        return self._queue.get(block, timeout)

    def get_nowait(self) -> Any:
        return self._queue.get_nowait()

    def empty(self) -> bool:
        return self._queue.empty()


__all__ = [
    "PipeReader",
    "PipeWriter",
    "decode",
    "encode",
]
