"""Detecta cuándo un usuario empieza o deja de estar en vivo y lo avisa.

Las ubicaciones en vivo llegan cada pocos segundos; aquí se filtran para
emitir solo los *cambios* de estado. También cubre el caso que Telegram no
avisa: que el periodo en vivo venza solo (``live_until``).

El estado vive en memoria. Tras un reinicio, la primera ubicación de cada
usuario vuelve a emitir su estado, lo cual es inofensivo.
"""

import asyncio
import logging
from datetime import UTC, datetime

from bot.application.ports.ports import LiveStatusNotifier, UbicationRepository
from bot.domain.live_status import LiveStatus
from bot.domain.ubication import Ubication

logger = logging.getLogger(__name__)

_State = tuple[bool, datetime | None]  # (en vivo, en vivo hasta)


class LiveStatusTracker:
    def __init__(self, notifier: LiveStatusNotifier, repo: UbicationRepository) -> None:
        self._notifier = notifier
        self._repo = repo
        self._states: dict[int, _State] = {} # Telegram ID -> (en vivo, en vivo hasta)
        self._timers: dict[int, asyncio.TimerHandle] = {}

    async def on_ubication(self, user_id: int, ubication: Ubication) -> None:
        now = datetime.now(UTC)
        live = ubication.is_live_at(now)
        await self._set(user_id, live, ubication.live_until if live else None, now)

    async def on_live_ended(self, user_id: int, ended_at: datetime) -> None:
        await self._set(user_id, False, None, ended_at)

    def close(self) -> None:
        for timer in self._timers.values():
            timer.cancel()
        self._timers.clear()

    async def _set(
        self, user_id: int, live: bool, live_until: datetime | None, at: datetime
    ) -> None:
        state: _State = (live, live_until)
        if self._states.get(user_id) == state:
            return
        self._states[user_id] = state
        self._schedule_expiry(user_id, live_until if live else None)
        await self._notifier.notify_status(LiveStatus(user_id, live, live_until, at))

    def _schedule_expiry(self, user_id: int, live_until: datetime | None) -> None:
        previous = self._timers.pop(user_id, None)
        if previous is not None:
            previous.cancel()
        if live_until is None:
            return
        delay = max(0.0, (live_until - datetime.now(UTC)).total_seconds())
        loop = asyncio.get_running_loop()
        self._timers[user_id] = loop.call_later(
            delay, lambda: loop.create_task(self._expire(user_id, live_until))
        )

    async def _expire(self, user_id: int, live_until: datetime) -> None:
        self._timers.pop(user_id, None)
        if self._states.get(user_id) != (True, live_until):
            return  # llegó otra ubicación con un periodo distinto
        try:
            await self._repo.end_live(user_id)
            await self._set(user_id, False, None, live_until)
        except Exception:
            logger.exception("No se pudo marcar el fin en vivo de %s", user_id)
