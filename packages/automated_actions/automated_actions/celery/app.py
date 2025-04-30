import logging

from automated_actions.config import settings
from celery import Celery

log = logging.getLogger(__name__)

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
    worker_log_format="[%(asctime)s: GJB] %(message)s",
    # support pydantic models
    task_serializer="pickle",
    result_serializer="pickle",
    event_serializer="json",
    accept_content=["application/json", "application/x-python-serialize"],
    result_accept_content=["application/json", "application/x-python-serialize"],
    include=["automated_actions.celery.openshift.tasks"],
)
