from prometheus_client import CollectorRegistry, Histogram

CELERY_REGISTRY = CollectorRegistry()

action_elapsed_time = Histogram(
    name="automated_actions_action_elapsed_seconds",
    documentation="Elapsed seconds since the moment in the action was inserted in the action table, including retries.",
    labelnames=["name", "status"],
    registry=CELERY_REGISTRY,
    buckets=(.05, .075, .1, .33, .66, 1.0, 2.0, 4.0, 6.0, 8.0, 10.0, 15.0, 20.0, 30.0, INF)
)
