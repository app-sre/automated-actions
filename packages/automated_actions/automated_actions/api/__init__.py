import logging

from fastapi import APIRouter, FastAPI

from automated_actions.api.v1 import router as v1_router
from automated_actions.auth import OPA, BearerTokenAuth, OpenIDConnect
from automated_actions.config import settings
from automated_actions.db.models import ALL_TABLES, User

api_router = APIRouter()
log = logging.getLogger(__name__)


def create_db_tables() -> None:
    """Create DynamoDB tables if they do not exist."""
    log.info("Attempting to create DynamoDB tables if they do not exist...")
    for table_model in ALL_TABLES:
        if not table_model.exists():
            log.info(f"Creating table {table_model.Meta.table_name}...")
            table_model.create_table(
                read_capacity_units=1, write_capacity_units=1, wait=True
            )
            log.info(f"Table {table_model.Meta.table_name} created.")
    log.info("All tables checked.")


async def initialize_auth_components(app: FastAPI) -> None:
    """Initialize authentication and authorization components."""
    log.info("Initializing authentication and authorization components...")
    app.state.oidc = await OpenIDConnect[User].create(  # type: ignore[type-var]
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
    log.info("Auth components initialized.")


def configure_routers(app: FastAPI) -> None:
    """Configure the API routers for the FastAPI app."""
    log.info("Configuring API routers...")
    if (
        hasattr(app.state, "oidc")
        and app.state.oidc
        and hasattr(app.state.oidc, "router")
    ):
        v1_router.include_router(
            app.state.oidc.router, prefix="/auth", tags=["v1-auth"]
        )
    else:
        log.warning(
            "OIDC component or its router not found in app.state. Skipping OIDC router inclusion in v1_router."
        )

    api_router.include_router(v1_router, prefix="/v1", tags=["v1"])
    log.info("API routers configured.")
