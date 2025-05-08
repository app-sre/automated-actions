import logging
import logging.config
import socket
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from importlib.metadata import version

from fastapi import APIRouter as FastAPIAPIRouter
from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from prometheus_fastapi_instrumentator import Instrumentator

from automated_actions.api import (
    api_router,
    configure_routers,
    create_db_tables,
    initialize_auth_components,
)
from automated_actions.config import settings

log = logging.getLogger(__name__)


@asynccontextmanager
async def app_lifespan_manager(
    app: FastAPI,
    *,
    run_db_init: bool = True,
    run_auth_init: bool = True,
    run_router_config: bool = True,
) -> AsyncGenerator[None, None]:
    log.info("Lifespan: Application startup sequence initiated.")

    if run_db_init:
        log.info("Lifespan: Executing database tables creation...")
        create_db_tables()

    if run_auth_init:
        log.info("Lifespan: Initializing authentication components...")
        await initialize_auth_components(app)

    # Router-Konfiguration und -Einbindung
    default_router = FastAPIAPIRouter()
    hostname = socket.gethostname()

    @default_router.get("/healthz", include_in_schema=False)
    async def healthz() -> str:
        return hostname

    app.include_router(default_router)

    if run_router_config:
        log.info("Lifespan: Configuring main API routers...")
        configure_routers(app)
        app.include_router(api_router, prefix="/api")

    log.info("Lifespan: Application startup complete.")
    yield
    log.info("Lifespan: Application shutdown sequence initiated.")


def create_app(
    *,
    logging_config: dict | None = None,
    run_db_init: bool = True,
    run_auth_init: bool = True,
    run_router_config: bool = True,
) -> FastAPI:
    @asynccontextmanager
    async def lifespan(app_instance: FastAPI) -> AsyncGenerator[None, None]:
        async with app_lifespan_manager(
            app_instance,
            run_db_init=run_db_init,
            run_auth_init=run_auth_init,
            run_router_config=run_router_config,
        ):
            yield

    if logging_config:
        logging.config.dictConfig(logging_config)

    app_instance = FastAPI(
        title="Automated Actions",
        description="Run automated actions",
        version=version("automated-actions"),
        debug=settings.debug,
        root_path=settings.root_path,
        openapi_url="/docs/openapi.json",
        lifespan=lifespan,
    )

    Instrumentator(excluded_handlers=["/metrics", "/healthz"]).instrument(
        app_instance
    ).expose(app_instance, include_in_schema=False)

    @app_instance.exception_handler(RequestValidationError)
    def validation_exception_handler(
        _: Request, exc: RequestValidationError
    ) -> JSONResponse:
        exc_str = f"{exc}".replace("\n", " ").replace("   ", " ")
        log.error(f"Validation error: {exc_str}")
        content = {"status_code": 422, "message": exc_str, "data": None}
        return JSONResponse(
            content=content, status_code=status.HTTP_422_UNPROCESSABLE_ENTITY
        )

    return app_instance
