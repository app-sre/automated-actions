from fastapi import APIRouter

from .noop.views import router as noop_router

router = APIRouter()
router.include_router(noop_router)
