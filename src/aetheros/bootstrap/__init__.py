"""AetherOS bootstrap package.

Logging is initialized lazily on first ``get_logger``/``setup_logging`` call
(see ``aetheros.core.logging.logger``), so importing this package creates no
run directory and installs no sinks.
"""

from __future__ import annotations

__all__: list[str] = []
