from urllib.parse import quote, urlsplit
from uuid import UUID

import httpx
from pydantic import BaseModel, SecretStr, ValidationError

from app.confg.settings import KeycloakSettings
from app.core.keycloak.schemas import AccessTokenClaims, TokenResponse
from app.user.schemas.user import User


class KeycloakError(Exception):
    """Ошибка конфигурации, запроса или ответа Keycloak."""


class InvalidTokenError(KeycloakError):
    """Токен не является действительным access-токеном приложения."""


class UserAlreadyExistsError(KeycloakError):
    """Keycloak отклонил регистрацию из-за конфликта пользователя."""


class RegistrationRejectedError(KeycloakError):
    """Данные пользователя не прошли проверку Keycloak."""


class UserRoles(BaseModel):
    """Роли области и роли клиента приложения из access-токена."""

    realm: tuple[str, ...]
    client: tuple[str, ...]


class TokenRequestRejectedError(KeycloakError):
    """Провайдер отклонил запрос на выдачу токенов."""

    def __init__(self, status_code: int) -> None:
        super().__init__("Запрос на выдачу токенов отклонён.")
        self.status_code = status_code


class KeycloakClient:
    """Асинхронный клиент Keycloak для аутентификации и регистрации."""

    def __init__(self, settings: KeycloakSettings, http: httpx.AsyncClient) -> None:
        self._settings = settings
        self._http = http

    @property
    def _realm_path(self) -> str:
        if not self._settings.realm:
            raise KeycloakError("В настройках Keycloak не задан realm.")
        return quote(self._settings.realm, safe="")

    @property
    def _oidc_url(self) -> str:
        base_url = str(self._settings.url).rstrip("/")
        return f"{base_url}/realms/{self._realm_path}/protocol/openid-connect"

    async def _post(
        self,
        url: str,
        *,
        data: dict[str, str] | None = None,
        json: dict[str, object] | None = None,
        auth: httpx.BasicAuth | None = None,
        headers: dict[str, str] | None = None,
        expected_status: int | None = 200,
    ) -> httpx.Response:
        try:
            response = await self._http.post(
                url, data=data, json=json, auth=auth, headers=headers
            )
        except httpx.RequestError:
            raise KeycloakError("Не удалось выполнить запрос к Keycloak.") from None

        if expected_status is not None and response.status_code != expected_status:
            raise KeycloakError(f"Keycloak вернул HTTP {response.status_code}.")
        return response

    @staticmethod
    def _json_object(response: httpx.Response) -> dict[str, object]:
        try:
            payload = response.json()
        except ValueError:
            raise KeycloakError("Keycloak вернул некорректный JSON.") from None
        if not isinstance(payload, dict):
            raise KeycloakError("Keycloak вернул неожиданный формат ответа.")
        return payload

    async def _introspect(self, token: str) -> AccessTokenClaims:
        if not token.strip():
            raise InvalidTokenError("Access-токен пуст.")
        client_id = self._settings.client_id
        client_secret = self._settings.client_secret
        if not client_id or not client_secret:
            raise KeycloakError("Не заданы учётные данные клиента проверки токенов.")

        response = await self._post(
            f"{self._oidc_url}/token/introspect",
            data={"token": token, "token_type_hint": "access_token"},
            auth=httpx.BasicAuth(client_id, client_secret.get_secret_value()),
        )
        payload = self._json_object(response)
        if payload.get("active") is not True or payload.get("typ") != "Bearer":
            raise InvalidTokenError("Keycloak не подтвердил access-токен.")
        try:
            claims = AccessTokenClaims.model_validate(payload)
        except ValidationError:
            raise InvalidTokenError("В токене отсутствуют корректные claims.") from None

        audience = [claims.aud] if isinstance(claims.aud, str) else claims.aud
        if client_id not in audience:
            raise InvalidTokenError("Access-токен выдан для другой аудитории.")
        return claims

    async def verify_token(self, token: str) -> UUID:
        """Проверяет токен доступа.

        Args:
            token: Токен доступа пользователя.

        Returns:
            UUID пользователя.

        Raises:
            InvalidTokenError: Токен недействителен или выдан другому клиенту.
            KeycloakError: Проверку токена не удалось выполнить.
        """
        return (await self._introspect(token)).sub

    async def get_user(self, token: str) -> User:
        """Преобразует данные проверенного токена в модель пользователя.

        Args:
            token: Токен доступа пользователя.

        Returns:
            Модель пользователя приложения.

        Raises:
            InvalidTokenError: Токен недействителен или выдан другому клиенту.
            KeycloakError: Проверку токена не удалось выполнить.
        """
        claims = await self._introspect(token)
        return User(
            user_id=claims.sub,
            username=claims.preferred_username,
            email=claims.email,
            first_name=claims.given_name,
            last_name=claims.family_name,
        )

    async def get_user_roles(self, token: str) -> UserRoles:
        """Возвращает роли пользователя из проверенного токена доступа.

        Args:
            token: Токен доступа пользователя.

        Returns:
            Роли области и клиента приложения.

        Raises:
            InvalidTokenError: Токен недействителен или выдан другому клиенту.
            KeycloakError: Проверку токена не удалось выполнить.
        """
        claims = await self._introspect(token)
        client_roles = claims.resource_access.get(self._settings.client_id or "")
        return UserRoles(
            realm=claims.realm_access.roles,
            client=client_roles.roles if client_roles else (),
        )

    async def authenticate(self, username: str, password: SecretStr) -> TokenResponse:
        """Запрашивает токены по имени пользователя и паролю.

        Args:
            username: Имя пользователя.
            password: Пароль пользователя.

        Returns:
            Токены, выданные Keycloak.

        Raises:
            TokenRequestRejectedError: Keycloak отклонил запрос.
            KeycloakError: Запрос не удалось выполнить или обработать.
        """
        return await self._request_tokens(
            {
                "grant_type": "password",
                "scope": "openid",
                "username": username,
                "password": password.get_secret_value(),
            }
        )

    async def refresh_tokens(self, refresh_token: SecretStr) -> TokenResponse:
        """Обновляет токены пользователя.

        Args:
            refresh_token: Токен обновления.

        Returns:
            Токены, выданные Keycloak.

        Raises:
            TokenRequestRejectedError: Keycloak отклонил запрос.
            KeycloakError: Запрос не удалось выполнить или обработать.
        """
        return await self._request_tokens(
            {
                "grant_type": "refresh_token",
                "refresh_token": refresh_token.get_secret_value(),
            }
        )

    async def _request_tokens(self, data: dict[str, str]) -> TokenResponse:
        response = await self._post_as_oidc_client("token", data)
        if response.status_code != 200:
            raise KeycloakError("Keycloak вернул неожиданный статус ответа.")
        try:
            return TokenResponse.model_validate(self._json_object(response))
        except ValidationError:
            raise KeycloakError(
                "Keycloak вернул некорректные данные токенов."
            ) from None

    async def logout(self, refresh_token: SecretStr) -> None:
        """Завершает сессию пользователя по токену обновления.

        Args:
            refresh_token: Токен обновления завершаемой сессии.

        Raises:
            TokenRequestRejectedError: Keycloak отклонил запрос.
            KeycloakError: Запрос не удалось выполнить.
        """
        response = await self._post_as_oidc_client(
            "logout", {"refresh_token": refresh_token.get_secret_value()}
        )
        if response.status_code != 204:
            raise KeycloakError("Keycloak вернул неожиданный статус выхода.")

    async def _post_as_oidc_client(
        self, endpoint: str, data: dict[str, str]
    ) -> httpx.Response:
        client_id = self._settings.client_id
        client_secret = self._settings.client_secret
        if not client_id or not client_secret:
            raise KeycloakError("Не заданы учётные данные OIDC-клиента.")

        response = await self._post(
            f"{self._oidc_url}/{endpoint}",
            data=data,
            auth=httpx.BasicAuth(client_id, client_secret.get_secret_value()),
            expected_status=None,
        )
        if response.is_client_error:
            raise TokenRequestRejectedError(response.status_code)
        return response

    async def register_user(
        self,
        username: str,
        email: str,
        password: SecretStr,
        *,
        first_name: str | None = None,
        last_name: str | None = None,
    ) -> UUID:
        """Создаёт учётную запись пользователя.

        Args:
            username: Имя пользователя.
            email: Адрес электронной почты пользователя.
            password: Пароль пользователя.
            first_name: Имя пользователя для профиля.
            last_name: Фамилия пользователя для профиля.

        Returns:
            UUID созданной учётной записи.

        Raises:
            UserAlreadyExistsError: Учётная запись уже существует.
            RegistrationRejectedError: Keycloak отклонил данные пользователя.
            KeycloakError: Запрос не удалось выполнить или обработать.
        """
        client_id = self._settings.admin_client_id
        client_secret = self._settings.admin_client_secret
        if not client_id or not client_secret:
            raise KeycloakError("Не заданы учётные данные сервисного клиента.")

        token_response = await self._post(
            f"{self._oidc_url}/token",
            data={"grant_type": "client_credentials"},
            auth=httpx.BasicAuth(client_id, client_secret.get_secret_value()),
        )
        admin_token = self._json_object(token_response).get("access_token")
        if not isinstance(admin_token, str) or not admin_token:
            raise KeycloakError("Keycloak не вернул access-токен сервисного клиента.")

        base_url = str(self._settings.url).rstrip("/")
        profile: dict[str, object] = {
            "username": username,
            "email": email,
            "enabled": True,
            "credentials": [
                {
                    "type": "password",
                    "value": password.get_secret_value(),
                    "temporary": False,
                }
            ],
        }
        if first_name is not None:
            profile["firstName"] = first_name
        if last_name is not None:
            profile["lastName"] = last_name

        response = await self._post(
            f"{base_url}/admin/realms/{self._realm_path}/users",
            headers={"Authorization": f"Bearer {admin_token}"},
            json=profile,
            expected_status=None,
        )
        if response.status_code == 409:
            raise UserAlreadyExistsError("Пользователь уже существует в Keycloak.")
        if response.status_code == 400:
            raise RegistrationRejectedError("Keycloak отклонил данные пользователя.")
        if response.status_code != 201:
            raise KeycloakError(f"Keycloak вернул HTTP {response.status_code}.")
        try:
            location = urlsplit(response.headers.get("Location", ""))
            return UUID(location.path.rstrip("/").rsplit("/", 1)[-1])
        except ValueError:
            raise KeycloakError(
                "Keycloak не вернул UUID созданного пользователя."
            ) from None
