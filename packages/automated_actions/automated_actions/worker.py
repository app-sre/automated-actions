from prometheus_client import start_http_server

# import celery app to start the worker
from automated_actions.celery.app import app  # noqa: F401 # pylint: disable=W0611
from automated_actions.config import settings

start_http_server(settings.worker_metrics_port)
