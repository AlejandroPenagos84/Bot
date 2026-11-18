"""Endpoints de sesión y perfil.

No hay registro público: el único usuario es el admin definido en el .env
(ver ``EnsureAdmin``).
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Response, status

from auth.application.use_cases.login import LoginUseCase
from auth.application.use_cases.logout import Logout
from auth.application.use_cases.refresh_session import RefreshSession
from auth.domain.user import User
from auth.http.container import AuthContainer
from auth.http.deps import (
    get_container,
    get_current_user,
    get_login,
    get_logout,
    get_optional_refresh_token,
    get_refresh_session,
    get_refresh_token,
)
from auth.http.schemas import (
    LoginRequest,
    TokenResponse,
    UserResponse,
)

router = APIRouter(prefix='/auth', tags=['auth'])


def _set_refresh_cookie(response: Response, token: str, container: AuthContainer) -> None:
    response.set_cookie(
        key=container.cookie_name,
        value=token,
        max_age=container.refresh_ttl_minutes * 60,
        httponly=True,
        secure=container.cookie_secure,
        samesite=container.cookie_samesite,
        path=container.cookie_path,
    )


def _clear_refresh_cookie(response: Response, container: AuthContainer) -> None:
    response.delete_cookie(
        key=container.cookie_name,
        path=container.cookie_path,
        secure=container.cookie_secure,
        samesite=container.cookie_samesite,
        httponly=True,
    )


@router.post('/login', response_model=TokenResponse)
def login(
    payload: LoginRequest,
    response: Response,
    use_case: Annotated[LoginUseCase, Depends(get_login)],
    container: Annotated[AuthContainer, Depends(get_container)],
) -> TokenResponse:
    pair = use_case.execute(payload.email, payload.password)
    _set_refresh_cookie(response, pair.refresh_token, container)
    return TokenResponse(
        access_token=pair.access_token,
        expires_in=container.access_ttl_minutes * 60,
    )


@router.post('/refresh', response_model=TokenResponse)
def refresh(
    response: Response,
    refresh_token: Annotated[str, Depends(get_refresh_token)],
    use_case: Annotated[RefreshSession, Depends(get_refresh_session)],
    container: Annotated[AuthContainer, Depends(get_container)],
) -> TokenResponse:
    pair = use_case.execute(refresh_token)
    _set_refresh_cookie(response, pair.refresh_token, container)
    return TokenResponse(
        access_token=pair.access_token,
        expires_in=container.access_ttl_minutes * 60,
    )


@router.post('/logout', status_code=status.HTTP_204_NO_CONTENT)
def logout(
    response: Response,
    refresh_token: Annotated[str | None, Depends(get_optional_refresh_token)],
    use_case: Annotated[Logout, Depends(get_logout)],
    container: Annotated[AuthContainer, Depends(get_container)],
) -> None:
    if refresh_token is not None:
        use_case.execute(refresh_token)
    _clear_refresh_cookie(response, container)


@router.get('/me', response_model=UserResponse)
def me(user: Annotated[User, Depends(get_current_user)]) -> UserResponse:
    return UserResponse.from_user(user)
