"""Reparte por WebSocket los eventos de ubicación a los admins conectados.

Mensajes que recibe el frontend:

  {"tipo": "ubicacion", "telegram_id", "lat", "lon", "fecha",
   "en_vivo": bool, "en_vivo_hasta": iso | null}
      ``en_vivo_hasta`` es null cuando no está en vivo o cuando se comparte
      sin límite de tiempo.

  {"tipo": "fin_en_vivo", "telegram_id", "fecha"}
      El usuario dejó de compartir su ubicación en tiempo real.
"""

from datetime import UTC, datetime

from fastapi import WebSocket

from bot.application.ports.ports import UbicationNotifier
from bot.domain.ubication import Ubication


class ConnectionManager(UbicationNotifier):
    def __init__(self):
        self.active_connections: dict[int, set[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, user_id: int):
        self.active_connections.setdefault(user_id, set()).add(websocket)

    def disconnect(self, user_id: int, websocket: WebSocket):
        client_ws = self.active_connections.get(user_id)
        if not client_ws:
            return
        client_ws.discard(websocket)

        if not client_ws:
            self.active_connections.pop(user_id, None)

    async def send_personal_message(self, ws: WebSocket, user_id: int, u: Ubication):
        await ws.send_json(self._ubication_payload(user_id, u))

    async def notify(self, user_id: int, ubication: Ubication) -> None:
        await self._broadcast(user_id, self._ubication_payload(user_id, ubication))

    async def notify_live_ended(self, user_id: int, ended_at: datetime) -> None:
        await self._broadcast(
            user_id,
            {
                "tipo": "fin_en_vivo",
                "telegram_id": user_id,
                "fecha": ended_at.isoformat(),
            },
        )

    async def _broadcast(self, user_id: int, payload: dict) -> None:
        for ws in list(self.active_connections.get(user_id, ())):
            try:
                await ws.send_json(payload)
            except Exception:
                self.disconnect(user_id, ws)

    @staticmethod
    def _ubication_payload(user_id: int, u: Ubication) -> dict:
        live = u.is_live_at(datetime.now(UTC))
        return {
            "tipo": "ubicacion",
            "telegram_id": user_id,
            "lat": u.latitude,
            "lon": u.longitude,
            "fecha": u.timestamp.isoformat(),
            "en_vivo": live,
            "en_vivo_hasta": u.live_until.isoformat() if live and u.live_until else None,
        }
