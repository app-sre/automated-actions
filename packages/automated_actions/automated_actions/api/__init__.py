import logging

from fastapi import APIRouter, FastAPI

from automated_actions.api.v1.auth import initialize_authz
from automated_actions.auth import OpenIDConnect
from automated_actions.config import settings

from .models import ALL_TABLES, User
from .v1 import router as v1_router

router = APIRouter()
log = logging.getLogger(__name__)


def startup_hook(app: FastAPI) -> None:
    """Startup hook."""
    log.info("API startup hook")

    for table in ALL_TABLES:
        # create pynamodb tables
        if not table.exists():
            table.create_table(read_capacity_units=1, write_capacity_units=1, wait=True)

    app.state.oidc = OpenIDConnect[User](
        issuer=settings.oidc_issuer,
        client_id=settings.oidc_client_id,
        client_secret=settings.oidc_client_secret,
        session_secret=settings.session_secret,
        enforce_https=not settings.debug,
        user_model=User,
    )
    app.state.authz = initialize_authz()
    v1_router.include_router(app.state.oidc.router, prefix="/auth")
    router.include_router(v1_router, prefix="/v1", tags=["v1"])
