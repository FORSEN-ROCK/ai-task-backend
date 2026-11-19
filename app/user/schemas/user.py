from uuid import UUID

from pydantic import BaseModel


class User(BaseModel):
    """Идентификация и основные контактные данные пользователя приложения."""

    user_id: UUID
    username: str | None = None
    email: str | None = None
    first_name: str | None = None
    last_name: str | None = None
