from sqlalchemy import URL
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from app.confg.settings import DatabaseSettings


def database_url(settings: DatabaseSettings) -> URL:
    """Собирает URL PostgreSQL для приложения и Alembic.

    Args:
        settings: Параметры подключения к PostgreSQL.

    Returns:
        URL подключения с асинхронным драйвером asyncpg.
    """
    return URL.create(
        drivername="postgresql+asyncpg",
        username=settings.user,
        password=settings.password.get_secret_value() if settings.password else None,
        host=settings.host,
        port=settings.port,
        database=settings.name,
    )


def create_database_engine(settings: DatabaseSettings) -> AsyncEngine:
    """Создаёт асинхронный движок PostgreSQL с пулом соединений.

    Args:
        settings: Параметры подключения и размер пула.

    Returns:
        Движок SQLAlchemy с драйвером asyncpg.
    """
    return create_async_engine(
        database_url(settings),
        pool_size=settings.pool_size,
        max_overflow=0,
        pool_pre_ping=True,
    )
