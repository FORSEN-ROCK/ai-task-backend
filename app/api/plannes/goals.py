from uuid import UUID

from fastapi import APIRouter, Response, status

from app.api.plannes.common import (
    Session,
    UserId,
    commit,
    require_record,
    update_record,
)
from app.plannes.models import Goal
from app.plannes.repository import goals_for
from app.plannes.schemas import GoalData, GoalRead

router = APIRouter(prefix="/goals")


@router.get("")
async def list_goals(session: Session, user_id: UserId) -> list[GoalRead]:
    """Возвращает цели текущего пользователя."""
    records = await session.scalars(
        goals_for(user_id).order_by(-Goal.priority, Goal.id)
    )
    return [GoalRead.model_validate(record) for record in records]


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_goal(data: GoalData, session: Session, user_id: UserId) -> GoalRead:
    """Создаёт цель."""
    record = Goal(user_id=user_id, **data.model_dump())
    session.add(record)
    await commit(session)
    return GoalRead.model_validate(record)


@router.get("/{record_id}")
async def get_goal(record_id: UUID, session: Session, user_id: UserId) -> GoalRead:
    """Возвращает цель по UUID."""
    record = await require_record(
        session, goals_for(user_id).where(Goal.id == record_id)
    )
    return GoalRead.model_validate(record)


@router.put("/{record_id}")
async def update_goal(
    record_id: UUID, data: GoalData, session: Session, user_id: UserId
) -> GoalRead:
    """Обновляет цель."""
    record = await require_record(
        session, goals_for(user_id).where(Goal.id == record_id)
    )
    update_record(record, data)
    await commit(session)
    return GoalRead.model_validate(record)


@router.delete(
    "/{record_id}", status_code=status.HTTP_204_NO_CONTENT, response_class=Response
)
async def delete_goal(record_id: UUID, session: Session, user_id: UserId) -> Response:
    """Удаляет цель, её задачи и связи этих задач."""
    record = await require_record(
        session, goals_for(user_id).where(Goal.id == record_id)
    )
    await session.delete(record)
    await commit(session)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
