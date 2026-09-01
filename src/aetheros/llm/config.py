from __future__ import annotations

import os
from dataclasses import dataclass, field

from dotenv import load_dotenv

from ..config.config_loader import get_settings

load_dotenv()


@dataclass(slots=True)
class LLMConfig:
    """
    Configuration for an OpenAI-compatible LLM provider.

    Values can be provided manually or loaded from environment variables.
    Manual values always take priority.
    """

    # repr=False keeps the key out of the dataclass repr, so it cannot leak
    # into a log line, an exception message, or a traceback frame dump.
    api_key: str = field(repr=False)
    model: str
    base_url: str | None = None

    temperature: float = 0.0
    max_tokens: int | None = None

    @classmethod
    def from_env(
        cls,
        *,
        api_key: str | None = None,
        model: str | None = None,
        base_url: str | None = None,
        api_key_env: str = "LLM_API_KEY",
        model_env: str = "LLM_MODEL",
        base_url_env: str = "LLM_BASE_URL",
    ) -> "LLMConfig":

        # Manual value → environment → default
        resolved_api_key = (
            api_key
            or os.getenv(api_key_env)
        )

        if not resolved_api_key:
            raise RuntimeError(
                f"Missing API key. Provide 'api_key' "
                f"or set {api_key_env}."
            )

        # The fallback comes from configuration (Settings.DEFAULT_MODEL),
        # never from a model identifier hardcoded here.
        resolved_model = (
            model
            or os.getenv(model_env)
            or get_settings().DEFAULT_MODEL
        )

        if not resolved_model:
            raise RuntimeError(
                f"Missing model. Provide 'model', set {model_env}, "
                f"or configure DEFAULT_MODEL."
            )

        resolved_base_url = (
            base_url
            or os.getenv(base_url_env)
        )

        return cls(
            api_key=resolved_api_key,
            model=resolved_model,
            base_url=resolved_base_url,
        )