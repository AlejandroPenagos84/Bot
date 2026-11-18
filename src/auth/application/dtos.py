"""DTOs de salida compartidos por los casos de uso de auth."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class TokenPair:
    access_token: str
    refresh_token: str
