"""Reparte por WebSocket (/ws/estado) los cambios de estado en vivo.

Mensaje que recibe el frontend:

  {"tipo": "estado", "telegram_id", "en_vivo": bool,
   "en_vivo_hasta": iso | null, "fecha": iso}
"""

from fastapi import WebSocket

from bot.application.ports.ports import LiveStatusNotifier
from bot.domain.live_status import LiveStatus


class StatusConnectionManager(LiveStatusNotifier):
    def __init__(self) -> None:
        self._connections: set[WebSocket] = set()

    def connect(self, websocket: WebSocket) -> None:
        self._connections.add(websocket)

    def disconnect(self, websocket: WebSocket) -> None:
        self._connections.discard(websocket)

    async def notify_status(self, status: LiveStatus) -> None:
        payload = {
            "tipo": "estado",
            "telegram_id": status.telegram_id,
            "en_vivo": status.live,
            "en_vivo_hasta": status.live_until.isoformat() if status.live_until else None,
            "fecha": status.changed_at.isoformat(),
        }
        for ws in list(self._connections):
            try:
                await ws.send_json(payload)
            except Exception:
                self.disconnect(ws)
