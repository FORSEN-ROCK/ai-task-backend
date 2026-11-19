from fastapi import APIRouter

from app.api.plannes import dependencies, factors, goals, tasks

router = APIRouter(prefix="/planning", tags=["planning"])
router.include_router(goals.router)
router.include_router(tasks.router)
router.include_router(factors.router)
router.include_router(dependencies.router)
