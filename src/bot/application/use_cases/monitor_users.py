"""Consultas del panel de administración sobre los usuarios del bot."""

from dataclasses import dataclass
from datetime import UTC, datetime

from bot.application.ports.ports import UbicationRepository, UserRepository
from bot.domain.ubication import Ubication


@dataclass(frozen=True)
class MonitoredUser:
    telegram_id: int
    telefono: str | None
    live: bool
    last_seen: datetime | None


class MonitorUsersUseCase:
    def __init__(self, users: UserRepository, ubications: UbicationRepository) -> None:
        self._users = users
        self._ubications = ubications

    async def list_users(self) -> list[MonitoredUser]:
        """Usuarios que se pueden seguir (los que tienen Telegram)."""
        now = datetime.now(UTC)
        result: list[MonitoredUser] = []
        for user in await self._users.list_all():
            if user.telegram_id is None:
                continue
            last = await self._ubications.get_last(user.telegram_id)
            result.append(
                MonitoredUser(
                    telegram_id=user.telegram_id,
                    telefono=user.telefono,
                    live=last is not None and last.is_live_at(now),
                    last_seen=last.timestamp if last else None,
                )
            )
        return result

    async def last_ubication(self, telegram_id: int) -> Ubication | None:
        return await self._ubications.get_last(telegram_id)
