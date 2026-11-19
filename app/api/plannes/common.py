from collections.abc import AsyncIterator
from typing import Annotated
from uuid import UUID

from fastapi import Depends, HTTPException, Request, status
from pydantic import BaseModel
from sqlalchemy import Select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.exc import StaleDataError

from app.core.models import Base


async def get_session(request: Request) -> AsyncIterator[AsyncSession]:
    """Открывает сессию БД на время запроса."""
    async with AsyncSession(
        request.app.state.db_engine, expire_on_commit=False
    ) as session:
        yield session


async def get_user_id(request: Request) -> UUID:
    """Возвращает UUID пользователя, проверенного middleware."""
    return request.state.user.user_id


Session = Annotated[AsyncSession, Depends(get_session)]
UserId = Annotated[UUID, Depends(get_user_id)]


async def require_record[Record: Base](
    session: AsyncSession, statement: Select[tuple[Record]]
) -> Record:
    """Возвращает доступную запись или отвечает HTTP 404."""
    record = await session.scalar(statement)
    if record is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Запись не найдена.")
    return record


async def commit(session: AsyncSession) -> None:
    """Фиксирует изменения и преобразует конфликт данных в HTTP 409."""
    try:
        await session.commit()
    except (IntegrityError, StaleDataError):
        await session.rollback()
        raise HTTPException(
            status.HTTP_409_CONFLICT, "Изменение конфликтует с состоянием данных."
        ) from None


def update_record(record: Base, data: BaseModel) -> None:
    """Переносит поля входной схемы в существующую запись."""
    for field, value in data.model_dump().items():
        setattr(record, field, value)
