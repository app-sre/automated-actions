import logging
from typing import Any

from celery.app.log import TaskFormatter as CeleryTaskFormatter
from celery.signals import after_setup_logger

from automated_actions.config import settings
from celery import Celery

# Disable gql transport INFO messages with query dump, they're just noise to us.
logging.getLogger("gql.transport.requests").setLevel(logging.WARNING)

log = logging.getLogger(__name__)


class TaskFormatter(CeleryTaskFormatter):
    """Custom task formatter to include action_id in the log format."""

    def format(self, record: logging.LogRecord) -> str:
        """Format the log record."""
        # set default values for task_name and task_id. These will be overridden
        # by the Celery task name and ID if available.
        record.task_name = record.name
        record.task_id = "unknown"
        return super().format(record)


@after_setup_logger.connect
def setup_loggers(logger: logging.Logger, **_: Any) -> None:
    """Attach a formatted log handler to the logger."""
    for handler in logger.handlers:
        logger.removeHandler(handler)
    handler = logging.StreamHandler()
    handler.setFormatter(
        TaskFormatter(
            "%(asctime)s [%(levelname)s] %(task_name)s action_id=%(task_id)s: %(message)s"
        )
    )
    logger.addHandler(handler)
    logger.setLevel(logging.DEBUG if settings.debug else logging.INFO)


app = Celery(
    "tasks",
    broker=settings.broker_url,
    broker_transport_options={
        "region": settings.broker_aws_region,
        "predefined_queues": {
            "celery": {
                "url": settings.sqs_url,
                "access_key_id": settings.broker_aws_access_key_id,
                "secret_access_key": settings.broker_aws_secret_access_key,
            }
        },
    },
    broker_connection_retry_on_startup=True,
    worker_enable_remote_control=False,
    worker_log_format="%(asctime)s [%(levelname)s] %(name)s %(message)s",
    # support pydantic models
    task_serializer="pickle",
    result_serializer="pickle",
    event_serializer="json",
    accept_content=["application/json", "application/x-python-serialize"],
    result_accept_content=["application/json", "application/x-python-serialize"],
    include=[
        "automated_actions.celery.external_resource.tasks",
        "automated_actions.celery.openshift.tasks",
        "automated_actions.celery.no_op.tasks",
    ],
)
