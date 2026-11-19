import asyncio
from pathlib import Path

from pytest import MonkeyPatch
from sqlalchemy.pool import AsyncAdaptedQueuePool

from app.confg import Settings
from app.main import app


def test_startup_loads_dotenv_and_applies_environment_overrides(
    tmp_path: Path, monkeypatch: MonkeyPatch
) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text(
        "DATABASE__HOST=database.local\n"
        "DATABASE__PORT=5433\n"
        "DATABASE__POOL_SIZE=3\n"
        "KEYCLOAK__URL=http://keycloak.local:8080\n"
        "KEYCLOAK__REALM=planner\n",
        encoding="utf-8",
    )
    monkeypatch.setitem(Settings.model_config, "env_file", env_file)
    monkeypatch.delenv("DATABASE__HOST", raising=False)
    monkeypatch.delenv("DATABASE__POOL_SIZE", raising=False)
    monkeypatch.delenv("KEYCLOAK__URL", raising=False)
    monkeypatch.delenv("KEYCLOAK__REALM", raising=False)
    monkeypatch.setenv("DATABASE__PORT", "5440")

    async def check_startup() -> None:
        async with app.router.lifespan_context(app):
            settings: Settings = app.state.settings
            assert settings.database.host == "database.local"
            assert settings.database.port == 5440
            assert settings.keycloak.url.host == "keycloak.local"
            assert settings.keycloak.realm == "planner"
            engine = app.state.db_engine
            pool = app.state.db_pool
            assert engine.url.drivername == "postgresql+asyncpg"
            assert engine.url.port == 5440
            assert pool is engine.pool
            assert isinstance(pool, AsyncAdaptedQueuePool)
            assert pool.size() == 3

        assert engine.pool is not pool
        assert not hasattr(app.state, "db_pool")

    asyncio.run(check_startup())
