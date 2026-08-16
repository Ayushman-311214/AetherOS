from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4


@dataclass(frozen=True, slots=True)
class Event:
    """
    Base class for all events in AetherOS.

    Every event inherits from this class.
    """

    event_id: str = field(default_factory=lambda: str(uuid4()))
    timestamp: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )

    def to_dict(self) -> dict[str, Any]:
        """
        Convert event into a serializable dictionary.
        """
        return asdict(self)

    @property
    def name(self) -> str:
        """
        Returns the event class name.
        """
        return self.__class__.__name__

    def __str__(self) -> str:
        return f"{self.name}(id={self.event_id})"