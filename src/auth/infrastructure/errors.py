"""Errores de infraestructura y traducción de fallos de SQLite."""

import sqlite3
from contextlib import contextmanager

from auth.errors import AuthError


class InfrastructureError(AuthError):
    """Error producido por un adaptador de infraestructura."""


class PersistenceError(InfrastructureError):
    """Error genérico de persistencia."""


class DuplicateRecord(PersistenceError):
    """Ya existe un registro con los mismos campos únicos."""


class RecordNotFound(PersistenceError):
    """El registro que se intentó modificar o borrar no existe."""


class DatabaseUnavailable(PersistenceError):
    """La base de datos no está disponible."""


@contextmanager
def sqlite_errors():
    try:
        yield
    except AuthError:
        raise
    except sqlite3.IntegrityError as exc:
        raise DuplicateRecord('A record with the same unique fields already exists') from exc
    except (sqlite3.OperationalError, sqlite3.ProgrammingError) as exc:
        raise DatabaseUnavailable('Database is unavailable') from exc
    except sqlite3.Error as exc:
        raise PersistenceError('Database operation failed') from exc

