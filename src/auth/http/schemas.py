"""DTOs de entrada y salida expuestos por la API HTTP de auth."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, Field, field_validator

from auth.domain.user import User, UserRole, UserStatus

def _normalize_email(value: str) -> str:
    value = value.strip().lower()
    local, sep, domain = value.partition('@')
    if not sep or not local or '.' not in domain:
        raise ValueError('email must have a valid format')
    if domain.startswith('.') or domain.endswith('.'):
        raise ValueError('email must have a valid format')
    return value


class EmailRequest(BaseModel):
    email: Annotated[str, Field(min_length=3, max_length=254)]

    @field_validator('email')
    @classmethod
    def _validate_email(cls, value: str) -> str:
        return _normalize_email(value)


class LoginRequest(EmailRequest):
    password: Annotated[str, Field(min_length=1, max_length=128)]


class UserResponse(BaseModel):
    id: str
    username: str
    email: str
    status: UserStatus
    role: UserRole
    created_at: datetime

    @classmethod
    def from_user(cls, user: User) -> UserResponse:
        return cls(
            id=user.id,
            username=user.username,
            email=user.email,
            status=user.status,
            role=user.role,
            created_at=user.created_at,
        )


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = 'bearer'
    expires_in: int

