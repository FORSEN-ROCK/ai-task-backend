from uuid import UUID

from sqlalchemy import ForeignKey, Text, Uuid, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.mutable import MutableList
from sqlalchemy.orm import Mapped, mapped_column

from app.core.models import Base


class UserCharacteristics(Base):
    """Хранит цели, выполненные подзадачи и инициативу пользователя."""

    __tablename__ = "user_characteristics"

    user_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("user_profiles.user_id", ondelete="CASCADE"), primary_key=True
    )
    minor_goal: Mapped[str | None] = mapped_column(Text)
    major_goal: Mapped[str | None] = mapped_column(Text)
    completed_subtasks: Mapped[list[str]] = mapped_column(
        MutableList.as_mutable(JSONB),
        default=list,
        server_default=text("'[]'::jsonb"),
    )
    initiative: Mapped[str | None] = mapped_column(Text)
