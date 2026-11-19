from datetime import date
from uuid import UUID, uuid4

from sqlalchemy import CheckConstraint, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.models import Base


class Goal(Base):
    """Цель пользователя."""

    __tablename__ = "planning_goals"
    __table_args__ = (
        CheckConstraint("available_minutes >= 0", name="ck_planning_goals_minutes"),
        CheckConstraint("priority BETWEEN 1 AND 5", name="ck_planning_goals_priority"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(index=True)
    title: Mapped[str] = mapped_column(Text)
    description: Mapped[str | None] = mapped_column(Text)
    deadline: Mapped[date | None]
    available_minutes: Mapped[int]
    priority: Mapped[int]


class Task(Base):
    """Задача, выполняемая в рамках цели."""

    __tablename__ = "planning_tasks"
    __table_args__ = (
        CheckConstraint("priority BETWEEN 1 AND 5", name="ck_planning_tasks_priority"),
        CheckConstraint("position >= 0", name="ck_planning_tasks_position"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    goal_id: Mapped[UUID] = mapped_column(
        ForeignKey("planning_goals.id", ondelete="CASCADE"), index=True
    )
    title: Mapped[str] = mapped_column(Text)
    priority: Mapped[int]
    position: Mapped[int]
    description: Mapped[str | None] = mapped_column(Text)


class Factor(Base):
    """Фактор, влияющий на планирование пользователя."""

    __tablename__ = "planning_factors"
    __table_args__ = (
        CheckConstraint(
            "kind IN ('facilitating', 'complicating')", name="ck_planning_factors_kind"
        ),
        CheckConstraint("impact_days > 0", name="ck_planning_factors_impact_days"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(index=True)
    kind: Mapped[str] = mapped_column(String(12))
    title: Mapped[str] = mapped_column(Text)
    is_short_term: Mapped[bool]
    impact_days: Mapped[int | None]


class TaskDependency(Base):
    """Направленная связь между двумя задачами."""

    __tablename__ = "planning_task_dependencies"
    __table_args__ = (
        UniqueConstraint(
            "left_task_id", "right_task_id", name="uq_planning_dependencies_pair"
        ),
        CheckConstraint(
            "left_task_id <> right_task_id", name="ck_planning_dependencies_distinct"
        ),
        CheckConstraint(
            "influence IN ('blocks', 'complements', 'relates_to')",
            name="ck_planning_dependencies_influence",
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    left_task_id: Mapped[UUID] = mapped_column(
        ForeignKey("planning_tasks.id", ondelete="CASCADE")
    )
    right_task_id: Mapped[UUID] = mapped_column(
        ForeignKey("planning_tasks.id", ondelete="CASCADE"), index=True
    )
    influence: Mapped[str] = mapped_column(String(12))
