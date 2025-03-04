from typing import Annotated

from fastapi import APIRouter, Depends

from automated_actions.api.models import User, UserSchemaOut

from .auth import oidc
from .views.noop import router as noop_router
from .views.task import router as task_router

router = APIRouter()
router.include_router(noop_router, dependencies=[Depends(oidc)])
router.include_router(task_router, dependencies=[Depends(oidc)])
router.include_router(oidc.router, prefix="/auth")


@router.get("/me", operation_id="me")
def me(user: Annotated[User, Depends(oidc)]) -> UserSchemaOut:
    return user.dump()
