from uuid import UUID

from pydantic import JsonValue
from sqlalchemy import Uuid, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.mutable import MutableDict
from sqlalchemy.orm import Mapped, mapped_column

from app.core.models import Base


class UserProfile(Base):
    """Хранит локальные предпочтения пользователя."""

    __tablename__ = "user_profiles"

    user_id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    preferences: Mapped[dict[str, JsonValue]] = mapped_column(
        MutableDict.as_mutable(JSONB),
        default=dict,
        server_default=text("'{}'::jsonb"),
    )
