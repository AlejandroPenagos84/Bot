"""Sincroniza el admin único con la configuración (.env) al arrancar."""

from dataclasses import replace

from auth.application.ports.refresh_store import RefreshTokenStore
from auth.application.ports.user_repository import UserRepository
from auth.domain.user import User, UserRole, UserStatus


class EnsureAdmin:
    """Garantiza que exista exactamente un admin activo con los datos dados.

    - Si no hay admin, lo crea.
    - Si ya hay uno (mismo correo, o el admin anterior si cambió el correo),
      le actualiza correo, username y hash. Si el hash cambió, revoca sus
      sesiones abiertas.
    - Cualquier otro admin que quede en la base se deshabilita.
    """

    def __init__(self, users: UserRepository, refresh_store: RefreshTokenStore) -> None:
        self._users = users
        self._refresh_store = refresh_store

    def execute(self, email: str, username: str, password_hash: str) -> User:
        admins = self._users.list_by_role(UserRole.ADMIN)
        current = self._users.get_by_email(email) or (admins[0] if admins else None)

        if current is None:
            admin = User(
                id=User.new_id(),
                username=username,
                email=email,
                hashed_password=password_hash,
                status=UserStatus.ACTIVE,
                role=UserRole.ADMIN,
            )
            self._users.save(admin)
        else:
            admin = replace(
                current,
                username=username,
                email=email,
                hashed_password=password_hash,
                status=UserStatus.ACTIVE,
                role=UserRole.ADMIN,
            )
            if admin != current:
                self._users.update(admin)
            if current.hashed_password != password_hash:
                self._refresh_store.revoke_user(admin.id)

        for other in admins:
            if other.id != admin.id and other.status is not UserStatus.DISABLED:
                self._users.update(replace(other, status=UserStatus.DISABLED))
                self._refresh_store.revoke_user(other.id)

        return admin
