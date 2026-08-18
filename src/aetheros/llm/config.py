from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(slots=True)
class LLMConfig:
    """
    Configuration for an OpenAI-compatible LLM provider.
    """

    api_key: str
    model: str
    base_url: str | None = None

    temperature: float = 0.0
    max_tokens: int | None = None

    @classmethod
    def from_env(
        cls,
        *,
        api_key_env: str = "OPENAI_API_KEY",
        model_env: str = "LLM_MODEL",
        base_url_env: str = "LLM_BASE_URL",
    ) -> "LLMConfig":

        api_key = os.getenv(api_key_env)

        if not api_key:
            raise RuntimeError(
                f"Missing environment variable: {api_key_env}"
            )

        model = os.getenv(
            model_env,
            "gpt-4o-mini",
        )

        base_url = os.getenv(
            base_url_env
        )

        return cls(
            api_key=api_key,
            model=model,
            base_url=base_url,
        )