import asyncio

from bot.application.ports.ports import UserRepository
from bot.domain.user import User
from bot.infrastructure.sqlite.database import SQLiteDatabase


class SQLiteUserRepository(UserRepository):
    def __init__(self, repo: SQLiteDatabase) -> None:
        self._repo = repo

    async def list_all(self) -> list[User]:
        rows = await asyncio.to_thread(self._repo.obtener_usuarios)
        return [user for row in rows if (user := self._to_user(row)) is not None]

    async def get_by_telegram(self, telegram_id: int) -> User | None:
        row = await asyncio.to_thread(
            self._repo.obtener_usuario_por_telegram, telegram_id
        )
        return self._to_user(row)

    async def create(self, telegram_id: int) -> User:
        await asyncio.to_thread(self._repo.crear_usuario, telegram_id)
        user = await self.get_by_telegram(telegram_id)
        if user is None:
            raise RuntimeError(f"No se pudo crear el usuario {telegram_id}")
        return user

    async def save_phone(self, telegram_id: int, phone: str) -> bool:
        user = await self.get_by_telegram(telegram_id)
        if user is None:
            return False
        return await asyncio.to_thread(
            self._repo.guardar_datos_personales, user.id, phone, None
        )

    async def save_consent(self, telegram_id: int, consent: bool) -> bool:
        user = await self.get_by_telegram(telegram_id)
        if user is None:
            return False
        return await asyncio.to_thread(
            self._repo.guardar_datos_personales, user.id, None, consent
        )

    @staticmethod
    def _to_user(row) -> User | None:
        if row is None:
            return None
        return User(
            id=row["id"],
            telegram_id=row["telegram_id"],
            telefono=row["telefono"],
            consentimiento=bool(row["consentimiento"]),
        )
