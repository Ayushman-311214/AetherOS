from __future__ import annotations

from ..core.interfaces.llm_provider import (
    LLMProvider,
)


class LLMProviderManager:
    """
    Manages available LLM providers and the active provider.
    """

    def __init__(self) -> None:

        self._providers: dict[
            str,
            LLMProvider,
        ] = {}

        self._active: str | None = None

    # ==========================================================
    # Registration
    # ==========================================================

    def register(
        self,
        provider: LLMProvider,
    ) -> None:

        if provider.name in self._providers:
            raise ValueError(
                f"Provider '{provider.name}' "
                "is already registered."
            )

        self._providers[
            provider.name
        ] = provider

    # ==========================================================
    # Lookup
    # ==========================================================

    def get(
        self,
        name: str,
    ) -> LLMProvider:

        try:
            return self._providers[name]

        except KeyError as exc:
            raise KeyError(
                f"LLM provider '{name}' "
                "is not registered."
            ) from exc

    # ==========================================================
    # Active Provider
    # ==========================================================

    def set_active(
        self,
        name: str,
    ) -> None:

        self.get(name)

        self._active = name

    @property
    def active(self) -> LLMProvider:

        if self._active is None:
            raise RuntimeError(
                "No active LLM provider configured."
            )

        return self._providers[
            self._active
        ]

    # ==========================================================
    # Information
    # ==========================================================

    def names(self) -> list[str]:
        return sorted(
            self._providers.keys()
        )

    def count(self) -> int:
        return len(self._providers)