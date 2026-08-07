from fastapi import APIRouter, Depends

from .dependencies import get_authz, get_user
from .views.action import owner_scoped_router as action_owner_scoped_router
from .views.action import router as action_router
from .views.admin import router as admin_router
from .views.external_resource import router as external_resource_router
from .views.no_op import router as no_op_router
from .views.openshift import router as openshift_router
from .views.user import router as user_router

router = APIRouter()
router.include_router(
    admin_router, dependencies=[Depends(get_user), Depends(get_authz)]
)
router.include_router(
    external_resource_router, dependencies=[Depends(get_user), Depends(get_authz)]
)
router.include_router(
    openshift_router, dependencies=[Depends(get_user), Depends(get_authz)]
)
router.include_router(
    action_router, dependencies=[Depends(get_user), Depends(get_authz)]
)
# action-detail/action-cancel authorize themselves via get_authorized_action
# (which injects the action's owner into the OPA call), not the generic get_authz.
router.include_router(action_owner_scoped_router, dependencies=[Depends(get_user)])
router.include_router(user_router, dependencies=[Depends(get_authz)])
router.include_router(no_op_router, dependencies=[Depends(get_authz)])
