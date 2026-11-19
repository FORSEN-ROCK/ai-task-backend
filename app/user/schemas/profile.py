from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, JsonValue


class UserProfile(BaseModel):
    """Локальный профиль с предпочтениями в формате JSON."""

    model_config = ConfigDict(from_attributes=True)

    user_id: UUID
    preferences: dict[str, JsonValue] = Field(default_factory=dict)
