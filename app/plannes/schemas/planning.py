from datetime import date
from enum import StrEnum
from typing import Annotated, Self
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

Title = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
Priority = Annotated[int, Field(ge=1, le=5)]
NonNegativeInt = Annotated[int, Field(ge=0, le=2_147_483_647)]


class PlanningData(BaseModel):
    """Общие правила валидации планируемых сущностей."""

    model_config = ConfigDict(from_attributes=True, extra="forbid")


class GoalData(PlanningData):
    """Поля для создания и обновления цели."""

    title: Title
    description: str | None = None
    deadline: date | None = None
    available_minutes: NonNegativeInt
    priority: Priority


class GoalRead(GoalData):
    """Цель с идентификаторами записи и владельца."""

    id: UUID
    user_id: UUID


class TaskData(PlanningData):
    """Задача с целью, приоритетом и позицией."""

    goal_id: UUID
    title: Title
    priority: Priority
    position: NonNegativeInt
    description: str | None = None


class TaskRead(TaskData):
    """Сохранённая задача."""

    id: UUID


class FactorKind(StrEnum):
    """Тип влияния фактора на планирование."""

    FACILITATING = "facilitating"
    COMPLICATING = "complicating"


class FactorData(PlanningData):
    """Фактор и длительность его влияния в днях."""

    kind: FactorKind
    title: Title
    is_short_term: bool
    impact_days: int | None = Field(default=None, gt=0, le=2_147_483_647)


class FactorRead(FactorData):
    """Фактор с идентификаторами записи и владельца."""

    id: UUID
    user_id: UUID


class DependencyInfluence(StrEnum):
    """Влияние левой задачи на правую."""

    BLOCKS = "blocks"
    COMPLEMENTS = "complements"
    RELATES_TO = "relates_to"


class TaskDependencyData(PlanningData):
    """Направленная связь между двумя разными задачами."""

    left_task_id: UUID
    right_task_id: UUID
    influence: DependencyInfluence

    @model_validator(mode="after")
    def validate_distinct_tasks(self) -> Self:
        """Запрещает связь задачи с самой собой."""
        if self.left_task_id == self.right_task_id:
            raise ValueError("Связь должна указывать на две разные задачи.")
        return self


class TaskDependencyRead(TaskDependencyData):
    """Сохранённая связь задач."""

    id: UUID
