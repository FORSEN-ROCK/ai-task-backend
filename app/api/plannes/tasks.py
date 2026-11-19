from uuid import UUID

from fastapi import APIRouter, Response, status

from app.api.plannes.common import (
    Session,
    UserId,
    commit,
    require_record,
    update_record,
)
from app.plannes.models import Goal, Task
from app.plannes.repository import goals_for, tasks_for
from app.plannes.schemas import TaskData, TaskRead

router = APIRouter(prefix="/tasks")


@router.get("")
async def list_tasks(session: Session, user_id: UserId) -> list[TaskRead]:
    """Возвращает задачи текущего пользователя."""
    records = await session.scalars(tasks_for(user_id).order_by(Task.position, Task.id))
    return [TaskRead.model_validate(record) for record in records]


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_task(data: TaskData, session: Session, user_id: UserId) -> TaskRead:
    """Создаёт задачу."""
    await require_record(session, goals_for(user_id).where(Goal.id == data.goal_id))
    record = Task(**data.model_dump())
    session.add(record)
    await commit(session)
    return TaskRead.model_validate(record)


@router.get("/{record_id}")
async def get_task(record_id: UUID, session: Session, user_id: UserId) -> TaskRead:
    """Возвращает задачу по UUID."""
    record = await require_record(
        session, tasks_for(user_id).where(Task.id == record_id)
    )
    return TaskRead.model_validate(record)


@router.put("/{record_id}")
async def update_task(
    record_id: UUID, data: TaskData, session: Session, user_id: UserId
) -> TaskRead:
    """Обновляет задачу."""
    record = await require_record(
        session, tasks_for(user_id).where(Task.id == record_id)
    )
    await require_record(session, goals_for(user_id).where(Goal.id == data.goal_id))
    update_record(record, data)
    await commit(session)
    return TaskRead.model_validate(record)


@router.delete(
    "/{record_id}", status_code=status.HTTP_204_NO_CONTENT, response_class=Response
)
async def delete_task(record_id: UUID, session: Session, user_id: UserId) -> Response:
    """Удаляет задачу."""
    record = await require_record(
        session, tasks_for(user_id).where(Task.id == record_id)
    )
    await session.delete(record)
    await commit(session)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
