"""Endpoints REST del panel de administración (solo admin).

  GET /api/v1/usuarios                          lista con estado en vivo
  GET /api/v1/usuarios/{telegram_id}/ubicacion  última ubicación guardada
"""

from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, status
from pydantic import BaseModel

from auth.api import AuthApi, Identity, NotAuthenticated
from bot.application.use_cases.monitor_users import MonitorUsersUseCase


class UserSummaryResponse(BaseModel):
    telegram_id: int
    telefono: str | None
    en_vivo: bool
    ultima_fecha: datetime | None


class UbicationResponse(BaseModel):
    telegram_id: int
    lat: float
    lon: float
    fecha: datetime
    en_vivo: bool
    en_vivo_hasta: datetime | None


def create_http_router(monitor: MonitorUsersUseCase, auth: AuthApi) -> APIRouter:
    # ``def`` (no async): FastAPI la corre en un hilo, y auth consulta SQLite.
    def require_admin(
        authorization: Annotated[str | None, Header()] = None,
    ) -> Identity:
        scheme, _, token = (authorization or "").partition(" ")
        if scheme.lower() != "bearer" or not token:
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Falta el token")
        try:
            identity = auth.authenticate(token)
        except NotAuthenticated:
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Token inválido") from None
        if not identity.is_admin:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Solo administradores")
        return identity

    router = APIRouter(
        prefix="/api/v1/usuarios",
        tags=["usuarios"],
        dependencies=[Depends(require_admin)],
    )

    @router.get("", response_model=list[UserSummaryResponse])
    async def list_users() -> list[UserSummaryResponse]:
        return [
            UserSummaryResponse(
                telegram_id=u.telegram_id,
                telefono=u.telefono,
                en_vivo=u.live,
                ultima_fecha=u.last_seen,
            )
            for u in await monitor.list_users()
        ]

    @router.get("/{telegram_id}/ubicacion", response_model=UbicationResponse)
    async def last_ubication(telegram_id: int) -> UbicationResponse:
        ubication = await monitor.last_ubication(telegram_id)
        if ubication is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Sin ubicación registrada")
        live = ubication.is_live_at(datetime.now(UTC))
        return UbicationResponse(
            telegram_id=telegram_id,
            lat=ubication.latitude,
            lon=ubication.longitude,
            fecha=ubication.timestamp,
            en_vivo=live,
            en_vivo_hasta=ubication.live_until if live else None,
        )

    return router
