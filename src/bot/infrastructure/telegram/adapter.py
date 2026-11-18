from telegram import Update
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from bot.application.ports.telegram import BotActionsPort, BotMessengerPort, LoginStep
from bot.domain.ubication import Ubication, live_until_from

HELP_TEXT = (
    "Soy un bot para recibir y guardar ubicaciones.\n\n"
    "/registrar - crear tu usuario\n"
    "/login - iniciar sesión (teléfono, consentimiento y STOMP)\n"
    "/ver - ver tu última ubicación\n"
    "/parar - dejar de compartir ubicación\n"
    "/logout - cerrar la sesión STOMP\n\n"
    "Para ubicación en vivo: Adjuntar → Ubicación → "
    "Compartir ubicación en tiempo real."
)


class TelegramAdapter:
    def __init__(
        self,
        application: Application,
        messenger: BotMessengerPort,
        actions: BotActionsPort,
    ) -> None:
        self._app = application
        self._messenger = messenger
        self._actions = actions

    def register(self) -> None:
        self._app.add_handler(CommandHandler("start", self._start))
        self._app.add_handler(CommandHandler("registrar", self._register))
        self._app.add_handler(CommandHandler("login", self._login))
        self._app.add_handler(CommandHandler("ver", self._show_last))
        self._app.add_handler(CommandHandler("parar", self._stop))
        self._app.add_handler(CommandHandler("logout", self._logout))
        self._app.add_handler(MessageHandler(filters.CONTACT, self._contact))
        self._app.add_handler(
            CallbackQueryHandler(self._consent, pattern=r"^consent:")
        )
        self._app.add_handler(MessageHandler(filters.LOCATION, self._location))

    async def _start(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        await self._messenger.send_text(self._chat_id(update), HELP_TEXT)
        
    async def _register(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        await self._actions.register_user(
            self._user_id(update), self._chat_id(update)
        )
        
        

    async def _login(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        step = await self._actions.resolve_login(
            self._user_id(update), self._chat_id(update)
        )
        self._set_step(context, step)

    async def _contact(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        contact = update.message.contact
        user_id = self._user_id(update)
        chat_id = self._chat_id(update)

        if context.user_data.get("paso") != LoginStep.PHONE.value:
            await self._messenger.send_text(
                chat_id, "Usa /login para iniciar sesión."
            )
            return

        if contact.user_id != user_id:
            await self._messenger.send_text(
                chat_id, "Comparte tu propio contacto, no el de otra persona."
            )
            return

        step = await self._actions.save_phone(
            user_id, chat_id, contact.phone_number
        )
        self._set_step(context, step)

    async def _consent(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        query = update.callback_query
        await query.answer()
        step = await self._actions.save_consent(
            self._user_id(update),
            self._chat_id(update),
            query.data == "consent:si",
        )
        self._set_step(context, step)

    async def _location(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        message = update.effective_message
        location = message.location
        live_period = location.live_period
        ubication = Ubication(
            latitude=location.latitude,
            longitude=location.longitude,
            timestamp=message.edit_date or message.date,
            # Telegram solo manda ``live_period`` mientras la ubicación en vivo
            # sigue activa; se cuenta desde el envío del mensaje original.
            live=live_period is not None,
            live_until=(
                live_until_from(message.date, live_period)
                if live_period is not None
                else None
            ),
        )
        await self._actions.share_ubication(
            self._user_id(update),
            self._chat_id(update),
            ubication,
            # Cada actualización en vivo llega como edición del mensaje original.
            is_update=update.edited_message is not None,
        )

    async def _show_last(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        await self._actions.show_last(
            self._user_id(update), self._chat_id(update)
        )

    async def _stop(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        await self._actions.stop_following(
            self._user_id(update), self._chat_id(update)
        )
        context.user_data.pop("paso", None)

    async def _logout(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        await self._actions.logout(
            self._user_id(update), self._chat_id(update)
        )
        context.user_data.pop("paso", None)

    @staticmethod
    def _user_id(update: Update) -> int:
        return update.effective_user.id

    @staticmethod
    def _chat_id(update: Update) -> int:
        return update.effective_chat.id

    @staticmethod
    def _set_step(context: ContextTypes.DEFAULT_TYPE, step: LoginStep) -> None:
        if step is LoginStep.READY:
            context.user_data.pop("paso", None)
        else:
            context.user_data["paso"] = step.value
