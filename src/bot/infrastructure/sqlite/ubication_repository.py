import asyncio
from datetime import datetime, timezone

from bot.application.ports.ports import UbicationRepository, UserRepository
from bot.domain.ubication import Ubication
from bot.infrastructure.sqlite.database import FORMATO_FECHA, SQLiteDatabase


class SQLiteUbicationRepository(UbicationRepository):
    def __init__(self, repo: SQLiteDatabase, users: UserRepository) -> None:
        self._repo = repo
        self._users = users

    async def get_last(self, user_id: int) -> Ubication | None:
        user = await self._users.get_by_telegram(user_id)
        if user is None:
            return None

        row = await asyncio.to_thread(self._repo.obtener_ultima, user.id)
        if row is None:
            return None

        return Ubication(
            latitude=row["lat"],
            longitude=row["lon"],
            timestamp=self._parse_timestamp(row["fecha"]),
            live=bool(row["en_vivo"]),
            live_until=(
                self._parse_timestamp(row["en_vivo_hasta"])
                if row["en_vivo_hasta"]
                else None
            ),
        )

    async def save_last(self, user_id: int, ubication: Ubication) -> None:
        user = await self._users.get_by_telegram(user_id)
        if user is None:
            return

        await asyncio.to_thread(
            self._repo.guardar_ubicacion,
            user.id,
            ubication.latitude,
            ubication.longitude,
            1,
            self._format_timestamp(ubication.timestamp),
            ubication.live,
            (
                self._format_timestamp(ubication.live_until)
                if ubication.live_until
                else None
            ),
        )

    async def end_live(self, user_id: int) -> None:
        user = await self._users.get_by_telegram(user_id)
        if user is None:
            return
        await asyncio.to_thread(self._repo.terminar_en_vivo, user.id)

    @staticmethod
    def _parse_timestamp(value: str) -> datetime:
        return datetime.strptime(value, FORMATO_FECHA).replace(tzinfo=timezone.utc)

    @staticmethod
    def _format_timestamp(timestamp: datetime) -> str:
        if timestamp.tzinfo is not None:
            timestamp = timestamp.astimezone(timezone.utc)
        return timestamp.strftime(FORMATO_FECHA)
