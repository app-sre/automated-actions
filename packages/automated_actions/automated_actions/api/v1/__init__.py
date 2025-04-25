from fastapi import APIRouter, Depends

from automated_actions.db.models import UserSchemaOut as UserSchemaOut  # noqa: PLC0414

from .dependencies import UserDep as UserDep  # noqa: PLC0414
from .dependencies import get_authz, get_user
from .views.action import router as action_router
from .views.noop import router as noop_router
from .views.openshift import router as openshift_router
from .views.user import router as user_router

router = APIRouter()
router.include_router(noop_router, dependencies=[Depends(get_user), Depends(get_authz)])
router.include_router(
    openshift_router, dependencies=[Depends(get_user), Depends(get_authz)]
)
router.include_router(action_router, dependencies=[Depends(get_user), Depends(get_authz)])
router.include_router(user_router, dependencies=[Depends(get_authz)])
