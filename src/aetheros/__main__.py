import asyncio
import sys

from .bootstrap.application import Application


def _restore_terminal() -> None:
    """
    Last-resort guarantee that the terminal cursor is visible on exit.

    The live trace dashboard hides the cursor once (``rich.live.Live.start()``)
    and normally re-shows it on a clean shutdown via ``recorder.stop()``; the
    CLI prompt also re-asserts it on every line. This covers the one path
    neither does: a failure or Ctrl+C during startup -- before the first prompt
    and before ``Application`` marks itself running, so ``Application.stop()``
    early-returns and never reaches the recorder -- which would otherwise leave
    the shell with a hidden caret after AetherOS is gone.

    Writing the DECTCEM "show" code is cheap, idempotent and harmless when the
    cursor is already visible. It is written to the *real* stream (unwrapping any
    Rich ``FileProxy`` still installed by an un-stopped Live) and only when that
    stream is a TTY, so redirected/captured output is untouched.
    """

    try:
        stream = getattr(sys.stdout, "rich_proxied_file", sys.stdout)

        if stream is not None and stream.isatty():
            stream.write("\x1b[?25h")
            stream.flush()

    except Exception:
        # Restoring the cursor is a courtesy on the way out; it must never turn
        # a shutdown into a traceback.
        pass


async def _main() -> None:
    app = Application()

    try:

        await app.start()


        await app.run()


    except asyncio.CancelledError:
        print("\nAetherOS shutdown requested.")

    finally:
        await app.stop()


def main() -> None:
    print("AetherOS Starting...")

    try:
        asyncio.run(_main())

    except KeyboardInterrupt:
        print("\nAetherOS stopped.")

    finally:
        # Always leave the terminal as we found it, whatever path we exit by:
        # clean shutdown, unhandled exception, or Ctrl+C during startup.
        _restore_terminal()


if __name__ == "__main__":
    main()
