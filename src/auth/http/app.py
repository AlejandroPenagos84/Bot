"""Fábrica de la aplicación FastAPI de autenticación."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from auth.http.container import AuthContainer, build_container
from auth.http.errors import register_exception_handlers
from auth.http.routers import auth, health


@asynccontextmanager
async def _lifespan(app: FastAPI) -> AsyncIterator[None]:
    try:
        yield
    finally:
        app.state.container.close()


def mount_auth(app: FastAPI, container: AuthContainer) -> None:
    """Monta auth dentro de una app existente (el monolito de main.py).

    Quien llama es dueño del ciclo de vida: debe ejecutar ``container.close()``
    al apagar.
    """
    app.state.container = container
    register_exception_handlers(app)
    app.include_router(health.router)
    app.include_router(auth.router, prefix='/api/v1')


def create_app(*, container: AuthContainer | None = None) -> FastAPI:
    """App de auth independiente (útil para pruebas)."""
    app = FastAPI(title='Auth API', version='1.0.0', lifespan=_lifespan)
    mount_auth(app, container or build_container())
    return app
