from uuid import UUID

from fastapi import APIRouter, Response, status

from app.api.plannes.common import (
    Session,
    UserId,
    commit,
    require_record,
    update_record,
)
from app.plannes.models import Factor
from app.plannes.repository import factors_for
from app.plannes.schemas import FactorData, FactorRead

router = APIRouter(prefix="/factors")


@router.get("")
async def list_factors(session: Session, user_id: UserId) -> list[FactorRead]:
    """Возвращает факторы текущего пользователя."""
    records = await session.scalars(
        factors_for(user_id).order_by(Factor.title, Factor.id)
    )
    return [FactorRead.model_validate(record) for record in records]


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_factor(
    data: FactorData, session: Session, user_id: UserId
) -> FactorRead:
    """Создаёт фактор."""
    record = Factor(user_id=user_id, **data.model_dump())
    session.add(record)
    await commit(session)
    return FactorRead.model_validate(record)


@router.get("/{record_id}")
async def get_factor(record_id: UUID, session: Session, user_id: UserId) -> FactorRead:
    """Возвращает фактор по UUID."""
    record = await require_record(
        session, factors_for(user_id).where(Factor.id == record_id)
    )
    return FactorRead.model_validate(record)


@router.put("/{record_id}")
async def update_factor(
    record_id: UUID, data: FactorData, session: Session, user_id: UserId
) -> FactorRead:
    """Обновляет фактор."""
    record = await require_record(
        session, factors_for(user_id).where(Factor.id == record_id)
    )
    update_record(record, data)
    await commit(session)
    return FactorRead.model_validate(record)


@router.delete(
    "/{record_id}", status_code=status.HTTP_204_NO_CONTENT, response_class=Response
)
async def delete_factor(record_id: UUID, session: Session, user_id: UserId) -> Response:
    """Удаляет фактор."""
    record = await require_record(
        session, factors_for(user_id).where(Factor.id == record_id)
    )
    await session.delete(record)
    await commit(session)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
