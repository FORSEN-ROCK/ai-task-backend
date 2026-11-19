from fastapi import APIRouter

router = APIRouter()


@router.get("/health", tags=["health"])
async def health() -> dict[str, str]:
    """Возвращает статус доступности API."""
    return {"status": "ok"}
