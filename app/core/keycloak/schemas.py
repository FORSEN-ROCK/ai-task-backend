from uuid import UUID

from pydantic import BaseModel, Field


class Roles(BaseModel):
    """Имена ролей из области или клиентского приложения."""

    roles: tuple[str, ...] = ()


class AccessTokenClaims(BaseModel):
    """Идентификатор, данные профиля и роли из полей токена Keycloak."""

    sub: UUID
    aud: str | list[str]
    preferred_username: str | None = None
    email: str | None = None
    email_verified: bool | None = None
    name: str | None = None
    given_name: str | None = None
    family_name: str | None = None
    locale: str | None = None
    realm_access: Roles = Field(default_factory=Roles)
    resource_access: dict[str, Roles] = Field(default_factory=dict)


class TokenResponse(BaseModel):
    """Поля ответа Keycloak на запрос токенов."""

    access_token: str = Field(min_length=1)
    refresh_token: str | None = None
    token_type: str | None = None
    expires_in: int | None = None
