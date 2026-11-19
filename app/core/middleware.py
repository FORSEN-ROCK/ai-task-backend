from fastapi import Request, status
from fastapi.responses import JSONResponse
from starlette.types import ASGIApp, Receive, Scope, Send

from app.core.keycloak.client import InvalidTokenError, KeycloakError

PUBLIC_ROUTES = frozenset(
    {
        ("GET", "/health"),
        ("GET", "/docs"),
        ("GET", "/docs/oauth2-redirect"),
        ("GET", "/redoc"),
        ("GET", "/openapi.json"),
        ("POST", "/auth/register"),
        ("POST", "/auth/login"),
        ("POST", "/auth/refresh"),
        ("POST", "/auth/logout"),
    }
)


class AuthenticationMiddleware:
    """Проверяет токен доступа и сохраняет пользователя в request.state."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request = Request(scope)
        path = request.url.path.removeprefix(scope.get("root_path", ""))
        if (request.method, path) in PUBLIC_ROUTES:
            await self.app(scope, receive, send)
            return

        try:
            credentials = request.headers.get("Authorization", "").split()
            if len(credentials) != 2 or credentials[0].lower() != "bearer":
                raise InvalidTokenError("Нужен Bearer-токен.")
            request.state.user = await request.app.state.keycloak.get_user(
                credentials[1]
            )
        except InvalidTokenError:
            response = JSONResponse(
                {"detail": "Требуется действительный access-токен."},
                status_code=status.HTTP_401_UNAUTHORIZED,
                headers={"WWW-Authenticate": "Bearer"},
            )
        except KeycloakError:
            response = JSONResponse(
                {"detail": "Сервис аутентификации недоступен."},
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        else:
            await self.app(scope, receive, send)
            return

        await response(scope, receive, send)
