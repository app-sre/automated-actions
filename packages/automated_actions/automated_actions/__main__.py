import sys

from automated_actions.app_factory import create_app
from automated_actions.config import settings

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

app = create_app(logging_config=logging_config)
