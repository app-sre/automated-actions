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

app = create_app(logging_config=logging_config)
