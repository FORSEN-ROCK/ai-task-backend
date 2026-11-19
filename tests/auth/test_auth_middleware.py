import asyncio
from uuid import UUID

import httpx
import pytest
from fastapi import FastAPI, Request
from pydantic import SecretStr

from app.confg.settings import KeycloakSettings
from app.core.keycloak.client import KeycloakClient
from app.core.middleware import AuthenticationMiddleware
from app.main import app
from app.user.schemas.user import User

USER_ID = UUID("00112233-4455-6677-8899-aabbccddeeff")


@pytest.mark.parametrize(
    ("authorization", "upstream_status", "active", "expected"),
    [
        ("Bearer valid", 200, True, 200),
        ("Bearer expired", 200, False, 401),
        ("Bearer valid", 503, False, 503),
        ("Basic abc", None, False, 401),
        (None, None, False, 401),
    ],
)
def test_middleware_authenticates_protected_requests(
    authorization: str | None,
    upstream_status: int | None,
    active: bool,
    expected: int,
) -> None:
    protected_app = FastAPI()
    protected_app.add_middleware(AuthenticationMiddleware)

    @protected_app.get("/private")
    async def private(request: Request) -> User:
        assert isinstance(request.state.user, User)
        return request.state.user

    def introspect(request: httpx.Request) -> httpx.Response:
        assert upstream_status is not None
        return httpx.Response(
            upstream_status,
            json={
                "active": active,
                "typ": "Bearer",
                "aud": "planner-api",
                "sub": str(USER_ID),
                "preferred_username": "alice",
            },
        )

    async def check() -> None:
        async with (
            httpx.AsyncClient(transport=httpx.MockTransport(introspect)) as upstream,
            httpx.AsyncClient(
                transport=httpx.ASGITransport(app=protected_app), base_url="http://test"
            ) as client,
        ):
            settings = KeycloakSettings(
                realm="planner",
                client_id="planner-api",
                client_secret=SecretStr("test"),
            )
            protected_app.state.keycloak = KeycloakClient(settings, upstream)
            headers = {"Authorization": authorization} if authorization else None
            response = await client.get("/private", headers=headers)

        assert response.status_code == expected
        if expected == 200:
            assert response.json()["user_id"] == str(USER_ID)
            assert response.json()["username"] == "alice"
        if expected == 401:
            assert response.headers["WWW-Authenticate"] == "Bearer"

    asyncio.run(check())


def test_application_middleware_keeps_documentation_public() -> None:
    async def check() -> None:
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            assert (await client.get("/docs")).status_code == 200
            assert (await client.get("/openapi.json")).status_code == 200
            assert (await client.get("/private")).status_code == 401

    asyncio.run(check())
