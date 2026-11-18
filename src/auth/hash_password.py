"""Genera el hash Argon2 para ADMIN_PASSWORD_HASH.

Uso: uv run python -m auth.hash_password
"""

import sys
from getpass import getpass

from auth.infrastructure.PasswordHasherArgon2 import PasswordHasherArgon2

MIN_LENGTH = 12


def main() -> int:
    password = getpass('Contraseña del admin: ')
    if len(password) < MIN_LENGTH:
        print(f'Debe tener al menos {MIN_LENGTH} caracteres.', file=sys.stderr)
        return 1
    if getpass('Repítela: ') != password:
        print('No coinciden.', file=sys.stderr)
        return 1

    hashed = PasswordHasherArgon2().hash(password)
    # Comillas simples: el hash tiene '$' y así python-dotenv no intenta expandirlo.
    print(f"\nPega esto en tu .env:\nADMIN_PASSWORD_HASH='{hashed}'")
    return 0


if __name__ == '__main__':
    sys.exit(main())
