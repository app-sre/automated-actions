from prometheus_client import CollectorRegistry, Histogram
from prometheus_client.utils import INF

CELERY_REGISTRY = CollectorRegistry()

action_elapsed_time = Histogram(
    name="automated_actions_action_elapsed_seconds",
    documentation="Elapsed seconds since the moment in the action was inserted in the action table, including retries.",
    labelnames=["name", "status"],
    registry=CELERY_REGISTRY,
    buckets=(
        0.05,
        0.075,
        0.1,
        0.33,
        0.66,
        1.0,
        2.0,
        4.0,
        6.0,
        8.0,
        10.0,
        15.0,
        20.0,
        30.0,
        INF,
    ),
)
