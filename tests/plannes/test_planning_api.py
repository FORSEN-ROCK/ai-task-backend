import asyncio
from collections.abc import AsyncIterator, Iterator
from typing import Any
from uuid import UUID

import httpx
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.api.plannes.common import get_session
from app.core.models import Base
from app.main import app
from app.plannes.models import Factor, Goal, Task, TaskDependency
from app.user.schemas.user import User

OWNER = str(UUID(int=1))
OTHER = str(UUID(int=2))


class InMemorySession:
    """Использует синхронную SQLite-сессию на асинхронной границе теста."""

    def __init__(self, session: Session) -> None:
        self.session = session
        self.add = session.add

    async def scalar(self, statement: Any) -> Any:
        return self.session.scalar(statement)

    async def scalars(self, statement: Any) -> Any:
        return self.session.scalars(statement)

    async def commit(self) -> None:
        self.session.commit()

    async def rollback(self) -> None:
        self.session.rollback()

    async def delete(self, record: Base) -> None:
        self.session.delete(record)


class TestIdentityProvider:
    """Преобразует тестовый токен в пользователя без сетевого запроса."""

    __test__ = False

    async def get_user(self, token: str) -> User:
        return User(user_id=UUID(token))


@pytest.fixture
def planning_app(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    engine = create_engine("sqlite://", poolclass=StaticPool)
    with engine.connect() as connection:
        connection.exec_driver_sql("PRAGMA foreign_keys=ON")
    Base.metadata.create_all(
        engine,
        tables=[
            Goal.__table__,
            Task.__table__,
            Factor.__table__,
            TaskDependency.__table__,
        ],
    )

    async def session() -> AsyncIterator[InMemorySession]:
        with Session(engine, expire_on_commit=False) as database:
            yield InMemorySession(database)

    monkeypatch.setitem(app.dependency_overrides, get_session, session)
    monkeypatch.setattr(app.state, "keycloak", TestIdentityProvider(), raising=False)
    try:
        yield
    finally:
        engine.dispose()


async def create(client: httpx.AsyncClient, path: str, data: dict[str, Any]) -> dict:
    response = await client.post(path, json=data)
    assert response.status_code == 201, response.text
    return response.json()


def test_goal_deletion_cascades_on_both_sides(planning_app: None) -> None:
    async def check() -> None:
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app),
            base_url="http://test/planning/",
            headers={"Authorization": f"Bearer {OWNER}"},
        ) as client:
            goal_data = {"title": "Goal", "available_minutes": 60, "priority": 5}
            first = await create(client, "goals", goal_data)
            second = await create(client, "goals", {**goal_data, "title": "Other"})
            task_data = {"title": "Task", "priority": 3, "position": 0}
            left = await create(client, "tasks", {**task_data, "goal_id": first["id"]})
            right = await create(
                client, "tasks", {**task_data, "goal_id": second["id"]}
            )
            relation = {
                "left_task_id": left["id"],
                "right_task_id": right["id"],
                "influence": "blocks",
            }
            forward = await create(client, "task-dependencies", relation)
            reverse = await create(
                client,
                "task-dependencies",
                {**relation, "left_task_id": right["id"], "right_task_id": left["id"]},
            )
            assert (
                await client.post("task-dependencies", json=relation)
            ).status_code == 409

            foreign = {"Authorization": f"Bearer {OTHER}"}
            for path, record in (
                ("goals", first),
                ("tasks", left),
                ("task-dependencies", forward),
            ):
                assert (await client.get(path, headers=foreign)).json() == []
                assert (
                    await client.get(f"{path}/{record['id']}", headers=foreign)
                ).status_code == 404
            assert (
                await client.delete(f"goals/{first['id']}", headers=foreign)
            ).status_code == 404

            assert (await client.delete(f"goals/{first['id']}")).status_code == 204
            assert (await client.get(f"tasks/{left['id']}")).status_code == 404
            assert (await client.get(f"tasks/{right['id']}")).status_code == 200
            assert (await client.get(f"goals/{second['id']}")).status_code == 200
            for record in (forward, reverse):
                assert (
                    await client.get(f"task-dependencies/{record['id']}")
                ).status_code == 404

    asyncio.run(check())


def test_factor_crud_respects_owner(planning_app: None) -> None:
    async def check() -> None:
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app),
            base_url="http://test/planning/",
            headers={"Authorization": f"Bearer {OWNER}"},
        ) as client:
            data = {"kind": "facilitating", "title": "Factor", "is_short_term": True}
            factor = await create(client, "factors", data)
            path = f"factors/{factor['id']}"
            assert (await client.get("factors")).json() == [factor]
            forbidden = await client.put(
                path, json=data, headers={"Authorization": f"Bearer {OTHER}"}
            )
            assert forbidden.status_code == 404
            updated = await client.put(path, json={**data, "impact_days": 2})
            assert updated.status_code == 200
            assert updated.json()["impact_days"] == 2
            assert (await client.delete(path)).status_code == 204
            assert (await client.get(path)).status_code == 404

    asyncio.run(check())
