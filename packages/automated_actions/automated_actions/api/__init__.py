import logging

from fastapi import APIRouter, FastAPI

from automated_actions.api.v1 import router as v1_router
from automated_actions.auth import OPA, BearerTokenAuth, OpenIDConnect
from automated_actions.config import settings
from automated_actions.db.models import ALL_TABLES, User

router = APIRouter()
log = logging.getLogger(__name__)


def startup_hook(app: FastAPI) -> None:
    """Startup hook."""
    log.info("API startup hook")

    for table in ALL_TABLES:
        # create pynamodb tables
        if not table.exists():
            table.create_table(read_capacity_units=1, write_capacity_units=1, wait=True)

    app.state.oidc = OpenIDConnect[User](  # type: ignore[type-var]
        issuer=settings.oidc_issuer,
        client_id=settings.oidc_client_id,
        client_secret=settings.oidc_client_secret,
        session_secret=settings.session_secret,
        session_timeout_secs=settings.session_timeout_secs,
        enforce_https=not settings.debug,
        user_model=User,
    )
    app.state.token = BearerTokenAuth[User](  # type: ignore[type-var]
        issuer=settings.url, secret=settings.token_secret, user_model=User
    )
    app.state.authz = OPA[User](opa_host=settings.opa_host, package_name="authz")  # type: ignore[type-var]
    v1_router.include_router(app.state.oidc.router, prefix="/auth")
    router.include_router(v1_router, prefix="/v1", tags=["v1"])
