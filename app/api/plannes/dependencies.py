from uuid import UUID

from fastapi import APIRouter, Response, status

from app.api.plannes.common import (
    Session,
    UserId,
    commit,
    require_record,
    update_record,
)
from app.plannes.models import Task, TaskDependency
from app.plannes.repository import dependencies_for, tasks_for
from app.plannes.schemas import TaskDependencyData, TaskDependencyRead

router = APIRouter(prefix="/task-dependencies")


async def require_owned_tasks(
    data: TaskDependencyData, session: Session, user_id: UserId
) -> None:
    """Проверяет доступ к обеим задачам связи."""
    tasks = tasks_for(user_id)
    await require_record(session, tasks.where(Task.id == data.left_task_id))
    await require_record(session, tasks.where(Task.id == data.right_task_id))


@router.get("")
async def list_dependencies(
    session: Session, user_id: UserId
) -> list[TaskDependencyRead]:
    """Возвращает связи задач текущего пользователя."""
    records = await session.scalars(
        dependencies_for(user_id).order_by(TaskDependency.id)
    )
    return [TaskDependencyRead.model_validate(record) for record in records]


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_dependency(
    data: TaskDependencyData, session: Session, user_id: UserId
) -> TaskDependencyRead:
    """Создаёт связь задач."""
    await require_owned_tasks(data, session, user_id)
    record = TaskDependency(**data.model_dump())
    session.add(record)
    await commit(session)
    return TaskDependencyRead.model_validate(record)


@router.get("/{record_id}")
async def get_dependency(
    record_id: UUID, session: Session, user_id: UserId
) -> TaskDependencyRead:
    """Возвращает связь задач по UUID."""
    record = await require_record(
        session, dependencies_for(user_id).where(TaskDependency.id == record_id)
    )
    return TaskDependencyRead.model_validate(record)


@router.put("/{record_id}")
async def update_dependency(
    record_id: UUID, data: TaskDependencyData, session: Session, user_id: UserId
) -> TaskDependencyRead:
    """Обновляет связь задач."""
    record = await require_record(
        session, dependencies_for(user_id).where(TaskDependency.id == record_id)
    )
    await require_owned_tasks(data, session, user_id)
    update_record(record, data)
    await commit(session)
    return TaskDependencyRead.model_validate(record)


@router.delete(
    "/{record_id}", status_code=status.HTTP_204_NO_CONTENT, response_class=Response
)
async def delete_dependency(
    record_id: UUID, session: Session, user_id: UserId
) -> Response:
    """Удаляет связь задач."""
    record = await require_record(
        session, dependencies_for(user_id).where(TaskDependency.id == record_id)
    )
    await session.delete(record)
    await commit(session)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
