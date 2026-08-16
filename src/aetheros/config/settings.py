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

    # -----------------------
    # Runtime
    # -----------------------

    MAX_RETRIES: int = 3
    REQUEST_TIMEOUT: int = 60

    # -----------------------
    # Feature Flags
    # -----------------------

    ENABLE_VISION: bool = True
    ENABLE_MEMORY: bool = False
    ENABLE_BROWSER: bool = False
    ENABLE_VOICE: bool = False