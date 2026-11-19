import asyncio

from sqlalchemy import URL, Connection
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.pool import NullPool

from alembic import context
from app.confg import Settings
from app.core.database import database_url
from app.core.models import Base
from app.user import models  # noqa: F401  # Регистрирует таблицы в Base.metadata.


def run_migrations(connection: Connection) -> None:
    """Выполняет миграции в транзакции на открытом соединении.

    Args:
        connection: Соединение, предоставленное асинхронным движком.
    """
    context.configure(connection=connection, target_metadata=Base.metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_online(url: URL) -> None:
    """Выполняет миграции через асинхронное подключение.

    Args:
        url: URL подключения к PostgreSQL.
    """
    engine = create_async_engine(url, poolclass=NullPool)
    try:
        async with engine.connect() as connection:
            await connection.run_sync(run_migrations)
    finally:
        await engine.dispose()


url = database_url(Settings().database)
if context.is_offline_mode():
    context.configure(
        url=url,
        target_metadata=Base.metadata,
        literal_binds=True,
    )
    with context.begin_transaction():
        context.run_migrations()
else:
    asyncio.run(run_online(url))
