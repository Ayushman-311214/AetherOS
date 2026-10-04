from pathlib import Path

from pydantic import AliasChoices, Field
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

    LOG_LEVEL: str = "INFO"  # "DEBUG" | "INFO" | "WARNING" | "ERROR" | "CRITICAL"
    LOG_ROTATION: str = "10 MB"
    # LOG_RETENTION: str = "14 days"
    LOG_RUNS_TO_KEEP: int = 2
    LOG_COMPRESSION: str = "zip"

    # -----------------------
    # Live execution trace
    # -----------------------

    # Verbosity of the live trace dashboard: off | error | minimal | normal |
    # debug | verbose. Parsed tolerantly by observability.resolve_level, so an
    # unknown value falls back to NORMAL rather than failing a run.
    
    TRACE_LEVEL: str = "verbose" # "off" | "error" | "minimal" | "normal" | "debug" | "verbose"

    # Whether each run's trace is persisted as JSONL under LOG_DIR/traces. The
    # live dashboard is independent of this: turning persistence off still shows
    # the trace, it just leaves no file behind.
    TRACE_PERSIST: bool = False

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
    # Vision grounding
    # -----------------------

    # Confidence bands for resolving a natural-language target to a screen
    # element. A match at or above HIGH is treated as unambiguous enough to act
    # on automatically; between MEDIUM and HIGH it is returned as a candidate to
    # confirm; below MEDIUM it is reported but never auto-clicked. These are
    # policy, not hardware, so they are configurable rather than pinned -- a
    # noisier screen or a stricter safety posture wants a higher HIGH.
    GROUNDING_CONFIDENCE_HIGH: float = 0.75
    GROUNDING_CONFIDENCE_MEDIUM: float = 0.45

    # -----------------------
    # Vision performance
    # -----------------------
    #
    # These knobs make the vision system usable interactively without removing
    # any capability. Every default below preserves the pre-optimization
    # behaviour (full resolution, no silent accuracy loss); the fast paths are
    # opt-in, so FAST-vs-ACCURATE is an explicit choice rather than a hidden
    # degradation. All are read once, in the vision layer, from this single
    # config object -- never via scattered os.getenv() calls.

    # Per-stage timing. When True the vision layer logs how long capture,
    # preprocessing, detection, OCR and grounding each took, at DEBUG. When
    # False (the default) it adds no logging at all, so production logs are
    # unchanged.
    VISION_PROFILE: bool = Field(
        default=False,
        validation_alias=AliasChoices("AETHEROS_VISION_PROFILE", "VISION_PROFILE"),
    )

    # Processing width, in pixels, that a frame is downscaled to before the
    # heavy detectors run. 0 (the default) means "do not downscale" -- full
    # native resolution, maximum accuracy, matching the historical behaviour.
    # Set it (e.g. 1280) to trade a little small-text/near-edge accuracy for a
    # large latency win on a high-resolution display: fewer pixels is less work
    # for both YOLO and PaddleOCR. The original full-resolution frame is kept
    # for coordinate precision; only the copy fed to the model is scaled, and
    # boxes are mapped back to original coordinates.
    VISION_WIDTH: int = Field(
        default=0,
        ge=0,
        validation_alias=AliasChoices("AETHEROS_VISION_WIDTH", "VISION_WIDTH"),
    )

    # Time-to-live, in milliseconds, of the short-lived screen-frame cache. A
    # read-only vision op (read text, detect, find text, analyze, ground) within
    # this window of a previous capture reuses that frame instead of grabbing
    # the screen again, so a "find X" immediately followed by "read Y" pays for
    # one capture, not two. 0 disables the cache. Grounded *actions*
    # (click/type) always bypass it and capture fresh -- acting on a stale frame
    # could click the wrong place, which §8 explicitly forbids.
    VISION_FRAME_TTL_MS: int = Field(
        default=300,
        ge=0,
        validation_alias=AliasChoices(
            "AETHEROS_VISION_FRAME_TTL_MS", "VISION_FRAME_TTL_MS"
        ),
    )

    # Detection weights (name or path). Nano by default: yolo11n is the smallest
    # YOLO11 model and the right trade-off for interactive UI detection, where
    # latency matters more than detecting rare COCO classes. Point it at a larger
    # .pt for an accuracy-first deployment.
    VISION_MODEL: str = Field(
        default="yolo11n.pt",
        validation_alias=AliasChoices("AETHEROS_VISION_MODEL", "VISION_MODEL"),
    )

    # Minimum confidence for a YOLO detection to be kept. Matches ultralytics'
    # own default; raise it to cut low-quality boxes (and a little
    # postprocessing work), lower it to surface more candidates.
    VISION_DETECTION_CONFIDENCE: float = Field(
        default=0.25,
        ge=0.0,
        le=1.0,
        validation_alias=AliasChoices(
            "AETHEROS_VISION_DETECTION_CONFIDENCE", "VISION_DETECTION_CONFIDENCE"
        ),
    )

    # YOLO inference size (longest side, pixels). 640 is the model's native
    # training size; smaller (e.g. 480) is faster with some recall loss on small
    # UI elements. Passed explicitly so inference size is a deliberate, logged
    # choice rather than whatever ultralytics happens to default to.
    VISION_DETECTION_IMGSZ: int = Field(
        default=640,
        ge=64,
        validation_alias=AliasChoices(
            "AETHEROS_VISION_DETECTION_IMGSZ", "VISION_DETECTION_IMGSZ"
        ),
    )

    # Torch device for detection. Empty (the default) means "auto": use CUDA
    # when torch reports it available, otherwise CPU. Set "cpu" to force CPU even
    # on a CUDA box, or "cuda:0" to pin a GPU. Never forces CUDA when it is
    # unavailable -- an explicit "cuda" on a CPU-only build falls back to CPU
    # with a warning rather than crashing.
    VISION_DETECTION_DEVICE: str = Field(
        default="",
        validation_alias=AliasChoices(
            "AETHEROS_VISION_DETECTION_DEVICE", "VISION_DETECTION_DEVICE"
        ),
    )

    # -----------------------
    # Runtime
    # -----------------------

    MAX_RETRIES: int = 3
    REQUEST_TIMEOUT: int = 60

    # Canonical budget for one agent run: the maximum number of tool-calling
    # iterations (agent-loop turns) a single goal is allowed before it must
    # produce a final answer. This is the ONE source of truth for that limit --
    # the planner's per-response acceptance cap, the AgentCore loop's iteration
    # budget and the LLMToolLoop budget are all seeded from it at startup rather
    # than each hardcoding their own 8.
    #
    # It is NOT any of: the LLM context/conversation window, the per-tool
    # timeout (TOOL_TIMEOUT_SECONDS), or the whole-workflow timeout
    # (DESKTOP_WORKFLOW_TIMEOUT_SECONDS). It only bounds how many tool-calling
    # turns the agent may take.
    #
    # Default 8 preserves the historical behaviour exactly when the env var is
    # unset, so existing installs are unchanged. Raise it (e.g.
    # AETHEROS_MAX_TOOL_CALLS=32) for goals that legitimately need more steps.
    # Each consumer still clamps to its own absolute safety ceiling
    # (planner TOOL_CALL_CEILING=32, loop ITERATION_CEILING=50), so an
    # over-large value is capped, never trusted blindly. Values below 1 or that
    # are not integers fail here at configuration load rather than degrading a
    # run at some unpredictable later point.
    MAX_TOOL_CALLS: int = Field(
        default=8,
        ge=1,
        validation_alias=AliasChoices("AETHEROS_MAX_TOOL_CALLS", "MAX_TOOL_CALLS"),
    )

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
    ENABLE_MEMORY: bool = True
    ENABLE_BROWSER: bool = True
    ENABLE_VOICE: bool = True


    # ╔══════════════════════════════════════════╗
    # ║         Trading Intelligence             ║
    # ╚══════════════════════════════════════════╝
    
    # The numerical trading core (market data -> indicators -> structure ->
    # evidence -> analysis) is self-contained and does not depend on Vision,
    # Desktop or an LLM. Every default below is non-breaking: with the flag on
    # and no provider credentials configured, the system uses the clearly
    # labelled MOCK provider, which can never be mistaken for real market data.

    # Master switch for the trading subsystem. On by default -- the core is
    # deterministic, dependency-light and safe to load; disabling it simply
    # skips registering the trading services and tools.
    ENABLE_TRADING: bool = Field(
        default=True,
        validation_alias=AliasChoices("AETHEROS_ENABLE_TRADING", "ENABLE_TRADING"),
    )

    # Which market-data provider to use. "mock" is the only provider shipped in
    # this increment; it is deterministic and loudly labelled SourceTier.MOCK.
    # Real vendor adapters register additional names later without changing
    # this contract.
    MARKET_DATA_PROVIDER: str = Field(
        default="yahoo",
        validation_alias=AliasChoices(
            "AETHEROS_MARKET_DATA_PROVIDER", "MARKET_DATA_PROVIDER"
        ),
    )

    # Default timeframe used when a request does not specify one.
    TRADING_DEFAULT_TIMEFRAME: str = Field(
        default="1d",
        validation_alias=AliasChoices(
            "AETHEROS_TRADING_DEFAULT_TIMEFRAME", "TRADING_DEFAULT_TIMEFRAME"
        ),
    )

    # Upper bound on candles requested/returned for one analysis, so a tool
    # call can never pull an unbounded series into memory or into the LLM
    # context.
    TRADING_MAX_CANDLES: int = Field(
        default=500,
        ge=10,
        le=5000,
        validation_alias=AliasChoices(
            "AETHEROS_TRADING_MAX_CANDLES", "TRADING_MAX_CANDLES"
        ),
    )

    # Cache time-to-live (seconds) for quotes and candle series respectively.
    # Quotes go stale fast; candle series can be reused a little longer.
    TRADING_CACHE_TTL_QUOTE: float = Field(
        default=5.0,
        gt=0.0,
        validation_alias=AliasChoices(
            "AETHEROS_TRADING_CACHE_TTL_QUOTE", "TRADING_CACHE_TTL_QUOTE"
        ),
    )
    TRADING_CACHE_TTL_CANDLES: float = Field(
        default=30.0,
        gt=0.0,
        validation_alias=AliasChoices(
            "AETHEROS_TRADING_CACHE_TTL_CANDLES", "TRADING_CACHE_TTL_CANDLES"
        ),
    )

    # A candle series older than (timeframe * this multiplier) is flagged STALE
    # in its DataQuality rather than silently presented as current.
    TRADING_STALE_MULTIPLIER: float = Field(
        default=3.0,
        gt=0.0,
        validation_alias=AliasChoices(
            "AETHEROS_TRADING_STALE_MULTIPLIER", "TRADING_STALE_MULTIPLIER"
        ),
    )

    # HTTP timeout (seconds) for network-backed market-data providers (e.g. the
    # Yahoo adapter). A provider must raise a typed error on timeout, never
    # return fabricated bars.
    TRADING_HTTP_TIMEOUT: float = Field(
        default=15.0,
        gt=0.0,
        validation_alias=AliasChoices(
            "AETHEROS_TRADING_HTTP_TIMEOUT", "TRADING_HTTP_TIMEOUT"
        ),
    )

    # Risk engine. All deterministic knobs for the trade-plan geometry.
    #
    # Stop distance = this multiple of ATR. 1.5x is a common volatility stop:
    # wide enough to sit outside normal noise, tight enough to keep risk defined.
    TRADING_RISK_ATR_STOP_MULT: float = Field(
        default=1.5,
        gt=0.0,
        validation_alias=AliasChoices(
            "AETHEROS_TRADING_RISK_ATR_STOP_MULT", "TRADING_RISK_ATR_STOP_MULT"
        ),
    )

    # Minimum acceptable reward:risk. Used to project a target when no structural
    # level lies ahead, and to flag (never hide) a setup whose R:R is too thin.
    TRADING_RISK_MIN_REWARD: float = Field(
        default=1.5,
        gt=0.0,
        validation_alias=AliasChoices(
            "AETHEROS_TRADING_RISK_MIN_REWARD", "TRADING_RISK_MIN_REWARD"
        ),
    )

    # Percent of account equity to risk per trade when sizing a position. Only
    # applied when the caller actually supplies an account equity.
    TRADING_RISK_ACCOUNT_PCT: float = Field(
        default=1.0,
        gt=0.0,
        le=100.0,
        validation_alias=AliasChoices(
            "AETHEROS_TRADING_RISK_ACCOUNT_PCT", "TRADING_RISK_ACCOUNT_PCT"
        ),
    )

    # Backtesting: walk-forward evaluation of a directional signal. The horizon
    # is how many bars ahead the realised move is scored over; warmup is the
    # minimum history a signal needs before its first (indicator-dependent) call
    # is trusted; min-sample is the fewest scored predictions below which a
    # result is flagged not reliable regardless of the headline accuracy.
    TRADING_BACKTEST_HORIZON: int = Field(
        default=5,
        ge=1,
        le=500,
        validation_alias=AliasChoices(
            "AETHEROS_TRADING_BACKTEST_HORIZON", "TRADING_BACKTEST_HORIZON"
        ),
    )

    TRADING_BACKTEST_WARMUP: int = Field(
        default=50,
        ge=1,
        le=5000,
        validation_alias=AliasChoices(
            "AETHEROS_TRADING_BACKTEST_WARMUP", "TRADING_BACKTEST_WARMUP"
        ),
    )

    TRADING_BACKTEST_MIN_SAMPLE: int = Field(
        default=30,
        ge=1,
        le=100000,
        validation_alias=AliasChoices(
            "AETHEROS_TRADING_BACKTEST_MIN_SAMPLE", "TRADING_BACKTEST_MIN_SAMPLE"
        ),
    )

    # Critic / validator: the go/no-go gate that can reject a weak signal.
    # min-evidence is the fewest reliable evidence items below which the case is
    # "insufficient" rather than approvable; min-agreement is the share of
    # directional evidence weight that must back the fused side (a lower share
    # means the indicators contradict the call and the signal is rejected).
    TRADING_CRITIC_MIN_EVIDENCE: int = Field(
        default=2,
        ge=1,
        le=100,
        validation_alias=AliasChoices(
            "AETHEROS_TRADING_CRITIC_MIN_EVIDENCE", "TRADING_CRITIC_MIN_EVIDENCE"
        ),
    )

    TRADING_CRITIC_MIN_AGREEMENT: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        validation_alias=AliasChoices(
            "AETHEROS_TRADING_CRITIC_MIN_AGREEMENT", "TRADING_CRITIC_MIN_AGREEMENT"
        ),
    )

    # Probability estimation + calibration (spec sections 6, 7). A deterministic
    # logistic model is trained on causal features to estimate P(up over the next
    # `horizon` bars), then Platt-calibrated on a held-out slice. The data is split
    # time-ordered (never shuffled) into train / calibration / holdout so the
    # reported edge is genuinely out-of-sample and free of look-ahead bias. A model
    # that does not beat the naive base-rate baseline on the holdout is reported as
    # NOT reliable rather than dressed up as a signal (sections 2, 3, 28, 61).
    TRADING_PROB_HORIZON: int = Field(
        default=5,
        ge=1,
        le=500,
        validation_alias=AliasChoices(
            "AETHEROS_TRADING_PROB_HORIZON", "TRADING_PROB_HORIZON"
        ),
    )

    # Fewest labelled rows required in each split before an estimate is trusted.
    # Below these a result is flagged not reliable regardless of the headline number.
    TRADING_PROB_MIN_TRAIN: int = Field(
        default=120,
        ge=10,
        le=1000000,
        validation_alias=AliasChoices(
            "AETHEROS_TRADING_PROB_MIN_TRAIN", "TRADING_PROB_MIN_TRAIN"
        ),
    )

    TRADING_PROB_MIN_CALIB: int = Field(
        default=40,
        ge=5,
        le=1000000,
        validation_alias=AliasChoices(
            "AETHEROS_TRADING_PROB_MIN_CALIB", "TRADING_PROB_MIN_CALIB"
        ),
    )

    TRADING_PROB_MIN_HOLDOUT: int = Field(
        default=40,
        ge=5,
        le=1000000,
        validation_alias=AliasChoices(
            "AETHEROS_TRADING_PROB_MIN_HOLDOUT", "TRADING_PROB_MIN_HOLDOUT"
        ),
    )

    # L2 penalty and gradient-descent budget for the numpy logistic model. Fixed
    # (not tuned per call) so a given series always yields the same coefficients.
    TRADING_PROB_L2: float = Field(
        default=1.0,
        ge=0.0,
        validation_alias=AliasChoices("AETHEROS_TRADING_PROB_L2", "TRADING_PROB_L2"),
    )

    TRADING_PROB_ITERS: int = Field(
        default=500,
        ge=1,
        le=100000,
        validation_alias=AliasChoices(
            "AETHEROS_TRADING_PROB_ITERS", "TRADING_PROB_ITERS"
        ),
    )

    TRADING_PROB_LR: float = Field(
        default=0.1,
        gt=0.0,
        validation_alias=AliasChoices("AETHEROS_TRADING_PROB_LR", "TRADING_PROB_LR"),
    )

    # Number of equal-width bins used to compute Expected Calibration Error.
    TRADING_PROB_ECE_BINS: int = Field(
        default=10,
        ge=2,
        le=100,
        validation_alias=AliasChoices(
            "AETHEROS_TRADING_PROB_ECE_BINS", "TRADING_PROB_ECE_BINS"
        ),
    )

    # Dead-band around P(up)=0.5 within which the directional call is SIDEWAYS
    # rather than a weak UP/DOWN. A calibrated probability barely off even odds is
    # not a directional edge.
    TRADING_PROB_DIRECTION_BAND: float = Field(
        default=0.10,
        ge=0.0,
        lt=0.5,
        validation_alias=AliasChoices(
            "AETHEROS_TRADING_PROB_DIRECTION_BAND", "TRADING_PROB_DIRECTION_BAND"
        ),
    )


    # ═══════════════════════════════════════════════
    #                News & sentiment
    # ═══════════════════════════════════════════════
    
    
    # Which news provider the bootstrapper wires. "mock" is the deterministic,
    # loudly-labelled synthetic feed; a real feed can be added behind the same
    # NewsProvider ABC without touching the sentiment/service layers.
    NEWS_PROVIDER: str = Field(
        default="yahoo",
        validation_alias=AliasChoices("AETHEROS_NEWS_PROVIDER", "NEWS_PROVIDER"),
    )

    # Upper bound on headlines fetched/scored per analysis request.
    TRADING_NEWS_MAX_ITEMS: int = Field(
        default=20,
        ge=1,
        le=500,
        validation_alias=AliasChoices(
            "AETHEROS_TRADING_NEWS_MAX_ITEMS", "TRADING_NEWS_MAX_ITEMS"
        ),
    )

    # Minimum headlines required before a news-sentiment read is considered
    # reliable; below this the read is surfaced but flagged too-thin.
    TRADING_NEWS_MIN_ITEMS: int = Field(
        default=3,
        ge=1,
        le=500,
        validation_alias=AliasChoices(
            "AETHEROS_TRADING_NEWS_MIN_ITEMS", "TRADING_NEWS_MIN_ITEMS"
        ),
    )


    # ═══════════════════════════════════════════════
    #         Event / economic calendar
    # ═══════════════════════════════════════════════
    
    # Which calendar provider the bootstrapper wires. "mock" is the
    # deterministic, loudly-labelled synthetic feed; a real earnings/economic
    # calendar can be added behind the same CalendarProvider ABC without
    # touching the service layer.
    CALENDAR_PROVIDER: str = Field(
        default="yahoo",
        validation_alias=AliasChoices(
            "AETHEROS_CALENDAR_PROVIDER", "CALENDAR_PROVIDER"
        ),
    )

    # Look-ahead window (in days) for scheduled-event risk: how far forward the
    # calendar layer scans for earnings/macro/dividend events relevant to a
    # prediction. Defaults to one trading week.
    TRADING_EVENT_HORIZON_DAYS: int = Field(
        default=7,
        ge=1,
        le=365,
        validation_alias=AliasChoices(
            "AETHEROS_TRADING_EVENT_HORIZON_DAYS", "TRADING_EVENT_HORIZON_DAYS"
        ),
    )


    # ═══════════════════════════════════════════════
    #         Fundamental analysis
    # ═══════════════════════════════════════════════
    
    # Which fundamentals provider the bootstrapper wires. "mock" is the
    # deterministic, loudly-labelled synthetic feed; a real financial-statements
    # vendor can be added behind the same FundamentalsProvider ABC without
    # touching the service layer.
    FUNDAMENTALS_PROVIDER: str = Field(
        default="yahoo",
        validation_alias=AliasChoices(
            "AETHEROS_FUNDAMENTALS_PROVIDER", "FUNDAMENTALS_PROVIDER"
        ),
    )

    # Minimum scored metrics required before a fundamental read is considered
    # reliable; below this the read is surfaced but flagged too-thin.
    TRADING_FUND_MIN_METRICS: int = Field(
        default=5,
        ge=1,
        le=50,
        validation_alias=AliasChoices(
            "AETHEROS_TRADING_FUND_MIN_METRICS", "TRADING_FUND_MIN_METRICS"
        ),
    )

    # ═══════════════════════════════════════════════
    #        Market-regime detection
    # ═══════════════════════════════════════════════
    
    # ---  (Increment 17) ---------------------------
    # ADX threshold at/above which the market is treated as trending rather
    # than range-bound (Wilder's classic 25); below it the tape is choppy.
    TRADING_REGIME_ADX_TREND: float = Field(
        default=25.0,
        ge=1.0,
        le=100.0,
        validation_alias=AliasChoices(
            "AETHEROS_TRADING_REGIME_ADX_TREND", "TRADING_REGIME_ADX_TREND"
        ),
    )

    # ATR-as-a-fraction-of-price at/above which the regime is classified
    # VOLATILE regardless of trend strength (0.03 == 3% of price; mirrors the
    # HIGH cut-off used by RiskBand.from_atr_pct).
    TRADING_REGIME_VOL_HIGH_PCT: float = Field(
        default=0.03,
        gt=0.0,
        le=1.0,
        validation_alias=AliasChoices(
            "AETHEROS_TRADING_REGIME_VOL_HIGH_PCT", "TRADING_REGIME_VOL_HIGH_PCT"
        ),
    )

    # Wilder period for the ADX/ATR maths behind the regime read.
    TRADING_REGIME_PERIOD: int = Field(
        default=14,
        ge=2,
        le=200,
        validation_alias=AliasChoices(
            "AETHEROS_TRADING_REGIME_PERIOD", "TRADING_REGIME_PERIOD"
        ),
    )

    # Minimum candles required before a regime is classified; below this the
    # read honestly returns UNKNOWN rather than a fabricated regime.
    TRADING_REGIME_MIN_BARS: int = Field(
        default=30,
        ge=1,
        le=5000,
        validation_alias=AliasChoices(
            "AETHEROS_TRADING_REGIME_MIN_BARS", "TRADING_REGIME_MIN_BARS"
        ),
    )

    # Default benchmark an instrument's relative strength is measured against
    # when the caller names none -- a broad-market proxy (spec sections 2, 27,
    # "sector/market strength"). Overridable per call.
    TRADING_BENCHMARK_SYMBOL: str = Field(
        default="SPY",
        min_length=1,
        validation_alias=AliasChoices(
            "AETHEROS_TRADING_BENCHMARK_SYMBOL", "TRADING_BENCHMARK_SYMBOL"
        ),
    )

    # Lookback window (in bars) over which relative strength compares the two
    # return series. Aligned down to the shorter series if either is thinner.
    TRADING_RS_LOOKBACK: int = Field(
        default=60,
        ge=2,
        le=5000,
        validation_alias=AliasChoices(
            "AETHEROS_TRADING_RS_LOOKBACK", "TRADING_RS_LOOKBACK"
        ),
    )

    # Minimum aligned bars required before a relative-strength read is made;
    # below this the read honestly returns UNKNOWN rather than a fabricated lean.
    TRADING_RS_MIN_BARS: int = Field(
        default=20,
        ge=2,
        le=5000,
        validation_alias=AliasChoices(
            "AETHEROS_TRADING_RS_MIN_BARS", "TRADING_RS_MIN_BARS"
        ),
    )

    # Excess return (instrument minus benchmark, as a fraction) within +/- this
    # band is scored SIDEWAYS/in-line, so a near-matching performance is not
    # credited as out- or under-performance (0.02 == 2% over the window).
    TRADING_RS_DEAD_BAND: float = Field(
        default=0.02,
        ge=0.0,
        le=1.0,
        validation_alias=AliasChoices(
            "AETHEROS_TRADING_RS_DEAD_BAND", "TRADING_RS_DEAD_BAND"
        ),
    )

    # Trailing baseline window (in bars) the anomaly detector measures the last
    # bar against. The last bar's return, volume and overnight gap are each
    # z-scored versus the mean/std of the prior TRADING_ANOMALY_LOOKBACK bars.
    TRADING_ANOMALY_LOOKBACK: int = Field(
        default=60,
        ge=3,
        le=5000,
        validation_alias=AliasChoices(
            "AETHEROS_TRADING_ANOMALY_LOOKBACK", "TRADING_ANOMALY_LOOKBACK"
        ),
    )

    # Minimum baseline bars required before an anomaly read is made; below this
    # the read honestly returns UNKNOWN rather than a fabricated z-score.
    TRADING_ANOMALY_MIN_BARS: int = Field(
        default=20,
        ge=3,
        le=5000,
        validation_alias=AliasChoices(
            "AETHEROS_TRADING_ANOMALY_MIN_BARS", "TRADING_ANOMALY_MIN_BARS"
        ),
    )

    # Absolute z-score at or above which the last bar's return/volume/gap is
    # flagged as a statistical anomaly (3.0 == a ~3-sigma move against its own
    # trailing baseline). Below this on every measure the read is "no anomaly".
    TRADING_ANOMALY_Z: float = Field(
        default=3.0,
        ge=0.5,
        le=20.0,
        validation_alias=AliasChoices(
            "AETHEROS_TRADING_ANOMALY_Z", "TRADING_ANOMALY_Z"
        ),
    )

    # Forward horizon (in bars) a historical-analogue read measures each past
    # analogue's realised outcome over -- "when the setup looked like today, what
    # happened over the next N bars?". Mirrors the backtest horizon default.
    TRADING_HIST_HORIZON: int = Field(
        default=5,
        ge=1,
        le=500,
        validation_alias=AliasChoices(
            "AETHEROS_TRADING_HIST_HORIZON", "TRADING_HIST_HORIZON"
        ),
    )

    # Number of nearest historical analogues (K) averaged for the read. The K
    # past bars whose causal feature vector is closest to the latest bar's.
    TRADING_HIST_NEIGHBORS: int = Field(
        default=25,
        ge=2,
        le=5000,
        validation_alias=AliasChoices(
            "AETHEROS_TRADING_HIST_NEIGHBORS", "TRADING_HIST_NEIGHBORS"
        ),
    )

    # Minimum labelled analogue rows (past bars with a fully-realised forward
    # outcome) required before a read is made; below this it returns UNKNOWN
    # rather than a fabricated lean.
    TRADING_HIST_MIN_ANALOGUES: int = Field(
        default=20,
        ge=2,
        le=5000,
        validation_alias=AliasChoices(
            "AETHEROS_TRADING_HIST_MIN_ANALOGUES", "TRADING_HIST_MIN_ANALOGUES"
        ),
    )

    # The analogue up-rate must clear 0.5 by more than +/- this band to lean
    # UP/DOWN; inside it the read is SIDEWAYS/inconclusive (0.10 == 60/40).
    TRADING_HIST_DEAD_BAND: float = Field(
        default=0.10,
        ge=0.0,
        le=0.5,
        validation_alias=AliasChoices(
            "AETHEROS_TRADING_HIST_DEAD_BAND", "TRADING_HIST_DEAD_BAND"
        ),
    )

    # Portfolio-level total risk budget as a fraction of account equity: the most
    # a whole basket of trades may risk at once (0.05 == 5% of equity across all
    # positions). The per-trade slice is this divided by the number of trades.
    TRADING_PORTFOLIO_MAX_RISK_PCT: float = Field(
        default=0.05,
        gt=0.0,
        le=1.0,
        validation_alias=AliasChoices(
            "AETHEROS_TRADING_PORTFOLIO_MAX_RISK_PCT", "TRADING_PORTFOLIO_MAX_RISK_PCT"
        ),
    )

    # Maximum gross notional exposure as a fraction of account equity (1.0 == no
    # leverage; the book's total position value may not exceed equity). The
    # allocator scales positions down to respect this.
    TRADING_PORTFOLIO_MAX_EXPOSURE_PCT: float = Field(
        default=1.0,
        gt=0.0,
        le=10.0,
        validation_alias=AliasChoices(
            "AETHEROS_TRADING_PORTFOLIO_MAX_EXPOSURE_PCT",
            "TRADING_PORTFOLIO_MAX_EXPOSURE_PCT",
        ),
    )

    # Fraction of the accumulated outcome history held out (most-recent, time-
    # ordered) to validate a proposed recalibration correction out-of-sample
    # before it is trusted. A correction that does not improve holdout Brier is
    # never trusted (spec section 7 -- no overfit, no manufactured confidence).
    TRADING_CALIB_HOLDOUT_FRACTION: float = Field(
        default=0.3,
        ge=0.1,
        le=0.5,
        validation_alias=AliasChoices(
            "AETHEROS_TRADING_CALIB_HOLDOUT_FRACTION",
            "TRADING_CALIB_HOLDOUT_FRACTION",
        ),
    )

    # The autonomous monitoring loop is OFF by default (spec section 29 -- autonomy
    # bounded and opt-in). When enabled, a scheduler runs one bounded monitoring
    # sweep every TRADING_MONITOR_INTERVAL_SECONDS; it never runs unless this is
    # explicitly turned on.
    TRADING_MONITOR_ENABLED: bool = Field(
        default=True,
        validation_alias=AliasChoices(
            "AETHEROS_TRADING_MONITOR_ENABLED", "TRADING_MONITOR_ENABLED"
        ),
    )

    # Seconds between autonomous monitoring sweeps when the loop is enabled.
    TRADING_MONITOR_INTERVAL_SECONDS: float = Field(
        default=300.0,
        ge=5.0,
        le=86400.0,
        validation_alias=AliasChoices(
            "AETHEROS_TRADING_MONITOR_INTERVAL_SECONDS",
            "TRADING_MONITOR_INTERVAL_SECONDS",
        ),
    )

    # Minimum resolved, reliably-probabilistic outcomes before a calibration
    # audit will PROPOSE a recalibration correction. Below this the audit still
    # measures realised calibration but proposes no correction (a tiny live
    # sample would overfit -- spec section 7).
    TRADING_CALIB_MIN_SAMPLE: int = Field(
        default=30,
        ge=2,
        le=100000,
        validation_alias=AliasChoices(
            "AETHEROS_TRADING_CALIB_MIN_SAMPLE", "TRADING_CALIB_MIN_SAMPLE"
        ),
    )

    # Gap between the mean predicted P(up) and the realised up-rate beyond which
    # the live model is flagged over-/under-confident (0.05 == 5 percentage
    # points); inside it the realised calibration is called well-calibrated.
    TRADING_CALIB_BIAS_BAND: float = Field(
        default=0.05,
        ge=0.0,
        le=0.5,
        validation_alias=AliasChoices(
            "AETHEROS_TRADING_CALIB_BIAS_BAND", "TRADING_CALIB_BIAS_BAND"
        ),
    )

    # Resolved-outcome store backend. "memory" (default) accumulates outcomes
    # within the session; "file"/"jsonl" persists them to JSON Lines so a
    # monitoring sweep's results survive restarts and accumulate. Both sit behind
    # the same OutcomeStore port. Only wired into the monitoring sweep when set.
    OUTCOME_STORE_BACKEND: str = Field(
        default="memory",
        validation_alias=AliasChoices(
            "AETHEROS_OUTCOME_STORE_BACKEND", "OUTCOME_STORE_BACKEND"
        ),
    )

    # Path the durable (file) outcome store writes to. Relative paths resolve
    # under DATA_DIR; the default is DATA_DIR/outcomes.jsonl.
    TRADING_OUTCOME_STORE_PATH: str = Field(
        default="outcomes.jsonl",
        min_length=1,
        validation_alias=AliasChoices(
            "AETHEROS_TRADING_OUTCOME_STORE_PATH", "TRADING_OUTCOME_STORE_PATH"
        ),
    )

    # Prediction-audit store backend. "memory" (default) keeps the within-session
    # in-process trail; "file"/"jsonl" persists every prediction to a JSON Lines
    # file so the audit history survives restarts. Both sit behind the same
    # PredictionStore port, so the orchestrator is unchanged either way.
    PREDICTION_STORE_BACKEND: str = Field(
        default="memory",
        validation_alias=AliasChoices(
            "AETHEROS_PREDICTION_STORE_BACKEND", "PREDICTION_STORE_BACKEND"
        ),
    )

    # Path the durable (file) prediction store writes to. Relative paths resolve
    # under DATA_DIR; the default is DATA_DIR/predictions.jsonl. Only used when
    # PREDICTION_STORE_BACKEND selects the file backend.
    TRADING_PREDICTION_STORE_PATH: str = Field(
        default="predictions.jsonl",
        min_length=1,
        validation_alias=AliasChoices(
            "AETHEROS_TRADING_PREDICTION_STORE_PATH", "TRADING_PREDICTION_STORE_PATH"
        ),
    )

    # Channel window (in bars) a breakout is measured against: the prior-N-bar
    # highest high / lowest low the latest close must exceed to count as a
    # breakout / breakdown (Donchian-style).
    TRADING_BREAKOUT_LOOKBACK: int = Field(
        default=20,
        ge=2,
        le=1000,
        validation_alias=AliasChoices(
            "AETHEROS_TRADING_BREAKOUT_LOOKBACK", "TRADING_BREAKOUT_LOOKBACK"
        ),
    )

    # Minimum bars required before a breakout read is made; below this the read
    # honestly returns UNKNOWN rather than a fabricated signal.
    TRADING_BREAKOUT_MIN_BARS: int = Field(
        default=25,
        ge=3,
        le=5000,
        validation_alias=AliasChoices(
            "AETHEROS_TRADING_BREAKOUT_MIN_BARS", "TRADING_BREAKOUT_MIN_BARS"
        ),
    )

    # Last-bar volume as a multiple of the channel's average volume at or above
    # which a breakout is treated as volume-confirmed (1.5 == 150% of average).
    TRADING_BREAKOUT_VOL_MULT: float = Field(
        default=1.5,
        ge=1.0,
        le=20.0,
        validation_alias=AliasChoices(
            "AETHEROS_TRADING_BREAKOUT_VOL_MULT", "TRADING_BREAKOUT_VOL_MULT"
        ),
    )

    # Half-width (in bars) of the local window used to confirm a swing pivot in
    # divergence detection: a bar is a pivot low/high only if it is the lowest/
    # highest close within +/- this many bars. Larger = fewer, more significant
    # pivots.
    TRADING_DIV_PIVOT_WINDOW: int = Field(
        default=3,
        ge=1,
        le=50,
        validation_alias=AliasChoices(
            "AETHEROS_TRADING_DIV_PIVOT_WINDOW", "TRADING_DIV_PIVOT_WINDOW"
        ),
    )

    # Minimum bars required before a divergence read is made; below this the read
    # honestly returns UNKNOWN rather than a fabricated signal.
    TRADING_DIV_MIN_BARS: int = Field(
        default=40,
        ge=10,
        le=5000,
        validation_alias=AliasChoices(
            "AETHEROS_TRADING_DIV_MIN_BARS", "TRADING_DIV_MIN_BARS"
        ),
    )

    # RSI period used as the oscillator in divergence detection.
    TRADING_DIV_RSI_PERIOD: int = Field(
        default=14,
        ge=2,
        le=100,
        validation_alias=AliasChoices(
            "AETHEROS_TRADING_DIV_RSI_PERIOD", "TRADING_DIV_RSI_PERIOD"
        ),
    )

    # The higher timeframe a multi-timeframe confirmation read compares the base
    # timeframe against, when the caller names none (default weekly).
    TRADING_MTF_HIGHER_TIMEFRAME: str = Field(
        default="1w",
        min_length=1,
        validation_alias=AliasChoices(
            "AETHEROS_TRADING_MTF_HIGHER_TIMEFRAME", "TRADING_MTF_HIGHER_TIMEFRAME"
        ),
    )

    # Maximum number of instruments a single watchlist scan will analyse. A cap
    # so one scan request cannot fan out into an unbounded number of fetches.
    TRADING_SCAN_MAX_SYMBOLS: int = Field(
        default=50,
        ge=1,
        le=500,
        validation_alias=AliasChoices(
            "AETHEROS_TRADING_SCAN_MAX_SYMBOLS", "TRADING_SCAN_MAX_SYMBOLS"
        ),
    )

    # Realised move (as a fraction of the entry price) within +/- this band is
    # scored SIDEWAYS when resolving a past prediction against later data, so a
    # near-flat move is not credited as a directional hit or miss. It grades the
    # three-way realised direction only; the binary up/down label behind a
    # probability's Brier contribution always uses the raw sign of the return.
    TRADING_EVAL_FLAT_BAND: float = Field(
        default=0.001,
        ge=0.0,
        le=1.0,
        validation_alias=AliasChoices(
            "AETHEROS_TRADING_EVAL_FLAT_BAND", "TRADING_EVAL_FLAT_BAND"
        ),
    )

    # Minimum number of *scored* (resolved, directional) predictions before an
    # aggregate performance/calibration summary is treated as reliable. Below
    # this the numbers are still reported, but flagged not reliable -- a handful
    # of outcomes is not a track record (spec sections 6, 9, 28).
    TRADING_PERF_MIN_SAMPLE: int = Field(
        default=20,
        ge=1,
        le=100000,
        validation_alias=AliasChoices(
            "AETHEROS_TRADING_PERF_MIN_SAMPLE", "TRADING_PERF_MIN_SAMPLE"
        ),
    )


    # ╔══════════════════════════════════════════╗
    # ║                Memory                     ║
    # ╚══════════════════════════════════════════╝

    # The memory subsystem is self-contained and offline-safe: the default
    # embedding backend is a deterministic, dependency-free hashing embedder, so
    # with MEMORY_ENABLED on and no model configured the layer still remembers
    # and retrieves (just with lexical-grade semantics). Every knob is read once,
    # here, into MemoryConfig -- never via scattered os.getenv (CLAUDE.md §18).
    # ENABLE_MEMORY (above) remains the master switch the bootstrapper gates on.

    # Path the SQLite memory database is written to. Relative paths resolve under
    # DATA_DIR; the default is DATA_DIR/memory.db.
    MEMORY_DATABASE: str = Field(
        default="memory.db",
        min_length=1,
        validation_alias=AliasChoices("AETHEROS_MEMORY_DATABASE", "MEMORY_DATABASE"),
    )

    # Embedding backend. "hashing" (default) is the deterministic local fallback;
    # real providers (ollama / openai) can be wired behind the same ABC later
    # without touching the vector or retrieval layers.
    MEMORY_VECTOR_PROVIDER: str = Field(
        default="hashing",
        validation_alias=AliasChoices(
            "AETHEROS_MEMORY_VECTOR_PROVIDER", "MEMORY_VECTOR_PROVIDER"
        ),
    )

    # Model identifier passed to a real embedding provider; ignored by the
    # hashing fallback. Empty means "provider default".
    MEMORY_EMBEDDING_MODEL: str = Field(
        default="",
        validation_alias=AliasChoices(
            "AETHEROS_MEMORY_EMBEDDING_MODEL", "MEMORY_EMBEDDING_MODEL"
        ),
    )

    # Dimensionality of the hashing embedder's vectors. Fixed per database: a
    # change only takes effect for memories embedded afterwards.
    MEMORY_EMBEDDING_DIM: int = Field(
        default=256,
        ge=16,
        le=4096,
        validation_alias=AliasChoices(
            "AETHEROS_MEMORY_EMBEDDING_DIM", "MEMORY_EMBEDDING_DIM"
        ),
    )

    # Default number of memories a retrieval returns after ranking.
    MEMORY_RETRIEVAL_LIMIT: int = Field(
        default=5,
        ge=1,
        le=100,
        validation_alias=AliasChoices(
            "AETHEROS_MEMORY_RETRIEVAL_LIMIT", "MEMORY_RETRIEVAL_LIMIT"
        ),
    )

    # Minimum blended similarity a candidate needs to survive retrieval. Keeps
    # weakly-related memories out of the LLM context (Rule 7).
    MEMORY_SIMILARITY_THRESHOLD: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        validation_alias=AliasChoices(
            "AETHEROS_MEMORY_SIMILARITY_THRESHOLD", "MEMORY_SIMILARITY_THRESHOLD"
        ),
    )

    # Whether decay / lifecycle transitions run (spec Phase 14).
    MEMORY_DECAY_ENABLED: bool = Field(
        default=True,
        validation_alias=AliasChoices(
            "AETHEROS_MEMORY_DECAY_ENABLED", "MEMORY_DECAY_ENABLED"
        ),
    )

    # Half-life, in days, used by the recency score and the decay pass. A memory
    # untouched for this long contributes half its original recency weight.
    MEMORY_DECAY_HALFLIFE_DAYS: float = Field(
        default=30.0,
        gt=0.0,
        validation_alias=AliasChoices(
            "AETHEROS_MEMORY_DECAY_HALFLIFE_DAYS", "MEMORY_DECAY_HALFLIFE_DAYS"
        ),
    )

    # Whether consolidation (dedup / merge / promotion) runs (spec Phase 12).
    MEMORY_CONSOLIDATION_ENABLED: bool = Field(
        default=True,
        validation_alias=AliasChoices(
            "AETHEROS_MEMORY_CONSOLIDATION_ENABLED", "MEMORY_CONSOLIDATION_ENABLED"
        ),
    )

    # Cosine similarity at/above which two memories of the same type are treated
    # as near-duplicates by the consolidator.
    MEMORY_DEDUP_THRESHOLD: float = Field(
        default=0.95,
        ge=0.5,
        le=1.0,
        validation_alias=AliasChoices(
            "AETHEROS_MEMORY_DEDUP_THRESHOLD", "MEMORY_DEDUP_THRESHOLD"
        ),
    )

    # Maximum number of items held in working memory before the oldest/least
    # important are summarised out (spec Phase 8 -- bounded context window).
    MEMORY_MAX_WORKING_CONTEXT: int = Field(
        default=50,
        ge=1,
        le=1000,
        validation_alias=AliasChoices(
            "AETHEROS_MEMORY_MAX_WORKING_CONTEXT", "MEMORY_MAX_WORKING_CONTEXT"
        ),
    )

    # Whether the agent automatically remembers useful experience after a run
    # (spec Phase 20). On by default now that the agent integration exists: when
    # memory is enabled the agent records an episode (and failure/recovery
    # records) after each meaningful run. Turn off to keep memory enabled for
    # recall + manual tools but stop automatic writes. (ENABLE_MEMORY is still
    # the master switch; this only matters when memory is on at all.)
    MEMORY_AUTO_REMEMBER: bool = Field(
        default=True,
        validation_alias=AliasChoices(
            "AETHEROS_MEMORY_AUTO_REMEMBER", "MEMORY_AUTO_REMEMBER"
        ),
    )

    # Agent recall (spec Phase 20C/20N). The maximum memories injected into the
    # planning context before a run, the minimum blended relevance score a
    # memory needs to be injected, and the total character budget for the
    # injected memory block -- the strict context budget that keeps recall from
    # polluting the LLM context (Rule 7).
    MEMORY_AGENT_RECALL_LIMIT: int = Field(
        default=5,
        ge=1,
        le=50,
        validation_alias=AliasChoices(
            "AETHEROS_MEMORY_AGENT_RECALL_LIMIT", "MEMORY_AGENT_RECALL_LIMIT"
        ),
    )

    MEMORY_AGENT_RECALL_MIN_SCORE: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        validation_alias=AliasChoices(
            "AETHEROS_MEMORY_AGENT_RECALL_MIN_SCORE", "MEMORY_AGENT_RECALL_MIN_SCORE"
        ),
    )

    MEMORY_AGENT_RECALL_MAX_CHARS: int = Field(
        default=1500,
        ge=100,
        le=20000,
        validation_alias=AliasChoices(
            "AETHEROS_MEMORY_AGENT_RECALL_MAX_CHARS", "MEMORY_AGENT_RECALL_MAX_CHARS"
        ),
    )
