"""Construcción e inyección de adaptadores y casos de uso de auth."""

from __future__ import annotations

import os
import sqlite3
from dataclasses import dataclass

from auth.application.ports.password_hasher import PasswordHasher
from auth.application.ports.refresh_store import RefreshTokenStore
from auth.application.ports.token_service import TokenService
from auth.application.ports.user_repository import UserRepository
from auth.application.use_cases.authenticate import Authenticate
from auth.application.use_cases.ensure_admin import EnsureAdmin
from auth.application.use_cases.login import LoginUseCase
from auth.application.use_cases.logout import Logout
from auth.application.use_cases.refresh_session import RefreshSession
from auth.infrastructure.PasswordHasherArgon2 import PasswordHasherArgon2
from auth.infrastructure.PyJwtTokenService import PyJwtTokenService
from auth.infrastructure.repositories.RefreshTokenStoreSQLite import RefreshTokenStoreSQLite
from auth.infrastructure.repositories.sqlite_schema import connect
from auth.infrastructure.repositories.UserRepositorySqlite import UserRepositorySQLite


def _env_int(name: str, default: int) -> int:
    value = os.getenv(name)
    return int(value) if value is not None else default


def _env_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {'1', 'true', 'yes', 'on'}


@dataclass(frozen=True)
class AdminConfig:
    email: str
    username: str
    password_hash: str


def _admin_config() -> AdminConfig:
    missing = [
        name
        for name in ('ADMIN_EMAIL', 'ADMIN_USERNAME', 'ADMIN_PASSWORD_HASH')
        if not os.getenv(name, '').strip()
    ]
    if missing:
        raise ValueError(
            f'Faltan variables del admin: {", ".join(missing)}. '
            'Genera el hash con: uv run python -m auth.hash_password'
        )
    password_hash = os.environ['ADMIN_PASSWORD_HASH'].strip()
    if not password_hash.startswith('$argon2'):
        # Evita pegar la contraseña en texto plano por error.
        raise ValueError(
            'ADMIN_PASSWORD_HASH debe ser un hash Argon2 ($argon2id$...), no la contraseña. '
            'Genéralo con: uv run python -m auth.hash_password'
        )
    return AdminConfig(
        email=os.environ['ADMIN_EMAIL'].strip().lower(),
        username=os.environ['ADMIN_USERNAME'].strip(),
        password_hash=password_hash,
    )


@dataclass
class AuthContainer:
    db_connection: sqlite3.Connection
    users: UserRepository
    hasher: PasswordHasher
    tokens: TokenService
    refresh_store: RefreshTokenStore
    login: LoginUseCase
    refresh: RefreshSession
    logout: Logout
    authenticate: Authenticate
    access_ttl_minutes: int
    refresh_ttl_minutes: int
    cookie_name: str
    cookie_secure: bool
    cookie_samesite: str
    cookie_path: str

    def close(self) -> None:
        self.db_connection.close()


def build_container(
    *,
    hasher: PasswordHasher | None = None,
) -> AuthContainer:
    secret = os.getenv('AUTH_JWT_SECRET')
    if not secret:
        raise ValueError('AUTH_JWT_SECRET is required')
    admin = _admin_config()  # antes de abrir la BD: falla rápido si falta config

    access_ttl_minutes = _env_int('AUTH_ACCESS_TTL_MINUTES', 15)
    refresh_ttl_minutes = _env_int('AUTH_REFRESH_TTL_MINUTES', 10080)

    connection = connect(os.getenv('AUTH_DB_PATH', '/data/auth.db'))
    users = UserRepositorySQLite(connection)
    hasher = hasher or PasswordHasherArgon2()
    tokens = PyJwtTokenService(secret, access_ttl_minutes, refresh_ttl_minutes)
    refresh_store = RefreshTokenStoreSQLite(connection)

    EnsureAdmin(users, refresh_store).execute(admin.email, admin.username, admin.password_hash)

    return AuthContainer(
        db_connection=connection,
        users=users,
        hasher=hasher,
        tokens=tokens,
        refresh_store=refresh_store,
        login=LoginUseCase(users, hasher, tokens, refresh_store),
        refresh=RefreshSession(tokens, users, refresh_store),
        logout=Logout(tokens, refresh_store),
        authenticate=Authenticate(tokens, users),
        access_ttl_minutes=access_ttl_minutes,
        refresh_ttl_minutes=refresh_ttl_minutes,
        cookie_name=os.getenv('AUTH_COOKIE_NAME', 'auth_refresh'),
        cookie_secure=_env_bool('AUTH_COOKIE_SECURE', True),
        cookie_samesite=os.getenv('AUTH_COOKIE_SAMESITE', 'lax'),
        cookie_path=os.getenv('AUTH_COOKIE_PATH', '/api/v1/auth'),
    )
