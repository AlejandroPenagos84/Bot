from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class LiveStatus:
    """Cambio en si un usuario está compartiendo su ubicación en tiempo real."""

    telegram_id: int
    live: bool
    # Hasta cuándo sigue en vivo (``None``: no está en vivo o no tiene límite).
    live_until: datetime | None
    changed_at: datetime
