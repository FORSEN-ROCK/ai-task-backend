from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class UserCharacteristics(BaseModel):
    """Цели, выполненные подзадачи и описание инициативы пользователя."""

    model_config = ConfigDict(from_attributes=True)

    user_id: UUID
    minor_goal: str | None = None
    major_goal: str | None = None
    completed_subtasks: list[str] = Field(default_factory=list)
    initiative: str | None = None
