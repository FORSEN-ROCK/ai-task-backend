from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI

from app.api.auth.routes import router as auth_router
from app.api.health import router as health_router
from app.api.plannes import router as planning_router
from app.confg import Settings
from app.core.database import create_database_engine
from app.core.keycloak.client import KeycloakClient
from app.core.middleware import AuthenticationMiddleware


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Инициализирует ресурсы приложения и освобождает их при остановке.

    Args:
        app: Экземпляр FastAPI, в состоянии которого хранятся ресурсы.

    Yields:
        Управление работающему приложению после инициализации ресурсов.
    """
    app.state.settings = Settings()
    engine = create_database_engine(app.state.settings.database)
    app.state.db_engine = engine
    app.state.db_pool = engine.pool
    try:
        async with httpx.AsyncClient(timeout=5.0) as http:
            app.state.keycloak = KeycloakClient(app.state.settings.keycloak, http)
            try:
                yield
            finally:
                del app.state.keycloak
    finally:
        await engine.dispose()
        del app.state.db_pool
        del app.state.db_engine


app = FastAPI(title="AI Task Planner", lifespan=lifespan)
app.add_middleware(AuthenticationMiddleware)
app.include_router(health_router)
app.include_router(auth_router)
app.include_router(planning_router)
