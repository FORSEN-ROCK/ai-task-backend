import asyncio
import json
from urllib.parse import parse_qs
from uuid import UUID

import httpx
import pytest
from pydantic import SecretStr

from app.confg.settings import KeycloakSettings
from app.core.keycloak.client import (
    InvalidTokenError,
    KeycloakClient,
    UserAlreadyExistsError,
)

USER_ID = UUID("00112233-4455-6677-8899-aabbccddeeff")
SETTINGS = KeycloakSettings(
    realm="planner",
    client_id="planner-api",
    client_secret=SecretStr("api-secret"),
    admin_client_id="planner-admin",
    admin_client_secret=SecretStr("admin-secret"),
)


def test_verify_token_and_get_roles() -> None:
    def handle(request: httpx.Request) -> httpx.Response:
        assert request.url.path.endswith("/token/introspect")
        assert request.headers["Authorization"].startswith("Basic ")
        assert parse_qs(request.content.decode())["token"] == ["access-token"]
        return httpx.Response(
            200,
            json={
                "active": True,
                "typ": "Bearer",
                "sub": str(USER_ID),
                "preferred_username": "alice",
                "given_name": "Alice",
                "family_name": "Example",
                "aud": ["planner-api"],
                "realm_access": {"roles": ["member"]},
                "resource_access": {"planner-api": {"roles": ["editor"]}},
            },
        )

    async def check() -> None:
        async with httpx.AsyncClient(transport=httpx.MockTransport(handle)) as http:
            client = KeycloakClient(SETTINGS, http)
            assert await client.verify_token("access-token") == USER_ID
            user = await client.get_user("access-token")
            assert user.user_id == USER_ID
            assert user.username == "alice"
            assert user.first_name == "Alice"
            assert user.last_name == "Example"
            assert "sub" not in user.model_dump()
            roles = await client.get_user_roles("access-token")
            assert roles.realm == ("member",)
            assert roles.client == ("editor",)

    asyncio.run(check())


@pytest.mark.parametrize(
    "claims",
    [
        {"active": False},
        {"active": True, "typ": "Refresh", "aud": "planner-api"},
        {"active": True, "typ": "Bearer", "aud": "another-api"},
        {"active": True, "typ": "Bearer", "aud": "planner-api", "sub": "invalid"},
    ],
)
def test_verify_token_rejects_invalid_claims(claims: dict[str, object]) -> None:
    def handle(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"sub": str(USER_ID), **claims})

    async def check() -> None:
        async with httpx.AsyncClient(transport=httpx.MockTransport(handle)) as http:
            with pytest.raises(InvalidTokenError):
                await KeycloakClient(SETTINGS, http).verify_token("invalid")

    asyncio.run(check())


@pytest.mark.parametrize("status", [201, 409])
def test_register_user(status: int) -> None:
    def handle(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/protocol/openid-connect/token"):
            assert parse_qs(request.content.decode()) == {
                "grant_type": ["client_credentials"]
            }
            return httpx.Response(200, json={"access_token": "admin-token"})

        assert request.url.path == "/admin/realms/planner/users"
        assert request.headers["Authorization"] == "Bearer admin-token"
        user = json.loads(request.content)
        assert user["username"] == "alice"
        assert user["email"] == "alice@example.com"
        assert user["credentials"][0]["value"] == "user-password"
        return httpx.Response(
            status, headers={"Location": f"/admin/realms/planner/users/{USER_ID}"}
        )

    async def check() -> None:
        async with httpx.AsyncClient(transport=httpx.MockTransport(handle)) as http:
            client = KeycloakClient(SETTINGS, http)
            password = SecretStr("user-password")
            if status == 409:
                with pytest.raises(UserAlreadyExistsError):
                    await client.register_user("alice", "alice@example.com", password)
            else:
                assert (
                    await client.register_user("alice", "alice@example.com", password)
                    == USER_ID
                )

    asyncio.run(check())
