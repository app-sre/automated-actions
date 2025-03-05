from fastapi import APIRouter, Depends

from automated_actions.api.models import UserSchemaOut

from .auth import get_authz
from .dependencies import UserDep, get_user
from .views.noop import router as noop_router
from .views.openshift import router as openshift_router
from .views.task import router as task_router

router = APIRouter()
router.include_router(noop_router, dependencies=[Depends(get_user), Depends(get_authz)])
router.include_router(
    openshift_router, dependencies=[Depends(get_user), Depends(get_authz)]
)
router.include_router(task_router, dependencies=[Depends(get_user), Depends(get_authz)])


@router.get("/me", operation_id="me", dependencies=[Depends(get_authz)])
def me(user: UserDep) -> UserSchemaOut:
    return user.dump()
