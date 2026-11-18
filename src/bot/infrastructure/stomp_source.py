import asyncio
import json
import logging
import os
from datetime import datetime, timezone
import stomp
from stomp.exception import StompException

from bot.application.ports.ports import (
    OnLiveEnded,
    OnUbication,
    UbicationPublisherPort,
    UbicationSourcePort,
)
from bot.domain.ubication import Ubication

logger = logging.getLogger(__name__)

# Campo ``tipo`` de los mensajes en /topic/ubicaciones/<id>.
TIPO_UBICACION = "ubicacion"
TIPO_FIN_EN_VIVO = "fin_en_vivo"


class _StompListener(stomp.ConnectionListener):
    def __init__(self, source: "StompSource") -> None:
        self._source = source

    def on_message(self, frame) -> None:
        self._source._handle_message(frame)

    def on_error(self, frame) -> None:
        logger.error("Error from STOMP: %s", frame.body)

    def on_disconnected(self) -> None:
        self._source._handle_disconnected()


class StompSource(UbicationSourcePort, UbicationPublisherPort):
    def __init__(self) -> None:
        self._host = os.environ.get("STOMP_HOST", "localhost")
        self._port = int(os.environ.get("STOMP_PORT", "61613"))
        self._user = os.environ.get("STOMP_USER", "admin")
        self._password = os.environ.get("STOMP_PASS", "admin")
        self._conn = stomp.Connection([(self._host, self._port)])
        self._conn.set_listener("", _StompListener(self))
        self._loop: asyncio.AbstractEventLoop | None = None
        self._on_ubication: OnUbication | None = None
        self._on_live_ended: OnLiveEnded | None = None
        self._subscribed: set[int] = set()

    def start(
        self,
        loop: asyncio.AbstractEventLoop,
        on_ubication: OnUbication,
        on_live_ended: OnLiveEnded,
    ) -> None:
        self._loop = loop
        self._on_ubication = on_ubication
        self._on_live_ended = on_live_ended

    def _connect(self) -> bool:
        if self._conn.is_connected():
            return True
        try:
            self._conn.connect(self._user, self._password, wait=True)
            return True
        except StompException as exc:
            logger.error("No se pudo conectar a STOMP: %s", exc)
            return False

    def _subscribe(self, user_id: int) -> bool:
        if user_id in self._subscribed:
            return True
        if not self._connect():
            return False
        try:
            self._conn.subscribe(
                destination=f"/topic/ubicaciones/{user_id}",
                id=str(user_id),
                ack="auto",
            )
        except StompException as exc:
            logger.error("No se pudo suscribir a STOMP: %s", exc)
            return False
        self._subscribed.add(user_id)
        return True

    def _unsubscribe(self, user_id: int) -> None:
        if user_id in self._subscribed and self._conn.is_connected():
            try:
                self._conn.unsubscribe(str(user_id))
            except StompException as exc:
                logger.error("No se pudo desuscribir de STOMP: %s", exc)
        self._subscribed.discard(user_id)

    def _handle_disconnected(self) -> None:
        self._subscribed.clear()
        logger.warning("Conexión STOMP cerrada")

    def _handle_message(self, frame) -> None:
        if self._loop is None or self._on_ubication is None or self._on_live_ended is None:
            return
        try:
            data = json.loads(frame.body)
            user_id = int(data["telegram_id"])
            # Sin ``tipo``: mensajes del formato anterior, que siempre eran ubicaciones.
            tipo = data.get("tipo", TIPO_UBICACION)
            if tipo == TIPO_UBICACION:
                coro = self._on_ubication(user_id, self._parse_ubication(data))
            elif tipo == TIPO_FIN_EN_VIVO:
                coro = self._on_live_ended(user_id, self._parse_date(data.get("fecha")))
            else:
                logger.warning("Mensaje STOMP con tipo desconocido: %s", tipo)
                return
        except (TypeError, ValueError, KeyError, json.JSONDecodeError):
            return
        asyncio.run_coroutine_threadsafe(coro, self._loop)

    @staticmethod
    def _parse_date(value: str | None) -> datetime:
        return datetime.fromisoformat(value) if value else datetime.now(timezone.utc)

    @classmethod
    def _parse_ubication(cls, data: dict) -> Ubication:
        live_until = data.get("en_vivo_hasta")
        return Ubication(
            latitude=float(data["lat"]),
            longitude=float(data["lon"]),
            timestamp=cls._parse_date(data.get("fecha") or data.get("timestamp")),
            live=bool(data.get("en_vivo", False)),
            live_until=datetime.fromisoformat(live_until) if live_until else None,
        )

    async def suscribe(self, user_id: int) -> bool:
        return await asyncio.to_thread(self._subscribe, user_id)

    async def unsubscribe(self, user_id: int) -> bool:
        await asyncio.to_thread(self._unsubscribe, user_id)
        return True

    async def publish(self, user_id: int, ubication: Ubication) -> None:
        await self._send(
            user_id,
            {
                "tipo": TIPO_UBICACION,
                "telegram_id": user_id,
                "lat": ubication.latitude,
                "lon": ubication.longitude,
                "fecha": ubication.timestamp.isoformat(),
                "en_vivo": ubication.live,
                "en_vivo_hasta": (
                    ubication.live_until.isoformat() if ubication.live_until else None
                ),
            },
        )

    async def publish_live_ended(self, user_id: int, ended_at: datetime) -> None:
        await self._send(
            user_id,
            {
                "tipo": TIPO_FIN_EN_VIVO,
                "telegram_id": user_id,
                "fecha": ended_at.isoformat(),
            },
        )

    async def _send(self, user_id: int, payload: dict) -> None:
        if not await asyncio.to_thread(self._connect):
            raise StompException("No se pudo conectar a STOMP")
        body = json.dumps(payload)
        await asyncio.to_thread(
            self._conn.send,
            destination=f"/topic/ubicaciones/{user_id}",
            body=body,
            content_type="application/json",
        )
