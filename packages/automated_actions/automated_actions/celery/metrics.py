from prometheus_client import CollectorRegistry, Histogram

CELERY_REGISTRY = CollectorRegistry()

action_elapsed_time = Histogram(
    name="automated_actions_action_elapsed_seconds",
    documentation="Elapsed seconds since the moment in the action was inserted in the action table, including retries.",
    labelnames=["name", "status"],
    registry=CELERY_REGISTRY,
)
