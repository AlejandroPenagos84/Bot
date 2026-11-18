from dataclasses import dataclass


@dataclass(frozen=True)
class User:
    id: int
    telegram_id: int | None
    telefono: str | None
    consentimiento: bool
