import logging
import logging.config
import socket
import sys
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from importlib.metadata import version

from fastapi import APIRouter, FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from prometheus_fastapi_instrumentator import Instrumentator

from automated_actions.api import router
from automated_actions.api import startup_hook as api_startup_hook
from automated_actions.config import settings

HOSTNAME = socket.gethostname()
default_router = APIRouter()
log = logging.getLogger(__name__)

logging_config = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "default": {
            "format": "%(levelname)-9s %(message)s",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "default",
            "stream": sys.stdout,
        },
    },
    "root": {
        "handlers": ["console"],
        "level": "INFO",
    },
    "automated-actions": {
        "handlers": ["console"],
        "level": "DEBUG" if settings.debug else "INFO",
    },
    "loggers": {
        "automated_actions": {
            "handlers": ["console"],
            "propagate": False,
        },
    },
}


@default_router.get("/healthz", include_in_schema=False)
async def healthz() -> str:
    """Kubernetes readiness check."""
    return HOSTNAME


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:  # noqa: RUF029
    """Startup and shutdown events."""
    logging.config.dictConfig(logging_config)
    log.info("Starting Automated Actions")
    api_startup_hook(app)

    # init routers after the sub apps startup hooks!
    app.include_router(default_router)
    app.include_router(router, prefix="/api")

    yield
    log.info("Shutting down Automated Actions")


app = FastAPI(
    title="Automated Actions",
    description="Run automated actions",
    version=version("automated-actions"),
    debug=settings.debug,
    root_path=settings.root_path,
    openapi_url="/docs/openapi.json",
    lifespan=lifespan,
)
instrumentator = Instrumentator(
    excluded_handlers=[
        "/metrics",
        "/healthz",
    ]
).instrument(app)

instrumentator.expose(app, include_in_schema=False)


@app.exception_handler(RequestValidationError)
def validation_exception_handler(
    _: Request, exc: RequestValidationError
) -> JSONResponse:
    exc_str = f"{exc}".replace("\n", " ").replace("   ", " ")
    log.error(f"validation error: {exc_str}")
    content = {"status_code": 422, "message": exc_str, "data": None}
    return JSONResponse(
        content=content, status_code=status.HTTP_422_UNPROCESSABLE_ENTITY
    )
