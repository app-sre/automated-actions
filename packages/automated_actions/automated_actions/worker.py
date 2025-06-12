from prometheus_client import start_http_server
from prometheus_client.multiprocess import MultiProcessCollector

# import celery app to start the worker
from automated_actions.celery.app import app  # noqa: F401 # pylint: disable=W0611
from automated_actions.celery.metrics import CELERY_REGISTRY
from automated_actions.config import settings

MultiProcessCollector(CELERY_REGISTRY)
start_http_server(port=settings.worker_metrics_port, registry=CELERY_REGISTRY)
