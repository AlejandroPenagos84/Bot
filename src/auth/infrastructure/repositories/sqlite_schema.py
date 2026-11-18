"""Esquema SQLite de auth y apertura de la conexión con los PRAGMA recomendados."""

import sqlite3

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id              TEXT PRIMARY KEY,
    username        TEXT NOT NULL UNIQUE,
    email           TEXT NOT NULL UNIQUE,
    hashed_password TEXT NOT NULL,
    status          TEXT NOT NULL CHECK (status IN ('pending', 'active', 'disabled')),
    role            TEXT NOT NULL DEFAULT 'user' CHECK (role IN ('admin', 'user')),
    created_at      TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS refresh_tokens (
    jti         TEXT PRIMARY KEY,
    user_id     TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    family_id   TEXT NOT NULL,
    expires_at  TEXT NOT NULL,
    revoked_at  TEXT,
    replaced_by TEXT
);

CREATE INDEX IF NOT EXISTS ix_refresh_tokens_family ON refresh_tokens (family_id);
"""


def connect(path: str) -> sqlite3.Connection:
    """Abre la base, activa WAL, espera ante bloqueos y crea las tablas."""
    conn = sqlite3.connect(path, check_same_thread=False)
    conn.execute('PRAGMA journal_mode=WAL')
    conn.execute('PRAGMA busy_timeout=5000')
    conn.execute('PRAGMA foreign_keys=ON')
    conn.executescript(SCHEMA)
    _migrate(conn)
    return conn


def _migrate(conn: sqlite3.Connection) -> None:
    """Agrega columnas nuevas a bases creadas con un esquema anterior."""
    columns = {row[1] for row in conn.execute('PRAGMA table_info(users)')}
    if 'role' not in columns:
        conn.execute(
            "ALTER TABLE users ADD COLUMN role TEXT NOT NULL DEFAULT 'user' "
            "CHECK (role IN ('admin', 'user'))"
        )
        conn.commit()
