import logging
from datetime import UTC, datetime

from bot.application.ports.ports import (
    UbicationPublisherPort,
    UbicationRepository,
    UserRepository,
)
from bot.application.ports.telegram import BotActionsPort, BotMessengerPort, LoginStep
from bot.application.use_cases.follow_user import FollowUserUseCase
from bot.application.use_cases.live_status_tracker import LiveStatusTracker
from bot.domain.ubication import Ubication

logger = logging.getLogger(__name__)

CONSENT_TEXT = (
    "Paso 2/2: ¿aceptas el tratamiento de tus datos personales "
    "conforme a la Ley 1581 de 2012?"
)


class BotActionsService(BotActionsPort):
    def __init__(
        self,
        users: UserRepository,
        ubications: UbicationRepository,
        follow: FollowUserUseCase,
        publisher: UbicationPublisherPort,
        messenger: BotMessengerPort,
        live_status: LiveStatusTracker,
    ) -> None:
        self._users = users
        self._ubications = ubications
        self._follow = follow
        self._publisher = publisher
        self._messenger = messenger
        self._live_status = live_status

    async def register_user(self, telegram_id: int, chat_id: int) -> None:
        if await self._users.get_by_telegram(telegram_id) is not None:
            await self._messenger.send_text(
                chat_id, "Ya estás registrado. Continúa con /login."
            )
            return
        await self._users.create(telegram_id)
        await self._messenger.send_text(
            chat_id, "Usuario registrado. Ahora usa /login para iniciar sesión."
        )

    async def resolve_login(self, telegram_id: int, chat_id: int) -> LoginStep:
        user = await self._users.get_by_telegram(telegram_id)
        if user is None:
            await self._messenger.send_text(
                chat_id, "Primero regístrate con /registrar."
            )
            return LoginStep.READY

        if not user.telefono:
            await self._messenger.ask_phone(
                chat_id,
                "Paso 1/2: comparte tu teléfono con el botón de abajo.",
            )
            return LoginStep.PHONE

        if not user.consentimiento:
            await self._messenger.ask_consent(chat_id, CONSENT_TEXT)
            return LoginStep.CONSENT

        if await self._subscribe(telegram_id):
            await self._messenger.send_text(
                chat_id,
                "Sesión iniciada. Ya puedes compartir tu ubicación en tiempo real.",
            )
        else:
            await self._messenger.send_text(
                chat_id,
                "No pude conectar con STOMP. Revisa que ActiveMQ esté arriba "
                "e intenta /login de nuevo.",
            )
        return LoginStep.READY

    async def save_phone(
        self, telegram_id: int, chat_id: int, phone: str
    ) -> LoginStep:
        user = await self._users.get_by_telegram(telegram_id)
        if user is None:
            await self._messenger.send_text(
                chat_id, "Primero regístrate con /registrar."
            )
            return LoginStep.READY

        if not await self._users.save_phone(telegram_id, phone):
            await self._messenger.send_text(
                chat_id, "No pude guardar tu teléfono (¿ya está en uso?)."
            )
            return LoginStep.PHONE

        await self._messenger.remove_keyboard(chat_id, "Teléfono guardado.")
        await self._messenger.ask_consent(chat_id, CONSENT_TEXT)
        return LoginStep.CONSENT

    async def save_consent(
        self, telegram_id: int, chat_id: int, accepted: bool
    ) -> LoginStep:
        user = await self._users.get_by_telegram(telegram_id)
        if user is None:
            await self._messenger.send_text(
                chat_id, "Primero regístrate con /registrar."
            )
            return LoginStep.READY

        if not await self._users.save_consent(telegram_id, accepted):
            await self._messenger.send_text(
                chat_id, "No pude guardar tu consentimiento."
            )
            return LoginStep.READY

        if not accepted:
            await self._messenger.send_text(
                chat_id,
                "Sin consentimiento no puedo iniciar la sesión. "
                "Puedes intentarlo de nuevo con /login.",
            )
            return LoginStep.READY

        if await self._subscribe(telegram_id):
            await self._messenger.send_text(
                chat_id,
                "Sesión iniciada. Ya puedes compartir tu ubicación en tiempo real.",
            )
        else:
            await self._messenger.send_text(
                chat_id,
                "Datos guardados, pero no pude conectar con STOMP. "
                "Intenta /login de nuevo.",
            )
        return LoginStep.READY

    async def share_ubication(
        self,
        telegram_id: int,
        chat_id: int,
        ubication: Ubication,
        is_update: bool,
    ) -> None:
        if is_update:
            await self._handle_live_update(telegram_id, ubication)
            return

        if await self._users.get_by_telegram(telegram_id) is None:
            await self._messenger.send_text(
                chat_id, "Primero regístrate con /registrar."
            )
            return

        if not ubication.live:
            await self._messenger.send_text(
                chat_id, "Ubicación puntual recibida (no en tiempo real)."
            )
            return

        if not await self._follow.is_following(telegram_id):
            await self._messenger.send_text(
                chat_id,
                "Inicia sesión con /login antes de compartir ubicación en vivo.",
            )
            return

        try:
            await self._publisher.publish(telegram_id, ubication)
        except Exception:
            logger.exception("No se pudo publicar la ubicación de %s", telegram_id)
            await self._messenger.send_text(
                chat_id, "No pude publicar la ubicación en STOMP."
            )
            return

        await self._messenger.send_text(
            chat_id, f"Ubicación en vivo iniciada ({self._duration_text(ubication)})."
        )

    async def _handle_live_update(self, telegram_id: int, ubication: Ubication) -> None:
        """Ediciones del mensaje en vivo: llegan cada pocos segundos, así que
        no se le responde nada al usuario salvo cuando la ubicación termina."""
        if not await self._follow.is_following(telegram_id):
            return

        try:
            if ubication.live:
                await self._publisher.publish(telegram_id, ubication)
                return
            # Edición sin ``live_period``: el usuario dejó de compartir.
            await self._end_live(telegram_id, ubication.timestamp)
        except Exception:
            logger.exception("No se pudo publicar la actualización de %s", telegram_id)

    async def _end_live(self, telegram_id: int, ended_at: datetime) -> None:
        # Se guarda aquí también por si nadie más está suscrito al topic y el
        # evento de STOMP no vuelve a este proceso.
        await self._ubications.end_live(telegram_id)
        # Igual que arriba: con /parar la suscripción se cancela enseguida y el
        # evento podría no volver; el tracker descarta el aviso duplicado.
        await self._live_status.on_live_ended(telegram_id, ended_at)
        await self._publisher.publish_live_ended(telegram_id, ended_at)

    @staticmethod
    def _duration_text(ubication: Ubication) -> str:
        if ubication.live_until is None:
            return "sin límite de tiempo"
        minutes = round((ubication.live_until - ubication.timestamp).total_seconds() / 60)
        return f"{minutes} min"

    async def show_last(self, telegram_id: int, chat_id: int) -> None:
        ubication = await self._ubications.get_last(telegram_id)
        if ubication is None:
            await self._messenger.send_text(
                chat_id, "Aún no has compartido tu ubicación."
            )
            return
        await self._messenger.send_location(
            chat_id, ubication.latitude, ubication.longitude
        )

    async def stop_following(self, telegram_id: int, chat_id: int) -> None:
        await self._stop_live(telegram_id)
        await self._unsubscribe(telegram_id)
        await self._messenger.send_text(
            chat_id,
            "Dejé de seguir tu ubicación. Para cortar la ubicación en vivo, "
            "pulsa «Detener compartir» en el mensaje de ubicación del chat.",
        )

    async def logout(self, telegram_id: int, chat_id: int) -> None:
        await self._stop_live(telegram_id)
        await self._unsubscribe(telegram_id)
        await self._messenger.send_text(
            chat_id,
            "Sesión STOMP cerrada. Tus datos personales siguen guardados.",
        )

    async def _stop_live(self, telegram_id: int) -> None:
        """Al cortar el seguimiento, el frontend debe dejar de mostrarlo en vivo."""
        if not await self._follow.is_following(telegram_id):
            return
        try:
            await self._end_live(telegram_id, datetime.now(UTC))
        except Exception:
            logger.exception("No se pudo avisar el fin en vivo de %s", telegram_id)

    async def _subscribe(self, telegram_id: int) -> bool:
        if await self._follow.is_following(telegram_id):
            return True
        try:
            await self._follow.follow_user(telegram_id)
            return True
        except Exception:
            return False

    async def _unsubscribe(self, telegram_id: int) -> None:
        if not await self._follow.is_following(telegram_id):
            return
        try:
            await self._follow.unfollow_user(telegram_id)
        except Exception:
            return
