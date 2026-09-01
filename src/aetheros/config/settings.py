from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # -----------------------
    # Project
    # -----------------------

    APP_NAME: str = "AetherOS"
    VERSION: str = "0.1.0"
    DEBUG: bool = True

    # -----------------------
    # Providers
    # -----------------------

    DEFAULT_PROVIDER: str = "ollama"
    DEFAULT_MODEL: str = "qwen3:8b"

    # -----------------------
    # API Keys
    # -----------------------

    OPENAI_API_KEY: str = ""
    OPENROUTER_API_KEY: str = ""
    GROQ_API_KEY: str = ""

    # -----------------------
    # Logging
    # -----------------------

    LOG_LEVEL: str = "INFO"

    # -----------------------
    # Paths
    # -----------------------

    ROOT_DIR: Path = Path(__file__).resolve().parent.parent
    LOG_DIR: Path = ROOT_DIR / "logs"
    DATA_DIR: Path = ROOT_DIR / "data"
    CACHE_DIR: Path = ROOT_DIR / ".cache"

    # -----------------------
    # Desktop
    # -----------------------

    SCREENSHOT_FORMAT: str = "png"

    # -----------------------
    # Vision
    # -----------------------

    OCR_LANGUAGE: str = "en"

    # Vision tools get their own, much larger budget. A full-screen PaddleOCR
    # pass on CPU measured 136s cold and 92s warm on a 1920x1080 desktop, so the
    # general TOOL_TIMEOUT_SECONDS cancelled every OCR call before it could
    # finish — the tools were correct and reported a timeout regardless.
    #
    # Configurable rather than pinned because this number is hardware, not
    # policy: a CUDA build finishes the same pass in single-digit seconds, and
    # nobody on that machine should wait five minutes to learn a tool is wedged.
    VISION_TOOL_TIMEOUT_SECONDS: float = 300.0

    # -----------------------
    # Runtime
    # -----------------------

    MAX_RETRIES: int = 3
    REQUEST_TIMEOUT: int = 60

    # Default execution budget applied to any tool that does not declare its
    # own. Deliberately short: a mouse click or clipboard read that has not
    # returned in 30s is broken, and an agent waiting on it has no way to tell
    # "slow" from "hung".
    TOOL_TIMEOUT_SECONDS: float = 30.0

    # -----------------------
    # Desktop automation
    # -----------------------

    # Whether action tools read state back after acting. Off is a diagnostic
    # mode only: with verification disabled every result reports
    # ``verified: false`` rather than claiming an unchecked success, because a
    # switched-off check must never look like a passing one.
    DESKTOP_VERIFY_ACTIONS: bool = True

    # Pixels of slack allowed when confirming a mouse move. Not zero: Windows
    # applies pointer acceleration and per-monitor DPI scaling, so a move to
    # (800, 600) can legitimately land on (799, 600), and an exact-match check
    # would report a working mouse as broken.
    DESKTOP_POSITION_TOLERANCE: int = 2

    # Ceiling for every ``wait_for_*`` tool. Held below TOOL_TIMEOUT_SECONDS so
    # a wait that finds nothing returns a usable "condition not met within Ns"
    # result instead of being cancelled by the executor, which surfaces as an
    # indistinguishable "Timeout" and loses the diagnosis.
    DESKTOP_MAX_WAIT_SECONDS: float = 25.0

    # Gap between polls while waiting on a window, process or clipboard change.
    # Short enough to feel immediate, long enough that a 25s wait costs ~250
    # cheap Win32 calls rather than a busy loop.
    DESKTOP_POLL_INTERVAL_SECONDS: float = 0.1

    # Default budget for a subprocess started by the terminal tools, also held
    # under TOOL_TIMEOUT_SECONDS so the process is killed and its partial output
    # returned, rather than the tool being cancelled with the child left running
    # and orphaned.
    DESKTOP_COMMAND_TIMEOUT_SECONDS: float = 20.0

    # Largest file the read tools will load into a tool result. A model asking
    # to read a 2GB log should get a clear refusal, not an OOM.
    DESKTOP_MAX_READ_BYTES: int = 1_000_000

    # -----------------------
    # Desktop safety policy
    # -----------------------

    # Power state changes (shutdown, restart, sleep, log off) are refused
    # outright unless this is switched on *and* the call passes an explicit
    # confirm flag. Two independent gates because one bad tool call must not be
    # able to power off a machine mid-analysis; the operator opts in per install
    # and the caller still has to mean it.
    DESKTOP_ALLOW_POWER_ACTIONS: bool = False

    # Arbitrary command execution. On by default because the terminal tools are
    # a core capability, but exposed so a locked-down deployment can remove them
    # without editing code.
    DESKTOP_ALLOW_SHELL: bool = True

    # File and directory deletion. Path validation applies regardless; this is
    # the blunt switch for environments where the agent should never delete.
    DESKTOP_ALLOW_DELETE: bool = True

    # Force a confirm flag on medium-risk actions (closing windows, terminating
    # processes, overwriting files) in addition to the high-risk ones that always
    # require it. Off by default: it makes routine automation unusable.
    DESKTOP_REQUIRE_CONFIRM_MEDIUM_RISK: bool = False

    # Extra paths to protect from write/delete, beyond the built-in system
    # directories. Semicolon-separated absolute paths; ``os.pathsep`` is not used
    # because that is ``;`` on Windows and ``:`` on POSIX, and a config value
    # that changes meaning per platform is a footgun in a shared .env.
    DESKTOP_PROTECTED_PATHS: str = ""

    # When set, filesystem writes are confined to these roots (semicolon
    # separated). Empty means "anywhere the protected-path rules allow", which is
    # the default because the agent legitimately works across the user's disk.
    DESKTOP_FILE_ROOTS: str = ""

    # -----------------------
    # Desktop automation engine
    # -----------------------

    # Hard ceiling on retries for a single workflow step, and on self-healing
    # recovery attempts. Bounded by construction: an unbounded retry loop around
    # a UI action that will never succeed is indistinguishable from a hang.
    DESKTOP_STEP_MAX_ATTEMPTS: int = 3
    DESKTOP_RECOVERY_MAX_ATTEMPTS: int = 2

    # Base delay for exponential backoff between step attempts, in seconds.
    DESKTOP_RETRY_BACKOFF_SECONDS: float = 0.25

    # Wall-clock ceiling on one whole workflow. Enforced inside the engine rather
    # than left to the executor's timeout so that hitting it still returns a
    # complete ExecutionResult -- every step run so far, with its verification --
    # instead of a bare "timed out" that says nothing about how far the
    # automation got or what state the machine was left in.
    DESKTOP_WORKFLOW_TIMEOUT_SECONDS: float = 180.0

    # -----------------------
    # Feature Flags
    # -----------------------

    ENABLE_VISION: bool = True
    ENABLE_MEMORY: bool = False
    ENABLE_BROWSER: bool = False
    ENABLE_VOICE: bool = False