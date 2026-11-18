from abc import ABC, abstractmethod
from enum import Enum

from bot.domain.ubication import Ubication


class LoginStep(str, Enum):
    PHONE = "telefono"
    CONSENT = "consentimiento"
    READY = "listo"


class BotMessengerPort(ABC):
    @abstractmethod
    async def send_text(self, chat_id: int, text: str) -> None: ...

    @abstractmethod
    async def ask_phone(self, chat_id: int, text: str) -> None: ...

    @abstractmethod
    async def ask_consent(self, chat_id: int, text: str) -> None: ...

    @abstractmethod
    async def remove_keyboard(self, chat_id: int, text: str) -> None: ...

    @abstractmethod
    async def send_location(
        self, chat_id: int, latitude: float, longitude: float
    ) -> None: ...


class BotActionsPort(ABC):
    @abstractmethod
    async def register_user(self, telegram_id: int, chat_id: int) -> None: ...

    @abstractmethod
    async def resolve_login(self, telegram_id: int, chat_id: int) -> LoginStep: ...

    @abstractmethod
    async def save_phone(
        self, telegram_id: int, chat_id: int, phone: str
    ) -> LoginStep: ...

    @abstractmethod
    async def save_consent(
        self, telegram_id: int, chat_id: int, accepted: bool
    ) -> LoginStep: ...

    @abstractmethod
    async def share_ubication(
        self,
        telegram_id: int,
        chat_id: int,
        ubication: Ubication,
        is_update: bool,
    ) -> None:
        """``is_update``: edición de un mensaje de ubicación en vivo ya enviado."""

    @abstractmethod
    async def show_last(self, telegram_id: int, chat_id: int) -> None: ...

    @abstractmethod
    async def stop_following(self, telegram_id: int, chat_id: int) -> None: ...

    @abstractmethod
    async def logout(self, telegram_id: int, chat_id: int) -> None: ...
