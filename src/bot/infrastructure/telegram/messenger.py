from telegram import Bot, ReplyKeyboardRemove

from bot.application.ports.telegram import BotMessengerPort
from bot.infrastructure.telegram.keyboards import consent_keyboard, phone_keyboard


class TelegramMessenger(BotMessengerPort):
    def __init__(self, bot: Bot) -> None:
        self._bot = bot

    async def send_text(self, chat_id: int, text: str) -> None:
        await self._bot.send_message(chat_id=chat_id, text=text)

    async def ask_phone(self, chat_id: int, text: str) -> None:
        await self._bot.send_message(
            chat_id=chat_id, text=text, reply_markup=phone_keyboard()
        )

    async def ask_consent(self, chat_id: int, text: str) -> None:
        await self._bot.send_message(
            chat_id=chat_id, text=text, reply_markup=consent_keyboard()
        )

    async def remove_keyboard(self, chat_id: int, text: str) -> None:
        await self._bot.send_message(
            chat_id=chat_id, text=text, reply_markup=ReplyKeyboardRemove()
        )

    async def send_location(
        self, chat_id: int, latitude: float, longitude: float
    ) -> None:
        await self._bot.send_location(
            chat_id=chat_id, latitude=latitude, longitude=longitude
        )
