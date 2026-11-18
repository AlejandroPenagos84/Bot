"""WebSockets del panel de administración.

/ws: el admin sigue en vivo la ubicación de UN usuario de Telegram.
/ws/estado: el admin recibe cuándo cualquier usuario empieza o deja de
estar en vivo (handshake solo con {"token": ...}). Mismos códigos de cierre.

Protocolo:
  1. El cliente conecta y, en menos de HANDSHAKE_TIMEOUT_S, envía
     {"token": "<access_token>", "telegram_id": <id>}.
  2. Si el token es de un admin activo, recibe la última ubicación conocida
     y luego cada ubicación nueva.
  3. Códigos de cierre:
       1008  no autorizado (token inválido, no admin, mensaje mal formado, timeout)
       1011  error interno (p. ej. STOMP caído)
       4401  el token venció: el cliente hace /refresh y reconecta
"""

import asyncio
import json
import logging
from collections.abc import Callable
from datetime import UTC, datetime

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from auth.api import AuthApi, Identity, NotAuthenticated
from bot.application.ports.ports import UbicationNotifier
from bot.application.use_cases.follow_user import FollowUserUseCase
from bot.infrastructure.status_connection_manager import StatusConnectionManager

logger = logging.getLogger(__name__)

HANDSHAKE_TIMEOUT_S = 10
CLOSE_UNAUTHORIZED = 1008
CLOSE_INTERNAL = 1011
CLOSE_TOKEN_EXPIRED = 4401


class CloseConnection(Exception):
    """Corta el flujo del endpoint y cierra el socket con ``code``."""

    def __init__(self, code: int) -> None:
        super().__init__(code)
        self.code = code


# --- 1. Handshake ----------------------------------------------------------


def parse_handshake(raw: str) -> tuple[str, int] | None:
    try:
        data = json.loads(raw)
        token, telegram_id = data["token"], int(data["telegram_id"])
    except (json.JSONDecodeError, TypeError, KeyError, ValueError):
        return None
    if not isinstance(token, str) or not token:
        return None
    return token, telegram_id


def parse_token_handshake(raw: str) -> str | None:
    try:
        token = json.loads(raw)["token"]
    except (json.JSONDecodeError, TypeError, KeyError):
        return None
    return token if isinstance(token, str) and token else None


async def receive_handshake[T](
    websocket: WebSocket, parse: Callable[[str], T | None] = parse_handshake
) -> T:
    """Espera el primer mensaje con límite de tiempo y lo valida."""
    try:
        raw = await asyncio.wait_for(websocket.receive_text(), HANDSHAKE_TIMEOUT_S)
    except TimeoutError:
        raise CloseConnection(CLOSE_UNAUTHORIZED) from None

    parsed = parse(raw)
    if parsed is None:
        raise CloseConnection(CLOSE_UNAUTHORIZED)
    return parsed


# --- 2. Autorización -------------------------------------------------------


async def authenticate_admin(auth: AuthApi, token: str) -> Identity:
    """Mismo cierre para todo rechazo: no se le dice al cliente por qué."""
    try:
        # to_thread: auth consulta SQLite y no debe bloquear el event loop.
        identity = await asyncio.to_thread(auth.authenticate, token)
    except NotAuthenticated:
        raise CloseConnection(CLOSE_UNAUTHORIZED) from None
    if not identity.is_admin:
        raise CloseConnection(CLOSE_UNAUTHORIZED)
    return identity



# --- 3. Suscripciones de esta conexión ------------------------------------


class ConnectionSubscriptions:
    """Usuarios que sigue UN socket.

    ``FollowUserUseCase`` lleva la cuenta global (cuántos sockets siguen a
    cada usuario); esta clase solo recuerda qué limpiar cuando este socket
    se cierre.
    """

    def __init__(
        self,
        websocket: WebSocket,
        follow_user: FollowUserUseCase,
        manager: UbicationNotifier,
    ) -> None:
        self._websocket = websocket
        self._follow_user = follow_user
        self._manager = manager
        self._followed: set[int] = set()

    async def follow(self, telegram_id: int) -> None:
        if telegram_id in self._followed:
            return  # ya lo sigue: no inflar el contador del caso de uso
        try:
            last = await self._follow_user.follow_user(telegram_id)
        except Exception:
            logger.exception("No se pudo seguir al usuario %s", telegram_id)
            raise CloseConnection(CLOSE_INTERNAL) from None  # sin detalles al cliente

        self._followed.add(telegram_id)
        await self._manager.connect(self._websocket, telegram_id)
        if last is not None:
            await self._manager.send_personal_message(
                self._websocket, telegram_id, last
            )

    async def close(self) -> None:
        """Deja de seguir a todos; nunca lanza, para no tapar el error original."""
        for telegram_id in self._followed:
            self._manager.disconnect(telegram_id, self._websocket)
            try:
                await self._follow_user.unfollow_user(telegram_id)
            except Exception:
                logger.exception("Error dejando de seguir a %s", telegram_id)
        self._followed.clear()


# --- 4. Vida de la conexión ------------------------------------------------


async def keep_alive_until(websocket: WebSocket, expires_at: datetime) -> None:
    """Mantiene el socket abierto hasta que venza el token."""
    while True:
        remaining = (expires_at - datetime.now(UTC)).total_seconds()
        if remaining <= 0:
            raise CloseConnection(CLOSE_TOKEN_EXPIRED)
        try:
            await asyncio.wait_for(websocket.receive_text(), remaining)
        except TimeoutError:
            continue  # la siguiente vuelta cierra con 4401


# --- Endpoint --------------------------------------------------------------


def create_router(
    follow_user: FollowUserUseCase,
    manager: UbicationNotifier,
    status_manager: StatusConnectionManager,
    auth: AuthApi,
) -> APIRouter:
    router = APIRouter()

    @router.websocket("/ws/estado")
    async def status_endpoint(websocket: WebSocket) -> None:
        await websocket.accept()
        try:
            token = await receive_handshake(websocket, parse_token_handshake)
            identity = await authenticate_admin(auth, token)
            status_manager.connect(websocket)
            await keep_alive_until(websocket, identity.expires_at)
        except CloseConnection as exc:
            await websocket.close(code=exc.code)
        except WebSocketDisconnect:
            pass
        finally:
            status_manager.disconnect(websocket)

    @router.websocket("/ws")
    async def websocket_endpoint(websocket: WebSocket) -> None:
        await websocket.accept()
        subscriptions = ConnectionSubscriptions(websocket, follow_user, manager)

        try:
            token, telegram_id = await receive_handshake(websocket)
            identity = await authenticate_admin(auth, token)
            await subscriptions.follow(telegram_id)
            await keep_alive_until(websocket, identity.expires_at)
        except CloseConnection as exc:
            await websocket.close(code=exc.code)
        except WebSocketDisconnect:
            pass  # el cliente se fue
        finally:
            await subscriptions.close()

    return router
