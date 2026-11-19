from uuid import UUID

from sqlalchemy import Select, select

from app.plannes.models import Factor, Goal, Task, TaskDependency


def goals_for(user_id: UUID) -> Select[tuple[Goal]]:
    """Выбирает цели владельца."""
    return select(Goal).where(Goal.user_id == user_id)


def tasks_for(user_id: UUID) -> Select[tuple[Task]]:
    """Выбирает задачи через принадлежность их целей владельцу."""
    return select(Task).join(Goal).where(Goal.user_id == user_id)


def factors_for(user_id: UUID) -> Select[tuple[Factor]]:
    """Выбирает факторы владельца."""
    return select(Factor).where(Factor.user_id == user_id)


def dependencies_for(user_id: UUID) -> Select[tuple[TaskDependency]]:
    """Выбирает связи, обе задачи которых принадлежат владельцу."""
    owned_task_ids = tasks_for(user_id).with_only_columns(Task.id)
    return select(TaskDependency).where(
        TaskDependency.left_task_id.in_(owned_task_ids),
        TaskDependency.right_task_id.in_(owned_task_ids),
    )
