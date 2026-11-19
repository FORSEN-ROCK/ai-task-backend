import asyncio
import json
from urllib.parse import parse_qs

import httpx
import pytest
from pydantic import SecretStr

from app.confg.settings import KeycloakSettings
from app.core.keycloak.client import KeycloakClient
from app.main import app


@pytest.mark.parametrize("upstream_status", [204, 400])
def test_logout_route(monkeypatch: pytest.MonkeyPatch, upstream_status: int) -> None:
    def handle(request: httpx.Request) -> httpx.Response:
        assert request.url.path.endswith("/protocol/openid-connect/logout")
        assert request.headers["Authorization"].startswith("Basic ")
        assert parse_qs(request.content.decode()) == {"refresh_token": ["refresh"]}
        return httpx.Response(upstream_status)

    async def check() -> None:
        settings = KeycloakSettings(
            realm="planner",
            client_id="planner-api",
            client_secret=SecretStr("api-secret"),
        )
        async with (
            httpx.AsyncClient(transport=httpx.MockTransport(handle)) as upstream,
            httpx.AsyncClient(
                transport=httpx.ASGITransport(app=app), base_url="http://test"
            ) as client,
        ):
            monkeypatch.setattr(
                app.state, "keycloak", KeycloakClient(settings, upstream), raising=False
            )
            response = await client.post(
                "/auth/logout", json={"refresh_token": "refresh"}
            )

        assert response.status_code == upstream_status
        if upstream_status == 204:
            assert response.content == b""

    asyncio.run(check())


@pytest.mark.parametrize(
    ("route", "body", "grant", "upstream_status", "payload", "expected"),
    [
        (
            "login",
            {"username": "alice", "password": "password"},
            "password",
            200,
            {
                "access_token": "access",
                "refresh_token": "refresh",
                "session_state": "keycloak-specific",
            },
            {"access_token": "access", "refresh_token": "refresh"},
        ),
        (
            "login",
            {"username": "alice", "password": "wrong"},
            "password",
            401,
            {"error": "invalid_grant", "error_description": "Invalid credentials"},
            {"detail": "Запрос на выдачу токенов отклонён."},
        ),
        (
            "refresh",
            {"refresh_token": "refresh"},
            "refresh_token",
            200,
            {"access_token": "new-access", "refresh_token": "new-refresh"},
            {"access_token": "new-access", "refresh_token": "new-refresh"},
        ),
        (
            "refresh",
            {"refresh_token": "expired"},
            "refresh_token",
            400,
            {"error": "invalid_grant"},
            {"detail": "Запрос на выдачу токенов отклонён."},
        ),
    ],
)
def test_token_routes_map_keycloak_response(
    monkeypatch: pytest.MonkeyPatch,
    route: str,
    body: dict[str, str],
    grant: str,
    upstream_status: int,
    payload: dict[str, str],
    expected: dict[str, str],
) -> None:
    def handle(request: httpx.Request) -> httpx.Response:
        assert request.url.path.endswith("/protocol/openid-connect/token")
        assert request.headers["Authorization"].startswith("Basic ")
        data = parse_qs(request.content.decode())
        assert data["grant_type"] == [grant]
        for name, value in body.items():
            assert data[name] == [value]
        return httpx.Response(upstream_status, json=payload)

    async def check() -> None:
        settings = KeycloakSettings(
            realm="planner",
            client_id="planner-api",
            client_secret=SecretStr("api-secret"),
        )
        async with (
            httpx.AsyncClient(transport=httpx.MockTransport(handle)) as upstream,
            httpx.AsyncClient(
                transport=httpx.ASGITransport(app=app), base_url="http://test"
            ) as client,
        ):
            monkeypatch.setattr(
                app.state, "keycloak", KeycloakClient(settings, upstream), raising=False
            )
            response = await client.post(f"/auth/{route}", json=body)

        assert response.status_code == upstream_status
        assert response.json() == expected
        assert response.headers["Cache-Control"] == "no-store"

    asyncio.run(check())


@pytest.mark.parametrize("upstream_status", [201, 400, 409])
def test_registration_route(
    monkeypatch: pytest.MonkeyPatch, upstream_status: int
) -> None:
    def handle(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/token"):
            return httpx.Response(200, json={"access_token": "admin-token"})
        assert request.url.path == "/admin/realms/planner/users"
        profile = json.loads(request.content)
        assert profile["firstName"] == "Alice"
        assert profile["lastName"] == "Example"
        return httpx.Response(
            upstream_status,
            headers={"Location": "/users/00112233-4455-6677-8899-aabbccddeeff"},
        )

    async def check() -> None:
        settings = KeycloakSettings(
            realm="planner",
            admin_client_id="planner-admin",
            admin_client_secret=SecretStr("admin-secret"),
        )
        async with (
            httpx.AsyncClient(transport=httpx.MockTransport(handle)) as upstream,
            httpx.AsyncClient(
                transport=httpx.ASGITransport(app=app), base_url="http://test"
            ) as client,
        ):
            monkeypatch.setattr(
                app.state, "keycloak", KeycloakClient(settings, upstream), raising=False
            )
            response = await client.post(
                "/auth/register",
                json={
                    "username": "alice",
                    "email": "alice@example.com",
                    "password": "password",
                    "first_name": "Alice",
                    "last_name": "Example",
                },
            )
            invalid = await client.post(
                "/auth/register",
                json={"username": "alice", "password": {"secret": "private"}},
            )

        assert response.status_code == upstream_status
        if upstream_status == 201:
            assert response.content == b""
        assert invalid.status_code == 422
        assert "private" not in invalid.text

    asyncio.run(check())
