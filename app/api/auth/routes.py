from collections.abc import Awaitable, Callable
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.routing import APIRoute
from pydantic import BaseModel, Field, SecretStr

from app.core.keycloak.client import (
    KeycloakClient,
    KeycloakError,
    RegistrationRejectedError,
    TokenRequestRejectedError,
    UserAlreadyExistsError,
)
from app.core.keycloak.schemas import TokenResponse


class AuthRoute(APIRoute):
    """Формирует ошибки валидации без вывода содержимого запроса."""

    def get_route_handler(self) -> Callable[[Request], Awaitable[Response]]:
        handler = super().get_route_handler()

        async def handle(request: Request) -> Response:
            try:
                return await handler(request)
            except RequestValidationError:
                return JSONResponse(
                    {"detail": "Проверьте обязательные поля запроса."},
                    status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                )

        return handle


router = APIRouter(prefix="/auth", tags=["auth"], route_class=AuthRoute)
TOKEN_HEADERS = {"Cache-Control": "no-store", "Pragma": "no-cache"}


class LoginRequest(BaseModel):
    """Данные для входа по имени пользователя и паролю."""

    username: str = Field(min_length=1)
    password: SecretStr = Field(min_length=1)


class RegistrationRequest(LoginRequest):
    """Данные для создания учётной записи пользователя."""

    email: str = Field(min_length=1)
    first_name: str | None = Field(default=None, min_length=1)
    last_name: str | None = Field(default=None, min_length=1)


class RefreshRequest(BaseModel):
    """Токен обновления для получения новой пары токенов."""

    refresh_token: SecretStr = Field(min_length=1)


class AuthTokens(BaseModel):
    """Токены приложения и срок действия токена доступа в секундах."""

    access_token: str
    refresh_token: str | None = None
    token_type: str | None = None
    expires_in: int | None = None


async def get_keycloak(request: Request) -> KeycloakClient:
    """Возвращает клиент аутентификации для текущего приложения."""
    return request.app.state.keycloak


Keycloak = Annotated[KeycloakClient, Depends(get_keycloak)]


@router.post("/register", status_code=status.HTTP_201_CREATED, response_class=Response)
async def register(data: RegistrationRequest, keycloak: Keycloak) -> Response:
    """Регистрирует пользователя."""
    try:
        await keycloak.register_user(
            data.username,
            data.email,
            data.password,
            first_name=data.first_name,
            last_name=data.last_name,
        )
    except UserAlreadyExistsError as exc:
        raise HTTPException(
            status.HTTP_409_CONFLICT, "Пользователь уже существует."
        ) from exc
    except RegistrationRejectedError as exc:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, "Данные пользователя отклонены."
        ) from exc
    except KeycloakError as exc:
        raise HTTPException(
            status.HTTP_502_BAD_GATEWAY, "Ошибка сервиса аутентификации."
        ) from exc
    return Response(status_code=status.HTTP_201_CREATED)


async def issue_tokens(
    request: Awaitable[TokenResponse], response: Response
) -> AuthTokens:
    """Преобразует ответ провайдера в публичный формат выдачи токенов."""
    response.headers.update(TOKEN_HEADERS)
    try:
        tokens = await request
    except TokenRequestRejectedError as exc:
        raise HTTPException(
            exc.status_code, "Запрос на выдачу токенов отклонён.", headers=TOKEN_HEADERS
        ) from exc
    except KeycloakError as exc:
        raise HTTPException(
            status.HTTP_502_BAD_GATEWAY,
            "Ошибка сервиса аутентификации.",
            headers=TOKEN_HEADERS,
        ) from exc
    return AuthTokens(
        access_token=tokens.access_token,
        refresh_token=tokens.refresh_token,
        token_type=tokens.token_type,
        expires_in=tokens.expires_in,
    )


@router.post("/login", response_model_exclude_none=True)
async def login(
    data: LoginRequest, keycloak: Keycloak, response: Response
) -> AuthTokens:
    """Получает токены по логину и паролю."""
    return await issue_tokens(
        keycloak.authenticate(data.username, data.password), response
    )


@router.post("/refresh", response_model_exclude_none=True)
async def refresh(
    data: RefreshRequest, keycloak: Keycloak, response: Response
) -> AuthTokens:
    """Обновляет токены."""
    return await issue_tokens(keycloak.refresh_tokens(data.refresh_token), response)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT, response_class=Response)
async def logout(data: RefreshRequest, keycloak: Keycloak) -> Response:
    """Завершает сессию пользователя по токену обновления."""
    try:
        await keycloak.logout(data.refresh_token)
    except TokenRequestRejectedError as exc:
        raise HTTPException(
            exc.status_code, "Запрос на завершение сессии отклонён."
        ) from exc
    except KeycloakError as exc:
        raise HTTPException(
            status.HTTP_502_BAD_GATEWAY, "Ошибка сервиса аутентификации."
        ) from exc
    return Response(status_code=status.HTTP_204_NO_CONTENT)
