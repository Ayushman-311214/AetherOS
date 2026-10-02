"""
AetherOS Trading Intelligence.

This package is the core product of AetherOS: an evidence-based trading
intelligence and decision-support layer. It is deliberately independent of the
Desktop, Vision and Browser capability layers -- the numerical/API path must
work on its own, and those layers *enhance* it when available (see CLAUDE.md and
the Trading Intelligence spec).

Layering follows the established AetherOS pattern:

    domain models  ->  providers (interface + impls)  ->  services  ->  tools
                                                                          |
                                                                    ToolRegistry
                                                                          |
                                                                     Agent / LLM

Nothing here fabricates market data. Synthetic data is produced only by the
explicitly labelled MockMarketDataProvider (SourceTier.MOCK) and is surfaced as
such all the way to the analysis limitations, so it can never be mistaken for
real production data.
"""

from __future__ import annotations

__all__ = [
    "domain",
    "indicators",
    "providers",
    "services",
]
