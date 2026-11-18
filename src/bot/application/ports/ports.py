import asyncio
from abc import ABC, abstractmethod
from collections.abc import Awaitable, Callable
from datetime import datetime

from bot.domain.live_status import LiveStatus
from bot.domain.ubication import Ubication
from bot.domain.user import User


# Callbacks con los que la fuente entrega lo que recibe.
OnUbication = Callable[[int, Ubication], Awaitable[None]]
OnLiveEnded = Callable[[int, datetime], Awaitable[None]]


class UbicationSourcePort(ABC):
    @abstractmethod
    def start(
        self,
        loop: asyncio.AbstractEventLoop,
        on_ubication: OnUbication,
        on_live_ended: OnLiveEnded,
    ) -> None:
        """Registra a quién entregar los eventos recibidos.

        ``loop`` es el event loop de la app: la fuente puede recibir en otro
        hilo y debe programar los callbacks en él. Se llama una vez al
        arrancar, antes de cualquier ``suscribe``.
        """

    @abstractmethod
    async def suscribe(self, user_id: int) -> bool: ...
    @abstractmethod
    async def unsubscribe(self, user_id: int) -> bool: ...

class UbicationRepository(ABC):
    @abstractmethod
    async def get_last(self, user_id: int) -> Ubication | None: ...
    @abstractmethod
    async def save_last(self, user_id: int, ubication: Ubication) -> None: ...
    @abstractmethod
    async def end_live(self, user_id: int) -> None:
        """Marca la última ubicación del usuario como ya no en vivo."""

class UbicationNotifier(ABC):
    @abstractmethod
    async def notify(self, user_id: int, ubication: Ubication) -> None: ...
    @abstractmethod
    async def notify_live_ended(self, user_id: int, ended_at: datetime) -> None: ...


class LiveStatusNotifier(ABC):
    """Avisa a todos los interesados cuando alguien empieza o deja de estar en vivo."""

    @abstractmethod
    async def notify_status(self, status: LiveStatus) -> None: ...


class UbicationPublisherPort(ABC):
    @abstractmethod
    async def publish(self, user_id: int, ubication: Ubication) -> None: ...
    @abstractmethod
    async def publish_live_ended(self, user_id: int, ended_at: datetime) -> None: ...


class UserRepository(ABC):
    @abstractmethod
    async def list_all(self) -> list[User]: ...

    @abstractmethod
    async def get_by_telegram(self, telegram_id: int) -> User | None: ...

    @abstractmethod
    async def create(self, telegram_id: int) -> User: ...

    @abstractmethod
    async def save_phone(self, telegram_id: int, phone: str) -> bool: ...

    @abstractmethod
    async def save_consent(self, telegram_id: int, consent: bool) -> bool: ...
