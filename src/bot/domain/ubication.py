from dataclasses import dataclass
from datetime import datetime, timedelta

# Telegram usa este valor de ``live_period`` para "compartir indefinidamente".
LIVE_PERIOD_FOREVER = 0x7FFFFFFF


@dataclass(frozen=True)
class Ubication:
    latitude: float
    longitude: float
    timestamp: datetime
    # ``live``: viene de una ubicación en tiempo real que sigue activa.
    # ``live_until``: hasta cuándo Telegram la seguirá actualizando
    # (``None`` con ``live=True`` significa sin límite).
    live: bool = False
    live_until: datetime | None = None

    def is_live_at(self, now: datetime) -> bool:
        """En vivo y sin vencer. Telegram no avisa cuando el periodo expira solo."""
        return self.live and (self.live_until is None or now < self.live_until)

    def ended(self) -> "Ubication":
        """La misma posición, marcada como ya no en vivo."""
        return Ubication(self.latitude, self.longitude, self.timestamp)


def live_until_from(sent_at: datetime, live_period: int) -> datetime | None:
    """``live_period`` se cuenta desde que se envió el mensaje original."""
    if live_period >= LIVE_PERIOD_FOREVER:
        return None
    return sent_at + timedelta(seconds=live_period)
