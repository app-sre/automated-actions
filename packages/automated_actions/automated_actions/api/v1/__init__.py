from fastapi import APIRouter, Depends

from automated_actions.api.models import UserSchemaOut as UserSchemaOut

from .dependencies import UserDep as UserDep
from .dependencies import get_authz, get_user
from .views.noop import router as noop_router
from .views.openshift import router as openshift_router
from .views.task import router as task_router
from .views.user import router as user_router

router = APIRouter()
router.include_router(noop_router, dependencies=[Depends(get_user), Depends(get_authz)])
router.include_router(
    openshift_router, dependencies=[Depends(get_user), Depends(get_authz)]
)
router.include_router(task_router, dependencies=[Depends(get_user), Depends(get_authz)])
router.include_router(user_router, dependencies=[Depends(get_authz)])
