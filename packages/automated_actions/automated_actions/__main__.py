from typing import Any

from fastapi.openapi.utils import get_openapi

from automated_actions.app_factory import create_app
from automated_actions.config import settings

log_level = "DEBUG" if settings.debug else "INFO"

logging_config = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "default": {
            "()": "uvicorn.logging.DefaultFormatter",
            "fmt": "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        },
        "access": {
            "()": "uvicorn.logging.AccessFormatter",
            "fmt": "%(asctime)s [%(levelname)s] %(client_addr)s - %(request_line)s %(status_code)s",
        },
    },
    "handlers": {
        "default": {
            "formatter": "default",
            "class": "logging.StreamHandler",
            "stream": "ext://sys.stderr",
        },
        "access": {
            "formatter": "access",
            "class": "logging.StreamHandler",
            "stream": "ext://sys.stdout",
        },
    },
    "loggers": {
        "": {  # root logger
            "level": log_level,
            "handlers": ["default"],
            "propagate": False,
        },
        "uvicorn": {
            "handlers": ["default"],
            "level": log_level,
            "propagate": False,
        },
        "uvicorn.error": {"level": log_level},
        "uvicorn.access": {
            "handlers": ["access"],
            "level": log_level,
            "propagate": False,
        },
    },
}


def custom_openapi() -> dict[str, Any]:
    if app.openapi_schema:
        return app.openapi_schema
    openapi_schema = get_openapi(
        title="Automated Actions API",
        version="1.0.0",
        summary="Automated Actions API OpenAPI schema",
        description="REST API for Automated Actions integrations",
        routes=app.routes,
    )
    # get rid of the default Validation Error (422) response added by FastAPI
    # otherwise automated-actions-client lists them as possible responses for all endpoints ... very annoying!
    for path in openapi_schema["paths"].values():
        for operation in path.values():
            responses = operation.get("responses", {})
            if "422" in responses:
                del responses["422"]
    app.openapi_schema = openapi_schema
    return app.openapi_schema


app = create_app(logging_config=logging_config)

# See https://fastapi.tiangolo.com/how-to/extending-openapi/#override-the-method for details
app.openapi = custom_openapi  # type: ignore[method-assign]
